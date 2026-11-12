"""Detached source checker; the checker never operates the Flow browser."""
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

script = ROOT / 'preparar-lote.py'
for process in psutil.process_iter(['pid', 'name', 'cmdline']):
    if (process.info['name'] or '').lower().startswith('python') and str(script) in (process.info['cmdline'] or []):
        raise SystemExit('Source checker already running: ' + str(process.pid))
with (ROOT / 'sincronizacao.log').open('a', encoding='utf-8') as log:
    process = subprocess.Popen([sys.executable, '-u', str(script), '--watch'], cwd=BASE,
        stdin=subprocess.DEVNULL, stdout=log, stderr=log, **process_options(detached=True))
(ROOT / 'sincronizacao-processo.json').write_text(json.dumps({'pid': process.pid, 'at': time.time(),
    'script': str(script), 'generation_capability': False}), encoding='utf-8')
print('Source checker started:', process.pid)
