import os
import threading
import time
from flask import Flask, request, jsonify, Response
from werkzeug.serving import make_server
import xml.etree.ElementTree as ET
from objects import NodoOptimizado, LectorXML
import socket


class GestorNodos:
    def __init__(self):
        self.nodos_activos = {}
        self.capacidad_maxima = 100000
        self.estado = "disponible"
        self.imagenes_procesando = 0
        self.lock = threading.Lock()
    
    def procesar_xml_imagenes(self, xml_content, aplicar_transformaciones=True):
        """
        Procesa un XML con múltiples imágenes y aplica transformaciones.
        Retorna XML fusionado con todas las imágenes procesadas.
        """
        num_imagenes = 0
        try:
            root = ET.fromstring(xml_content)
            imagenes = root.findall('imagen')
            num_imagenes = len(imagenes)
            
            if not imagenes:
                return self._crear_xml_error("No se encontraron imágenes en el XML")
        except:
            return self._crear_xml_error("XML malformado")
        
        with self.lock:
            if self.imagenes_procesando + num_imagenes > self.capacidad_maxima:
                return self._crear_xml_error("Capacidad máxima excedida")
            self.imagenes_procesando += num_imagenes
            self.estado = "procesando"
        
        try:
            # Crear XML de respuesta fusionado
            root_respuesta = ET.Element("imagenes_procesadas")
            root_respuesta.set("total_procesadas", "0")
            root_respuesta.set("total_errores", "0")
            
            xmls_temporales = []
            nodos_procesados = []
            
            # Procesar cada imagen
            for i, imagen_elem in enumerate(imagenes):
                datos_b64 = imagen_elem.text
                transformaciones = imagen_elem.get('transformaciones', '')
                formato = imagen_elem.get('formato', 'JPEG')
                
                if not datos_b64:
                    continue
                
                temp_xml = f"temp_batch_{int(time.time())}_{i}.xml"
                xmls_temporales.append(temp_xml)
                
                try:
                    # Crear XML temporal
                    temp_root = ET.Element("imagenes")
                    temp_imagen = ET.SubElement(temp_root, "imagen", {
                        "formato": formato,
                        "transformaciones": transformaciones
                    })
                    temp_imagen.text = datos_b64
                    
                    temp_tree = ET.ElementTree(temp_root)
                    temp_tree.write(temp_xml, encoding="utf-8", xml_declaration=True)
                    
                    # Cargar con NodoOptimizado
                    nodo = NodoOptimizado(temp_xml)
                    
                    if aplicar_transformaciones and transformaciones:
                        # Aplicar transformaciones existentes
                        trans_list = transformaciones.split(', ')
                        for trans in trans_list:
                            if 'escala_grises' in trans:
                                nodo.escala_grises()
                            elif 'rotar' in trans:
                                angle = 45
                                if '_' in trans:
                                    try:
                                        angle = int(trans.split('_')[-1].replace('°', ''))
                                    except:
                                        pass
                                nodo.rotar(angle)
                            elif 'redimensionar' in trans:
                                if 'x' in trans:
                                    try:
                                        dims = trans.split('_')[1].split('x')
                                        size = (int(dims[0]), int(dims[1]))
                                        nodo.redimensionar(size)
                                    except:
                                        nodo.redimensionar()
                    
                    nodos_procesados.append(nodo)
                    
                except Exception as e:
                    print(f"Error procesando imagen {i}: {e}")
                    error_imagen = ET.SubElement(root_respuesta, "imagen")
                    error_imagen.set("error", str(e))
                    error_imagen.set("indice_original", str(i))
            
            # Fusionar todos los nodos procesados en un solo XML
            procesadas = 0
            errores = int(root_respuesta.get("total_errores", "0"))
            
            for j, nodo in enumerate(nodos_procesados):
                try:
                    temp_output = f"temp_output_batch_{int(time.time())}_{j}.xml"
                    xmls_temporales.append(temp_output)
                    
                    nodo.generar_xml_optimizado(temp_output, "JPEG", calidad=80)
                    
                    # Leer y fusionar
                    output_tree = ET.parse(temp_output)
                    output_imagen = output_tree.getroot().find('imagen')
                    
                    if output_imagen is not None:
                        nueva_imagen = ET.SubElement(root_respuesta, "imagen")
                        nueva_imagen.attrib.update(output_imagen.attrib)
                        nueva_imagen.set("indice_procesado", str(j))
                        nueva_imagen.text = output_imagen.text
                        procesadas += 1
                        
                except Exception as e:
                    print(f"Error fusionando imagen {j}: {e}")
                    errores += 1
            
            # Actualizar contadores
            root_respuesta.set("total_procesadas", str(procesadas))
            root_respuesta.set("total_errores", str(errores))
            
            # Limpiar archivos temporales
            for temp_file in xmls_temporales:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass
            
            return ET.tostring(root_respuesta, encoding='unicode')
            
        except Exception as e:
            return self._crear_xml_error(f"Error general: {str(e)}")
        
        finally:
            with self.lock:
                self.imagenes_procesando -= num_imagenes
                if self.imagenes_procesando == 0:
                    self.estado = "disponible"
    
    def procesar_xml_transformaciones(self, xml_content, transformaciones_extra=None):
        """
        Procesa XML aplicando transformaciones específicas.
        """
        return self.procesar_xml_imagenes(xml_content, aplicar_transformaciones=True)
    
    def convertir_imagen_unica(self, xml_content, formato_salida="JPEG", calidad=85):
        """
        Convierte una sola imagen y la devuelve.
        """
        try:
            root = ET.fromstring(xml_content)
            imagenes = root.findall('imagen')
            
            if len(imagenes) != 1:
                return self._crear_xml_error("Solo se acepta una imagen")
            
            imagen_elem = imagenes[0]
            datos_b64 = imagen_elem.text
            
            if not datos_b64:
                return self._crear_xml_error("No hay datos de imagen")
            
            with self.lock:
                if self.imagenes_procesando >= self.capacidad_maxima:
                    return self._crear_xml_error("Capacidad máxima excedida")
                self.imagenes_procesando += 1
                self.estado = "procesando"
            
            temp_xml = f"temp_single_{int(time.time())}.xml"
            temp_output = f"temp_single_out_{int(time.time())}.xml"
            
            try:
                # Crear XML temporal
                temp_root = ET.Element("imagenes")
                temp_imagen = ET.SubElement(temp_root, "imagen", {
                    "formato": imagen_elem.get('formato', 'JPEG')
                })
                temp_imagen.text = datos_b64
                
                temp_tree = ET.ElementTree(temp_root)
                temp_tree.write(temp_xml, encoding="utf-8", xml_declaration=True)
                
                # Procesar
                nodo = NodoOptimizado(temp_xml)
                nodo.generar_xml_optimizado(temp_output, formato_salida, calidad)
                
                # Leer resultado
                output_tree = ET.parse(temp_output)
                output_imagen = output_tree.getroot().find('imagen')
                
                # Crear respuesta
                root_respuesta = ET.Element("imagen_convertida")
                nueva_imagen = ET.SubElement(root_respuesta, "imagen")
                nueva_imagen.attrib.update(output_imagen.attrib)
                nueva_imagen.text = output_imagen.text
                
                # Limpiar
                for temp_file in [temp_xml, temp_output]:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                
                return ET.tostring(root_respuesta, encoding='unicode')
                
            except Exception as e:
                return self._crear_xml_error(f"Error convertiendo: {str(e)}")
            
            finally:
                with self.lock:
                    self.imagenes_procesando -= 1
                    if self.imagenes_procesando == 0:
                        self.estado = "disponible"
                        
        except Exception as e:
            return self._crear_xml_error(f"Error procesando XML: {str(e)}")
    
    def obtener_estado(self):
        """Retorna el estado actual del gestor."""
        with self.lock:
            return {
                "estado": self.estado,
                "imagenes_procesando": self.imagenes_procesando,
                "capacidad_maxima": self.capacidad_maxima,
                "capacidad_disponible": self.capacidad_maxima - self.imagenes_procesando,
                "disponible": self.imagenes_procesando < self.capacidad_maxima
            }
    
    def _crear_xml_error(self, mensaje_error):
        """Crea un XML de respuesta con error."""
        root = ET.Element("error")
        root.text = mensaje_error
        return ET.tostring(root, encoding='unicode')


