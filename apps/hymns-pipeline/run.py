"""Run from the checkout without installing the Python package globally."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))
from hymns_pipeline.cli import main

if __name__ == '__main__':
    main()
