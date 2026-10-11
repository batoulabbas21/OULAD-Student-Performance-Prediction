"""Session 2 pattern: stable IRIs, RDFLib graph, typed literals, Turtle output."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'common'))
from pipeline import main

if __name__ == '__main__':
    sys.argv.insert(1, 'rdf')
    main()
