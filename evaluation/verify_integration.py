"""Run the complete integration regression gate (use --fixture in CI)."""
import runpy
from pathlib import Path
import sys
directory=Path(__file__).resolve().parents[1]/'src/integration'
sys.path.insert(0,str(directory))
if __name__=='__main__': runpy.run_path(str(directory/'run.py'),run_name='__main__')
