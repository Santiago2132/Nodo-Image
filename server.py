import io
import asyncio
from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from image_processor import ImageProcessor
from xml_handler import XMLHandler
from config import Config

def create_app(is_receiver: bool = False) -> FastAPI:
    """Factory para crear aplicación FastAPI"""
    
    app = FastAPI(
        title="Image Processing Node",
        description="Nodo optimizado para procesamiento de imágenes",
        version="2.0.0"
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Instancia del procesador
    processor = ImageProcessor()
    xml_handler = XMLHandler()
    
    @app.post("/process")
    async def process_images(request: Request):
        """Procesa imágenes según transformaciones XML"""
        processor.set_status("receiving")
        
        try:
            # Obtener y validar XML
            body = await request.body()
            if len(body) > Config.MAX_IMAGE_SIZE:
                raise HTTPException(400, "Payload demasiado grande")
            
            xml_str = body.decode('utf-8')
            images = xml_handler.parse_xml(xml_str)
            
            if not images:
                raise HTTPException(400, "No se encontraron imágenes en el XML")
            
        except ValueError as e:
            processor.set_status("error", str(e))
            error_xml = xml_handler.create_error_response(str(e), 400)
            return StreamingResponse(
                io.BytesIO(error_xml.encode('utf-8')), 
                media_type="application/xml"
            )
        except Exception as e:
            processor.set_status("error", str(e))
            raise HTTPException(400, f"Error parsing XML: {str(e)}")
        
        try:
            # Procesar imágenes
            processed = processor.process_images_batch(images)
            
            # Generar respuesta XML
            response_xml = xml_handler.build_response_xml(processed, include_metadata=True)
            
            return StreamingResponse(
                io.BytesIO(response_xml.encode('utf-8')), 
                media_type="application/xml",
                headers={
                    "Content-Disposition": "attachment; filename=processed_images.xml",
                    "X-Processing-Time": str(asyncio.get_event_loop().time()),
                    "X-Images-Count": str(len(processed))
                }
            )
            
        except Exception as e:
            processor.set_status("error", str(e))
            error_xml = xml_handler.create_error_response(f"Processing error: {str(e)}", 500)
            return StreamingResponse(
                io.BytesIO(error_xml.encode('utf-8')), 
                media_type="application/xml"
            )
    
    @app.get("/status")
    async def get_status():
        """Obtiene estado del nodo"""
        status = processor.get_status()
        return StreamingResponse(
            io.BytesIO(xml_handler.create_status_response(status).encode('utf-8')),
            media_type="application/xml"
        )
    
    @app.get("/health")
    async def health_check():
        """Health check para balanceadores de carga"""
        status = processor.get_status()
        if status["state"] == "error":
            raise HTTPException(503, "Service unhealthy")
        return {"status": "healthy", "node_type": "receiver" if is_receiver else "sender"}
    
    @app.get("/info")
    async def get_info():
        """Información del nodo"""
        info = {
            "cores": Config.NUM_CORES,
            "threads": Config.NUM_THREADS,
            "max_workers": Config.MAX_WORKERS,
            "supported_formats": Config.SUPPORTED_FORMATS,
            "max_image_size": Config.MAX_IMAGE_SIZE,
            "node_type": "receiver" if is_receiver else "sender"
        }
        return StreamingResponse(
            io.BytesIO(xml_handler.create_status_response(info).encode('utf-8')),
            media_type="application/xml"
        )
    
    @app.get("/")
    async def root():
        """Endpoint raíz"""
        return {"message": "Image Processing Node", "type": "receiver" if is_receiver else "sender"}
    
    return app