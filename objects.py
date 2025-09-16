import base64
import gzip
import io
import os
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
import datetime


class LectorXML:
    """
    Clase para leer y mostrar contenido de archivos XML generados por la clase Nodo.
    """
    
    def __init__(self, archivo_xml):
        """
        Inicializa el lector con un archivo XML.
        
        Args:
            archivo_xml (str): Ruta del archivo XML a leer
        """
        self.archivo_xml = archivo_xml
        self.tree = None
        self.cargar_xml()
    
    def cargar_xml(self):
        """Carga el archivo XML."""
        try:
            self.tree = ET.parse(self.archivo_xml)
            print(f"✅ XML cargado: {self.archivo_xml}")
        except ET.ParseError as e:
            print(f"⌐ Error al parsear XML: {e}")
        except FileNotFoundError:
            print(f"⌐ Archivo no encontrado: {self.archivo_xml}")
    
    def mostrar_informacion(self):
        """Muestra información completa del XML."""
        if not self.tree:
            print("⌐ No hay XML cargado")
            return
        
        root = self.tree.getroot()
        print(f"\n📄 INFORMACIÓN DEL XML: {self.archivo_xml}")
        print("=" * 50)
        
        # Información del archivo
        tamaño_archivo = os.path.getsize(self.archivo_xml) / 1024  # KB
        print(f"📁 Tamaño del archivo: {tamaño_archivo:.2f} KB")
        
        # Información de cada imagen
        for i, imagen in enumerate(root.findall('imagen'), 1):
            print(f"\n🖼️  IMAGEN {i}:")
            print(f"   📋 Formato: {imagen.get('formato', 'No especificado')}")
            print(f"   🔄 Transformaciones: {imagen.get('transformaciones', 'Ninguna')}")
            print(f"   📊 Total transformaciones: {imagen.get('total_transformaciones', '0')}")
            
            # Información de los datos
            datos_b64 = imagen.text
            if datos_b64:
                tamaño_b64 = len(datos_b64)
                print(f"   💾 Tamaño datos base64: {tamaño_b64:,} caracteres")
                
                # Calcular tamaño descomprimido aproximado
                try:
                    datos_comprimidos = base64.b64decode(datos_b64)
                    datos_descomprimidos = gzip.decompress(datos_comprimidos)
                    tamaño_original = len(datos_descomprimidos) / 1024
                    ratio_compresion = len(datos_comprimidos) / len(datos_descomprimidos) * 100
                    
                    print(f"   📦 Tamaño comprimido: {len(datos_comprimidos)/1024:.2f} KB")
                    print(f"   📂 Tamaño descomprimido: {tamaño_original:.2f} KB")
                    print(f"   📈 Ratio de compresión: {ratio_compresion:.1f}%")
                    
                except Exception as e:
                    print(f"   ⚠️  Error al analizar datos: {e}")
    
    def extraer_imagen(self, indice=0, ruta_salida=None):
        """
        Extrae una imagen del XML y la guarda.
        
        Args:
            indice (int): Índice de la imagen a extraer (0 para la primera)
            ruta_salida (str): Ruta donde guardar la imagen
        """
        if not self.tree:
            print("⌐ No hay XML cargado")
            return
        
        imagenes = self.tree.getroot().findall('imagen')
        if indice >= len(imagenes):
            print(f"⌐ Índice {indice} fuera de rango. Hay {len(imagenes)} imagen(es)")
            return
        
        imagen_elem = imagenes[indice]
        formato = imagen_elem.get('formato', 'PNG')
        
        if not ruta_salida:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            ruta_salida = f"imagen_extraida_{timestamp}.{formato.lower()}"
        
        try:
            # Decodificar y descomprimir
            datos_b64 = imagen_elem.text
            datos_comprimidos = base64.b64decode(datos_b64)
            datos_imagen = gzip.decompress(datos_comprimidos)
            
            # Crear imagen y guardar
            img = Image.open(io.BytesIO(datos_imagen))
            img.save(ruta_salida)
            
            print(f"✅ Imagen extraída: {ruta_salida}")
            print(f"   📏 Dimensiones: {img.size}")
            print(f"   🎨 Modo: {img.mode}")
            
        except Exception as e:
            print(f"⌐ Error al extraer imagen: {e}")
    
    def comparar_tamaños(self):
        """Compara tamaños de compresión."""
        if not self.tree:
            return
        
        print(f"\n📊 ANÁLISIS DE COMPRESIÓN")
        print("=" * 40)
        
        for i, imagen in enumerate(self.tree.getroot().findall('imagen')):
            datos_b64 = imagen.text
            if datos_b64:
                try:
                    datos_comprimidos = base64.b64decode(datos_b64)
                    datos_descomprimidos = gzip.decompress(datos_comprimidos)
                    
                    tamaño_original = len(datos_descomprimidos)
                    tamaño_comprimido = len(datos_comprimidos)
                    tamaño_b64 = len(datos_b64)
                    
                    print(f"🖼️  Imagen {i+1}:")
                    print(f"   Original: {tamaño_original/1024:.2f} KB")
                    print(f"   Comprimido: {tamaño_comprimido/1024:.2f} KB")
                    print(f"   Base64: {tamaño_b64/1024:.2f} KB")
                    print(f"   Reducción: {(1-tamaño_comprimido/tamaño_original)*100:.1f}%")
                    
                except Exception as e:
                    print(f"⌐ Error en imagen {i+1}: {e}")


