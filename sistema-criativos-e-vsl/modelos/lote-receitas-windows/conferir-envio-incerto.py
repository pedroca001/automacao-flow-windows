"""Read-only evidence for an uncertain UI submission; never retries or edits state."""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / 'retomada-macro'))
from noturno_core import atomic, norm, read, validate_plan
from noturno_adapter import Adapter

cid = sys.argv[1]
plan = read(ROOT / 'plano-noturno.json')
state = read(ROOT / 'estado-noturno.json')
scene = state['scenes'][cid]
attempt = scene['attempts'][-1]
inventory = Adapter(ROOT, plan, validate_plan(plan)).inventory()
reference = attempt['reference']['id']
related = [v for v in inventory['videos'] if reference in v.get('refs', [])]
claimed = {s.get('video') for s in state['scenes'].values() if s.get('video')}
recent = [v for v in inventory['videos'] if v.get('created', [0])[0] >= attempt['started_at'] - 2]
evidence = {
    'at': time.time(), 'cid': cid, 'status_at_read': scene['status'],
    'attempt_number': attempt['number'], 'started_at': attempt['started_at'],
    'reference_id': reference, 'provider_video_count': len(inventory['videos']),
    'exact_matches': [v for v in related
                      if norm(v.get('prompt') or '') == norm(attempt['prompt'])
                      and set(v.get('refs', [])) == {reference}
                      and v.get('created', [0])[0] >= attempt['started_at'] - 2],
    'all_related_results': related,
    'recent_results': recent,
    'unclaimed_recent_results': [v for v in recent if v['id'] not in claimed],
    'recent_prompt_matches': [v for v in recent if norm(v.get('prompt') or '') == norm(attempt['prompt'])],
    'source_names': {s['id']: s['name'] for s in inventory['sources']},
    'generation_retried': False, 'state_changed': False,
}
path = ROOT / ('CONFERENCIA-INCERTO-' + cid + '-' + str(int(evidence['at'])) + '.json')
atomic(path, evidence)
print(json.dumps({'evidence': str(path), 'cid': cid, 'exact_matches': evidence['exact_matches'],
                  'related_count': len(related), 'recent_count': len(evidence['recent_results']),
                  'unclaimed_recent_results': evidence['unclaimed_recent_results'],
                  'recent_prompt_matches': evidence['recent_prompt_matches'],
                  'state_changed': False}))
