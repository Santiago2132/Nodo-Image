import multiprocessing
import os

class Config:
    """Configuración global del sistema"""
    
    # Configuración de recursos
    NUM_CORES = 2
    NUM_THREADS = multiprocessing.cpu_count() * 2  # Configurable basado en CPU
    MAX_WORKERS = NUM_CORES * NUM_THREADS
    
    # Puertos de comunicación
    RECEIVER_PORTS = [8001, 8002]  # 2 puertos receptores
    SENDER_PORTS = [8003, 8004, 8005, 8006]  # 4 puertos emisores
    
    # Configuración de imágenes
    MAX_IMAGE_SIZE = 50 * 1024 * 1024  # 50MB máximo por imagen
    SUPPORTED_FORMATS = ['JPEG', 'PNG', 'TIFF', 'BMP', 'GIF', 'WEBP']
    DEFAULT_QUALITY = 95
    
    # Configuración de fuentes para marcas de agua
    FONT_PATHS = [
        "/System/Library/Fonts/Arial.ttf",  # macOS
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
        "C:/Windows/Fonts/arial.ttf",  # Windows
        "arial.ttf"  # Local
    ]
    
    # Configuración de timeouts
    PROCESSING_TIMEOUT = 30  # segundos
    
    @classmethod
    def get_available_font(cls):
        """Encuentra la primera fuente disponible"""
        for font_path in cls.FONT_PATHS:
            if os.path.exists(font_path):
                return font_path
        return None