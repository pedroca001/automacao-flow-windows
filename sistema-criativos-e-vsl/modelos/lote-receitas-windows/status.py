import json
from collections import Counter
from pathlib import Path
import time
import psutil

root = Path(__file__).resolve().parent
sync = json.loads((root / 'PREFLIGHT-SINCRONIZACAO.json').read_text(encoding='utf-8'))
state = json.loads((root / 'estado-noturno.json').read_text(encoding='utf-8'))
launch = json.loads((root / 'launcher-windows.json').read_text(encoding='utf-8'))
try:
    process = psutil.Process(launch['pid'])
    controller_live = process.is_running() and str(root / 'executar-lote.py') in process.cmdline()
    controller_process = {'pid': process.pid, 'created_at': process.create_time(), 'command': process.cmdline()}
except psutil.Error:
    controller_live, controller_process = False, None
supervisor_path = root / 'supervisor-status.json'
supervisor = json.loads(supervisor_path.read_text(encoding='utf-8')) if supervisor_path.exists() else {}
try:
    supervisor_process = psutil.Process(supervisor['pid'])
    supervisor_live = supervisor_process.is_running() and str(root / 'supervisor_30min.py') in supervisor_process.cmdline()
except (psutil.Error, KeyError):
    supervisor_live = False
print(json.dumps({'at': time.time(), 'controller_alive': controller_live, 'controller_process': controller_process,
    'state': state['status'], 'stop_reason': state.get('stop_reason'),
    'supervisor_alive': supervisor_live,
    'supervisor': {k: supervisor[k] for k in ('pid', 'phase', 'at', 'cooldown_seconds', 'resume_after', 'reason') if k in supervisor},
    'cooldown_remaining_seconds': max(0, round(supervisor['resume_after'] - time.time())) if supervisor_live and supervisor.get('phase') == 'cooldown' and supervisor.get('resume_after') else None,
    'source_verified': sync['verified_images'], 'source_errors': sync['errors'][:3],
    'videos': dict(Counter(v['status'] for v in state['videos'].values())),
    'scenes': dict(Counter(s['status'] for s in state['scenes'].values())),
    'active_scenes': [{'id': cid, 'status': s['status'], 'attempts': len(s['attempts']), 'video': s.get('video')}
                      for cid, s in state['scenes'].items() if s['status'] not in ('pending', 'blocked', 'complete')][:12],
    'recent_events': state['events'][-3:]}, ensure_ascii=True))