# Instancia global del gestor
gestor = GestorNodos()

# Crear aplicaciones Flask para cada puerto
app_8001 = Flask(__name__)
app_8002 = Flask(__name__)
app_8003 = Flask(__name__)
app_8004 = Flask(__name__)


# Puerto 8001: Procesamiento básico de imágenes
@app_8001.route('/procesar', methods=['POST'])
def procesar_imagenes():
    try:
        if request.content_type == 'application/xml' or request.content_type == 'text/xml':
            xml_content = request.data.decode('utf-8')
        else:
            xml_content = request.get_data(as_text=True)
        
        if not xml_content:
            return Response(
                gestor._crear_xml_error("No se recibió contenido XML"),
                mimetype='application/xml',
                status=400
            )
        
        # Verificar capacidad
        estado = gestor.obtener_estado()
        if not estado["disponible"]:
            return Response(
                gestor._crear_xml_error("Servidor saturado, intente más tarde"),
                mimetype='application/xml',
                status=503
            )
        
        resultado = gestor.procesar_xml_imagenes(xml_content)
        
        return Response(
            resultado,
            mimetype='application/xml',
            status=200
        )
        
    except Exception as e:
        return Response(
            gestor._crear_xml_error(f"Error del servidor: {str(e)}"),
            mimetype='application/xml',
            status=500
        )


