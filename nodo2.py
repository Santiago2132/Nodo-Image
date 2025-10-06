import os
import threading
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.serving import make_server
import xml.etree.ElementTree as ET
from objects2 import NodoOptimizado
import socket
import subprocess
import re
import json
import xmlrpc.server
import xmlrpc.client
from socketserver import ThreadingMixIn
from concurrent.futures import ThreadPoolExecutor, as_completed
import io
import base64
import gzip
from PIL import Image

def obtener_ip_real():
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
        root = ET.Element("error")
        root.text = mensaje_error
        return ET.tostring(root, encoding='unicode')
    
    def _procesar_imagen_individual_optimizado(self, imagen_elem, indice, aplicar_transformaciones):
        try:
            datos_b64 = imagen_elem.text
            transformaciones = imagen_elem.get('transformaciones', '')
            formato = imagen_elem.get('formato', 'JPEG').upper()
            calidad = int(imagen_elem.get('calidad', '85'))  # Agregar calidad por imagen
            
            if not datos_b64:
                return None, f"Sin datos en imagen {indice}", None, None
            
            datos_comprimidos = base64.b64decode(datos_b64)
            datos_imagen = gzip.decompress(datos_comprimidos)
            img = Image.open(io.BytesIO(datos_imagen))
            
            nodo = NodoOptimizado()
            nodo.imagen_original = img
            nodo.imagen_procesada = img.copy()
            
            if aplicar_transformaciones and transformaciones:
                self._aplicar_transformaciones_optimizado(nodo, transformaciones)
            
            return nodo, None, formato, calidad  # Retornar formato y calidad
            
        except Exception as e:
            return None, str(e), None, None
    
    def _aplicar_transformaciones_optimizado(self, nodo, transformaciones_str):
        """Aplica transformaciones en orden optimizado."""
        trans_list = transformaciones_str.split(', ')
        
        # Agrupar por tipo
        ajustes_color = []
        geometricas = []
        efectos = []
        otros = []
        
        for trans in trans_list:
            if any(x in trans for x in ['escala_grises', 'ajustar_brillo', 'convertir_a']):
                ajustes_color.append(trans)
            elif any(x in trans for x in ['rotar', 'redimensionar', 'reflejar', 'recortar']):
                geometricas.append(trans)
            elif any(x in trans for x in ['desenfocar', 'perfilar']):
                efectos.append(trans)
            else:
                otros.append(trans)
        
        # Aplicar en orden óptimo
        for trans in ajustes_color + geometricas + efectos + otros:
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
            except Exception:
                pass
    
    def _fusionar_nodo_a_xml_optimizado(self, nodo, root_respuesta, indice, formato_salida, calidad):
        """Versión optimizada sin archivos temporales."""
        try:
            # Generar XML en memoria
            b64_data = nodo.convertir_y_comprimir_optimizado(formato_salida, calidad)
            
            nueva_imagen = ET.SubElement(root_respuesta, "imagen")
            nueva_imagen.set("formato", formato_salida)
            nueva_imagen.set("calidad", str(calidad))
            nueva_imagen.set("transformaciones", ", ".join(nodo.transformaciones_aplicadas))
            nueva_imagen.set("total_transformaciones", str(len(nodo.transformaciones_aplicadas)))
            nueva_imagen.set("indice_procesado", str(indice))
            nueva_imagen.text = b64_data
            
            return True
            
        except Exception:
            return False
    
    def procesar_xml_imagenes(self, xml_content, aplicar_transformaciones=True):
        """Versión optimizada con threading."""
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
            
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {
                    executor.submit(
                        self._procesar_imagen_individual_optimizado,
                        imagen_elem, i, aplicar_transformaciones
                    ): i
                    for i, imagen_elem in enumerate(imagenes)
                }
                
                for future in as_completed(futures):
                    i = futures[future]
                    nodo, error, formato, calidad = future.result()
                    
                    if error:
                        error_imagen = ET.SubElement(root_respuesta, "imagen")
                        error_imagen.set("error", error)
                        error_imagen.set("indice_original", str(i))
                    else:
                        nodos_procesados.append((nodo, formato, calidad, i))
            
            procesadas = 0
            errores = 0
            
            for nodo, formato, calidad, indice in nodos_procesados:
                if self._fusionar_nodo_a_xml_optimizado(nodo, root_respuesta, indice, formato, calidad):
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
        return self.procesar_xml_imagenes(xml_content, aplicar_transformaciones=True)
    
    def convertir_imagen_unica(self, xml_content, formato_salida="JPEG", calidad=85):
        """Versión optimizada sin archivos temporales."""
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
            
            try:
                # Procesar en memoria
                datos_comprimidos = base64.b64decode(datos_b64)
                datos_imagen = gzip.decompress(datos_comprimidos)
                img = Image.open(io.BytesIO(datos_imagen))
                
                nodo = NodoOptimizado()
                nodo.imagen_original = img
                nodo.imagen_procesada = img.copy()
                
                # Convertir formato
                b64_data = nodo.convertir_y_comprimir_optimizado(formato_salida.upper(), calidad)
                
                root_respuesta = ET.Element("imagen_convertida")
                nueva_imagen = ET.SubElement(root_respuesta, "imagen")
                nueva_imagen.set("formato", formato_salida.upper())
                nueva_imagen.set("calidad", str(calidad))
                nueva_imagen.text = b64_data
                
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
        with self.lock:
            return {
                "estado": self.estado,
                "imagenes_procesando": self.imagenes_procesando,
                "capacidad_maxima": self.capacidad_maxima,
                "capacidad_disponible": self.capacidad_maxima - self.imagenes_procesando,
                "disponible": self.imagenes_procesando < self.capacidad_maxima
            }


class RPCNodoService:
    def __init__(self, gestor):
        self.gestor = gestor
    
    def ping(self):
        return "pong"
    
    def _procesar_con_validacion(self, xml_content, metodo_procesamiento):
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
            if formato_salida.upper() not in ['JPEG', 'JPG', 'PNG', 'WEBP', 'TIFF']:
                return json.dumps({
                    "success": False,
                    "error": "Formato no soportado. Use: JPEG, JPG, PNG, WEBP, TIFF"
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
        
        print(f"📌 Intentando registrar nodo {ip_nodo} en balanceador RPC {BALANCEADOR_RPC_URL}")
        
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
    try:
        server = make_server(ip_local, puerto, app)
        print(f"✅ Servidor REST opcional iniciado en {ip_local}:{puerto}")
        server.serve_forever()
    except Exception as e:
        print(f"❌ Error iniciando servidor REST: {e}")


def main():
    print("🚀 Iniciando Nodo RPC de Imagen OPTIMIZADO...")
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
    
    print("📌 Registrando nodo en balanceador...")
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
    print("⚡ OPTIMIZACIONES ACTIVAS:")
    print("   - Threading paralelo (max 4 workers)")
    print("   - Sin archivos temporales (procesamiento en memoria)")
    print("   - Compresión nivel 6 (balance velocidad/tamaño)")
    print("   - JPEG optimize=False, progressive=False")
    print("   - Redimensionamiento BILINEAR")
    print("   - Caché de conversión RGB")
    print("   - Orden de transformaciones optimizado")
    print("⚡ Nodo ejecutándose... (Ctrl+C para detener)")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo nodo...")
        print("✅ Nodo detenido")


if __name__ == "__main__":
    main()