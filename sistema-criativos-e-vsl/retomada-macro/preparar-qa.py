"""Prepara grades de revisão sem bloquear geração, transferência ou montagem."""
import json
import hashlib
import os
from pathlib import Path
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

ROOT = Path(__file__).resolve().parent
QA = ROOT / 'qa'

def render(item):
    cid, scene = item
    if not Path(scene['file']).is_file():
        return None
    revision = scene.get('generation_revision', 1)
    image = QA / (cid + f'_R{revision:02d}_2fps.jpg')
    metadata = image.with_suffix('.json')
    if not image.exists() or not metadata.exists() or json.loads(metadata.read_text()).get('video') != scene['video']:
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-threads', '1', '-i', scene['file'],
                        '-vf', 'fps=2,scale=180:-1,tile=4x4', '-frames:v', '1', str(image)], check=True, capture_output=True)
        # A grade a 2 fps termina em 7,5s; o frame que alimenta a próxima cena
        # está perto de 8s. Exibi-lo na última célula evita omitir defeitos da ponte.
        exact_last = Path(scene['last_frame'])
        assert hashlib.sha256(exact_last.read_bytes()).hexdigest() == scene['last_frame_sha256'], 'Frame final alterado.'
        with Image.open(image) as sheet, Image.open(exact_last) as last:
            tile_size = (sheet.width // 4, sheet.height // 4)
            sheet.paste(last.convert('RGB').resize(tile_size), (3 * tile_size[0], 3 * tile_size[1]))
            sheet.save(image, quality=90)
        metadata.write_text(json.dumps({'video': scene['video'], 'source_sha256': scene.get('sha256') or hashlib.sha256(Path(scene['file']).read_bytes()).hexdigest(), 'last_tile': 'exact_last_frame', 'last_frame_sha256': scene['last_frame_sha256']}))
    return {'cid': cid, 'video': scene['video'], 'revision': revision, 'sheet': str(image)}

with ThreadPoolExecutor(max_workers=2) as pool:
    while True:
        state = json.loads((ROOT / 'spec.json.state.json').read_text())
        reviewed_path = QA / 'revisoes-cenas.json'
        reviewed = json.loads(reviewed_path.read_text()) if reviewed_path.exists() else {}
        approved = {}
        for filename in ('etapa4-aprovada.json', 'etapa5-aprovada.json'):
            p = QA / filename
            if p.exists():
                approved.update(json.loads(p.read_text()))
        candidates = [(cid, scene) for cid, scene in state['cenas'].items()
                      if scene.get('done') and scene.get('file') and (int(cid[4:7]) >= 84 or (int(cid[4:7]) >= 74 and int(cid[-1]) >= 4))
                      and approved.get(cid) != scene.get('video')
                      and reviewed.get(cid, {}).get('video') != scene.get('video')]
        results = [r for r in pool.map(render, candidates) if r]
        p = QA / 'pendentes.json'
        tmp = p.with_suffix('.tmp')
        tmp.write_text(json.dumps(results, indent=2))
        os.replace(tmp, p)
        if json.loads((ROOT / 'PROGRESSO.json').read_text()).get('status') == 'complete':
            break
        time.sleep(3)
