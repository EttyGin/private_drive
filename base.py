import threading
import socket
import select
import sys

from kubernetes import config
from contextlib import contextmanager
from kubernetes.client import Configuration
from kubernetes.client.api import core_v1_api
from kubernetes.stream import portforward

POD_NAME = 'jupyter-e'
NAMESPACE = 'jhub'
REMOTE_PORT = 22
LOCAL_PORT = 2222

# Event flag to signal server shutdown
shutdown_event = threading.Event()

def handle_connection(client_socket, api_instance):
    pf = portforward(
        api_instance.connect_get_namespaced_pod_portforward,
        POD_NAME,
        NAMESPACE,
        ports=str(REMOTE_PORT),
    )
    remote_socket = pf.socket(REMOTE_PORT)
    
    try:
        while not shutdown_event.is_set():
            rlist, _, _ = select.select([client_socket, remote_socket], [], [], 1.0)  # Add timeout to check shutdown_event
            for sock in rlist:
                data = sock.recv(4096)
                if data:
                    if sock is client_socket:
                        remote_socket.sendall(data)
                    else:
                        client_socket.sendall(data)
    except Exception as e:
        error_message = f"[ERROR] Connection error: {e}"
        # if hasattr(pf, 'error') and callable(getattr(pf, 'error')):
        error_message += f" - Pod error: {pf.error(REMOTE_PORT)}"
        print(error_message)
        # Signal server to shutdown on client error
        shutdown_event.set()
        raise
    finally:
        client_socket.close()
        remote_socket.close()


def portforward_server(core_v1):
    with create_server() as server:
        print(f"Listening on localhost:{LOCAL_PORT} and forwarding to pod {POD_NAME}:{REMOTE_PORT}")
        
        while not shutdown_event.is_set():
            readable, _, _ = select.select([server], [], [], 1.0)
            
            if server in readable:
                client_socket, client_addr = server.accept()
                print(f"\n[INFO] Connection accepted from {client_addr}")
                client_thread = threading.Thread(
                    target=handle_connection,
                    args=(client_socket, core_v1),
                    daemon=True
                )
                client_thread.start()
                print("[INFO] Port forward started...")
        
        print("[INFO] Server shutdown initiated")
        return
            
@contextmanager
def create_server():
    server = None
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('localhost', LOCAL_PORT))
        server.listen(5)
        yield server
    except KeyboardInterrupt:
        print("\n[INFO] Stop port forward (KeyboardInterrupt received)")
        shutdown_event.set()
    except Exception as e:
        print(f"[ERROR] Server error: {e}")
        shutdown_event.set()
    finally:
        if server:
            server.close()


if __name__ == '__main__':
    config.load_kube_config()
    c = Configuration.get_default_copy()
    c.assert_hostname = False
    Configuration.set_default(c)
    core_v1 = core_v1_api.CoreV1Api()
    portforward_server(core_v1)
    print("[INFO] Server shutdown complete")
    sys.exit(0)