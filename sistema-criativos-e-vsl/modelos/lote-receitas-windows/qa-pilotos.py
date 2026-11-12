"""Create per-scene contact sheets at 2 fps from already generated pilot clips."""
import json
import os
import argparse
from pathlib import Path
import subprocess
import tempfile
from PIL import Image, ImageOps, ImageDraw

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--ids', nargs='+', default=['PAR-001', 'PAR-002', 'PAR-003'])
args = parser.parse_args()
state = json.loads((ROOT / 'estado-noturno.json').read_text(encoding='utf-8'))
out = ROOT / 'qa-pilotos'
out.mkdir(exist_ok=True)
results = []
for cid, scene in state['scenes'].items():
    if scene['pair'] not in args.ids or scene['status'] != 'complete':
        continue
    target = out / (cid + '-2fps.jpg')
    if not target.exists():
        with tempfile.TemporaryDirectory(prefix='flow-pilot-') as tmp:
            subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', scene['file'],
                            '-vf', 'fps=2,scale=180:320', str(Path(tmp) / '%03d.jpg')], check=True,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            frames = sorted(Path(tmp).glob('*.jpg'))
            sheet = Image.new('RGB', (720, ((len(frames) + 3) // 4) * 344), '#202020')
            draw = ImageDraw.Draw(sheet)
            for i, path in enumerate(frames):
                x, y = (i % 4) * 180, (i // 4) * 344
                with Image.open(path) as frame:
                    sheet.paste(frame, (x, y + 24))
                draw.text((x + 5, y + 4), f'{cid} {i / 2:.1f}s', fill='white')
            sheet.save(target, quality=90)
    results.append({'id': cid, 'sheet': str(target), 'video': scene['file'], 'sha256': scene['sha256']})
(out / 'indice.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
print(json.dumps(results))
