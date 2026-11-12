"""Read-only check of the current provider generation IDs; never submit."""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / 'retomada-macro'))
from noturno_core import read, validate_plan
from noturno_adapter import Adapter

state = read(ROOT / 'estado-noturno.json')
plan = read(ROOT / 'plano-noturno.json')
active = {cid: s for cid, s in state['scenes'].items()
          if s['status'] == 'rendering' and s.get('video')}
adapter = Adapter(ROOT, plan, validate_plan(plan))
checks = {}
ids = list(active)
for start in range(0, len(ids), 3):
    checks.update(adapter.status({cid: active[cid] for cid in ids[start:start + 3]}))
print(json.dumps({'at': time.time(), 'state_updated_at': state['updated_at'],
    'provider': checks,
    'reserved': [{'id': cid, **{k: s.get(k) for k in ('status', 'video', 'render_started_at', 'submitted_at', 'reason', 'reserve', 'server_ready')}}
                 for cid, s in state['scenes'].items() if s.get('reserve') or s['status'] in ('rendering', 'submitted', 'submitting')],
    'failed': [{'id': cid, 'reason': s.get('reason'), 'detail': s.get('detail'), 'video': s.get('video')}
               for cid, s in state['scenes'].items() if s['status'] == 'failed'],
    'input_sent': False}))
