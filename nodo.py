import base64
import io
import multiprocessing
import threading
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageDraw, ImageFont
import xml.etree.ElementTree as ET
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import requests  # For client testing

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Parameters for cores and threads
NUM_CORES = 2
NUM_THREADS = 2

# Node status
STATUS = {"state": "active", "error": None}
lock = threading.Lock()

def set_status(state: str, error: str = None):
    with lock:
        STATUS["state"] = state
        STATUS["error"] = error

def apply_transformations(image_data: bytes, transformations: list) -> bytes:
    try:
        img = Image.open(io.BytesIO(image_data))
        output_format = img.format or 'JPEG'  # Default format
        
        for trans in transformations:
            if trans['type'] == 'grayscale':
                img = img.convert('L')
            elif trans['type'] == 'resize':
                width, height = trans.get('width', img.width), trans.get('height', img.height)
                img = img.resize((int(width), int(height)))
            elif trans['type'] == 'crop':
                left, top, right, bottom = int(trans['left']), int(trans['top']), int(trans['right']), int(trans['bottom'])
                img = img.crop((left, top, right, bottom))
            elif trans['type'] == 'rotate':
                degrees = float(trans.get('degrees', 0))
                img = img.rotate(degrees, expand=True)
            elif trans['type'] == 'reflect':
                axis = trans.get('axis', 'horizontal')
                img = ImageOps.mirror(img) if axis == 'horizontal' else ImageOps.flip(img)
            elif trans['type'] == 'blur':
                radius = float(trans.get('radius', 2))
                img = img.filter(ImageFilter.GaussianBlur(radius))
            elif trans['type'] == 'sharpen':
                factor = float(trans.get('factor', 2.0))
                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(factor)
            elif trans['type'] == 'brightness_contrast':
                brightness = float(trans.get('brightness', 1.0))
                contrast = float(trans.get('contrast', 1.0))
                img = ImageEnhance.Brightness(img).enhance(brightness)
                img = ImageEnhance.Contrast(img).enhance(contrast)
            elif trans['type'] == 'watermark':
                text = trans.get('text', 'Watermark')
                position_str = trans.get('position', '(0,0)')
                # Parse position string like "(10,20)"
                if isinstance(position_str, str) and position_str.startswith('('):
                    coords = position_str.strip('()').split(',')
                    position = (int(coords[0]), int(coords[1]))
                else:
                    position = (0, 0)
                font_size = int(trans.get('font_size', 20))
                draw = ImageDraw.Draw(img)
                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except:
                    font = ImageFont.load_default()
                draw.text(position, text, font=font, fill=(255, 255, 255, 128))
            elif trans['type'] == 'convert':
                format_name = trans.get('format', 'JPEG').upper()
                if format_name == 'JPG': 
                    format_name = 'JPEG'
                output_format = format_name
                
        output = io.BytesIO()
        # Convert to RGB if saving as JPEG and image has transparency
        if output_format == 'JPEG' and img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        elif output_format == 'JPEG' and img.mode == 'L':
            # Grayscale to RGB for JPEG
            img = img.convert('RGB')
        img.save(output, format=output_format, quality=95)
        return output.getvalue()
    except Exception as e:
        set_status("error", str(e))
        raise

def process_image(args):
    img_data, trans_list = args
    return apply_transformations(img_data, trans_list)

def parse_xml(xml_str: str):
    root = ET.fromstring(xml_str)
    images = []
    for img_node in root.findall('image'):
        img_b64 = img_node.find('data').text
        img_data = base64.b64decode(img_b64)
        trans_list = []
        for trans_node in img_node.findall('transformation'):
            trans_type = trans_node.get('type')
            trans_dict = {'type': trans_type}
            for param in trans_node:
                try:
                    # Try to convert to number if possible
                    value = param.text
                    if value and value.replace('.', '').replace('-', '').isdigit():
                        trans_dict[param.tag] = float(value) if '.' in value else int(value)
                    else:
                        trans_dict[param.tag] = value
                except:
                    trans_dict[param.tag] = param.text
            trans_list.append(trans_dict)
        images.append((img_data, trans_list))
    return images

def build_response_xml(processed_images: list):
    root = ET.Element('response')
    for idx, img_bytes in enumerate(processed_images):
        img_node = ET.SubElement(root, 'image')
        img_node.set('id', str(idx))
        data_node = ET.SubElement(img_node, 'data')
        data_node.text = base64.b64encode(img_bytes).decode('utf-8')
    return ET.tostring(root, encoding='unicode')

@app.post("/process")
async def process_images(request: Request):
    set_status("processing")
    try:
        xml_str = await request.body()
        images = parse_xml(xml_str.decode('utf-8'))
    except Exception as e:
        set_status("error", str(e))
        raise HTTPException(status_code=400, detail=f"Invalid XML: {str(e)}")
    
    try:
        # Simplified processing without nested multiprocessing/threading
        processed = []
        for img_data, trans_list in images:
            result = apply_transformations(img_data, trans_list)
            processed.append(result)
        
        set_status("active")
    except Exception as e:
        set_status("error", str(e))
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    
    response_xml = build_response_xml(processed)
    return StreamingResponse(io.BytesIO(response_xml.encode('utf-8')), media_type="application/xml")

@app.get("/status")
async def get_status():
    with lock:
        return JSONResponse(content=STATUS)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)