class NodoOptimizado:
    """
    Versión optimizada de Nodo con mejor compresión, opciones de calidad 
    y soporte para cargar imágenes desde XML.
    """
    
    def __init__(self, imagen_path=None):
        # Misma inicialización que la clase original
        self.imagen_original = None
        self.imagen_procesada = None
        self.transformaciones_aplicadas = []
        self.MAX_TRANSFORMACIONES = 5
        
        if imagen_path:
            self.cargar_imagen(imagen_path)
        else:
            self._crear_imagen_prueba()
    
    def cargar_imagen(self, imagen_path):
        """Carga una imagen desde archivo (formatos tradicionales o XML)."""
        if not os.path.exists(imagen_path):
            print(f"⚠️ Archivo no encontrado: {imagen_path}. Creando imagen de prueba...")
            self._crear_imagen_prueba()
            return
        
        # Detectar si es un archivo XML
        if imagen_path.lower().endswith('.xml'):
            self._cargar_desde_xml(imagen_path)
        else:
            # Cargar imagen tradicional
            try:
                self.imagen_original = Image.open(imagen_path)
                self.imagen_procesada = self.imagen_original.copy()
                print(f"✅ Imagen cargada: {imagen_path}")
            except Exception as e:
                print(f"⌐ Error al cargar imagen: {e}. Creando imagen de prueba...")
                self._crear_imagen_prueba()
    
    def _cargar_desde_xml(self, xml_path, indice_imagen=0):
        """
        Carga una imagen desde un archivo XML.
        
        Args:
            xml_path (str): Ruta del archivo XML
            indice_imagen (int): Índice de la imagen a cargar (0 para la primera)
        """
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            imagenes = root.findall('imagen')
            
            if not imagenes:
                print(f"⌐ No se encontraron imágenes en el XML: {xml_path}")
                self._crear_imagen_prueba()
                return
            
            if indice_imagen >= len(imagenes):
                print(f"⚠️ Índice {indice_imagen} fuera de rango. Usando primera imagen.")
                indice_imagen = 0
            
            imagen_elem = imagenes[indice_imagen]
            datos_b64 = imagen_elem.text
            
            if not datos_b64:
                print(f"⌐ No hay datos de imagen en el XML")
                self._crear_imagen_prueba()
                return
            
            # Decodificar y descomprimir la imagen
            datos_comprimidos = base64.b64decode(datos_b64)
            datos_imagen = gzip.decompress(datos_comprimidos)
            
            # Crear objeto Image
            self.imagen_original = Image.open(io.BytesIO(datos_imagen))
            self.imagen_procesada = self.imagen_original.copy()
            
            # Mostrar información de carga
            formato = imagen_elem.get('formato', 'Desconocido')
            transformaciones_previas = imagen_elem.get('transformaciones', 'Ninguna')
            
            print(f"✅ Imagen cargada desde XML: {xml_path}")
            print(f"   📏 Dimensiones: {self.imagen_original.size}")
            print(f"   📋 Formato original: {formato}")
            print(f"   🔄 Transformaciones previas: {transformaciones_previas}")
            
        except ET.ParseError as e:
            print(f"⌐ Error al parsear XML: {e}")
            self._crear_imagen_prueba()
        except Exception as e:
            print(f"⌐ Error al cargar desde XML: {e}")
            self._crear_imagen_prueba()
    
    def _crear_imagen_prueba(self):
        """Crea una imagen de prueba más pequeña."""
        self.imagen_original = Image.new("RGB", (300, 300), color=(200, 200, 255))
        draw = ImageDraw.Draw(self.imagen_original)
        draw.rectangle([25, 25, 275, 275], outline=(100, 100, 100), width=2)
        draw.text((100, 140), "Prueba Optimizada", fill=(0, 0, 0))
        self.imagen_procesada = self.imagen_original.copy()
        print("✅ Imagen de prueba optimizada creada")
    
    def escala_grises(self):
        """Convierte la imagen a escala de grises."""
        if self._puede_aplicar_transformacion():
            self.imagen_procesada = self.imagen_procesada.convert("L")
            self._registrar_transformacion("escala_grises")
        return self
    
    def redimensionar(self, size=(200, 200)):
        """Redimensiona la imagen al tamaño especificado."""
        if self._puede_aplicar_transformacion():
            # Usar LANCZOS para mejor calidad en redimensionamiento
            self.imagen_procesada = self.imagen_procesada.resize(size, Image.Resampling.LANCZOS)
            self._registrar_transformacion(f"redimensionar_{size[0]}x{size[1]}")
        return self
    
    def recortar(self, box=(0, 0, 100, 100)):
        """Recorta la imagen según la caja especificada (left, top, right, bottom)."""
        if self._puede_aplicar_transformacion():
            self.imagen_procesada = self.imagen_procesada.crop(box)
            self._registrar_transformacion(f"recortar_{box}")
        return self
    
    def rotar(self, angle=45):
        """Rota la imagen en el ángulo especificado."""
        if self._puede_aplicar_transformacion():
            # Usar expand=True para no cortar la imagen
            self.imagen_procesada = self.imagen_procesada.rotate(angle, expand=True, fillcolor='white')
            self._registrar_transformacion(f"rotar_{angle}°")
        return self
    
    def reflejar(self, direccion='horizontal'):
        """Refleja la imagen horizontal o verticalmente."""
        if self._puede_aplicar_transformacion():
            if direccion == 'horizontal':
                self.imagen_procesada = self.imagen_procesada.transpose(Image.FLIP_LEFT_RIGHT)
            elif direccion == 'vertical':
                self.imagen_procesada = self.imagen_procesada.transpose(Image.FLIP_TOP_BOTTOM)
            else:
                print(f"⚠️ Dirección no válida: {direccion}. Usando horizontal por defecto.")
                self.imagen_procesada = self.imagen_procesada.transpose(Image.FLIP_LEFT_RIGHT)
            self._registrar_transformacion(f"reflejar_{direccion}")
        return self
    
    def desenfocar(self, radio=2):
        """Aplica un desenfoque gaussiano a la imagen."""
        if self._puede_aplicar_transformacion():
            self.imagen_procesada = self.imagen_procesada.filter(ImageFilter.GaussianBlur(radio))
            self._registrar_transformacion(f"desenfocar_radio_{radio}")
        return self
    
    def perfilar(self, factor=2.0):
        """Aumenta la nitidez de la imagen."""
        if self._puede_aplicar_transformacion():
            enhancer = ImageEnhance.Sharpness(self.imagen_procesada)
            self.imagen_procesada = enhancer.enhance(factor)
            self._registrar_transformacion(f"perfilar_factor_{factor}")
        return self
    
    def ajustar_brillo_contraste(self, brillo=1.0, contraste=1.0):
        """Ajusta el brillo y el contraste de la imagen."""
        if self._puede_aplicar_transformacion():
            enhancer_brillo = ImageEnhance.Brightness(self.imagen_procesada)
            self.imagen_procesada = enhancer_brillo.enhance(brillo)
            enhancer_contraste = ImageEnhance.Contrast(self.imagen_procesada)
            self.imagen_procesada = enhancer_contraste.enhance(contraste)
            self._registrar_transformacion(f"ajustar_brillo_{brillo}_contraste_{contraste}")
        return self
    
    def insertar_texto(self, texto="Marca de agua", posicion=(10, 10), color=(255, 255, 255)):
        """Inserta texto o marca de agua en la imagen."""
        if self._puede_aplicar_transformacion():
            draw = ImageDraw.Draw(self.imagen_procesada)
            
            # Ajustar color según el modo de la imagen
            if self.imagen_procesada.mode == "L":  # Escala de grises
                if isinstance(color, tuple):
                    # Convertir RGB a escala de grises usando luminancia
                    if len(color) >= 3:
                        color_gris = int(0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2])
                    else:
                        color_gris = color[0] if len(color) > 0 else 255
                else:
                    color_gris = color
                draw.text(posicion, texto, fill=color_gris)
            elif self.imagen_procesada.mode == "1":  # Blanco y negro
                # Para modo binario, usar solo 0 (negro) o 255 (blanco)
                color_binario = 255 if sum(color) > 384 else 0  # Umbral para decidir blanco/negro
                draw.text(posicion, texto, fill=color_binario)
            else:  # RGB, RGBA, etc.
                draw.text(posicion, texto, fill=color)
            
            self._registrar_transformacion(f"insertar_texto_{texto}")
        return self
    
    def convertir_formato(self, formato="JPEG"):
        """Convierte la imagen al formato especificado (JPG, PNG, TIF)."""
        if self._puede_aplicar_transformacion():
            if formato.upper() in ["JPG", "JPEG"]:
                if self.imagen_procesada.mode in ("RGBA", "LA", "P"):
                    self.imagen_procesada = self.imagen_procesada.convert("RGB")
            elif formato.upper() == "PNG":
                pass  # PNG soporta RGBA
            elif formato.upper() == "TIF" or formato.upper() == "TIFF":
                pass  # TIFF soporta varios modos
            else:
                print(f"⚠️ Formato no soportado: {formato}. Manteniendo actual.")
                return self
            self._registrar_transformacion(f"convertir_a_{formato.upper()}")
        return self
    
    def _puede_aplicar_transformacion(self):
        if len(self.transformaciones_aplicadas) >= self.MAX_TRANSFORMACIONES:
            print(f"⚠️ Máximo de {self.MAX_TRANSFORMACIONES} transformaciones alcanzado")
            return False
        return True
    
    def _registrar_transformacion(self, nombre):
        self.transformaciones_aplicadas.append(nombre)
        print(f"✅ Aplicada: {nombre} ({len(self.transformaciones_aplicadas)}/{self.MAX_TRANSFORMACIONES})")
    
    def convertir_y_comprimir_optimizado(self, formato="JPEG", calidad=85, nivel_compresion=9):
        """
        Versión optimizada de compresión con opciones de calidad.
        
        Args:
            formato (str): Formato de imagen ("JPEG", "PNG", "WEBP")
            calidad (int): Calidad para JPEG/WEBP (1-95, menor = más compresión)
            nivel_compresion (int): Nivel de compresión gzip (1-9, mayor = más compresión)
        """
        buffer = io.BytesIO()
        
        # Configurar opciones según formato
        save_options = {}
        if formato.upper() == "JPEG":
            save_options = {"quality": calidad, "optimize": True}
            # Convertir a RGB si es necesario para JPEG
            if self.imagen_procesada.mode in ("RGBA", "LA", "P"):
                img_to_save = self.imagen_procesada.convert("RGB")
            else:
                img_to_save = self.imagen_procesada
        elif formato.upper() == "PNG":
            save_options = {"optimize": True}
            img_to_save = self.imagen_procesada
        elif formato.upper() == "WEBP":
            save_options = {"quality": calidad, "optimize": True}
            img_to_save = self.imagen_procesada
        else:
            img_to_save = self.imagen_procesada
        
        # Guardar con opciones optimizadas
        img_to_save.save(buffer, format=formato.upper(), **save_options)
        datos = buffer.getvalue()
        
        # Comprimir con gzip (nivel máximo para XML)
        datos_gzip = gzip.compress(datos, compresslevel=nivel_compresion)
        datos_b64 = base64.b64encode(datos_gzip).decode("utf-8")
        
        # Mostrar estadísticas de compresión
        print(f"📊 Compresión - Original: {len(datos)/1024:.1f}KB → "
              f"Comprimido: {len(datos_gzip)/1024:.1f}KB → "
              f"Base64: {len(datos_b64)/1024:.1f}KB")
        
        return datos_b64
    
    def generar_xml_optimizado(self, archivo_salida="resultado_optimizado.xml", 
                              formato_salida="JPEG", calidad=75):
        """Genera XML con compresión optimizada."""
        if not self.imagen_procesada:
            print("⌐ No hay imagen para procesar")
            return None
        
        # Usar método de compresión optimizada
        b64_data = self.convertir_y_comprimir_optimizado(formato_salida, calidad)
        
        # Crear XML con metadatos adicionales
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
        
        # Guardar archivo
        tree = ET.ElementTree(root)
        tree.write(archivo_salida, encoding="utf-8", xml_declaration=True)
        
        # Mostrar estadísticas del archivo
        tamaño_archivo = os.path.getsize(archivo_salida) / 1024
        print(f"📄 XML optimizado generado: {archivo_salida} ({tamaño_archivo:.1f} KB)")
        return tree


