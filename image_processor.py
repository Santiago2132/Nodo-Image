import io
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple, Dict, Any
from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageDraw, ImageFont
from config import Config

# Global function for processing single image (needed for multiprocessing)
def process_single_image(image_data_and_transforms):
    """Global function to process a single image with transformations"""
    image_data, transformations = image_data_and_transforms
    return apply_transformations_static(image_data, transformations)

def apply_transformations_static(image_data: bytes, transformations: List[Dict]) -> bytes:
    """Static function to apply transformations to an image"""
    try:
        img = Image.open(io.BytesIO(image_data))
        output_format = img.format or 'JPEG'
        
        for trans in transformations:
            img = apply_single_transformation_static(img, trans)
            if trans['type'] == 'convert':
                output_format = trans.get('format', 'JPEG').upper()
                if output_format == 'JPG':
                    output_format = 'JPEG'
        
        return save_image_static(img, output_format)
        
    except Exception as e:
        raise Exception(f"Image processing error: {str(e)}")

def apply_single_transformation_static(img: Image.Image, trans: Dict) -> Image.Image:
    """Static function to apply a specific transformation"""
    trans_type = trans['type']
    
    if trans_type == 'grayscale':
        return img.convert('L')
        
    elif trans_type == 'resize':
        width = int(trans.get('width', img.width))
        height = int(trans.get('height', img.height))
        mode = trans.get('mode', 'LANCZOS')
        resample = getattr(Image, mode, Image.LANCZOS)
        return img.resize((width, height), resample)
        
    elif trans_type == 'crop':
        left = int(trans.get('left', 0))
        top = int(trans.get('top', 0))
        right = int(trans.get('right', img.width))
        bottom = int(trans.get('bottom', img.height))
        return img.crop((left, top, right, bottom))
        
    elif trans_type == 'rotate':
        degrees = float(trans.get('degrees', 0))
        expand = trans.get('expand', True)
        fillcolor = trans.get('fillcolor', None)
        return img.rotate(degrees, expand=expand, fillcolor=fillcolor)
        
    elif trans_type == 'reflect':
        axis = trans.get('axis', 'horizontal')
        return ImageOps.mirror(img) if axis == 'horizontal' else ImageOps.flip(img)
        
    elif trans_type == 'blur':
        blur_type = trans.get('blur_type', 'gaussian')
        if blur_type == 'gaussian':
            radius = float(trans.get('radius', 2))
            return img.filter(ImageFilter.GaussianBlur(radius))
        elif blur_type == 'motion':
            return img.filter(ImageFilter.BLUR)
        elif blur_type == 'box':
            radius = float(trans.get('radius', 2))
            return img.filter(ImageFilter.BoxBlur(radius))
        
    elif trans_type == 'sharpen':
        factor = float(trans.get('factor', 2.0))
        return ImageEnhance.Sharpness(img).enhance(factor)
        
    elif trans_type == 'brightness_contrast':
        brightness = float(trans.get('brightness', 1.0))
        contrast = float(trans.get('contrast', 1.0))
        color = float(trans.get('color', 1.0))
        img = ImageEnhance.Brightness(img).enhance(brightness)
        img = ImageEnhance.Contrast(img).enhance(contrast)
        img = ImageEnhance.Color(img).enhance(color)
        return img
        
    elif trans_type == 'watermark':
        return add_watermark_static(img, trans)
        
    elif trans_type == 'noise_reduction':
        return img.filter(ImageFilter.MedianFilter(size=3))
        
    elif trans_type == 'edge_enhance':
        strength = trans.get('strength', 'normal')
        if strength == 'more':
            return img.filter(ImageFilter.EDGE_ENHANCE_MORE)
        return img.filter(ImageFilter.EDGE_ENHANCE)
        
    elif trans_type == 'emboss':
        return img.filter(ImageFilter.EMBOSS)
        
    elif trans_type == 'find_edges':
        return img.filter(ImageFilter.FIND_EDGES)
        
    elif trans_type == 'autocontrast':
        cutoff = float(trans.get('cutoff', 0))
        return ImageOps.autocontrast(img, cutoff=cutoff)
        
    elif trans_type == 'equalize':
        return ImageOps.equalize(img)
        
    elif trans_type == 'invert':
        return ImageOps.invert(img)
        
    elif trans_type == 'posterize':
        bits = int(trans.get('bits', 4))
        return ImageOps.posterize(img, bits)
        
    elif trans_type == 'solarize':
        threshold = int(trans.get('threshold', 128))
        return ImageOps.solarize(img, threshold)
    
    return img

