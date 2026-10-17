"""Create a local password once; preserve an existing configuration."""
import secrets
from common import ROOT
def main():
    path=ROOT/'.env.integration'
    if path.exists(): print('Existing .env.integration retained.'); return
    text=(ROOT/'config/postgres/connection.env.example').read_text(encoding='utf-8')
    text=text.replace('replace-with-your-local-password',secrets.token_hex(24))
    with path.open('x',encoding='utf-8') as f: f.write(text)
    print('Created ignored .env.integration. Password is not printed.')
if __name__=='__main__': main()