# -------------------------------
# Ejemplos de uso
# -------------------------------

def ejemplo_carga_xml():
    """Ejemplo de carga desde XML."""
    print("=== EJEMPLO CARGA DESDE XML ===")
    
    # 1. Crear un XML inicial
    print("\n1. Creando XML inicial...")
    nodo1 = NodoOptimizado()
    nodo1.escala_grises().rotar(30)
    nodo1.generar_xml_optimizado("imagen_base.xml", "JPEG", 80)
    
    # 2. Cargar desde el XML generado y aplicar más transformaciones
    print("\n2. Cargando desde XML y aplicando nuevas transformaciones...")
    nodo2 = NodoOptimizado("imagen_base.xml")
    nodo2.redimensionar((150, 150)).reflejar("horizontal")
    nodo2.generar_xml_optimizado("imagen_procesada.xml", "PNG")
    
    # 3. Cargar nuevamente y continuar
    print("\n3. Cargando imagen procesada...")
    nodo3 = NodoOptimizado("imagen_procesada.xml")
    nodo3.desenfocar(1).insertar_texto("Final", (10, 10))
    nodo3.generar_xml_optimizado("imagen_final.xml", "JPEG", 90)
    
    print("\n✅ Ciclo completo de carga y procesamiento desde XML completado!")


