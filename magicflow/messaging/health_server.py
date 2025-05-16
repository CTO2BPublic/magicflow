from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from magicflow.libs.logging_service import LoggingService

logger = LoggingService().getLogger(__name__)

class HealthHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, dispatcher=None, **kwargs):
        self.dispatcher = dispatcher
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path == '/health':
            if self.dispatcher and not self.dispatcher.stopped():
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'OK')
            else:
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Service Unhealthy')
        else:
            self.send_response(404)
            self.end_headers()

def run_health_server(dispatcher, port=8080):
    def handler(*args, **kwargs):
        return HealthHandler(*args, dispatcher=dispatcher, **kwargs)
    
    server = HTTPServer(('', port), handler)
    logger.info(f"Starting health server on port {port}")
    server.serve_forever()

def start_health_server(dispatcher, port=8080):
    health_thread = threading.Thread(target=run_health_server, args=(dispatcher, port), daemon=True)
    health_thread.start()
    return health_thread 