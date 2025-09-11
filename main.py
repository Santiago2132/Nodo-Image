#!/usr/bin/env python3
import asyncio
import uvicorn
from multiprocessing import Process
from config import Config
from server import create_app

def start_server(port: int, is_receiver: bool = False):
    """Inicia un servidor en un puerto específico"""
    app = create_app(is_receiver=is_receiver)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

def main():
    """Inicia todos los servidores (2 receptores, 4 emisores)"""
    servers = []
    
    # Servidores receptores (puertos 8001-8002)
    for port in Config.RECEIVER_PORTS:
        p = Process(target=start_server, args=(port, True))
        servers.append(p)
        p.start()
        print(f"Servidor receptor iniciado en puerto {port}")
    
    # Servidores emisores (puertos 8003-8006)
    for port in Config.SENDER_PORTS:
        p = Process(target=start_server, args=(port, False))
        servers.append(p)
        p.start()
        print(f"Servidor emisor iniciado en puerto {port}")
    
    try:
        # Esperar a que todos los procesos terminen
        for server in servers:
            server.join()
    except KeyboardInterrupt:
        print("\nDeteniendo servidores...")
        for server in servers:
            server.terminate()
            server.join()

if __name__ == "__main__":
    main()