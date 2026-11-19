import json,threading,unittest
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from web import server,ApiError

class LocalHTTP(unittest.TestCase):
    def setUp(self):
        def dispatch(method,path,body,query):
            if path=='/api/echo':return body or {'ok':True}
            raise ApiError('Not found.',404)
        self.app=server(dispatch)
        self.thread=threading.Thread(target=self.app.serve_forever,kwargs={'poll_interval':.01},daemon=True)
        self.thread.start();self.base=f'http://127.0.0.1:{self.app.server_port}'
        with urlopen(self.base+'/api/session') as response:self.token=json.load(response)['token']
    def tearDown(self):
        self.app.shutdown();self.thread.join();self.app.server_close()
    def status(self,request):
        try:
            with urlopen(request) as response:return response.status
        except HTTPError as exc:return exc.code
    def test_host_guard_static_allowlist_and_headers(self):
        self.assertEqual(self.status(Request(self.base+'/api/echo',headers={'Host':'untrusted.example'})),403)
        self.assertEqual(self.status(self.base+'/../../app.py'),404)
        with urlopen(self.base+'/app.js') as response:
            self.assertIn("default-src 'self'",response.headers['Content-Security-Policy'])
            self.assertEqual(response.headers['X-Content-Type-Options'],'nosniff')
    def test_writes_need_token_and_json(self):
        self.assertEqual(self.status(Request(self.base+'/api/echo',b'{}',{'Content-Type':'application/json'})),403)
        headers={'X-Local-Token':self.token,'Content-Type':'text/plain'}
        self.assertEqual(self.status(Request(self.base+'/api/echo',b'{}',headers)),415)
        headers['Content-Type']='application/json'
        self.assertEqual(self.status(Request(self.base+'/api/echo',b'{',headers)),400)
        self.assertEqual(self.status(Request(self.base+'/api/echo',b'[]',headers)),400)
        self.assertEqual(self.status(Request(self.base+'/api/echo',b'{"value":7}',headers)),200)
    def test_cross_origin_and_large_body_rejected(self):
        headers={'X-Local-Token':self.token,'Content-Type':'application/json','Origin':'https://elsewhere.example'}
        self.assertEqual(self.status(Request(self.base+'/api/echo',b'{}',headers)),403)
        headers.pop('Origin')
        self.assertEqual(self.status(Request(self.base+'/api/echo',b'x'*262145,headers)),413)
if __name__=='__main__':unittest.main()

