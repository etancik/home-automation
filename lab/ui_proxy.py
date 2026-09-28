"""Fixed TCP forwarder: expose the private HA UI without giving HA an egress route."""
import select
import socket
import socketserver

class Forward(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            with socket.create_connection(('ha',8123),timeout=10) as upstream:
                upstream.settimeout(None)
                peers={self.request:upstream,upstream:self.request}
                while True:
                    ready,_,_=select.select(list(peers),[],[],60)
                    if not ready: continue
                    for source in ready:
                        data=source.recv(65536)
                        if not data: return
                        peers[source].sendall(data)
        except (OSError,ConnectionError):
            return

class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address=True
    daemon_threads=True

with Server(('0.0.0.0',8123),Forward) as server:
    server.serve_forever()
