import os,sys
from pathlib import Path
implementation=os.environ.get('M4_CONTRACT_IMPLEMENTATION')
if implementation:
    sys.path.insert(0,str(Path(implementation)/'scripts'))
sys.path.insert(0,str(Path(__file__).parent))
