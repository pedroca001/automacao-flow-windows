"""Resumo compacto de pendências, tentativas e QA, sem imprimir prompts completos."""
import argparse,json,time
from pathlib import Path
from core import read,reserved_generation_slots
from cli import locate

def brief(path):
    root=Path(path).parent
    state=read(root/'estado-personagens.json',{})
    counts={}
    issues=[]
    for cid,s in state.get('scenes',{}).items():
        counts[s['status']]=counts.get(s['status'],0)+1
        if s['status'] in ('uncertain','needs_review','failed','discarded'):
            issues.append({'scene':cid,'status':s['status'],'reason':s.get('reason'),'attempts':len(s['attempts']),
                           'response_errors':[e for r in s['attempts'][-1].get('response_receipts',[]) for e in r['errors']] if s['attempts'] else []})
    print(json.dumps({'status':state.get('status'),'counts':counts,'deliveries':len(state.get('deliveries',{})),
                      'discarded':state.get('discarded',{}),'issues':issues,
                      'inflight':sum(counts.get(k,0) for k in ('rendering','confirming','submitting')),
                      'reserved_unknown':reserved_generation_slots(state.get('scenes',{}),state.get('uncertain_reservations',{}),time.time()),'local_processing':counts.get('checking',0),
                      'macro_performance':[{'scene':cid,**a['performance']} for cid,s in state.get('scenes',{}).items() for a in s.get('attempts',[]) if a.get('performance')],
                      'reviews':[{'scene':r.get('scene'),'status':r.get('status'),'reason':r.get('reason'),'attempt':r.get('attempt')} for f in sorted((root/'revisoes').glob('*.json')) for r in [read(f)]]},ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plano');a=p.parse_args();brief(locate(a.plano))
