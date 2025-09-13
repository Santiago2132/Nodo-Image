import base64
import xml.etree.ElementTree as ET
from typing import List, Tuple, Dict, Any, Generator
from xml.sax import ContentHandler, make_parser
from xml.sax.handler import feature_namespaces
import io
import threading

class StreamingXMLParser(ContentHandler):
    """Parser XML optimizado para batches grandes"""
    
    def __init__(self):
        self.images = []
        self.current_image_data = None
        self.current_transformations = []
        self.current_transformation = None
        self.current_element = None
        self.current_text = ""
        self.in_data = False
        self.in_transformation = False
    
    def startElement(self, name, attrs):
        self.current_element = name
        self.current_text = ""
        
        if name == "image":
            self.current_image_data = None
            self.current_transformations = []
        elif name == "data":
            self.in_data = True
        elif name == "transformation":
            self.in_transformation = True
            trans_type = attrs.get('type', '')
            self.current_transformation = {'type': trans_type}
            # Add attributes as parameters
            for attr_name, attr_value in attrs.items():
                if attr_name != 'type':
                    self.current_transformation[attr_name] = self._parse_value(attr_value)
    
    def characters(self, content):
        self.current_text += content
    
    def endElement(self, name):
        if name == "data" and self.in_data:
            self.in_data = False
            try:
                self.current_image_data = base64.b64decode(self.current_text.strip())
            except Exception as e:
                raise ValueError(f"Error decodificando imagen base64: {str(e)}")
        
        elif name == "transformation" and self.in_transformation:
            self.in_transformation = False
            if self.current_transformation:
                self.current_transformations.append(self.current_transformation)
                self.current_transformation = None
        
        elif name == "image":
            if self.current_image_data and self.current_transformations:
                self.images.append((self.current_image_data, self.current_transformations))
        
        elif self.in_transformation and self.current_transformation and name != "transformation":
            # Add transformation parameter
            self.current_transformation[name] = self._parse_value(self.current_text.strip())
        
        self.current_text = ""
    
    def _parse_value(self, value: str) -> Any:
        """Convierte string a tipo apropiado"""
        value = value.strip()
        
        if value.lower() in ['true', 'false']:
            return value.lower() == 'true'
        
        if '.' in value and value.replace('.', '').replace('-', '').isdigit():
            return float(value)
        
        if value.replace('-', '').isdigit():
            return int(value)
        
        return value

