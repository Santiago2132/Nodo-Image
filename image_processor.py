import io
import gc
import threading
import psutil
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import List, Tuple, Dict, Any, Iterator
from collections import deque
from functools import lru_cache
import numpy as np
try:
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageDraw, ImageFont
    # Try to use Pillow-SIMD if available
    from PIL import __version__
    PILLOW_SIMD = 'post' in __version__
except ImportError:
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageDraw, ImageFont
    PILLOW_SIMD = False

from config import Config

class MemoryManager:
    """Gestor de memoria para procesamiento masivo"""
    
    def __init__(self):
        self.peak_usage = 0
        self.current_usage = 0
        
    def check_memory(self) -> bool:
        """Verifica si hay memoria suficiente"""
        memory = psutil.virtual_memory()
        self.current_usage = memory.used
        self.peak_usage = max(self.peak_usage, self.current_usage)
        return memory.available > Config.MEMORY_BUFFER_SIZE
    
    def force_cleanup(self):
        """Forzar limpieza de memoria"""
        gc.collect()

class ImageCache:
    """Cache LRU para imágenes procesadas"""
    
    def __init__(self, maxsize: int = 1000):
        self.cache = {}
        self.access_order = deque()
        self.maxsize = maxsize
        self.lock = threading.Lock()
    
    def get(self, key: str) -> bytes:
        with self.lock:
            if key in self.cache:
                self.access_order.remove(key)
                self.access_order.append(key)
                return self.cache[key]
        return None
    
    def put(self, key: str, value: bytes):
        with self.lock:
            if len(self.cache) >= self.maxsize:
                oldest = self.access_order.popleft()
                del self.cache[oldest]
            self.cache[key] = value
            self.access_order.append(key)

# Global optimized functions with caching
@lru_cache(maxsize=128)
def get_cached_font(font_size: int):
    """Cache de fuentes para evitar recargar"""
    try:
        font_path = Config.get_available_font()
        if font_path:
            return ImageFont.truetype(font_path, font_size)
    except:
        pass
    return ImageFont.load_default()

def numpy_to_pil(arr: np.ndarray) -> Image.Image:
    """Conversión optimizada numpy -> PIL"""
    return Image.fromarray(arr.astype('uint8'))

def pil_to_numpy(img: Image.Image) -> np.ndarray:
    """Conversión optimizada PIL -> numpy"""
    return np.array(img)

def process_single_image_optimized(args):
    """Procesamiento optimizado de imagen individual con numpy"""
    image_data, transformations, use_numpy = args
    
    try:
        img = Image.open(io.BytesIO(image_data))
        original_format = img.format or 'JPEG'
        
        # Convert to numpy for faster operations if enabled
        if use_numpy and Config.USE_NUMPY and len(transformations) > 2:
            img_array = pil_to_numpy(img)
            img = apply_numpy_transformations(img_array, transformations, img.mode)
            output_format = original_format
        else:
            output_format = original_format
            for trans in transformations:
                img = apply_single_transformation_optimized(img, trans)
                if trans['type'] == 'convert':
                    output_format = trans.get('format', 'JPEG').upper()
                    if output_format == 'JPG':
                        output_format = 'JPEG'
        
        return save_image_optimized(img, output_format)
        
    except Exception as e:
        raise Exception(f"Image processing error: {str(e)}")

def apply_numpy_transformations(img_array: np.ndarray, transformations: List[Dict], mode: str) -> Image.Image:
    """Aplicar transformaciones usando NumPy para mejor performance"""
    
    for trans in transformations:
        trans_type = trans['type']
        
        if trans_type == 'grayscale':
            if len(img_array.shape) == 3:
                # Convert RGB to grayscale using optimized weights
                weights = np.array([0.299, 0.587, 0.114])
                img_array = np.dot(img_array, weights).astype(np.uint8)
                
        elif trans_type == 'brightness_contrast':
            brightness = float(trans.get('brightness', 1.0))
            contrast = float(trans.get('contrast', 1.0))
            
            # Vectorized brightness/contrast adjustment
            img_array = img_array.astype(np.float32)
            img_array = img_array * contrast + (brightness - 1.0) * 128
            img_array = np.clip(img_array, 0, 255).astype(np.uint8)
            
        elif trans_type == 'invert':
            img_array = 255 - img_array
            
        # For complex transformations, fall back to PIL
        else:
            img = numpy_to_pil(img_array)
            img = apply_single_transformation_optimized(img, trans)
            img_array = pil_to_numpy(img)
    
    return numpy_to_pil(img_array)

