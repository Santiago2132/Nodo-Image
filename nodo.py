import os
import threading
import time
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from werkzeug.serving import make_server
import xml.etree.ElementTree as ET
from objects import NodoOptimizado, LectorXML
import socket
import subprocess
import re
import json
import sys
import xmlrpc.server
import xmlrpc.client
from socketserver import ThreadingMixIn

def obtener_ip_real():
    """
    Obtiene la IP real de la mÃ¡quina en la red local.
    """
    # MÃ©todo 1: Conectar a un servidor externo (mÃ¡s confiable)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            if not ip.startswith("127."):
                return ip
    except:
        pass
    
    # MÃ©todo 2: Usar ip route (Linux/Mac)
    try:
        result = subprocess.run(['ip', 'route', 'get', '8.8.8.8'], 
                              capture_output=True, text=True, timeout=3)
        match = re.search(r'src (\d+\.\d+\.\d+\.\d+)', result.stdout)
        if match:
            return match.group(1)
    except:
        pass
    
    # MÃ©todo 3: Usar hostname -I (Linux)
    try:
        result = subprocess.run(['hostname', '-I'], 
                              capture_output=True, text=True, timeout=3)
        ips = result.stdout.strip().split()
        for ip in ips:
            if not ip.startswith("127.") and "." in ip:
                return ip
    except:
        pass
    
    # Fallback
    try:
        ip = socket.gethostbyname(socket.gethostname())
        if not ip.startswith("127."):
            return ip
    except:
        pass
    
    return "127.0.0.1"

# URL del balanceador - CONFIGURABLE
BALANCEADOR_IP = "192.168.154.129"  # Cambiar por la IP real del balanceador
BALANCEADOR_RPC_URL = f"http://{BALANCEADOR_IP}:8000"

class ThreadedXMLRPCServer(ThreadingMixIn, xmlrpc.server.SimpleXMLRPCServer):
    pass

class GestorNodos:
    def __init__(self):
        self.nodos_activos = {}
        self.capacidad_maxima = 100000
        self.estado = "disponible"
        self.imagenes_procesando = 0
        self.lock = threading.Lock()
    
    def procesar_xml_imagenes(self, xml_content, aplicar_transformaciones=True):
        """
        Procesa un XML con mÃºltiples imÃ¡genes y aplica transformaciones.
        Retorna XML fusionado con todas las imÃ¡genes procesadas.
        """
        num_imagenes = 0
        try:
            root = ET.fromstring(xml_content)
            imagenes = root.findall('imagen')
            num_imagenes = len(imagenes)
            
            if not imagenes:
                return self._crear_xml_error("No se encontraron imÃ¡genes en el XML")
        except:
            return self._crear_xml_error("XML malformado")
        
        with self.lock:
            if self.imagenes_procesando + num_imagenes > self.capacidad_maxima:
                return self._crear_xml_error("Capacidad mÃ¡xima excedida")
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
                                        angle = int(trans.split('_')[-1].replace('Â°', ''))
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
        Procesa XML aplicando transformaciones especÃ­ficas.
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
                    return self._crear_xml_error("Capacidad mÃ¡xima excedida")
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


class RPCNodoService:
    """Servicio RPC para el nodo"""
    def __init__(self, gestor):
        self.gestor = gestor
    
    def ping(self):
        """RPC method para verificar conectividad"""
        return "pong"
    
    def procesar_imagenes(self, xml_content):
        """RPC method para procesamiento batch de imÃ¡genes"""
        try:
            estado = self.gestor.obtener_estado()
            if not estado["disponible"]:
                return json.dumps({
                    "success": False,
                    "error": "Servidor saturado, intente mÃ¡s tarde"
                })
            
            resultado = self.gestor.procesar_xml_imagenes(xml_content)
            
            # Verificar si es error
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
    
    def transformar_imagenes(self, xml_content):
        """RPC method para transformaciones batch de imÃ¡genes"""
        try:
            estado = self.gestor.obtener_estado()
            if not estado["disponible"]:
                return json.dumps({
                    "success": False,
                    "error": "Servidor saturado, intente mÃ¡s tarde"
                })
            
            resultado = self.gestor.procesar_xml_transformaciones(xml_content)
            
            # Verificar si es error
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
    
    def convertir_imagen_unica(self, xml_content, formato_salida="JPEG", calidad=85):
        """RPC method para conversiÃ³n de imagen Ãºnica"""
        try:
            # Validar formato
            if formato_salida.upper() not in ['JPEG', 'PNG', 'WEBP']:
                return json.dumps({
                    "success": False,
                    "error": "Formato no soportado. Use: JPEG, PNG, WEBP"
                })
            
            resultado = self.gestor.convertir_imagen_unica(xml_content, formato_salida, calidad)
            
            # Verificar si es error
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
        """RPC method para obtener estado del nodo"""
        try:
            estado = self.gestor.obtener_estado()
            return json.dumps(estado)
        except Exception as e:
            return json.dumps({
                "error": f"Error al obtener estado: {str(e)}"
            })


