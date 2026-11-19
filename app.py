import argparse,json,os
from pathlib import Path
from reviewer import analyze,evaluate,export_csv,parse_input
from web import ApiError,run

def make_dispatch():
    def dispatch(method,path,data,query):
        if method=='GET' and path=='/api/config':return {'llm_configured':bool(os.getenv('LLM_BASE_URL') and os.getenv('LLM_MODEL'))}
        if method=='POST' and path=='/api/analyze':
            rows=parse_input(data.get('source'),data.get('format','text'))
            result=analyze(rows,data.get('mode','baseline'));result['csv']=export_csv(result)
            return result
        raise ApiError('Not found.',404)
    return dispatch

def main():
    p=argparse.ArgumentParser(description='Four-label requirements quality review')
    sub=p.add_subparsers(dest='command',required=True);s=sub.add_parser('serve');s.add_argument('--port',type=int,default=8767)
    for cmd in ('analyze','evaluate'):
        q=sub.add_parser(cmd);q.add_argument('--input',required=True);q.add_argument('--mode',choices=['baseline','llm'],default='baseline');q.add_argument('--output')
        if cmd=='analyze':q.add_argument('--format',choices=['json','csv'],default='json')
    args=p.parse_args()
    try:
        if args.command=='serve':return run(make_dispatch(),args.port)
        path=Path(args.input);rows=parse_input(path.read_text(encoding='utf-8-sig'),path.suffix.lstrip('.') if path.suffix.lower() in ('.json','.csv') else 'text')
        result=evaluate(rows,args.mode) if args.command=='evaluate' else analyze(rows,args.mode)
        output=export_csv(result) if args.command=='analyze' and args.format=='csv' else json.dumps(result,indent=2)
        if args.output:Path(args.output).write_text(output,encoding='utf-8')
        else:print(output)
    except (ApiError,OSError) as exc:p.exit(2,f'Error: {exc}\n')
if __name__=='__main__':main()
