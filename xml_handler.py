import base64
import xml.etree.ElementTree as ET
from typing import List, Tuple, Dict, Any

class XMLHandler:
    """Manejador de XML para entrada y salida"""
    
    @staticmethod
    def parse_xml(xml_str: str) -> List[Tuple[bytes, List[Dict]]]:
        """Parse XML de entrada y extrae imágenes con transformaciones"""
        try:
            root = ET.fromstring(xml_str)
        except ET.ParseError as e:
            raise ValueError(f"XML mal formado: {str(e)}")
        
        images = []
        
        for img_node in root.findall('image'):
            # Extraer datos de imagen
            data_node = img_node.find('data')
            if data_node is None or not data_node.text:
                raise ValueError("Nodo de datos de imagen faltante o vacío")
            
            try:
                img_data = base64.b64decode(data_node.text)
            except Exception as e:
                raise ValueError(f"Error decodificando imagen base64: {str(e)}")
            
            # Extraer transformaciones
            trans_list = []
            for trans_node in img_node.findall('transformation'):
                trans_type = trans_node.get('type')
                if not trans_type:
                    continue
                
                trans_dict = {'type': trans_type}
                
                # Procesar parámetros de transformación
                for param in trans_node:
                    value = param.text
                    if value:
                        trans_dict[param.tag] = XMLHandler._parse_value(value)
                
                # Procesar atributos del nodo transformación
                for attr_name, attr_value in trans_node.attrib.items():
                    if attr_name != 'type':
                        trans_dict[attr_name] = XMLHandler._parse_value(attr_value)
                
                trans_list.append(trans_dict)
            
            images.append((img_data, trans_list))
        
        return images
    
    @staticmethod
    def _parse_value(value: str) -> Any:
        """Convierte string a tipo apropiado"""
        value = value.strip()
        
        # Boolean
        if value.lower() in ['true', 'false']:
            return value.lower() == 'true'
        
        # Float
        if '.' in value and value.replace('.', '').replace('-', '').isdigit():
            return float(value)
        
        # Integer
        if value.replace('-', '').isdigit():
            return int(value)
        
        # String
        return value
    
    @staticmethod
    def build_response_xml(processed_images: List[bytes], include_metadata: bool = False) -> str:
        """Construye XML de respuesta con imágenes procesadas"""
        root = ET.Element('response')
        root.set('timestamp', str(int(__import__('time').time())))
        root.set('count', str(len(processed_images)))
        
        for idx, img_bytes in enumerate(processed_images):
            img_node = ET.SubElement(root, 'image')
            img_node.set('id', str(idx))
            img_node.set('size', str(len(img_bytes)))
            
            # Datos de imagen
            data_node = ET.SubElement(img_node, 'data')
            data_node.text = base64.b64encode(img_bytes).decode('utf-8')
            
            # Metadata opcional
            if include_metadata:
                meta_node = ET.SubElement(img_node, 'metadata')
                format_node = ET.SubElement(meta_node, 'format')
                format_node.text = XMLHandler._detect_format(img_bytes)
        
        return ET.tostring(root, encoding='unicode')
    
    @staticmethod
    def _detect_format(img_bytes: bytes) -> str:
        """Detecta el formato de imagen por magic bytes"""
        if img_bytes.startswith(b'\xFF\xD8\xFF'):
            return 'JPEG'
        elif img_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'PNG'
        elif img_bytes.startswith(b'II*\x00') or img_bytes.startswith(b'MM\x00*'):
            return 'TIFF'
        elif img_bytes.startswith(b'BM'):
            return 'BMP'
        elif img_bytes.startswith(b'GIF8'):
            return 'GIF'
        elif img_bytes.startswith(b'RIFF') and b'WEBP' in img_bytes[:12]:
            return 'WEBP'
        else:
            return 'UNKNOWN'
    
    @staticmethod
    def create_error_response(error_msg: str, error_code: int = 500) -> str:
        """Crea respuesta XML de error"""
        root = ET.Element('error')
        root.set('code', str(error_code))
        root.set('timestamp', str(int(__import__('time').time())))
        
        message_node = ET.SubElement(root, 'message')
        message_node.text = error_msg
        
        return ET.tostring(root, encoding='unicode')
    
    @staticmethod
    def create_status_response(status: Dict[str, Any]) -> str:
        """Crea respuesta XML de estado"""
        root = ET.Element('status')
        root.set('timestamp', str(int(__import__('time').time())))
        
        for key, value in status.items():
            node = ET.SubElement(root, key)
            node.text = str(value) if value is not None else 'null'
        
        return ET.tostring(root, encoding='unicode')