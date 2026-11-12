"""Supplier delivery audit adapted to the 1200-video Windows execution."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / 'retomada-macro'))
from noturno_core import ALLOWED_MODELS, atomic, read


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument('--pilotos', action='store_true')
    scope.add_argument('--concluidos', action='store_true', help='Audit all currently complete videos; never declares the 1200-video goal complete.')
    args = parser.parse_args()
    plan, state = read(ROOT / 'plano-noturno.json'), read(ROOT / 'estado-noturno.json')
    assert len(plan['videos']) == 1200 and len(state['scenes']) == 4800
    full = not (args.pilotos or args.concluidos)
    items = (plan['videos'][:3] if args.pilotos else
             [v for v in plan['videos'] if state['videos'][v['id']]['status'] == 'complete'] if args.concluidos else plan['videos'])
    assert items, 'No complete videos to audit.'
    inventory = read(ROOT / 'inventario-imagens.json')
    if full:
        sync = read(ROOT / 'PREFLIGHT-SINCRONIZACAO.json')
        assert sync['status'] == 'ready' and not sync['errors'], 'Source synchronization/validation is not complete.'
        assert len(inventory) == len({v['sha256'] for v in inventory.values()}) == 1200
        assert Counter(v['variant'] for v in items) == {'standard': 600, 'olive_honey_cinnamon': 600}
    assert all(state['videos'][v['id']]['status'] == 'complete' for v in items), 'Videos still pending.'

    def verify(item):
        key = item['id']
        receipt = state['videos'][key]
        path = Path(receipt['file'])
        assert path.parent == Path(plan['output'])
        assert path.name == Path(item['source_name']).stem + '_32s.mp4'
        expected = read(ROOT / 'receipts' / (key + '.json'))
        assert expected['sha256'] == receipt['sha256'] and expected['file'] == str(path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == receipt['sha256']
        info = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams',
            '-show_format', '-of', 'json', str(path)], text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0))
        video = next(s for s in info['streams'] if s['codec_type'] == 'video')
        duration = float(info['format']['duration'])
        assert abs(duration - 32) < .1
        assert (video['width'], video['height']) == (720, 1280)
        assert video['codec_name'] == 'h264' and video['r_frame_rate'] == '24/1'
        assert any(s['codec_type'] == 'audio' for s in info['streams'])
        assert not any(s['codec_type'] == 'subtitle' for s in info['streams'])
        source_record = inventory[key.removeprefix('PAR-')]
        assert hashlib.sha256(Path(item['recipe']['file']).read_bytes()).hexdigest() == source_record['sha256']
        if full:
            assert hashlib.sha256(Path(source_record['source']).read_bytes()).hexdigest() == source_record['sha256'], 'The synchronized approved source changed: ' + key
        scene_ids = [f'{key}_{n}' for n in range(1, 5)]
        generation_ids = []
        for cid in scene_ids:
            scene = state['scenes'][cid]
            assert scene['status'] == 'complete' and scene.get('video')
            assert scene.get('model') in ALLOWED_MODELS, 'Unexpected generation model: ' + cid
            assert hashlib.sha256(Path(scene['file']).read_bytes()).hexdigest() == scene['sha256']
            assert hashlib.sha256(Path(scene['last_frame']).read_bytes()).hexdigest() == scene['last_frame_sha256']
            download_receipts = [read(p) for p in (ROOT / 'downloads').glob(cid + '_R*.json')]
            assert any(r.get('video') == scene['video'] and r.get('file') == scene['file']
                       and r.get('sha256') == scene['sha256'] and r.get('last_frame_sha256') == scene['last_frame_sha256']
                       for r in download_receipts), 'Download receipt mismatch: ' + cid
            expected_source_sha = (source_record['sha256'] if scene['number'] == 1
                                   else state['scenes'][f"{key}_{scene['number'] - 1}"]['last_frame_sha256'])
            assert scene['reference']['source_sha256'] == expected_source_sha, 'Continuity mismatch: ' + cid
            assert hashlib.sha256(Path(scene['reference']['upload_file']).read_bytes()).hexdigest() == expected_source_sha
            generation_ids.append(scene['video'])
        concat_path = ROOT / 'entrega' / (path.stem + '.concat.txt')
        if concat_path.exists():
            actual_lines = concat_path.read_text(encoding='utf-8').splitlines()
            expected_lines = []
            for cid in scene_ids:
                source_path = Path(state['scenes'][cid]['file']).resolve().as_posix().replace("'", "'\\''")
                expected_lines.extend(["file '" + source_path + "'", 'duration 8'])
            assert actual_lines == expected_lines, 'Composition order mismatch: ' + key
        return {'id': key, 'variant': item['variant'], 'source_image': item['source_name'],
                'source_sha256': source_record['sha256'], 'file': str(path), 'sha256': digest,
                'seconds': duration, 'width': 720, 'height': 1280, 'fps': '24/1',
                'codec': 'h264', 'scene_ids': scene_ids, 'generation_ids': generation_ids,
                'continuity_verified': True, 'download_receipts_verified': True,
                'concat_manifest': str(concat_path) if concat_path.exists() else None}

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(verify, items))
    assert len({v['sha256'] for v in results}) == len(items), 'Duplicate final hashes.'
    assert len({generation for video in results for generation in video['generation_ids']}) == len(items) * 4, 'A provider generation was reused across scenes.'
    if full:
        assert {v['file'] for v in results} == {str(p) for p in Path(plan['output']).glob('*.mp4')}
    audit = {'at': time.time(), 'status': 'complete' if full else 'pilot_technical_complete' if args.pilotos else 'partial_technical_complete',
             'project_url': read(ROOT / 'config-lote.json')['project_url'],
             'planned_videos': 1200, 'verified_videos': len(results), 'verified_scenes': len(results) * 4,
             'verified_variants': dict(Counter(v['variant'] for v in results)), 'seconds_per_video': 32,
             'validation': 'Final/source/scene/frame hashes; provider ID uniqueness; download receipts and continuation source hashes; composition manifests when present; ffprobe, dimensions, fps, codec, duration, audio, names and counts. Full decoding during supplier download/composition.',
             'visual_qa': 'not_reviewed_all', 'videos': results}
    name = 'AUDITORIA-FINAL.json' if full else 'AUDITORIA-PILOTOS.json' if args.pilotos else 'AUDITORIA-PARCIAL.json'
    atomic(ROOT / name, audit)
    atomic(Path(plan['output']) / name, audit)
    print(json.dumps({k: v for k, v in audit.items() if k != 'videos'}))


if __name__ == '__main__':
    main()
