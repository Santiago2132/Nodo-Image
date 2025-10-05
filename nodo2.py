import os
import threading
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.serving import make_server
import xml.etree.ElementTree as ET
from objects import NodoOptimizado
import socket
import subprocess
import re
import json
import xmlrpc.server
import xmlrpc.client
from socketserver import ThreadingMixIn

def obtener_ip_real():
    """Obtiene la IP real de la máquina en la red local."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            if not ip.startswith("127."):
                return ip
    except:
        pass
    
    try:
        result = subprocess.run(['ip', 'route', 'get', '8.8.8.8'], 
                              capture_output=True, text=True, timeout=3)
        match = re.search(r'src (\d+\.\d+\.\d+\.\d+)', result.stdout)
        if match:
            return match.group(1)
    except:
        pass
    
    try:
        result = subprocess.run(['hostname', '-I'], 
                              capture_output=True, text=True, timeout=3)
        ips = result.stdout.strip().split()
        for ip in ips:
            if not ip.startswith("127.") and "." in ip:
                return ip
    except:
        pass
    
    try:
        ip = socket.gethostbyname(socket.gethostname())
        if not ip.startswith("127."):
            return ip
    except:
        pass
    
    return "127.0.0.1"

BALANCEADOR_IP = "192.168.154.129"
BALANCEADOR_RPC_URL = f"http://{BALANCEADOR_IP}:8000"

class ThreadedXMLRPCServer(ThreadingMixIn, xmlrpc.server.SimpleXMLRPCServer):
    pass

class GestorNodos:
    def __init__(self):
        self.capacidad_maxima = 100000
        self.estado = "disponible"
        self.imagenes_procesando = 0
        self.lock = threading.Lock()
    
    def _crear_xml_error(self, mensaje_error):
        """Crea un XML de respuesta con error."""
        root = ET.Element("error")
        root.text = mensaje_error
        return ET.tostring(root, encoding='unicode')
    
    def _procesar_imagen_individual(self, imagen_elem, indice, aplicar_transformaciones):
        """Procesa una imagen individual y retorna el nodo procesado o None si falla."""
        datos_b64 = imagen_elem.text
        transformaciones = imagen_elem.get('transformaciones', '')
        formato = imagen_elem.get('formato', 'JPEG').upper()
        
        if not datos_b64:
            return None, f"Sin datos en imagen {indice}"
        
        temp_xml = f"temp_batch_{int(time.time())}_{indice}.xml"
        
        try:
            # Crear XML temporal con formato original
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
                self._aplicar_transformaciones(nodo, transformaciones)
            
            return nodo, None
            
        except Exception as e:
            return None, str(e)
        finally:
            if os.path.exists(temp_xml):
                try:
                    os.remove(temp_xml)
                except:
                    pass
    
    def _aplicar_transformaciones(self, nodo, transformaciones_str):
        """Aplica transformaciones a un nodo."""
        trans_list = transformaciones_str.split(', ')
        
        for trans in trans_list:
            try:
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
                elif 'reflejar' in trans:
                    direccion = trans.split('_')[1] if '_' in trans else 'horizontal'
                    nodo.reflejar(direccion)
                elif 'desenfocar' in trans:
                    radio = int(trans.split('_')[-1]) if '_' in trans else 2
                    nodo.desenfocar(radio)
                elif 'perfilar' in trans:
                    factor = float(trans.split('_')[-1]) if '_' in trans else 2.0
                    nodo.perfilar(factor)
                elif 'ajustar_brillo' in trans:
                    parts = trans.split('_')
                    brillo = float(parts[2]) if len(parts) > 2 else 1.0
                    contraste = float(parts[4]) if len(parts) > 4 else 1.0
                    nodo.ajustar_brillo_contraste(brillo, contraste)
                elif 'insertar_texto' in trans:
                    texto = trans.split('_', 2)[2] if '_' in trans else "Marca"
                    nodo.insertar_texto(texto)
                elif 'convertir_a' in trans:
                    formato = trans.split('_')[-1].upper()
                    nodo.convertir_formato(formato)
            except Exception as e:
                print(f"Error aplicando transformación {trans}: {e}")
    
    def _fusionar_nodo_a_xml(self, nodo, root_respuesta, indice, formato_salida, calidad):
        """Fusiona el resultado de un nodo al XML de respuesta."""
        temp_output = f"temp_output_batch_{int(time.time())}_{indice}.xml"
        
        try:
            nodo.generar_xml_optimizado(temp_output, formato_salida, calidad)
            
            output_tree = ET.parse(temp_output)
            output_imagen = output_tree.getroot().find('imagen')
            
            if output_imagen is not None:
                nueva_imagen = ET.SubElement(root_respuesta, "imagen")
                nueva_imagen.attrib.update(output_imagen.attrib)
                nueva_imagen.set("indice_procesado", str(indice))
                nueva_imagen.text = output_imagen.text
                return True
            return False
            
        except Exception as e:
            print(f"Error fusionando imagen {indice}: {e}")
            return False
        finally:
            if os.path.exists(temp_output):
                try:
                    os.remove(temp_output)
                except:
                    pass
    
    def procesar_xml_imagenes(self, xml_content, aplicar_transformaciones=True):
        """Procesa XML con múltiples imágenes y aplica transformaciones."""
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
            root_respuesta = ET.Element("imagenes_procesadas")
            root_respuesta.set("total_procesadas", "0")
            root_respuesta.set("total_errores", "0")
            
            nodos_procesados = []
            formatos_originales = []
            
            # Procesar cada imagen
            for i, imagen_elem in enumerate(imagenes):
                formato_deseado = imagen_elem.get('formato', 'JPEG').upper()
                formatos_originales.append(formato_deseado)
                
                nodo, error = self._procesar_imagen_individual(imagen_elem, i, aplicar_transformaciones)
                
                if error:
                    error_imagen = ET.SubElement(root_respuesta, "imagen")
                    error_imagen.set("error", error)
                    error_imagen.set("indice_original", str(i))
                else:
                    nodos_procesados.append((nodo, formato_deseado))
            
            # Fusionar nodos procesados
            procesadas = 0
            errores = 0
            
            for j, (nodo, formato_original) in enumerate(nodos_procesados):
                if self._fusionar_nodo_a_xml(nodo, root_respuesta, j, formato_original, 80):
                    procesadas += 1
                else:
                    errores += 1
            
            root_respuesta.set("total_procesadas", str(procesadas))
            root_respuesta.set("total_errores", str(errores + (num_imagenes - len(nodos_procesados))))
            
            return ET.tostring(root_respuesta, encoding='unicode')
            
        except Exception as e:
            return self._crear_xml_error(f"Error general: {str(e)}")
        finally:
            with self.lock:
                self.imagenes_procesando -= num_imagenes
                if self.imagenes_procesando == 0:
                    self.estado = "disponible"
    
    def procesar_xml_transformaciones(self, xml_content, transformaciones_extra=None):
        """Procesa XML aplicando transformaciones específicas."""
        return self.procesar_xml_imagenes(xml_content, aplicar_transformaciones=True)
    
    def convertir_imagen_unica(self, xml_content, formato_salida="JPEG", calidad=85):
        """Convierte una sola imagen."""
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
                temp_root = ET.Element("imagenes")
                temp_imagen = ET.SubElement(temp_root, "imagen", {
                    "formato": imagen_elem.get('formato', 'JPEG')
                })
                temp_imagen.text = datos_b64
                
                temp_tree = ET.ElementTree(temp_root)
                temp_tree.write(temp_xml, encoding="utf-8", xml_declaration=True)
                
                nodo = NodoOptimizado(temp_xml)
                nodo.generar_xml_optimizado(temp_output, formato_salida.upper(), calidad)
                
                output_tree = ET.parse(temp_output)
                output_imagen = output_tree.getroot().find('imagen')
                
                root_respuesta = ET.Element("imagen_convertida")
                nueva_imagen = ET.SubElement(root_respuesta, "imagen")
                nueva_imagen.attrib.update(output_imagen.attrib)
                nueva_imagen.text = output_imagen.text
                
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


class RPCNodoService:
    """Servicio RPC para el nodo"""
    def __init__(self, gestor):
        self.gestor = gestor
    
    def ping(self):
        return "pong"
    
    def _procesar_con_validacion(self, xml_content, metodo_procesamiento):
        """Método común para procesar con validación de estado."""
        try:
            estado = self.gestor.obtener_estado()
            if not estado["disponible"]:
                return json.dumps({
                    "success": False,
                    "error": "Servidor saturado, intente más tarde"
                })
            
            resultado = metodo_procesamiento(xml_content)
            
            if resultado.startswith("<error>"):
                return json.dumps({
                    "success": False,
                    "error": resultado
                })
            
            return json.dumps({
                "success": True,
                "xml_result": resultado
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Error del servidor: {str(e)}"
            })
    
    def procesar_imagenes(self, xml_content):
        return self._procesar_con_validacion(
            xml_content, 
            self.gestor.procesar_xml_imagenes
        )
    
    def transformar_imagenes(self, xml_content):
        return self._procesar_con_validacion(
            xml_content,
            self.gestor.procesar_xml_transformaciones
        )
    
    def convertir_imagen_unica(self, xml_content, formato_salida="JPEG", calidad=85):
        try:
            if formato_salida.upper() not in ['JPEG', 'PNG', 'WEBP']:
                return json.dumps({
                    "success": False,
                    "error": "Formato no soportado. Use: JPEG, PNG, WEBP"
                })
            
            resultado = self.gestor.convertir_imagen_unica(
                xml_content, 
                formato_salida.upper(), 
                calidad
            )
            
            if resultado.startswith("<error>"):
                return json.dumps({
                    "success": False,
                    "error": resultado
                })
            
            return json.dumps({
                "success": True,
                "xml_result": resultado
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Error del servidor: {str(e)}"
            })
    
    def obtener_estado(self):
        try:
            estado = self.gestor.obtener_estado()
            return json.dumps(estado)
        except Exception as e:
            return json.dumps({
                "error": f"Error al obtener estado: {str(e)}"
            })


def registrar_nodo_en_balanceador_rpc(ip_nodo):
    """Registra el nodo en el balanceador de cargas via RPC"""
    try:
        datos_registro = {
            "encendido": "true",
            "ip": ip_nodo,
            "puertos": [9000],
            "servicios": {
                "9000": "nodo_rpc_service"
            },
            "capacidad_maxima": 100000
        }
        
        print(f"🔌 Intentando registrar nodo {ip_nodo} en balanceador RPC {BALANCEADOR_RPC_URL}")
        
        balanceador_client = xmlrpc.client.ServerProxy(BALANCEADOR_RPC_URL)
        resultado = balanceador_client.registrar_nodo(json.dumps(datos_registro))
        
        if resultado:
            print(f"✅ Nodo registrado exitosamente en balanceador: {ip_nodo}")
        else:
            print(f"⚠️ Error al registrar nodo en balanceador")
            
    except Exception as e:
        print(f"❌ Error conectando con balanceador RPC: {e}")
        print(f"   Verificar que el balanceador esté ejecutándose en {BALANCEADOR_IP}:8000")


def iniciar_servidor_rpc_nodo(ip, puerto=9000):
    """Inicia el servidor RPC del nodo"""
    try:
        server = ThreadedXMLRPCServer((ip, puerto), allow_none=True)
        server.register_introspection_functions()
        
        rpc_service = RPCNodoService(gestor)
        server.register_instance(rpc_service)
        
        print(f"✅ Servidor RPC del nodo iniciado en {ip}:{puerto}")
        server.serve_forever()
    except Exception as e:
        print(f"❌ Error iniciando servidor RPC del nodo: {e}")


gestor = GestorNodos()

app = Flask(__name__)
CORS(app, origins="*", allow_headers=["Content-Type", "Authorization"], methods=["GET", "POST", "OPTIONS"])

@app.route('/estado', methods=['GET'])
def consultar_estado():
    try:
        estado = gestor.obtener_estado()
        return jsonify(estado)
    except Exception as e:
        return jsonify({
            "error": f"Error al obtener estado: {str(e)}"
        }), 500

@app.route('/salud', methods=['GET'])
def check_health():
    return jsonify({
        "status": "healthy",
        "service": "Gestor de Nodos RPC de Imagen",
        "timestamp": time.time()
    })


def ejecutar_servidor_rest(app, puerto, ip_local):
    """Ejecuta servidor REST opcional."""
    try:
        server = make_server(ip_local, puerto, app)
        print(f"✅ Servidor REST opcional iniciado en {ip_local}:{puerto}")
        server.serve_forever()
    except Exception as e:
        print(f"❌ Error iniciando servidor REST: {e}")


def main():
    """Función principal que inicia el nodo RPC."""
    print("🚀 Iniciando Nodo RPC de Imagen...")
    print("=" * 50)
    
    ip_local = obtener_ip_real()
    print(f"🌐 IP detectada: {ip_local}")
    
    puerto_rpc = 9000
    servidor_rpc = threading.Thread(
        target=iniciar_servidor_rpc_nodo, 
        args=(ip_local, puerto_rpc),
        daemon=True
    )
    servidor_rpc.start()
    
    time.sleep(2)
    
    print("🔌 Registrando nodo en balanceador...")
    registrar_nodo_en_balanceador_rpc(ip_local)
    
    puerto_rest = 8003
    servidor_rest = threading.Thread(
        target=ejecutar_servidor_rest,
        args=(app, puerto_rest, ip_local),
        daemon=True
    )
    servidor_rest.start()
    
    print("🎯 Servicios disponibles:")
    print(f"  • RPC Puerto {puerto_rpc}: Comunicación con balanceador")
    print("    - procesar_imagenes(xml_content)")
    print("    - transformar_imagenes(xml_content)")  
    print("    - convertir_imagen_unica(xml_content, formato, calidad)")
    print("    - obtener_estado()")
    print("    - ping()")
    print(f"  • REST Puerto {puerto_rest}: GET /estado - Estado del servidor")
    print(f"  • REST Puerto {puerto_rest}: GET /salud - Health check")
    
    print(f"\n⚡ Capacidad: {gestor.capacidad_maxima:,} imágenes simultáneas")
    print(f"⚡ IP del nodo: {ip_local}")
    print(f"⚡ Balanceador configurado: {BALANCEADOR_IP}:8000 (RPC)")
    print(f"⚡ Puerto RPC: {puerto_rpc}")
    print("⚡ Nodo ejecutándose... (Ctrl+C para detener)")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo nodo...")
        print("✅ Nodo detenido")


if __name__ == "__main__":
    main()