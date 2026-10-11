"""Session 1 pattern: descriptive profiles plus explicit relationship checks.

Use --raw for original core tables; --ydata for additional lab-style HTML reports.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'common'))
from pipeline import main

if __name__ == '__main__':
    sys.argv.insert(1, 'profile')
    main()
