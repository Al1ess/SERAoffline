from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        # Кодируем в UTF-8
        html = '<h1>✅ SERVER WORKS!</h1><p>Port: 5100</p>'
        self.wfile.write(html.encode('utf-8'))
    
    def log_message(self, format, *args):
        # Тихий режим
        pass

print("🚀 Starting server on 0.0.0.0:5100")
print("🌐 Open in browser: http://155.212.171.112:5100")
server = HTTPServer(('0.0.0.0', 5100), Handler)
server.serve_forever()
