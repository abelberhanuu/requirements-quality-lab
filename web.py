"""Loopback-only JSON/static server for local portfolio demonstrations."""
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import json
import secrets

class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status

class Response:
    def __init__(self, body, content_type='application/json; charset=utf-8', status=200):
        self.body, self.content_type, self.status = body, content_type, status

def server(dispatch, port=0):
    token = secrets.token_urlsafe(24)
    static = Path(__file__).parent / 'static'
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Do not record user-submitted records or requirements.

        def reply(self, body, status=200, content_type='application/json; charset=utf-8'):
            if isinstance(body, (dict, list)):
                body = json.dumps(body, allow_nan=False)
            data = body if isinstance(body, bytes) else str(body).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(data)

        def handle_request(self):
            try:
                hosts = {f'localhost:{self.server.server_port}', f'127.0.0.1:{self.server.server_port}'}
                if self.headers.get('Host') not in hosts:
                    raise ApiError('Use the localhost URL printed by the application.', 403)
                url = urlsplit(self.path)
                if self.command == 'GET' and url.path == '/api/session':
                    return self.reply({'token': token})
                body = None
                if self.command != 'GET':
                    origin = self.headers.get('Origin')
                    if origin and origin not in {f'http://{h}' for h in hosts}:
                        raise ApiError('Cross-origin writes are not allowed.', 403)
                    if not secrets.compare_digest(self.headers.get('X-Local-Token', '').encode('utf-8'), token.encode('utf-8')):
                        raise ApiError('Missing or expired local session token.', 403)
                    if self.headers.get_content_type() != 'application/json':
                        raise ApiError('Send application/json.', 415)
                    try:
                        size = int(self.headers.get('Content-Length', '0'))
                    except ValueError:
                        raise ApiError('Invalid content length.')
                    if not 0 < size <= 262144:
                        raise ApiError('Request must contain at most 256 KiB.', 413)
                    try:
                        body = json.loads(self.rfile.read(size))
                    except (ValueError, UnicodeError):
                        raise ApiError('Invalid JSON.')
                    if not isinstance(body, dict):
                        raise ApiError('JSON body must be an object.')
                if url.path.startswith('/api/'):
                    value = dispatch(self.command, url.path, body, url.query)
                    if isinstance(value, Response):
                        return self.reply(value.body, value.status, value.content_type)
                    return self.reply(value)
                if self.command != 'GET':
                    raise ApiError('Not found.', 404)
                names = {'/': ('index.html', 'text/html; charset=utf-8'),
                         '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                         '/style.css': ('style.css', 'text/css; charset=utf-8')}
                if url.path not in names:
                    raise ApiError('Not found.', 404)
                name, mime = names[url.path]
                return self.reply((static / name).read_bytes(), content_type=mime)
            except ApiError as exc:
                self.reply({'error': str(exc)}, exc.status)
            except Exception:
                self.reply({'error': 'The request could not be completed. Check the local configuration.'}, 500)

        do_GET = do_POST = do_PATCH = do_DELETE = handle_request
    return HTTPServer(('127.0.0.1', port), Handler)

def run(dispatch, port):
    app = server(dispatch, port)
    print(f'Open http://127.0.0.1:{app.server_port} (local demonstration only)', flush=True)
    try:
        app.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        app.server_close()
