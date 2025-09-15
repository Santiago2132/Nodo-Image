import base64
import gzip
import io
import os
import xml.etree.ElementTree as ET
from PIL import Image, ImageOps, ImageEnhance, ImageDraw, ImageFilter


class Nodo:
    """
    Clase para manejar transformaciones de imágenes.
    Permite aplicar máximo 5 transformaciones y generar archivos XML.
    """
    
    def __init__(self, imagen_path=None):
        """
        Inicializa el nodo con una imagen.
        
        Args:
            imagen_path (str): Ruta de la imagen a procesar
        """
        self.imagen_original = None
        self.imagen_procesada = None
        self.transformaciones_aplicadas = []
        self.MAX_TRANSFORMACIONES = 5
        
        if imagen_path:
            self.cargar_imagen(imagen_path)
        else:
            self._crear_imagen_prueba()
    
    def cargar_imagen(self, imagen_path):
        """Carga una imagen desde archivo."""
        if os.path.exists(imagen_path):
            self.imagen_original = Image.open(imagen_path)
            self.imagen_procesada = self.imagen_original.copy()
            print(f"✅ Imagen cargada: {imagen_path}")
        else:
            print(f"⚠️ Imagen no encontrada: {imagen_path}. Creando imagen de prueba...")
            self._crear_imagen_prueba()
    
    def _crear_imagen_prueba(self):
        """Crea una imagen de prueba."""
        self.imagen_original = Image.new("RGB", (400, 400), color=(200, 200, 255))
        draw = ImageDraw.Draw(self.imagen_original)
        draw.rectangle([50, 50, 350, 350], outline=(100, 100, 100), width=3)
        draw.text((150, 180), "Imagen de prueba", fill=(0, 0, 0))
        self.imagen_procesada = self.imagen_original.copy()
        print("✅ Imagen de prueba creada")
    
    def reiniciar(self):
        """Reinicia las transformaciones aplicadas."""
        if self.imagen_original:
            self.imagen_procesada = self.imagen_original.copy()
            self.transformaciones_aplicadas = []
            print("✅ Transformaciones reiniciadas")
    
    # -------------------------------
    # Métodos de transformación
    # -------------------------------
    
    def escala_grises(self):
        """Convierte la imagen a escala de grises."""
        if self._puede_aplicar_transformacion():
            self.imagen_procesada = self.imagen_procesada.convert("L")
            self._registrar_transformacion("escala_grises")
        return self
    
    def redimensionar(self, size=(300, 300)):
        """Redimensiona la imagen."""
        if self._puede_aplicar_transformacion():
            self.imagen_procesada = self.imagen_procesada.resize(size)
            self._registrar_transformacion(f"redimensionar_{size[0]}x{size[1]}")
        return self
    
    def recortar(self, box=(50, 50, 250, 250)):
        """Recorta la imagen según las coordenadas especificadas."""
        if self._puede_aplicar_transformacion():
            self.imagen_procesada = self.imagen_procesada.crop(box)
            self._registrar_transformacion("recortar")
        return self
    
    def rotar(self, angle=45):
        """Rota la imagen el ángulo especificado."""
        if self._puede_aplicar_transformacion():
            self.imagen_procesada = self.imagen_procesada.rotate(angle)
            self._registrar_transformacion(f"rotar_{angle}°")
        return self
    
    def reflejar(self):
        """Refleja la imagen horizontalmente."""
        if self._puede_aplicar_transformacion():
            self.imagen_procesada = ImageOps.mirror(self.imagen_procesada)
            self._registrar_transformacion("reflejar")
        return self
    
    def desenfocar(self, radio=3):
        """Aplica desenfoque gaussiano."""
        if self._puede_aplicar_transformacion():
            self.imagen_procesada = self.imagen_procesada.filter(ImageFilter.GaussianBlur(radio))
            self._registrar_transformacion(f"desenfocar_{radio}")
        return self
    
    def perfilar(self):
        """Aplica filtro de perfilado (sharpen)."""
        if self._puede_aplicar_transformacion():
            self.imagen_procesada = self.imagen_procesada.filter(ImageFilter.SHARPEN)
            self._registrar_transformacion("perfilar")
        return self
    
    def ajustar_brillo_contraste(self, brillo=1.2, contraste=1.3):
        """Ajusta brillo y contraste."""
        if self._puede_aplicar_transformacion():
            img = ImageEnhance.Brightness(self.imagen_procesada).enhance(brillo)
            img = ImageEnhance.Contrast(img).enhance(contraste)
            self.imagen_procesada = img
            self._registrar_transformacion(f"brillo_contraste_{brillo}_{contraste}")
        return self
    
    def insertar_texto(self, texto="Marca de agua", posicion=(10, 10), color=(255, 0, 0)):
        """Inserta texto en la imagen."""
        if self._puede_aplicar_transformacion():
            # Asegurar que esté en RGB
            if self.imagen_procesada.mode != "RGB":
                self.imagen_procesada = self.imagen_procesada.convert("RGB")
            
            img_edit = self.imagen_procesada.copy()
            draw = ImageDraw.Draw(img_edit)
            draw.text(posicion, texto, fill=color)
            self.imagen_procesada = img_edit
            self._registrar_transformacion(f"texto_{texto}")
        return self
    
    # -------------------------------
    # Métodos auxiliares
    # -------------------------------
    
    def _puede_aplicar_transformacion(self):
        """Verifica si se puede aplicar otra transformación."""
        if len(self.transformaciones_aplicadas) >= self.MAX_TRANSFORMACIONES:
            print(f"⚠️ Máximo de {self.MAX_TRANSFORMACIONES} transformaciones alcanzado")
            return False
        return True
    
    def _registrar_transformacion(self, nombre):
        """Registra una transformación aplicada."""
        self.transformaciones_aplicadas.append(nombre)
        print(f"✅ Aplicada: {nombre} ({len(self.transformaciones_aplicadas)}/{self.MAX_TRANSFORMACIONES})")
    
    def mostrar_transformaciones(self):
        """Muestra las transformaciones aplicadas."""
        if self.transformaciones_aplicadas:
            print("🔄 Transformaciones aplicadas:")
            for i, trans in enumerate(self.transformaciones_aplicadas, 1):
                print(f"  {i}. {trans}")
        else:
            print("📝 No se han aplicado transformaciones")
    
    def guardar_imagen(self, ruta_salida="imagen_procesada.png"):
        """Guarda la imagen procesada."""
        if self.imagen_procesada:
            self.imagen_procesada.save(ruta_salida)
            print(f"💾 Imagen guardada: {ruta_salida}")
    
    def convertir_y_comprimir(self, formato="JPEG"):
        """
        Convierte la imagen a un formato, comprime con gzip
        y la devuelve en base64.
        """
        buffer = io.BytesIO()
        self.imagen_procesada.save(buffer, format=formato)
        datos = buffer.getvalue()
        datos_gzip = gzip.compress(datos)
        datos_b64 = base64.b64encode(datos_gzip).decode("utf-8")
        return datos_b64
    
    def generar_xml(self, archivo_salida="resultado.xml", formato_salida="JPEG"):
        """Genera un archivo XML con la imagen procesada."""
        if not self.imagen_procesada:
            print("❌ No hay imagen para procesar")
            return None
        
        # Codificar imagen
        b64_data = self.convertir_y_comprimir(formato_salida)
        
        # Crear XML
        root = ET.Element("imagenes")
        nodo = ET.SubElement(root, "imagen", {
            "formato": formato_salida,
            "transformaciones": ", ".join(self.transformaciones_aplicadas),
            "total_transformaciones": str(len(self.transformaciones_aplicadas))
        })
        nodo.text = b64_data
        
        # Guardar archivo
        tree = ET.ElementTree(root)
        tree.write(archivo_salida, encoding="utf-8", xml_declaration=True)
        print(f"📄 Archivo XML generado: {archivo_salida}")
        return tree


