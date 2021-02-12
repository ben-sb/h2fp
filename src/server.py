from states.stream_state import StreamState
from connection import Connection
import socket
import ssl
import threading
import traceback

class Server:
    def __init__(self):
        self.state = StreamState.IDLE
        self.server_sock = self.create_socket()

    def create_socket(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', 443))

        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(certfile="certs/localhost.crt", keyfile="certs/localhost.key")
        ctx.set_alpn_protocols(['h2'])

        return ctx.wrap_socket(sock, server_side=True)

    def start(self):
        print('Server listening on localhost:443')
        self.server_sock.listen(200)
        while True:
            try:
                s, _ = self.server_sock.accept()
                s.settimeout(10)
                conn = Connection(s)
                conn.start()
            except KeyboardInterrupt:
                break
            except Exception as e:
                print('Server encountered error: ', str(e))
                traceback.print_exc()