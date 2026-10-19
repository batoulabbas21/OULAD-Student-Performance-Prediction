"""Ask one question, print the query, answer rows, checks and mode."""
import argparse,json
from access_layer import AccessLayer,Model

def main():
    p=argparse.ArgumentParser();p.add_argument('question',nargs='?');p.add_argument('--mode',choices=['catalog','live','record','replay'],default='catalog')
    p.add_argument('--env-file');p.add_argument('--model');p.add_argument('--list',action='store_true');p.add_argument('--show-prompt',action='store_true')
    a=p.parse_args();layer=AccessLayer(Model(a.mode,a.env_file,a.model,max_requests=3))
    if a.list:
        for e in layer.examples: print(e['question'])
        return
    if not a.question:p.error('Supply a question or --list.')
    if a.show_prompt: print(layer.prompt(a.question));return
    result=layer.answer(a.question,catalog=a.mode=='catalog');print(json.dumps({'mode':a.mode,**result},indent=2))
    if result['status']=='invalid':raise SystemExit(1)

if __name__=='__main__':main()