def registrar_nodo_en_balanceador_rpc(ip_nodo):
    """
    Registra el nodo en el balanceador de cargas via RPC
    """
    try:
        datos_registro = {
            "encendido": "true",
            "ip": ip_nodo,
            "puertos": [9000],  # Puerto RPC
            "servicios": {
                "9000": "nodo_rpc_service"
            },
            "capacidad_maxima": 100000
        }
        
        print(f"ðŸ¡ Intentando registrar nodo {ip_nodo} en balanceador RPC {BALANCEADOR_RPC_URL}")
        
        # Conectar con balanceador RPC
        balanceador_client = xmlrpc.client.ServerProxy(BALANCEADOR_RPC_URL)
        
        # Registrar nodo
        resultado = balanceador_client.registrar_nodo(json.dumps(datos_registro))
        
        if resultado:
            print(f"âœ… Nodo registrado exitosamente en balanceador: {ip_nodo}")
        else:
            print(f"âš ï¸  Error al registrar nodo en balanceador")
            
    except Exception as e:
        print(f"âŒ Error conectando con balanceador RPC: {e}")
        print(f"   Verificar que el balanceador estÃ© ejecutÃ¡ndose en {BALANCEADOR_IP}:8000")


def iniciar_servidor_rpc_nodo(ip, puerto=9000):
    """Inicia el servidor RPC del nodo"""
    try:
        server = ThreadedXMLRPCServer((ip, puerto), allow_none=True)
        server.register_introspection_functions()
        
        # Registrar servicio RPC del nodo
        rpc_service = RPCNodoService(gestor)
        server.register_instance(rpc_service)
        
        print(f"âœ… Servidor RPC del nodo iniciado en {ip}:{puerto}")
        server.serve_forever()
    except Exception as e:
        print(f"âŒ Error iniciando servidor RPC del nodo: {e}")


# Instancia global del gestor
gestor = GestorNodos()

# Crear aplicación Flask para el endpoint REST de estado (opcional)
app = Flask(__name__)
CORS(app, origins="*", allow_headers=["Content-Type", "Authorization"], methods=["GET", "POST", "OPTIONS"])

@app.route('/estado', methods=['GET'])
def consultar_estado():
    """Endpoint REST opcional para consulta de estado"""
    try:
        estado = gestor.obtener_estado()
        return jsonify(estado)
    except Exception as e:
        return jsonify({
            "error": f"Error al obtener estado: {str(e)}"
        }), 500

@app.route('/salud', methods=['GET'])
def check_health():
    """Health check REST opcional"""
    return jsonify({
        "status": "healthy",
        "service": "Gestor de Nodos RPC de Imagen",
        "timestamp": time.time()
    })


def ejecutar_servidor_rest(app, puerto, ip_local):
    """Ejecuta servidor REST opcional."""
    try:
        server = make_server(ip_local, puerto, app)
        print(f"âœ… Servidor REST opcional iniciado en {ip_local}:{puerto}")
        server.serve_forever()
    except Exception as e:
        print(f"âŒ Error iniciando servidor REST: {e}")


def main():
    """FunciÃ³n principal que inicia el nodo RPC."""
    print("ðŸš€ Iniciando Nodo RPC de Imagen...")
    print("=" * 50)
    
    # Obtener IP real
    ip_local = obtener_ip_real()
    print(f"ðŸ IP detectada: {ip_local}")
    
    # Iniciar servidor RPC en hilo separado
    puerto_rpc = 9000
    servidor_rpc = threading.Thread(
        target=iniciar_servidor_rpc_nodo, 
        args=(ip_local, puerto_rpc),
        daemon=True
    )
    servidor_rpc.start()
    
    # Esperar un momento para que el servidor RPC inicie
    time.sleep(2)
    
    # Registrar nodo en balanceador via RPC
    print("ðŸ¡ Registrando nodo en balanceador...")
    registrar_nodo_en_balanceador_rpc(ip_local)
    
    # Iniciar servidor REST opcional para estado
    puerto_rest = 8003
    servidor_rest = threading.Thread(
        target=ejecutar_servidor_rest,
        args=(app, puerto_rest, ip_local),
        daemon=True
    )
    servidor_rest.start()
    
    print("ðŸ¡ Servicios disponibles:")
    print(f"  â€¢ RPC Puerto {puerto_rpc}: Comunicación con balanceador")
    print("    - procesar_imagenes(xml_content)")
    print("    - transformar_imagenes(xml_content)")  
    print("    - convertir_imagen_unica(xml_content, formato, calidad)")
    print("    - obtener_estado()")
    print("    - ping()")
    print(f"  â€¢ REST Puerto {puerto_rest}: GET /estado - Estado del servidor (opcional)")
    print(f"  â€¢ REST Puerto {puerto_rest}: GET /salud - Health check (opcional)")
    
    print(f"\nâš¡ Capacidad: {gestor.capacidad_maxima:,} imÃ¡genes simultÃ¡neas")
    print(f"âš¡ IP del nodo: {ip_local}")
    print(f"âš¡ Balanceador configurado: {BALANCEADOR_IP}:8000 (RPC)")
    print(f"âš¡ Puerto RPC: {puerto_rpc}")
    print("âš¡ Comunicación RPC con balanceador habilitada")
    print("âš¡ Nodo ejecutÃ¡ndose... (Ctrl+C para detener)")
    
    try:
        # Mantener el programa principal vivo
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nðŸ›' Deteniendo nodo...")
        print("âœ… Nodo detenido")


if __name__ == "__main__":
    main()