def add_watermark_static(img: Image.Image, trans: Dict) -> Image.Image:
    """Static function to add watermark to image"""
    text = trans.get('text', 'Watermark')
    position_str = trans.get('position', '(10,10)')
    font_size = int(trans.get('font_size', 20))
    opacity = int(trans.get('opacity', 128))
    color = trans.get('color', 'white')
    
    # Parse position
    if isinstance(position_str, str) and position_str.startswith('('):
        coords = position_str.strip('()').split(',')
        position = (int(coords[0]), int(coords[1]))
    else:
        position = (10, 10)
    
    # Create overlay for watermark
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Load font
    try:
        font_path = Config.get_available_font()
        if font_path:
            font = ImageFont.truetype(font_path, font_size)
        else:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    # Color mapping
    color_map = {
        'white': (255, 255, 255, opacity),
        'black': (0, 0, 0, opacity),
        'red': (255, 0, 0, opacity),
        'blue': (0, 0, 255, opacity),
        'green': (0, 255, 0, opacity)
    }
    text_color = color_map.get(color, (255, 255, 255, opacity))
    
    draw.text(position, text, font=font, fill=text_color)
    
    # Composite watermark onto image
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    return Image.alpha_composite(img, overlay)

def save_image_static(img: Image.Image, output_format: str) -> bytes:
    """Static function to save image in specified format"""
    output = io.BytesIO()
    
    # Format conversion
    if output_format == 'JPEG':
        if img.mode in ('RGBA', 'LA', 'P'):
            # Create white background for JPEG
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode == 'L':
            img = img.convert('RGB')
        img.save(output, format=output_format, quality=Config.DEFAULT_QUALITY, optimize=True)
        
    elif output_format == 'PNG':
        if img.mode not in ('RGBA', 'LA'):
            img = img.convert('RGBA')
        img.save(output, format=output_format, optimize=True)
        
    elif output_format in ['TIFF', 'TIF']:
        img.save(output, format='TIFF', compression='lzw')
        
    else:
        img.save(output, format=output_format)
    
    return output.getvalue()

class ImageProcessor:
    """Image processor optimized with multithreading"""
    
    def __init__(self):
        self.status = {"state": "active", "error": None}
        self.lock = threading.Lock()
    
    def set_status(self, state: str, error: str = None):
        """Thread-safe status update"""
        with self.lock:
            self.status["state"] = state
            self.status["error"] = error
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status"""
        with self.lock:
            return self.status.copy()
    
    def apply_transformations(self, image_data: bytes, transformations: List[Dict]) -> bytes:
        """Apply transformations to an image"""
        try:
            return apply_transformations_static(image_data, transformations)
        except Exception as e:
            self.set_status("error", str(e))
            raise
    
    def process_images_batch(self, images: List[Tuple[bytes, List[Dict]]]) -> List[bytes]:
        """Process multiple images using multithreading only"""
        self.set_status("processing")
        
        try:
            # Use ThreadPoolExecutor instead of ProcessPoolExecutor
            with ThreadPoolExecutor(max_workers=Config.NUM_THREADS) as executor:
                futures = [executor.submit(self.apply_transformations, img_data, trans_list) 
                          for img_data, trans_list in images]
                results = [future.result() for future in futures]
                
            self.set_status("active")
            return results
                
        except Exception as e:
            self.set_status("error", str(e))
            raise