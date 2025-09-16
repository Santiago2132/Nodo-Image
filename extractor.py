import base64
import gzip
import io
import xml.etree.ElementTree as ET
from PIL import Image

# -------------------------------
# Función para decodificar imagen
# -------------------------------
def decodificar_imagen(data_codificada: str) -> Image.Image:
    # Decodificar Base64
    data_binaria = base64.b64decode(data_codificada)
    # Descomprimir Gzip
    data_descomprimida = gzip.decompress(data_binaria)
    # Crear imagen desde bytes
    return Image.open(io.BytesIO(data_descomprimida))

# -------------------------------
# Cargar XML y extraer imágenes
# -------------------------------
def procesar_xml(ruta_xml: str, formato_salida: str = "PNG"):
    tree = ET.parse(ruta_xml)
    root = tree.getroot()

    for i, nodo in enumerate(root.findall("imagen")):
        data = nodo.text.strip()
        img = decodificar_imagen(data)

        # Nombre de salida
        nombre_archivo = f"imagen_{i+1}.{formato_salida.lower()}"
        img.save(nombre_archivo, formato_salida.upper())
        print(f"✅ Imagen guardada como {nombre_archivo}")

# -------------------------------
# Ejemplo de uso
# -------------------------------
if __name__ == "__main__":
    ruta = "resultado_cadena_final.xml"  # tu archivo XML
    formato = "PNG"  # Cambia a "JPEG", "PNG" o "AVIF"
    procesar_xml(ruta, formato)