def ejemplo_usando_prueba_lectura():
    """Ejemplo específico usando prueba_lectura.xml como entrada."""
    print("=== EJEMPLO USANDO PRUEBA_LECTURA.XML ===")
    
    # Verificar si existe el archivo
    if not os.path.exists("prueba_lectura.xml"):
        print("⚠️ No se encuentra prueba_lectura.xml, creando uno de ejemplo...")
        # Crear el archivo de ejemplo
        nodo_temp = NodoOptimizado()
        nodo_temp.escala_grises().rotar(30)
        nodo_temp.generar_xml_optimizado("prueba_lectura.xml", "JPEG", 30)
        print("✅ Archivo prueba_lectura.xml creado")
    
    print("\n1. Analizando prueba_lectura.xml...")
    # Mostrar información del archivo original
    lector = LectorXML("prueba_lectura.xml")
    lector.mostrar_informacion()
    
    print("\n2. Cargando imagen desde prueba_lectura.xml...")
    # Cargar la imagen desde el XML
    nodo = NodoOptimizado("prueba_lectura.xml")
    
    print("\n3. Aplicando nuevas transformaciones...")
    # Aplicar nuevas transformaciones a la imagen ya procesada
    nodo.redimensionar((400, 400))  # Redimensionar a 400x400
    nodo.reflejar("vertical")       # Reflejar verticalmente
    nodo.ajustar_brillo_contraste(1.2, 1.3)  # Aumentar brillo y contraste
    
    print("\n4. Generando nuevo XML con transformaciones adicionales...")
    # Generar nuevo XML con mejor calidad
    nodo.generar_xml_optimizado("imagen_transformada.xml", "PNG")
    
    print("\n5. Verificando resultado...")
    # Mostrar información del nuevo archivo
    lector_nuevo = LectorXML("imagen_transformada.xml")
    lector_nuevo.mostrar_informacion()
    
    print("\n6. Comparando tamaños de archivo...")
    # Comparar tamaños
    tamaño_original = os.path.getsize("prueba_lectura.xml") / 1024
    tamaño_nuevo = os.path.getsize("imagen_transformada.xml") / 1024
    print(f"📊 Archivo original: {tamaño_original:.1f} KB")
    print(f"📊 Archivo nuevo: {tamaño_nuevo:.1f} KB")
    print(f"📊 Diferencia: {tamaño_nuevo - tamaño_original:+.1f} KB")
    
    print("\n7. Extrayendo imagen final para verificación...")
    # Extraer la imagen final para verificación
    lector_nuevo.extraer_imagen(0, "resultado_final_verificacion.png")
    
    print("\n✅ Procesamiento completo de prueba_lectura.xml terminado!")
    print("📁 Archivos generados:")
    print("   - imagen_transformada.xml (XML con nuevas transformaciones)")
    print("   - resultado_final_verificacion.png (imagen final extraída)")