def apply_single_transformation_optimized(img: Image.Image, trans: Dict) -> Image.Image:
    """Transformación optimizada individual"""
    trans_type = trans['type']
    
    if trans_type == 'grayscale':
        return img.convert('L')
        
    elif trans_type == 'resize':
        width = int(trans.get('width', img.width))
        height = int(trans.get('height', img.height))
        # Use fastest resampling for batch processing
        return img.resize((width, height), Image.NEAREST)
        
    elif trans_type == 'crop':
        left = max(0, int(trans.get('left', 0)))
        top = max(0, int(trans.get('top', 0)))
        right = min(img.width, int(trans.get('right', img.width)))
        bottom = min(img.height, int(trans.get('bottom', img.height)))
        return img.crop((left, top, right, bottom))
        
    elif trans_type == 'rotate':
        degrees = float(trans.get('degrees', 0))
        expand = trans.get('expand', False)  # False for speed
        return img.rotate(degrees, expand=expand, resample=Image.NEAREST)
        
    elif trans_type == 'reflect':
        axis = trans.get('axis', 'horizontal')
        return ImageOps.mirror(img) if axis == 'horizontal' else ImageOps.flip(img)
        
    elif trans_type == 'blur':
        radius = min(10, float(trans.get('radius', 2)))  # Limit radius for performance
        return img.filter(ImageFilter.GaussianBlur(radius))
        
    elif trans_type == 'sharpen':
        factor = max(0.5, min(3.0, float(trans.get('factor', 2.0))))
        return ImageEnhance.Sharpness(img).enhance(factor)
        
    elif trans_type == 'brightness_contrast':
        brightness = max(0.1, min(3.0, float(trans.get('brightness', 1.0))))
        contrast = max(0.1, min(3.0, float(trans.get('contrast', 1.0))))
        color = max(0.1, min(3.0, float(trans.get('color', 1.0))))
        
        img = ImageEnhance.Brightness(img).enhance(brightness)
        img = ImageEnhance.Contrast(img).enhance(contrast)
        if img.mode in ('RGB', 'RGBA'):
            img = ImageEnhance.Color(img).enhance(color)
        return img
        
    elif trans_type == 'watermark':
        return add_watermark_optimized(img, trans)
        
    elif trans_type == 'autocontrast':
        cutoff = float(trans.get('cutoff', 0))
        return ImageOps.autocontrast(img, cutoff=cutoff)
        
    elif trans_type == 'invert':
        return ImageOps.invert(img)
    
    return img

def add_watermark_optimized(img: Image.Image, trans: Dict) -> Image.Image:
    """Watermark optimizado con cache de fuentes"""
    text = trans.get('text', 'Watermark')
    position_str = trans.get('position', '(10,10)')
    font_size = int(trans.get('font_size', 20))
    opacity = int(trans.get('opacity', 128))
    color = trans.get('color', 'white')
    
    # Parse position optimized
    try:
        if isinstance(position_str, str) and ',' in position_str:
            coords = position_str.strip('()').split(',')
            position = (int(coords[0]), int(coords[1]))
        else:
            position = (10, 10)
    except:
        position = (10, 10)
    
    # Use cached font
    font = get_cached_font(font_size)
    
    # Optimized color mapping
    color_map = {
        'white': (255, 255, 255, opacity),
        'black': (0, 0, 0, opacity),
        'red': (255, 0, 0, opacity),
        'blue': (0, 0, 255, opacity),
        'green': (0, 255, 0, opacity)
    }
    text_color = color_map.get(color, (255, 255, 255, opacity))
    
    # Create minimal overlay
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.text(position, text, font=font, fill=text_color)
    
    return Image.alpha_composite(img, overlay)

def save_image_optimized(img: Image.Image, output_format: str) -> bytes:
    """Guardado optimizado de imagen"""
    output = io.BytesIO()
    
    if output_format == 'JPEG':
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            if img.mode == 'RGBA':
                background.paste(img, mask=img.split()[-1])
            else:
                background.paste(img)
            img = background
        elif img.mode == 'L':
            img = img.convert('RGB')
        
        img.save(output, format=output_format, 
                quality=Config.DEFAULT_QUALITY, 
                optimize=Config.OPTIMIZE_IMAGES,
                progressive=True)  # Progressive JPEG for better streaming
        
    elif output_format == 'PNG':
        if img.mode not in ('RGBA', 'LA', 'RGB', 'L'):
            img = img.convert('RGBA')
        img.save(output, format=output_format, 
                optimize=Config.OPTIMIZE_IMAGES,
                compress_level=6)  # Balance between speed and compression
        
    else:
        img.save(output, format=output_format)
    
    return output.getvalue()

