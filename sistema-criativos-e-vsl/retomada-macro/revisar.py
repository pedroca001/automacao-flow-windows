"""Registra uma revisão visual explícita, sem alterar o estado do controlador."""
import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
QA = ROOT / 'qa'
OUTPUT = Path('/Users/pedrobassi/Downloads/teste 20 de outubro/Entrega')


def read(path):
    return json.loads(path.read_text()) if path.exists() else {}


def save(path, data):
    temporary = path.with_suffix('.review.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    os.replace(temporary, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['aprovar', 'rejeitar'])
    parser.add_argument('items', nargs='+', help='CID:Rxx da grade efetivamente vista')
    parser.add_argument('--nota', required=True)
    args = parser.parse_args()
    state = read(ROOT / 'spec.json.state.json')['cenas']
    items = []
    for value in args.items:
        cid, revision = value.split(':R')
        scene = state[cid]
        assert scene.get('done') and Path(scene['file']).is_file(), 'Cena não baixada: ' + cid
        assert scene.get('generation_revision', 1) == int(revision), 'Revisão mudou: ' + cid
        metadata = QA / f'{cid}_R{int(revision):02d}_2fps.json'
        assert read(metadata).get('video') == scene['video'], 'Grade desatualizada: ' + cid
        if args.action == 'rejeitar':
            assert not (OUTPUT / (cid.rsplit('_', 1)[0] + '_40s.mp4')).exists(), 'Entrega concluída: ' + cid
        items.append((cid, scene['video']))
    reviews = read(QA / 'revisoes-cenas.json')
    retries = read(QA / 'regerar-cadeia.json')
    gates = {n: read(QA / f'etapa{n}-aprovada.json') for n in [4, 5]}
    for cid, video in items:
        verdict = 'approved' if args.action == 'aprovar' else 'rejected'
        reviews[cid] = {'video': video, 'verdict': verdict, 'review': args.nota}
        number = int(cid[-1])
        if args.action == 'aprovar' and number in gates:
            gates[number][cid] = video
        if args.action == 'rejeitar':
            retries[cid] = {'video': video, 'reason': args.nota}
            if number in gates:
                gates[number].pop(cid, None)
    save(QA / 'revisoes-cenas.json', reviews)
    for n, gate in gates.items():
        save(QA / f'etapa{n}-aprovada.json', gate)
    if args.action == 'rejeitar':
        save(QA / 'regerar-cadeia.json', retries)
    print(args.action + ': ' + ', '.join(cid for cid, _ in items))


if __name__ == '__main__':
    main()