def ejemplo_cadena_procesamiento():
    """Ejemplo de cadena de procesamiento usando múltiples XMLs."""
    print("\n=== EJEMPLO CADENA DE PROCESAMIENTO ===")
    
    # Verificar archivo inicial
    if not os.path.exists("prueba_lectura.xml"):
        print("Creando prueba_lectura.xml inicial...")
        nodo_temp = NodoOptimizado()
        nodo_temp.escala_grises().rotar(30)
        nodo_temp.generar_xml_optimizado("prueba_lectura.xml", "JPEG", 30)
    
    # Etapa 1: Cargar y aplicar primeras transformaciones
    print("\nETAPA 1: Cargando prueba_lectura.xml y aplicando redimensionado...")
    nodo1 = NodoOptimizado("prueba_lectura.xml")
    nodo1.redimensionar((300, 300))
    nodo1.generar_xml_optimizado("etapa1.xml", "JPEG", 70)
    
    # Etapa 2: Cargar resultado anterior y aplicar efectos
    print("\nETAPA 2: Aplicando efectos de imagen...")
    nodo2 = NodoOptimizado("etapa1.xml")
    nodo2.ajustar_brillo_contraste(1.1, 1.2)
    nodo2.generar_xml_optimizado("etapa2.xml", "PNG")
    
    # Etapa 3: Cargar y finalizar con marca de agua
    print("\nETAPA 3: Añadiendo marca de agua final...")
    nodo3 = NodoOptimizado("etapa2.xml")
    # Usar color apropiado para escala de grises (valor único en lugar de RGB)
    nodo3.insertar_texto("PROCESADO", (10, 10), (255, 255, 0))  # Se convertirá automáticamente
    nodo3.generar_xml_optimizado("resultado_cadena_final.xml", "JPEG", 85)
    
    # Mostrar resumen de toda la cadena
    print("\n📊 RESUMEN DE LA CADENA DE PROCESAMIENTO:")
    archivos = ["prueba_lectura.xml", "etapa1.xml", "etapa2.xml", "resultado_cadena_final.xml"]
    
    for archivo in archivos:
        if os.path.exists(archivo):
            tamaño = os.path.getsize(archivo) / 1024
            # Leer transformaciones del XML
            try:
                tree = ET.parse(archivo)
                root = tree.getroot()
                imagen = root.find('imagen')
                transformaciones = imagen.get('transformaciones', 'Ninguna')
                total = imagen.get('total_transformaciones', '0')
                print(f"   📁 {archivo}: {tamaño:.1f}KB - {total} transformaciones: {transformaciones}")
            except:
                print(f"   📁 {archivo}: {tamaño:.1f}KB")
    
    print("\n✅ Cadena de procesamiento completada!")


