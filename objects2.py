import base64
import gzip
import io
import os
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
import datetime


class LectorXML:
    """Clase para leer y mostrar contenido de archivos XML generados por la clase Nodo."""
    
    def __init__(self, archivo_xml):
        self.archivo_xml = archivo_xml
        self.tree = None
        self.cargar_xml()
    
    def cargar_xml(self):
        try:
            self.tree = ET.parse(self.archivo_xml)
        except (ET.ParseError, FileNotFoundError):
            pass
    
    def mostrar_informacion(self):
        if not self.tree:
            return
        
        root = self.tree.getroot()
        tamaño_archivo = os.path.getsize(self.archivo_xml) / 1024
        
        for i, imagen in enumerate(root.findall('imagen'), 1):
            datos_b64 = imagen.text
            if datos_b64:
                tamaño_b64 = len(datos_b64)
                try:
                    datos_comprimidos = base64.b64decode(datos_b64)
                    datos_descomprimidos = gzip.decompress(datos_comprimidos)
                    tamaño_original = len(datos_descomprimidos) / 1024
                    ratio_compresion = len(datos_comprimidos) / len(datos_descomprimidos) * 100
                except Exception:
                    pass
    
    def extraer_imagen(self, indice=0, ruta_salida=None):
        if not self.tree:
            return
        
        imagenes = self.tree.getroot().findall('imagen')
        if indice >= len(imagenes):
            return
        
        imagen_elem = imagenes[indice]
        formato = imagen_elem.get('formato', 'PNG')
        
        if not ruta_salida:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            ruta_salida = f"imagen_extraida_{timestamp}.{formato.lower()}"
        
        try:
            datos_b64 = imagen_elem.text
            datos_comprimidos = base64.b64decode(datos_b64)
            datos_imagen = gzip.decompress(datos_comprimidos)
            img = Image.open(io.BytesIO(datos_imagen))
            img.save(ruta_salida)
        except Exception:
            pass
    
    def comparar_tamaños(self):
        if not self.tree:
            return
        
        for i, imagen in enumerate(self.tree.getroot().findall('imagen')):
            datos_b64 = imagen.text
            if datos_b64:
                try:
                    datos_comprimidos = base64.b64decode(datos_b64)
                    datos_descomprimidos = gzip.decompress(datos_comprimidos)
                except Exception:
                    pass


