#!/usr/bin/env python3
"""
TCP Proxy for Maestro Testing
Forwards traffic between local machine and backend services running in Docker

Usage:
    python tcp_proxy.py --local-port 8001 --remote-port 8001
    python tcp_proxy.py --local-port 8002 --remote-port 8002
"""

import argparse
import socket
import threading
import sys

def forward(src, dst, name):
    """Forward data from src to dst socket"""
    try:
        while True:
            data = src.recv(4096)
            if not data:
                break
            dst.sendall(data)
    except Exception as e:
        print(f"[{name}] Connection closed: {e}")
    finally:
        src.close()
        dst.close()

def proxy_connection(local_conn, remote_host, remote_port, name):
    """Handle a single proxy connection"""
    try:
        remote_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_conn.connect((remote_host, remote_port))
        
        print(f"[{name}] Connected: {local_conn.getpeername()} <-> {remote_host}:{remote_port}")
        
        # Start forwarding threads
        threading.Thread(
            target=forward,
            args=(local_conn, remote_conn, f"{name}->"),
            daemon=True
        ).start()
        
        threading.Thread(
            target=forward,
            args=(remote_conn, local_conn, f"<-{name}"),
            daemon=True
        ).start()
        
    except Exception as e:
        print(f"[{name}] Error: {e}")
        local_conn.close()

def start_proxy(local_port, remote_host, remote_port):
    """Start the TCP proxy server"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind(('0.0.0.0', local_port))
        server.listen(5)
        print(f"[*] Proxy listening on port {local_port} -> {remote_host}:{remote_port}")
        
        connection_count = 0
        
        while True:
            local_conn, addr = server.accept()
            connection_count += 1
            name = f"Conn-{connection_count}"
            
            threading.Thread(
                target=proxy_connection,
                args=(local_conn, remote_host, remote_port, name),
                daemon=True
            ).start()
            
    except KeyboardInterrupt:
        print("\n[*] Shutting down proxy...")
        server.close()

def main():
    parser = argparse.ArgumentParser(description='TCP Proxy for Maestro Testing')
    parser.add_argument('--local-port', type=int, required=True, help='Local port to listen on')
    parser.add_argument('--remote-host', type=str, default='localhost', help='Remote host to forward to')
    parser.add_argument('--remote-port', type=int, required=True, help='Remote port to forward to')
    
    args = parser.parse_args()
    
    print(f"=== TCP Proxy ===")
    print(f"Local:  0.0.0.0:{args.local_port}")
    print(f"Remote: {args.remote_host}:{args.remote_port}")
    print("=================")
    print("")
    
    start_proxy(args.local_port, args.remote_host, args.remote_port)

if __name__ == '__main__':
    main()