def ejemplo_lector():
    """Ejemplo de uso del lector de XML."""
    print("\n=== EJEMPLO LECTOR XML ===")
    
    # Crear un XML de prueba primero
    nodo = NodoOptimizado("imagen_prueba.jpg")
    nodo.escala_grises().rotar(30)
    nodo.generar_xml_optimizado("prueba_lectura.xml", formato_salida="JPEG", calidad=30)
    
    # Leer y mostrar información
    lector = LectorXML("prueba_lectura.xml")
    lector.mostrar_informacion()
    lector.comparar_tamaños()
    lector.extraer_imagen(0, "imagen_recuperada.jpg")


def comparar_optimizaciones():
    """Compara diferentes niveles de optimización."""
    print("\n=== COMPARACIÓN DE OPTIMIZACIONES ===")
    
    nodo = NodoOptimizado()
    nodo.escala_grises().rotar(45)
    
    # Generar con diferentes calidades
    formatos = [
        ("JPEG", 95, "alta_calidad.xml"),
        ("JPEG", 75, "media_calidad.xml"), 
        ("JPEG", 50, "baja_calidad.xml"),
        ("PNG", 100, "png_optimizado.xml")
    ]
    
    for formato, calidad, archivo in formatos:
        nodo.generar_xml_optimizado(archivo, formato, calidad)
        tamaño = os.path.getsize(archivo) / 1024
        print(f"📁 {archivo}: {tamaño:.1f} KB")


if __name__ == "__main__":
    # Ejecutar el ejemplo específico usando prueba_lectura.xml
    ejemplo_usando_prueba_lectura()
    
    # También ejecutar ejemplo de cadena de procesamiento
    ejemplo_cadena_procesamiento()