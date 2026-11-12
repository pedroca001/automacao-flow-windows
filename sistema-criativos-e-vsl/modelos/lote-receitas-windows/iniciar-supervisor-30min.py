"""Start one detached supervisor for this exact 1200-video execution."""
import json
from pathlib import Path
import subprocess
import sys
import time
import psutil

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parents[1]
sys.path.insert(0, str(BASE / 'scripts'))
from flow_platform import process_options

script = ROOT / 'supervisor_30min.py'
for process in psutil.process_iter(['pid', 'cmdline']):
    if str(script) in (process.info['cmdline'] or []):
        raise SystemExit('Supervisor already running: ' + str(process.pid))
assert not (ROOT / 'PARAR').exists(), 'User stop must be preserved.'
with (ROOT / 'supervisor-30min.log').open('a', encoding='utf-8') as stream:
    process = subprocess.Popen([sys.executable, '-u', str(script)], cwd=BASE,
        stdin=subprocess.DEVNULL, stdout=stream, stderr=stream, **process_options(detached=True))
(ROOT / 'supervisor-processo.json').write_text(json.dumps({'pid': process.pid, 'at': time.time(),
    'script': str(script), 'cooldown_seconds': 1800}, indent=2), encoding='utf-8')
print('Supervisor started:', process.pid)
