"""Local browser page plus the Session 7 TEXT2SPARQL GET contract on port 8007."""
import argparse,json
from http.server import BaseHTTPRequestHandler,HTTPServer
from urllib.parse import parse_qs,urlparse
from common import DATASET
from access_layer import AccessLayer,Model
from pathlib import Path

def ui(layer,mode):
    folder=Path(__file__).resolve().parent/'ui'
    counts=layer.grounding['direct_counts'];prefix='https://example.org/oulad/schema#'
    data={'mode':mode,'dataset':DATASET,'examples':layer.examples,
          'stats':{'students':counts.get(prefix+'Student',0),
                   'enrollments':counts.get(prefix+'Enrollment',0),
                   'records':counts.get(prefix+'AssessmentRecord',0)}}
    page=(folder/'index.html').read_text(encoding='utf-8')
    page=page.replace('__APP_CSS__',(folder/'style.css').read_text(encoding='utf-8'))
    page=page.replace('__APP_JS__',(folder/'app.js').read_text(encoding='utf-8'))
    return page.replace('__APP_DATA__',json.dumps(data).replace('<','\\u003c'))


def create_server(layer,mode='catalog',port=8007,host='127.0.0.1'):
    class Handler(BaseHTTPRequestHandler):
        def respond(self,status,value,content_type='application/json; charset=utf-8'):
            body=(value if isinstance(value,str) else json.dumps(value)).encode('utf-8');self.send_response(status)
            self.send_header('Content-Type',content_type);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
        def do_GET(self):
            url=urlparse(self.path);args=parse_qs(url.query)
            if url.path=='/health':self.respond(200,{'status':'ready','mode':mode,'dataset':DATASET});return
            if url.path!='/':self.respond(404,{'error':'Unknown path'});return
            if not args:self.respond(200,ui(layer,mode),'text/html; charset=utf-8');return
            question=args.get('question',[''])[0];dataset=args.get('dataset',[DATASET])[0]
            if dataset!=DATASET or not question.strip() or len(question)>1000:self.respond(400,{'error':'Supply a question of 1–1,000 characters and dataset='+DATASET});return
            try:
                result=layer.answer(question,catalog=mode=='catalog');query=result['query']
                if query is None:
                    reason=' '.join(result['reason'].split())
                    query='# '+reason+'\nSELECT * WHERE { FILTER(false) }'
                self.respond(200,{'dataset':DATASET,'question':question,'mode':mode,**result,'query':query})
            except (RuntimeError,ValueError) as e:self.respond(503,{'error':str(e)})
        def log_message(self,*args):pass # Questions are not written to an access log.
    return HTTPServer((host,port),Handler)

def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['catalog','live','record','replay'],default='catalog');p.add_argument('--port',type=int,default=8007)
    p.add_argument('--host',choices=['127.0.0.1','0.0.0.0'],default='127.0.0.1');p.add_argument('--env-file');p.add_argument('--model');p.add_argument('--max-requests',type=int,default=45);a=p.parse_args()
    server=create_server(AccessLayer(Model(a.mode,a.env_file,a.model,a.max_requests)),a.mode,a.port,a.host)
    print(f'Open http://127.0.0.1:{a.port} | mode={a.mode} | Ctrl+C stops the server.',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
