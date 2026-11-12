"""One immediate user-authorized resume; preserve future 30-minute cooldowns."""
import json
from pathlib import Path
import subprocess
import sys
import time
import psutil
import supervisor_30min as supervisor
from flow_platform import macro_processes, process_options
from noturno_core import atomic, read, redact

ROOT, BASE = supervisor.ROOT, supervisor.BASE
assert not (ROOT / 'PARAR').exists(), 'Preserve explicit user stop.'
if supervisor.running(supervisor.CONTROLLER):
    raise SystemExit('Controller already running; no duplicate instance started.')
assert not macro_processes(BASE / 'scripts/flow_macro_windows.py'), 'Native macro still running.'
old = supervisor.running(ROOT / 'supervisor_30min.py')
processes = []
for item in old:
    try:
        process = psutil.Process(item['pid'])
        assert process.create_time() == item['created_at']
        assert str(ROOT / 'supervisor_30min.py') in process.cmdline()
        process.terminate()
        processes.append(process)
    except psutil.NoSuchProcess:
        pass
_, alive = psutil.wait_procs(processes, timeout=10)
assert not alive, 'Supervisor did not stop; no browser action performed.'
at = time.time()
result = {}
try:
    result = supervisor.prepare_resume()
    if result['outcome'] == 'clear':
        launch = subprocess.run([sys.executable, str(ROOT / 'iniciar-lote.py')], cwd=BASE,
                                capture_output=True, text=True, timeout=30, **process_options())
        if launch.returncode:
            raise RuntimeError(launch.stderr or launch.stdout)
        result['launch'] = launch.stdout.strip()
except Exception as error:
    result = {'outcome': 'requires_review' if any(k in str(error).lower() for k in ('login', 'captcha', 'identity', 'manual review', 'requires review')) else 'cooldown_again',
              'error': redact(error)}
finally:
    status = read(ROOT / 'supervisor-status.json', {})
    status.update(at=time.time(), phase='manual_resume_attempt', resume_after=None,
                  immediate_resume_requested_at=at, immediate_resume_instruction='pode começar agr.',
                  future_cooldown_seconds=1800, immediate_result=result)
    atomic(ROOT / 'supervisor-status.json', status)
    atomic(ROOT / ('COMECO-AGORA-' + str(int(at)) + '.json'),
           {'at': at, 'user_instruction': 'pode começar agr.', 'result': result, 'future_cooldown_seconds': 1800})
if result['outcome'] not in ('manual', 'requires_review'):
    subprocess.run([sys.executable, str(ROOT / 'iniciar-supervisor-30min.py')], cwd=BASE,
                   check=True, **process_options())
print(json.dumps(result))
