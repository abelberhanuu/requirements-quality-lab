import json,tempfile,threading,unittest
from http.server import BaseHTTPRequestHandler,HTTPServer
from pathlib import Path
from urllib.request import Request,urlopen
from reviewer import analyze,baseline,parse_input,evaluate,validate_model_result,llm,export_csv,normalize
from web import ApiError,server
from app import make_dispatch

class Review(unittest.TestCase):
    def test_four_defect_types_and_clear_control(self):
        cases=[('The system shall','incomplete'),('The system shall provide world-class service.','meaningless'),('The system shall respond quickly.','ambiguous')]
        for text,label in cases:self.assertIn(label,baseline([{'text':text}])[0]['labels'])
        self.assertEqual(baseline([{'text':'The service shall respond within 2 seconds.'}])[0]['labels'],[])
    def test_redundancy_preserves_number_and_negation_distinctions(self):
        rows=[{'text':'The system shall lock after 5 failures.'},{'text':'THE SYSTEM SHALL LOCK AFTER 5 FAILURES!'},{'text':'The system shall lock after 6 failures.'},{'text':'The system shall not lock after 5 failures.'}]
        r=baseline(rows)
        self.assertIn('redundant',r[1]['labels'])
        self.assertNotIn('redundant',r[2]['labels']);self.assertNotIn('redundant',r[3]['labels'])
    def test_input_validation_csv_json_and_unique_ids(self):
        self.assertEqual(len(parse_input('id,text\nA,The system shall export CSV.','csv')),1)
        self.assertEqual(parse_input('[{"text":"The system shall export CSV."}]','json')[0]['text'],'The system shall export CSV.')
        for rows in [[],[{'text':''}],[{'id':'A','text':'a'},{'id':'A','text':'b'}],[{'text':3}],['abc']]:
            with self.assertRaises(ApiError):normalize(rows)
        with self.assertRaises(ApiError):parse_input('bad','json')
    def test_evaluation_is_multilabel_and_scoped(self):
        rows=[{'text':'The system shall respond quickly.','expected_labels':'ambiguous'},{'text':'The system shall export CSV.','expected_labels':''}]
        m=evaluate(rows);self.assertEqual(m['sample_count'],2);self.assertEqual(m['micro']['tp'],1);self.assertEqual(m['micro']['fp'],0)
        with self.assertRaises(ApiError):evaluate([{'text':'The system shall export CSV.'}])
    def test_model_output_validation_and_csv_escape(self):
        rows=normalize([{'id':'A','text':'=danger'}])
        good={'results':[{'id':'A','labels':['incomplete'],'reason':'Missing behavior','suggested_rewrite':'Specify the behavior.'}]}
        r=validate_model_result(good,rows);self.assertEqual(r[0]['text'],'=danger')
        self.assertIn("'=danger",export_csv({'results':r}))
        for bad in [{'results':[]},{'results':[{'id':'A','labels':['made-up']}]},{'results':good['results']*2}]:
            with self.assertRaises(ApiError):validate_model_result(bad,rows)
    def test_mock_llm_protocol_and_redirect_policy(self):
        received=[]
        class Provider(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                data=json.loads(self.rfile.read(int(self.headers['Content-Length'])));received.append(data)
                rows=json.loads(data['messages'][1]['content'])['requirements']
                result={'results':[{'id':r['id'],'labels':[],'reason':'Mock review','suggested_rewrite':'Keep as written.'} for r in rows]}
                payload=json.dumps({'choices':[{'message':{'content':json.dumps(result)}}]}).encode()
                self.send_response(200);self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
        app=HTTPServer(('127.0.0.1',0),Provider);t=threading.Thread(target=app.serve_forever,kwargs={'poll_interval':.01},daemon=True);t.start()
        try:
            rows=normalize([{'text':'The system shall export CSV.'}])
            results=llm(rows,f'http://127.0.0.1:{app.server_port}/v1','mock')
            self.assertEqual(results[0]['reason'],'Mock review');self.assertEqual(received[0]['response_format'],{'type':'json_object'})
            with self.assertRaises(ApiError):llm(rows,'http://public.example/v1','mock')
            with self.assertRaises(ApiError):llm(rows,'https://name:secret@example.com/v1','mock')
        finally:app.shutdown();t.join();app.server_close()
    def test_http_review_and_oversized_input(self):
        app=server(make_dispatch());t=threading.Thread(target=app.serve_forever,kwargs={'poll_interval':.01},daemon=True);t.start();base=f'http://127.0.0.1:{app.server_port}'
        try:
            with urlopen(base+'/api/session') as r:token=json.load(r)['token']
            payload=json.dumps({'source':'The system shall respond quickly.','mode':'baseline','format':'text'}).encode()
            with urlopen(Request(base+'/api/analyze',payload,{'Content-Type':'application/json','X-Local-Token':token})) as r:
                self.assertEqual(json.load(r)['summary']['by_label']['ambiguous'],1)
            with self.assertRaises(ApiError):parse_input('x'*180001)
        finally:app.shutdown();t.join();app.server_close()
if __name__=='__main__':unittest.main()