# Puerto 8002: Procesamiento con transformaciones específicas
@app_8002.route('/transformar', methods=['POST'])
def transformar_imagenes():
    try:
        if request.content_type == 'application/xml' or request.content_type == 'text/xml':
            xml_content = request.data.decode('utf-8')
        else:
            xml_content = request.get_data(as_text=True)
        
        if not xml_content:
            return Response(
                gestor._crear_xml_error("No se recibió contenido XML"),
                mimetype='application/xml',
                status=400
            )
        
        # Verificar capacidad
        estado = gestor.obtener_estado()
        if not estado["disponible"]:
            return Response(
                gestor._crear_xml_error("Servidor saturado, intente más tarde"),
                mimetype='application/xml',
                status=503
            )
        
        resultado = gestor.procesar_xml_transformaciones(xml_content)
        
        return Response(
            resultado,
            mimetype='application/xml',
            status=200
        )
        
    except Exception as e:
        return Response(
            gestor._crear_xml_error(f"Error del servidor: {str(e)}"),
            mimetype='application/xml',
            status=500
        )


# Puerto 8004: Conversión de imagen única
@app_8004.route('/convertir', methods=['POST'])
def convertir_imagen_unica():
    try:
        if request.content_type == 'application/xml' or request.content_type == 'text/xml':
            xml_content = request.data.decode('utf-8')
        else:
            xml_content = request.get_data(as_text=True)
        
        if not xml_content:
            return Response(
                gestor._crear_xml_error("No se recibió contenido XML"),
                mimetype='application/xml',
                status=400
            )
        
        # Obtener parámetros de formato y calidad
        formato = request.args.get('formato', 'JPEG').upper()
        calidad = int(request.args.get('calidad', 85))
        
        # Validar formato
        if formato not in ['JPEG', 'PNG', 'WEBP']:
            return Response(
                gestor._crear_xml_error("Formato no soportado. Use: JPEG, PNG, WEBP"),
                mimetype='application/xml',
                status=400
            )
        
        resultado = gestor.convertir_imagen_unica(xml_content, formato, calidad)
        
        return Response(
            resultado,
            mimetype='application/xml',
            status=200
        )
        
    except ValueError:
        return Response(
            gestor._crear_xml_error("Parámetro calidad debe ser un número"),
            mimetype='application/xml',
            status=400
        )
    except Exception as e:
        return Response(
            gestor._crear_xml_error(f"Error del servidor: {str(e)}"),
            mimetype='application/xml',
            status=500
        )


# Puerto 8003: Consulta de estado
@app_8003.route('/estado', methods=['GET'])
def consultar_estado():
    try:
        estado = gestor.obtener_estado()
        return jsonify(estado)
        
    except Exception as e:
        return jsonify({
            "error": f"Error al obtener estado: {str(e)}"
        }), 500


@app_8003.route('/salud', methods=['GET'])
def check_health():
    return jsonify({
        "status": "healthy",
        "service": "Gestor de Nodos de Imagen",
        "timestamp": time.time()
    })


def ejecutar_servidor(app, puerto):
    """Ejecuta un servidor Flask en la IP local del PC y un puerto específico."""
    ip_local = socket.gethostbyname(socket.gethostname())
    server = make_server(ip_local, puerto, app)
    print(f"✅ Servidor iniciado en {ip_local}:{puerto}")
    server.serve_forever()

def main():
    """Función principal que inicia todos los servidores."""
    print("🚀 Iniciando Gestor de Nodos de Imagen...")
    print("=" * 50)
    
    # Crear hilos para cada servidor
    servidor_8001 = threading.Thread(
        target=ejecutar_servidor, 
        args=(app_8001, 8001),
        daemon=True
    )
    
    servidor_8002 = threading.Thread(
        target=ejecutar_servidor, 
        args=(app_8002, 8002),
        daemon=True
    )
    
    servidor_8003 = threading.Thread(
        target=ejecutar_servidor, 
        args=(app_8003, 8003),
        daemon=True
    )
    
    servidor_8004 = threading.Thread(
        target=ejecutar_servidor,
        args=(app_8004, 8004), 
        daemon=True
    )
    
    # Iniciar todos los servidores
    servidor_8001.start()
    servidor_8002.start() 
    servidor_8003.start()
    servidor_8004.start()
    
    print("📡 Servicios disponibles:")
    print("  • Puerto 8001: POST /procesar - Procesamiento batch N imágenes")
    print("  • Puerto 8002: POST /transformar - Transformaciones batch N imágenes")
    print("  • Puerto 8003: GET /estado - Estado del servidor")
    print("  • Puerto 8003: GET /salud - Health check")
    print("  • Puerto 8004: POST /convertir - Conversión imagen única")
    print(f"\n⚡ Capacidad: {gestor.capacidad_maxima:,} imágenes simultáneas")
    print("⚡ Servidores ejecutándose... (Ctrl+C para detener)")
    
    try:
        # Mantener el programa principal vivo
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo servidores...")
        print("✅ Servidores detenidos")


if __name__ == "__main__":
    main()