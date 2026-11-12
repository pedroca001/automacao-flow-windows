"""Detached start of the scoped supplier controller; preserve existing processes."""
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

hold_path = ROOT / 'BLOQUEIO-FLOW.json'
if hold_path.exists() and json.loads(hold_path.read_text(encoding='utf-8')).get('status') == 'active':
    raise SystemExit('Flow unusual-activity hold is active. Preserve receipts and resolve the service restriction before restarting.')

controller = ROOT / 'executar-lote.py'
existing = []
for process in psutil.process_iter(['pid', 'name', 'cmdline']):
    cmdline = process.info['cmdline'] or []
    if process.info['name'].lower().startswith('python') and str(controller) in cmdline:
        existing.append(process.info['pid'])
if existing:
    raise SystemExit('Controller already running: ' + str(existing))
with (ROOT / 'execucao-windows.log').open('a', encoding='utf-8') as stream:
    process = subprocess.Popen([sys.executable, '-u', str(controller)], cwd=BASE,
        stdin=subprocess.DEVNULL, stdout=stream, stderr=stream, **process_options(detached=True))
(ROOT / 'launcher-windows.json').write_text(json.dumps({'pid': process.pid, 'started_at': time.time(),
    'controller': str(controller), 'project': json.loads((ROOT / 'plano-noturno.json').read_text(encoding='utf-8'))['project'],
    'target_videos': 1200, 'native_macro': str(BASE / 'scripts/flow_macro_windows.py')}, indent=2), encoding='utf-8')
print('Controller started:', process.pid)
print('Report:', ROOT / 'RELATORIO-NOTURNO.json')
subprocess.Popen([sys.executable, str(ROOT / 'manter-acordado.py')], cwd=BASE,
    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    **process_options(detached=True))