# -------------------------------
# Ejemplos de uso
# -------------------------------

def ejemplo_basico():
    """Ejemplo básico de uso del Nodo."""
    print("=== EJEMPLO BÁSICO ===")
    
    # Crear nodo (creará imagen de prueba automáticamente)
    nodo = Nodo()
    
    # Aplicar transformaciones de forma encadenada (máximo 5)
    nodo.escala_grises().redimensionar((250, 250)).rotar(30).reflejar().insertar_texto("¡Hola!")
    
    # Mostrar transformaciones aplicadas
    nodo.mostrar_transformaciones()
    
    # Generar XML
    nodo.generar_xml("ejemplo_basico.xml")
    
    # Guardar imagen procesada
    nodo.guardar_imagen("ejemplo_basico.png")


def ejemplo_con_imagen():
    """Ejemplo con imagen específica."""
    print("\n=== EJEMPLO CON IMAGEN ===")
    
    # Crear nodo con imagen específica (si no existe, usará imagen de prueba)
    nodo = Nodo("imagen_prueba.jpg")
    
    # Aplicar transformaciones paso a paso
    nodo.ajustar_brillo_contraste(1.5, 1.2)
    nodo.desenfocar(2)
    nodo.recortar((25, 25, 375, 375))
    nodo.insertar_texto("Procesada", posicion=(50, 50), color=(0, 255, 0))
    
    # Intentar aplicar una sexta transformación (será rechazada)
    nodo.rotar(45)
    nodo.perfilar()  # Esta será rechazada por exceder el límite
    
    nodo.mostrar_transformaciones()
    nodo.generar_xml("ejemplo_imagen.xml", "PNG")


def ejemplo_reinicio():
    """Ejemplo mostrando cómo reiniciar transformaciones."""
    print("\n=== EJEMPLO CON REINICIO ===")
    
    nodo = Nodo()
    
    # Aplicar algunas transformaciones
    nodo.escala_grises().rotar(90).reflejar()
    print("Después de 3 transformaciones:")
    nodo.mostrar_transformaciones()
    
    # Reiniciar y aplicar otras transformaciones
    nodo.reiniciar()
    nodo.redimensionar((200, 200)).desenfocar().insertar_texto("Reiniciado")
    print("\nDespués del reinicio:")
    nodo.mostrar_transformaciones()
    
    nodo.generar_xml("ejemplo_reinicio.xml")


if __name__ == "__main__":
    ejemplo_con_imagen()