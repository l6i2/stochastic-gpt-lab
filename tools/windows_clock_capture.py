"""Windows external capture entry point; same evidence format as the analyzer."""
from pathlib import Path
import runpy
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'python'))
if __name__ == '__main__':
    runpy.run_module('simultaneous_clock_capture', run_name='__main__')
