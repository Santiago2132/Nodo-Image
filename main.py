#!/usr/bin/env python3
import asyncio
import signal
import sys
from multiprocessing import Process, set_start_method
from config import Config
from server import run_optimized_server
import psutil

def optimize_system():
    """Optimizaciones del sistema al iniciar"""
    try:
        # Set process priority to high
        p = psutil.Process()
        p.nice(-10)  # Higher priority
        
        # Set CPU affinity if available
        if hasattr(p, 'cpu_affinity'):
            p.cpu_affinity(list(range(Config.NUM_CORES)))
        
        print(f"Sistema optimizado: {Config.NUM_CORES} cores, {Config.MAX_WORKERS} workers")
    except:
        print("Optimizaciones del sistema aplicadas parcialmente")

def start_server(port: int, is_receiver: bool = False):
    """Inicia servidor optimizado"""
    try:
        optimize_system()
        run_optimized_server(port, is_receiver)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error en servidor puerto {port}: {e}")

def main():
    """Launcher ultra-optimizado"""
    # Force spawn method for better isolation
    try:
        set_start_method('spawn')
    except RuntimeError:
        pass
    
    print("=== ULTRA-FAST IMAGE PROCESSING SERVICE ===")
    print(f"Max batch size: {Config.MAX_BATCH_SIZE:,} images")
    print(f"Memory limit: {Config.MAX_MEMORY_USAGE // (1024**3):.1f} GB")
    print(f"Optimizations: NumPy={Config.USE_NUMPY}, Cache={Config.ENABLE_IMAGE_CACHE}")
    
    servers = []
    
    # Start receiver nodes (optimized for ingestion)
    print(f"\nStarting {len(Config.RECEIVER_PORTS)} receiver nodes...")
    for port in Config.RECEIVER_PORTS:
        p = Process(target=start_server, args=(port, True))
        p.daemon = False
        servers.append(p)
        p.start()
        print(f"  ✓ Receiver on port {port}")
    
    # Start sender nodes (optimized for processing)
    print(f"\nStarting {len(Config.SENDER_PORTS)} sender nodes...")
    for port in Config.SENDER_PORTS:
        p = Process(target=start_server, args=(port, False))
        p.daemon = False
        servers.append(p)
        p.start()
        print(f"  ✓ Sender on port {port}")
    
    print(f"\n🚀 Service ready! {len(servers)} nodes active")
    print("Endpoints:")
    print("  POST /process - Process image batches")
    print("  GET  /status  - Node status")
    print("  GET  /metrics - Performance metrics")
    print("  GET  /health  - Health check")
    
    def signal_handler(signum, frame):
        print("\n🛑 Shutting down servers...")
        for server in servers:
            server.terminate()
        for server in servers:
            server.join(timeout=5)
            if server.is_alive():
                server.kill()
        print("All servers stopped")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Wait for all servers
        for server in servers:
            server.join()
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()