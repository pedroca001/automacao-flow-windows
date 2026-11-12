"""Snapshot checked inputs while Drive synchronizes; never generates videos."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

from PIL import Image

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parents[1]
sys.path.insert(0, str(BASE / 'retomada-macro'))
from noturno_core import atomic, read, validate_plan

CONFIG = read(ROOT / 'config-lote.json')
SOURCE = Path(CONFIG['source'])
OUTPUT = Path(CONFIG['output'])
PROJECT_URL = CONFIG['project_url'].rstrip('/')
PROJECT = PROJECT_URL.rsplit('/', 1)[-1]



def templates():
    previous = read(BASE / 'retomada-macro/prompts-ativos.json')
    standard = {str(n): previous[str(n + 1)] for n in range(1, 5)}
    preserve = (' One continuous fixed-camera 8-second shot at ordinary speed, starting from the exact supplied frame. '
                'Preserve the original location, framing, lighting, sleeves, bowl, whisk, labels and every existing object. '
                'Only the same two hands connected to the same two arms exist. A moving hand leaves its old position empty. '
                'The original ingredient position stays empty until that exact container returns. All unhandled props stay stationary. '
                'Never change container identity, add ingredients, duplicate hands or invent objects. The bowl stays level on the table. '
                'No cuts, zoom, camera movement, speech, music, subtitles, new writing, graphics, recording interface or borders. '
                'Quiet natural handling sounds only. End with both original hands empty and still beside the bowl; the released whisk rests visibly inside it.')
    olive = {
        '1': ('Animate this exact starting image. At the start, the original right hand sets down and RELEASES the existing whisk inside the bowl, '
              'then rests empty beside the bowl. The original left hand releases the bowl, lifts ONLY the existing large olive-oil bottle from the left, '
              'tilts its already open real mouth down over the bowl and pours one short thin stream of olive oil through that opening. '
              'The stream starts at the real bottle mouth, falls down into the bowl and stops as the SAME bottle returns upright. '
              'Return and RELEASE that bottle in its original spot by second six. Never remove or create a cap. Olive oil remains the main ingredient. '
              'The honey and cinnamon stay untouched.' + preserve),
        '2': ('Continue this exact last frame. The original left hand stays still beside the bowl. Only the original right hand lifts '
              'the ONE existing smaller honey squeeze bottle, tilts the original open nozzle over the bowl and squeezes one brief thin strand '
              'of honey THROUGH THAT NOZZLE into the olive-oil mixture. Stop squeezing, return and RELEASE the SAME honey bottle in its '
              'original position by second six. The attached open flip-top remains attached throughout. The olive-oil bottle and cinnamon stay untouched.' + preserve),
        '3': ('Continue this exact last frame. The original left hand stays still beside the bowl. Only the original right hand lifts '
              'the ONE existing cinnamon jar from the right, tilts its already open shaker holes toward the same bowl and adds one small '
              'brief dusting of ground cinnamon THROUGH THOSE HOLES into the olive-oil and honey mixture. The fine powder falls from the '
              'shaker holes and stops immediately. Return and RELEASE the SAME jar in its original place by second six. '
              'Keep the original hinged shaker lid attached and open. No foam, eruption or new powder after the jar is upright. '
              'The olive-oil and honey bottles stay untouched.' + preserve),
        '4': previous['5'],
    }
    return {'standard': standard, 'olive_honey_cinnamon': olive}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--watch', action='store_true')
    args = parser.parse_args()
    slots = read(SOURCE / 'manifesto.json')['slots']
    assert len(slots) == 1200
    assert sorted(int(s['id']) for s in slots) == list(range(1, 1201))
    assert Counter(s['variant'] for s in slots) == {'standard': 600, 'olive_honey_cinnamon': 600}
    prompts = templates()
    atomic(ROOT / 'prompts-variantes.json', prompts)
    records = read(ROOT / 'inventario-imagens.json', {})
    observed = {}
    snapshot = ROOT / 'imagens-validadas'
    snapshot.mkdir(exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    plan = {'schema': 1, 'mode': 'recipe_only', 'scheduling': 'rolling_recipes', 'project': PROJECT,
            'output': str(OUTPUT), 'prompts': dict(prompts['standard']), 'videos': [],
            'limits': {'max_run_seconds': 1209600, 'batch_size': 3, 'max_rendering': 3,
                       'send_interval': 20, 'native_timeout': 240, 'min_free_gb': 15}}
    for slot in sorted(slots, key=lambda s: int(s['id'])):
        name = slot['id'] + '_' + slot['slug'] + '.png'
        cid = 'PAR-' + slot['id']
        plan['videos'].append({'id': cid, 'recipe': {'file': str(snapshot / name)},
                               'source_name': name, 'variant': slot['variant']})
        if slot['variant'] != 'standard':
            for n, value in prompts[slot['variant']].items():
                plan['prompts'][cid + '_' + n] = value
    validate_plan(plan)
    current = ROOT / 'plano-noturno.json'
    if current.exists():
        assert read(current) == plan, 'Existing plan differs: preserve tracking.'
    else:
        atomic(current, plan)
    atomic(ROOT / 'operacao-autorizada.json', {'at': time.time(), 'project_url': PROJECT_URL,
        'project_label': CONFIG.get('label', 'Windows - receitas padrao e azeite'),
        'source': str(SOURCE), 'output': str(OUTPUT), 'target_videos': 1200, 'target_scenes': 4800,
        'variants': {'standard': 600, 'olive_honey_cinnamon': 600},
        'authorization': 'Operator configured this batch locally; no production state is distributed with the source.',
        'zero_credit_model_required': True, 'prior_batches_preserved': True})
    while True:
        missing, unstable, errors = [], [], []
        for slot in slots:
            key = slot['id']
            name = key + '_' + slot['slug'] + '.png'
            src, dst = SOURCE / 'aprovadas' / name, snapshot / name
            if not src.exists():
                missing.append(name)
                continue
            try:
                st = src.stat()
                identity = (st.st_size, st.st_mtime_ns)
                if key in records:
                    assert identity == tuple(records[key]['source_stat']), 'Approved source changed after snapshot: ' + name
                    assert dst.is_file() and dst.stat().st_size == records[key]['bytes'], 'Snapshot missing or changed: ' + name
                    continue
                if observed.get(key) != identity:
                    observed[key] = identity
                    unstable.append(name)
                    continue
                data = src.read_bytes()
                assert identity == (src.stat().st_size, src.stat().st_mtime_ns), 'Source changed while reading'
                digest = hashlib.sha256(data).hexdigest()
                assert not any(v['sha256'] == digest for v in records.values()), 'Duplicate input hash: ' + name
                from io import BytesIO
                with Image.open(BytesIO(data)) as image:
                    image.load()
                    w, h = image.size
                    assert .45 <= w / h <= .80 and w >= 700 and h >= 1200, 'Invalid portrait image geometry'
                if dst.exists():
                    assert hashlib.sha256(dst.read_bytes()).hexdigest() == digest, 'Snapshot differs: ' + name
                else:
                    temp = dst.with_suffix('.tmp')
                    temp.write_bytes(data)
                    temp.replace(dst)
                records[key] = {'file': str(dst), 'source': str(src), 'source_stat': list(identity),
                                'sha256': digest, 'bytes': len(data), 'width': w, 'height': h,
                                'variant': slot['variant'], 'checked_at': time.time(),
                                'aspect_ratio': round(w / h, 6), 'source_preserved_without_crop': True}
            except Exception as error:
                errors.append({'file': name, 'error': str(error)})
        atomic(ROOT / 'inventario-imagens.json', records)
        status = {'at': time.time(), 'status': 'ready' if len(records) == 1200 and not errors else 'waiting_for_sync',
                  'verified_images': len(records), 'expected_images': 1200, 'missing': missing,
                  'waiting_for_stability': unstable, 'errors': errors,
                  'verified_variants': dict(Counter(v['variant'] for v in records.values())),
                  'project_url': PROJECT_URL, 'output': str(OUTPUT), 'source_validation_only': True}
        atomic(ROOT / 'PREFLIGHT-SINCRONIZACAO.json', status)
        print(json.dumps({k: status[k] for k in ('at', 'status', 'verified_images', 'verified_variants')}) +
              f' missing={len(missing)} unstable={len(unstable)} errors={len(errors)}', flush=True)
        if status['status'] == 'ready':
            assert len({v['sha256'] for v in records.values()}) == 1200
            break
        if not args.watch:
            break
        time.sleep(20)


if __name__ == '__main__':
    main()
