import multiprocessing
import os
import psutil

class Config:
    """Configuración optimizada para procesamiento masivo"""
    
    # Configuración de recursos extrema
    NUM_CORES = multiprocessing.cpu_count()
    AVAILABLE_RAM = psutil.virtual_memory().total
    
    # Optimización agresiva de threads
    NUM_THREADS = NUM_CORES * 4  # Más threads por core
    MAX_WORKERS = min(NUM_CORES * 8, 128)  # Cap para evitar overhead
    
    # Configuración de batch processing
    CHUNK_SIZE = 100  # Procesar en chunks para memory efficiency
    MAX_BATCH_SIZE = 1000000  # 1M images max
    
    # Memory management
    MAX_IMAGE_SIZE = 100 * 1024 * 1024  # 100MB por imagen
    MAX_MEMORY_USAGE = int(AVAILABLE_RAM * 0.8)  # 80% de RAM disponible
    MEMORY_BUFFER_SIZE = 1024 * 1024 * 512  # 512MB buffer
    
    # Configuración de puertos ampliada
    RECEIVER_PORTS = [8001, 8002, 8003, 8004]  # 4 receptores
    SENDER_PORTS = [8005, 8006, 8007, 8008, 8009, 8010]  # 6 emisores
    
    # Formatos optimizados
    SUPPORTED_FORMATS = ['JPEG', 'PNG', 'TIFF', 'BMP', 'GIF', 'WEBP']
    DEFAULT_QUALITY = 85  # Balance entre calidad y velocidad
    OPTIMIZE_IMAGES = True
    
    # Cache settings
    ENABLE_IMAGE_CACHE = True
    CACHE_SIZE = 1000
    
    # Configuración de fuentes para marcas de agua
    FONT_PATHS = [
        "/System/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "arial.ttf"
    ]
    
    # Timeouts optimizados
    PROCESSING_TIMEOUT = 300  # 5 minutos para batches grandes
    CONNECTION_TIMEOUT = 60
    
    # Performance tunning
    PILLOW_SIMD = True  # Use Pillow-SIMD if available
    USE_NUMPY = True    # NumPy optimizations
    PARALLEL_IO = True  # Parallel I/O operations
    
    @classmethod
    def get_available_font(cls):
        """Encuentra la primera fuente disponible con cache"""
        if not hasattr(cls, '_cached_font'):
            for font_path in cls.FONT_PATHS:
                if os.path.exists(font_path):
                    cls._cached_font = font_path
                    break
            else:
                cls._cached_font = None
        return cls._cached_font
    
    @classmethod
    def get_optimal_chunk_size(cls, batch_size: int, image_size_avg: int) -> int:
        """Calcula chunk size optimal basado en memoria disponible"""
        memory_per_image = image_size_avg * 3  # Factor de seguridad
        available_memory = cls.MAX_MEMORY_USAGE - cls.MEMORY_BUFFER_SIZE
        optimal_chunk = max(1, min(
            cls.CHUNK_SIZE,
            available_memory // (memory_per_image * cls.MAX_WORKERS),
            batch_size // cls.MAX_WORKERS
        ))
        return optimal_chunk