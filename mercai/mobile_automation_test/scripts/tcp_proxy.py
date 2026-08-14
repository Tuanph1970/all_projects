#!/usr/bin/env python3
"""
Simple TCP proxy to forward local port to remote server.
Used for E2E testing to allow Android emulator to access remote API.
"""
import socket
import threading
import sys
import signal

REMOTE_HOST = '112.213.91.103'
REMOTE_PORT = 8002
LOCAL_PORT = 8002

running = True

def signal_handler(sig, frame):
    global running
    running = False
    print('\nShutting down proxy...')
    sys.exit(0)

def handle_client(client_socket, remote_host, remote_port):
    """Handle a single client connection by proxying to remote server."""
    try:
        # Connect to remote server
        remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_socket.settimeout(30)
        remote_socket.connect((remote_host, remote_port))

        def forward(src, dst, name):
            try:
                while running:
                    data = src.recv(4096)
                    if not data:
                        break
                    dst.sendall(data)
            except Exception as e:
                pass
            finally:
                try:
                    src.close()
                except:
                    pass
                try:
                    dst.close()
                except:
                    pass

        # Start bidirectional forwarding
        client_to_remote = threading.Thread(target=forward, args=(client_socket, remote_socket, 'client->remote'))
        remote_to_client = threading.Thread(target=forward, args=(remote_socket, client_socket, 'remote->client'))

        client_to_remote.daemon = True
        remote_to_client.daemon = True

        client_to_remote.start()
        remote_to_client.start()

        client_to_remote.join()
        remote_to_client.join()

    except Exception as e:
        print(f'Error handling client: {e}')
    finally:
        try:
            client_socket.close()
        except:
            pass

def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server.bind(('0.0.0.0', LOCAL_PORT))
        server.listen(50)
        print(f'TCP Proxy started: localhost:{LOCAL_PORT} -> {REMOTE_HOST}:{REMOTE_PORT}')
        print('Press Ctrl+C to stop')

        server.settimeout(1.0)  # Allow periodic checks for shutdown

        while running:
            try:
                client_socket, addr = server.accept()
                print(f'Connection from {addr}')
                client_handler = threading.Thread(target=handle_client, args=(client_socket, REMOTE_HOST, REMOTE_PORT))
                client_handler.daemon = True
                client_handler.start()
            except socket.timeout:
                continue
            except Exception as e:
                if running:
                    print(f'Accept error: {e}')

    except Exception as e:
        print(f'Server error: {e}')
    finally:
        server.close()
        print('Proxy stopped')

if __name__ == '__main__':
    main()