class ImageProcessor:
    """Procesador de imágenes ultra-optimizado para batches masivos"""
    
    def __init__(self):
        self.status = {"state": "active", "error": None, "processed": 0, "total": 0}
        self.lock = threading.Lock()
        self.memory_manager = MemoryManager()
        self.cache = ImageCache(Config.CACHE_SIZE) if Config.ENABLE_IMAGE_CACHE else None
        
        # Pre-warm thread pools
        self.thread_pool = ThreadPoolExecutor(max_workers=Config.MAX_WORKERS)
        self.process_pool = ProcessPoolExecutor(max_workers=Config.NUM_CORES)
    
    def __del__(self):
        """Cleanup thread pools"""
        try:
            self.thread_pool.shutdown(wait=False)
            self.process_pool.shutdown(wait=False)
        except:
            pass
    
    def set_status(self, state: str, error: str = None, processed: int = None):
        """Thread-safe status update"""
        with self.lock:
            self.status["state"] = state
            if error is not None:
                self.status["error"] = error
            if processed is not None:
                self.status["processed"] = processed
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status with memory info"""
        with self.lock:
            status = self.status.copy()
            status["memory_usage"] = psutil.virtual_memory().percent
            status["cache_size"] = len(self.cache.cache) if self.cache else 0
            return status
    
    def process_images_batch(self, images: List[Tuple[bytes, List[Dict]]]) -> List[bytes]:
        """Ultra-optimized batch processing con chunking y memory management"""
        total_images = len(images)
        self.set_status("processing", None, 0)
        
        if total_images > Config.MAX_BATCH_SIZE:
            raise Exception(f"Batch size {total_images} exceeds maximum {Config.MAX_BATCH_SIZE}")
        
        try:
            # Determine optimal processing strategy
            avg_size = sum(len(img[0]) for img in images[:min(100, len(images))]) // min(100, len(images))
            chunk_size = Config.get_optimal_chunk_size(total_images, avg_size)
            use_numpy = Config.USE_NUMPY and total_images > 1000
            
            print(f"Processing {total_images} images in chunks of {chunk_size}, numpy: {use_numpy}")
            
            results = []
            processed_count = 0
            
            # Process in chunks to manage memory
            for i in range(0, total_images, chunk_size):
                chunk = images[i:i + chunk_size]
                
                # Memory check before processing chunk
                if not self.memory_manager.check_memory():
                    self.memory_manager.force_cleanup()
                    if not self.memory_manager.check_memory():
                        raise Exception("Insufficient memory for processing")
                
                # Process chunk with optimal executor
                if len(chunk) < 50:  # Small chunks use threads
                    chunk_results = self._process_chunk_threaded(chunk, use_numpy)
                else:  # Large chunks use processes
                    chunk_results = self._process_chunk_processes(chunk, use_numpy)
                
                results.extend(chunk_results)
                processed_count += len(chunk_results)
                
                self.set_status("processing", None, processed_count)
                
                # Periodic cleanup
                if i % (chunk_size * 4) == 0:
                    self.memory_manager.force_cleanup()
            
            self.set_status("active")
            return results
                
        except Exception as e:
            self.set_status("error", str(e))
            raise
    
    def _process_chunk_threaded(self, chunk: List[Tuple[bytes, List[Dict]]], use_numpy: bool) -> List[bytes]:
        """Procesar chunk con threads"""
        args = [(img_data, trans_list, use_numpy) for img_data, trans_list in chunk]
        
        with ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
            futures = [executor.submit(process_single_image_optimized, arg) for arg in args]
            return [future.result() for future in futures]
    
    def _process_chunk_processes(self, chunk: List[Tuple[bytes, List[Dict]]], use_numpy: bool) -> List[bytes]:
        """Procesar chunk con processes para mayor paralelismo"""
        args = [(img_data, trans_list, use_numpy) for img_data, trans_list in chunk]
        
        # Use existing process pool
        futures = [self.process_pool.submit(process_single_image_optimized, arg) for arg in args]
        return [future.result() for future in as_completed(futures)]