class XMLHandler:
    """Manejador XML ultra-optimizado para batches masivos"""
    
    def __init__(self):
        self.lock = threading.Lock()
    
    def parse_xml_optimized(self, xml_str: str) -> List[Tuple[bytes, List[Dict]]]:
        """Parser optimizado para XML grandes con streaming"""
        if len(xml_str) > 10 * 1024 * 1024:  # > 10MB, use streaming parser
            return self._parse_xml_streaming(xml_str)
        else:
            return self.parse_xml(xml_str)
    
    def _parse_xml_streaming(self, xml_str: str) -> List[Tuple[bytes, List[Dict]]]:
        """Streaming parser para XML muy grandes"""
        parser = make_parser()
        parser.setFeature(feature_namespaces, 0)
        handler = StreamingXMLParser()
        parser.setContentHandler(handler)
        
        try:
            parser.parse(io.StringIO(xml_str))
            return handler.images
        except Exception as e:
            raise ValueError(f"Error parsing XML: {str(e)}")
    
    @staticmethod
    def parse_xml(xml_str: str) -> List[Tuple[bytes, List[Dict]]]:
        """Parser XML estándar optimizado"""
        try:
            root = ET.fromstring(xml_str)
        except ET.ParseError as e:
            raise ValueError(f"XML mal formado: {str(e)}")
        
        images = []
        
        for img_node in root.findall('image'):
            # Extraer datos de imagen
            data_node = img_node.find('data')
            if data_node is None or not data_node.text:
                continue
            
            try:
                img_data = base64.b64decode(data_node.text.strip())
            except Exception:
                continue
            
            # Extraer transformaciones optimizado
            trans_list = []
            for trans_node in img_node.findall('transformation'):
                trans_type = trans_node.get('type')
                if not trans_type:
                    continue
                
                trans_dict = {'type': trans_type}
                
                # Procesar parámetros y atributos
                for param in trans_node:
                    if param.text:
                        trans_dict[param.tag] = XMLHandler._parse_value(param.text)
                
                for attr_name, attr_value in trans_node.attrib.items():
                    if attr_name != 'type':
                        trans_dict[attr_name] = XMLHandler._parse_value(attr_value)
                
                trans_list.append(trans_dict)
            
            if trans_list:  # Only add if has transformations
                images.append((img_data, trans_list))
        
        return images
    
    def build_response_xml_streaming(self, processed_images: List[bytes]) -> Generator[str, None, None]:
        """Genera XML de respuesta por chunks para batches masivos"""
        chunk_size = 1000  # Images per chunk
        
        # Header
        yield f'<?xml version="1.0" encoding="UTF-8"?>\n'
        yield f'<response timestamp="{int(__import__("time").time())}" count="{len(processed_images)}">\n'
        
        # Process in chunks
        for i in range(0, len(processed_images), chunk_size):
            chunk = processed_images[i:i + chunk_size]
            
            for idx, img_bytes in enumerate(chunk, start=i):
                yield f'  <image id="{idx}" size="{len(img_bytes)}">\n'
                yield f'    <data>'
                
                # Stream base64 encoding in chunks
                b64_data = base64.b64encode(img_bytes).decode('utf-8')
                chunk_size_b64 = 8192
                for j in range(0, len(b64_data), chunk_size_b64):
                    yield b64_data[j:j + chunk_size_b64]
                
                yield f'</data>\n'
                yield f'    <metadata><format>{self._detect_format(img_bytes)}</format></metadata>\n'
                yield f'  </image>\n'
        
        yield '</response>'
    
    @staticmethod
    def build_response_xml(processed_images: List[bytes], include_metadata: bool = False) -> str:
        """XML de respuesta estándar para batches pequeños"""
        root = ET.Element('response')
        root.set('timestamp', str(int(__import__('time').time())))
        root.set('count', str(len(processed_images)))
        
        for idx, img_bytes in enumerate(processed_images):
            img_node = ET.SubElement(root, 'image')
            img_node.set('id', str(idx))
            img_node.set('size', str(len(img_bytes)))
            
            data_node = ET.SubElement(img_node, 'data')
            data_node.text = base64.b64encode(img_bytes).decode('utf-8')
            
            if include_metadata:
                meta_node = ET.SubElement(img_node, 'metadata')
                format_node = ET.SubElement(meta_node, 'format')
                format_node.text = XMLHandler._detect_format(img_bytes)
        
        return ET.tostring(root, encoding='unicode')
    
    @staticmethod
    def _detect_format(img_bytes: bytes) -> str:
        """Detección optimizada de formato"""
        if not img_bytes:
            return 'UNKNOWN'
        
        # Check first few bytes for magic numbers
        header = img_bytes[:12]
        
        if header.startswith(b'\xFF\xD8\xFF'):
            return 'JPEG'
        elif header.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'PNG'
        elif header.startswith((b'II*\x00', b'MM\x00*')):
            return 'TIFF'
        elif header.startswith(b'BM'):
            return 'BMP'
        elif header.startswith(b'GIF8'):
            return 'GIF'
        elif header.startswith(b'RIFF') and b'WEBP' in header:
            return 'WEBP'
        else:
            return 'UNKNOWN'
    
    @staticmethod
    def _parse_value(value: str) -> Any:
        """Parser de valores optimizado"""
        value = value.strip()
        
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        if value.replace('-', '').replace('.', '').isdigit():
            return float(value) if '.' in value else int(value)
        
        return value
    
    @staticmethod
    def create_error_response(error_msg: str, error_code: int = 500) -> str:
        """Respuesta de error optimizada"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<error code="{error_code}" timestamp="{int(__import__('time').time())}">
    <message>{error_msg}</message>
</error>'''
    
    @staticmethod
    def create_status_response(status: Dict[str, Any]) -> str:
        """Respuesta de estado optimizada"""
        timestamp = int(__import__('time').time())
        elements = []
        
        for key, value in status.items():
            val_str = str(value) if value is not None else 'null'
            elements.append(f'    <{key}>{val_str}</{key}>')
        
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<status timestamp="{timestamp}">
{chr(10).join(elements)}
</status>'''