class NodoOptimizado:
    """Versión ultra-optimizada para velocidad máxima."""
    
    def __init__(self, imagen_path=None):
        self.imagen_original = None
        self.imagen_procesada = None
        self.transformaciones_aplicadas = []
        self.MAX_TRANSFORMACIONES = 20
        self._modo_rgb_cache = None
        
        if imagen_path:
            self.cargar_imagen(imagen_path)
        else:
            self._crear_imagen_prueba()
    
    def cargar_imagen(self, imagen_path):
        if not os.path.exists(imagen_path):
            self._crear_imagen_prueba()
            return
        
        if imagen_path.lower().endswith('.xml'):
            self._cargar_desde_xml(imagen_path)
        else:
            try:
                self.imagen_original = Image.open(imagen_path)
                self.imagen_procesada = self.imagen_original.copy()
            except Exception:
                self._crear_imagen_prueba()
    
    def _cargar_desde_xml(self, xml_path, indice_imagen=0):
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            imagenes = root.findall('imagen')
            
            if not imagenes:
                self._crear_imagen_prueba()
                return
            
            if indice_imagen >= len(imagenes):
                indice_imagen = 0
            
            imagen_elem = imagenes[indice_imagen]
            datos_b64 = imagen_elem.text
            
            if not datos_b64:
                self._crear_imagen_prueba()
                return
            
            datos_comprimidos = base64.b64decode(datos_b64)
            datos_imagen = gzip.decompress(datos_comprimidos)
            self.imagen_original = Image.open(io.BytesIO(datos_imagen))
            self.imagen_procesada = self.imagen_original.copy()
            
        except Exception:
            self._crear_imagen_prueba()
    
    def _crear_imagen_prueba(self):
        self.imagen_original = Image.new("RGB", (300, 300), color=(200, 200, 255))
        draw = ImageDraw.Draw(self.imagen_original)
        draw.rectangle([25, 25, 275, 275], outline=(100, 100, 100), width=2)
        draw.text((100, 140), "Prueba Optimizada", fill=(0, 0, 0))
        self.imagen_procesada = self.imagen_original.copy()
    
    def escala_grises(self):
        if self._puede_aplicar_transformacion():
            self.imagen_procesada = self.imagen_procesada.convert("L")
            self._modo_rgb_cache = None
            self._registrar_transformacion("escala_grises")
        return self
    
    def redimensionar(self, size=(200, 200)):
        if self._puede_aplicar_transformacion():
            self.imagen_procesada = self.imagen_procesada.resize(size, Image.Resampling.BILINEAR)
            self._modo_rgb_cache = None
            self._registrar_transformacion(f"redimensionar_{size[0]}x{size[1]}")
        return self
    
    def recortar(self, box=(0, 0, 100, 100)):
        if self._puede_aplicar_transformacion():
            self.imagen_procesada = self.imagen_procesada.crop(box)
            self._modo_rgb_cache = None
            self._registrar_transformacion(f"recortar_{box}")
        return self
    
    def rotar(self, angle=45):
        if self._puede_aplicar_transformacion():
            self.imagen_procesada = self.imagen_procesada.rotate(angle, expand=True, fillcolor='white')
            self._modo_rgb_cache = None
            self._registrar_transformacion(f"rotar_{angle}°")
        return self
    
    def reflejar(self, direccion='horizontal'):
        if self._puede_aplicar_transformacion():
            if direccion == 'horizontal':
                self.imagen_procesada = self.imagen_procesada.transpose(Image.FLIP_LEFT_RIGHT)
            elif direccion == 'vertical':
                self.imagen_procesada = self.imagen_procesada.transpose(Image.FLIP_TOP_BOTTOM)
            else:
                self.imagen_procesada = self.imagen_procesada.transpose(Image.FLIP_LEFT_RIGHT)
            self._modo_rgb_cache = None
            self._registrar_transformacion(f"reflejar_{direccion}")
        return self
    
    def desenfocar(self, radio=2):
        if self._puede_aplicar_transformacion():
            self.imagen_procesada = self.imagen_procesada.filter(ImageFilter.GaussianBlur(radio))
            self._registrar_transformacion(f"desenfocar_radio_{radio}")
        return self
    
    def perfilar(self, factor=2.0):
        if self._puede_aplicar_transformacion():
            enhancer = ImageEnhance.Sharpness(self.imagen_procesada)
            self.imagen_procesada = enhancer.enhance(factor)
            self._registrar_transformacion(f"perfilar_factor_{factor}")
        return self
    
    def ajustar_brillo_contraste(self, brillo=1.0, contraste=1.0):
        if self._puede_aplicar_transformacion():
            enhancer_brillo = ImageEnhance.Brightness(self.imagen_procesada)
            self.imagen_procesada = enhancer_brillo.enhance(brillo)
            enhancer_contraste = ImageEnhance.Contrast(self.imagen_procesada)
            self.imagen_procesada = enhancer_contraste.enhance(contraste)
            self._registrar_transformacion(f"ajustar_brillo_{brillo}_contraste_{contraste}")
        return self
    
    def insertar_texto(self, texto="Marca de agua", posicion=(10, 10), color=(255, 255, 255)):
        if self._puede_aplicar_transformacion():
            draw = ImageDraw.Draw(self.imagen_procesada)
            
            if self.imagen_procesada.mode == "L":
                if isinstance(color, tuple):
                    if len(color) >= 3:
                        color_gris = int(0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2])
                    else:
                        color_gris = color[0] if len(color) > 0 else 255
                else:
                    color_gris = color
                draw.text(posicion, texto, fill=color_gris)
            elif self.imagen_procesada.mode == "1":
                color_binario = 255 if sum(color) > 384 else 0
                draw.text(posicion, texto, fill=color_binario)
            else:
                draw.text(posicion, texto, fill=color)
            
            self._registrar_transformacion(f"insertar_texto_{texto}")
        return self
    
    def convertir_formato(self, formato="JPEG"):
        if self._puede_aplicar_transformacion():
            if formato.upper() in ["JPG", "JPEG"]:
                if self.imagen_procesada.mode in ("RGBA", "LA", "P"):
                    self.imagen_procesada = self.imagen_procesada.convert("RGB")
                    self._modo_rgb_cache = None
            self._registrar_transformacion(f"convertir_a_{formato.upper()}")
        return self
    
    def _puede_aplicar_transformacion(self):
        return len(self.transformaciones_aplicadas) < self.MAX_TRANSFORMACIONES
    
    def _registrar_transformacion(self, nombre):
        self.transformaciones_aplicadas.append(nombre)
    
    def convertir_y_comprimir_optimizado(self, formato="JPEG", calidad=85, nivel_compresion=6):
        buffer = io.BytesIO()
        
        save_options = {}
        if formato.upper() == "JPEG":
            save_options = {
                "quality": calidad, 
                "optimize": False,
                "progressive": False
            }
            if self.imagen_procesada.mode in ("RGBA", "LA", "P"):
                if not self._modo_rgb_cache or self._modo_rgb_cache.mode != "RGB":
                    self._modo_rgb_cache = self.imagen_procesada.convert("RGB")
                img_to_save = self._modo_rgb_cache
            else:
                img_to_save = self.imagen_procesada
        elif formato.upper() == "PNG":
            save_options = {"optimize": False}
            img_to_save = self.imagen_procesada
        elif formato.upper() == "WEBP":
            save_options = {"quality": calidad, "method": 0}
            img_to_save = self.imagen_procesada
        else:
            img_to_save = self.imagen_procesada
        
        img_to_save.save(buffer, format=formato.upper(), **save_options)
        datos = buffer.getvalue()
        datos_gzip = gzip.compress(datos, compresslevel=nivel_compresion)
        datos_b64 = base64.b64encode(datos_gzip).decode("utf-8")
        
        return datos_b64
    
    def generar_xml_optimizado(self, archivo_salida="resultado_optimizado.xml", 
                              formato_salida="JPEG", calidad=75):
        if not self.imagen_procesada:
            return None
        
        b64_data = self.convertir_y_comprimir_optimizado(formato_salida, calidad)
        
        root = ET.Element("imagenes")
        nodo = ET.SubElement(root, "imagen", {
            "formato": formato_salida,
            "calidad": str(calidad),
            "transformaciones": ", ".join(self.transformaciones_aplicadas),
            "total_transformaciones": str(len(self.transformaciones_aplicadas)),
            "fecha_generacion": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tamaño_original": f"{self.imagen_original.size[0]}x{self.imagen_original.size[1]}" if self.imagen_original else "N/A",
            "tamaño_final": f"{self.imagen_procesada.size[0]}x{self.imagen_procesada.size[1]}"
        })
        nodo.text = b64_data
        
        tree = ET.ElementTree(root)
        tree.write(archivo_salida, encoding="utf-8", xml_declaration=True)
        
        return tree