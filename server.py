import io
import asyncio
import gzip
from typing import Optional
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from image_processor import ImageProcessor
from xml_handler import XMLHandler
from config import Config
import uvicorn

def create_app(is_receiver: bool = False) -> FastAPI:
    """Factory optimizada para aplicación FastAPI"""
    
    app = FastAPI(
        title="Ultra-Fast Image Processing Node",
        description="Nodo ultra-optimizado para procesamiento masivo de imágenes",
        version="3.0.0"
    )
    
    # Middlewares optimizados
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Instancias singleton
    processor = ImageProcessor()
    xml_handler = XMLHandler()
    
    @app.post("/process")
    async def process_images(request: Request, background_tasks: BackgroundTasks):
        """Endpoint optimizado para procesamiento masivo"""
        processor.set_status("receiving")
        
        try:
            # Stream body for large payloads
            body = b""
            async for chunk in request.stream():
                body += chunk
                if len(body) > Config.MAX_IMAGE_SIZE * 1000:  # 1000 images max size
                    raise HTTPException(413, "Payload excesivamente grande")
            
            # Parse XML with streaming
            xml_str = body.decode('utf-8')
            images = xml_handler.parse_xml_optimized(xml_str)
            
            if not images:
                raise HTTPException(400, "No se encontraron imágenes válidas")
            
            if len(images) > Config.MAX_BATCH_SIZE:
                raise HTTPException(400, f"Batch excede límite de {Config.MAX_BATCH_SIZE}")
            
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
            # Background cleanup task
            background_tasks.add_task(cleanup_memory)
            
            # Process batch
            processed = processor.process_images_batch(images)
            
            # Stream response for large batches
            def generate_response():
                response_xml = xml_handler.build_response_xml_streaming(processed)
                for chunk in response_xml:
                    yield chunk.encode('utf-8')
            
            return StreamingResponse(
                generate_response(),
                media_type="application/xml",
                headers={
                    "Content-Disposition": "attachment; filename=processed_batch.xml",
                    "X-Images-Processed": str(len(processed)),
                    "X-Processing-Node": "receiver" if is_receiver else "sender"
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
        """Status con métricas de performance"""
        status = processor.get_status()
        return StreamingResponse(
            io.BytesIO(xml_handler.create_status_response(status).encode('utf-8')),
            media_type="application/xml"
        )
    
    @app.get("/health")
    async def health_check():
        """Health check optimizado"""
        status = processor.get_status()
        if status["state"] == "error":
            raise HTTPException(503, "Service unhealthy")
        
        return {
            "status": "healthy",
            "node_type": "receiver" if is_receiver else "sender",
            "memory_usage": status.get("memory_usage", 0),
            "processed": status.get("processed", 0)
        }
    
    @app.get("/metrics")
    async def get_metrics():
        """Métricas detalladas de rendimiento"""
        import psutil
        
        metrics = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "active_threads": Config.MAX_WORKERS,
            "cache_enabled": Config.ENABLE_IMAGE_CACHE,
            "pillow_simd": hasattr(processor, 'PILLOW_SIMD'),
            "numpy_enabled": Config.USE_NUMPY
        }
        
        return StreamingResponse(
            io.BytesIO(xml_handler.create_status_response(metrics).encode('utf-8')),
            media_type="application/xml"
        )
    
    @app.get("/info")
    async def get_info():
        """Información extendida del nodo"""
        info = {
            "cores": Config.NUM_CORES,
            "threads": Config.NUM_THREADS,
            "max_workers": Config.MAX_WORKERS,
            "chunk_size": Config.CHUNK_SIZE,
            "max_batch_size": Config.MAX_BATCH_SIZE,
            "supported_formats": Config.SUPPORTED_FORMATS,
            "max_image_size": Config.MAX_IMAGE_SIZE,
            "node_type": "receiver" if is_receiver else "sender",
            "optimizations": {
                "numpy": Config.USE_NUMPY,
                "cache": Config.ENABLE_IMAGE_CACHE,
                "parallel_io": Config.PARALLEL_IO,
                "memory_management": True
            }
        }
        return StreamingResponse(
            io.BytesIO(xml_handler.create_status_response(info).encode('utf-8')),
            media_type="application/xml"
        )
    
    @app.get("/")
    async def root():
        """Endpoint raíz con info del nodo"""
        return {
            "message": "Ultra-Fast Image Processing Node", 
            "type": "receiver" if is_receiver else "sender",
            "version": "3.0.0",
            "max_batch_size": Config.MAX_BATCH_SIZE
        }
    
    return app

async def cleanup_memory():
    """Background task para limpieza de memoria"""
    import gc
    gc.collect()

# Configuración optimizada de uvicorn
def run_optimized_server(port: int, is_receiver: bool = False):
    """Run server con configuración optimizada"""
    app = create_app(is_receiver=is_receiver)
    
    # Detectar sistema operativo para loop
    import sys
    loop_type = "uvloop" if sys.platform != "win32" else "asyncio"
    
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=False,  # Disable para mejor performance
        workers=1,  # Single worker per process
        loop=loop_type,  # Usar asyncio en Windows
        http="httptools" if sys.platform != "win32" else "h11",  # h11 para Windows
        limit_concurrency=1000,
        limit_max_requests=10000,
        timeout_keep_alive=30
    )
    
    server = uvicorn.Server(config)
    server.run()