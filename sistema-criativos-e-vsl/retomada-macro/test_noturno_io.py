"""Integração local com FFmpeg, PNGs e recibos reais. Nenhuma geração/rede."""
import contextlib
import copy
try:
    import fcntl
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
    from flow_platform import locks as fcntl
import io
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from PIL import Image
from noturno_adapter import Adapter, BASE, SOURCE
from noturno_core import DEFAULT_LIMITS, read
from compor import probe


class LocalIO(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.clip = cls.root / 'origem.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i',
                        'color=c=blue:s=720x1280:r=24:d=8', '-an', '-c:v', 'libx264',
                        '-threads', '2', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p', str(cls.clip)],
                       check=True, timeout=60)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.run = Path(tempfile.mkdtemp(dir=self.root))
        self.plan = {'project': 'bd52915a-92fd-4647-a49d-d61b22101d38', 'output': str(self.run / 'saida')}
        self.adapter = Adapter(self.run, self.plan, copy.deepcopy(DEFAULT_LIMITS))

    def test_missing_image_isolated_from_valid_upload(self):
        image = self.run / 'entrada.jpg'
        Image.new('RGB', (40, 60), 'red').save(image)
        def fake_background(action, **params):
            self.assertEqual(action, 'upload_many')
            return [{'id': 'fonte', 'name': Path(p).name} for p in params['files']]
        with patch.object(self.adapter, 'background', side_effect=fake_background):
            receipts = self.adapter.upload({'PAR-001_1': {'file': str(self.run / 'ausente.png')},
                                            'PAR-002_1': {'file': str(image)}})
        self.assertIn('error', receipts['PAR-001_1'])
        self.assertEqual(receipts['PAR-002_1']['id'], 'fonte')
        with Image.open(receipts['PAR-002_1']['upload_file']) as png:
            self.assertEqual(png.format, 'PNG')

    def test_compose_and_adopt_existing_receipt_without_overwrite(self):
        scenes = [{'file': str(self.clip)}] * 5
        receipt = self.adapter.compose('PAR-999', scenes)
        info = probe(receipt['file'])
        self.assertAlmostEqual(float(info['format']['duration']), 40, places=1)
        self.assertTrue(self.adapter.delivery_valid(receipt))
        self.assertEqual(self.adapter.compose('PAR-999', scenes), receipt)
        Path(receipt['file']).write_bytes(b'arquivo alterado')
        with self.assertRaisesRegex(RuntimeError, 'preservada'):
            self.adapter.compose('PAR-999', scenes)
        self.assertEqual(Path(receipt['file']).read_bytes(), b'arquivo alterado')

    def test_recipe_only_compose_32_seconds_with_source_name(self):
        self.plan.update(mode='recipe_only', videos=[{'id': 'PAR-001', 'source_name': '001_camping_05.png'}])
        receipt = self.adapter.compose('PAR-001', [{'file': str(self.clip)}] * 4)
        self.assertEqual(Path(receipt['file']).name, '001_camping_05_32s.mp4')
        self.assertEqual(receipt['seconds'], 32)
        self.assertAlmostEqual(float(probe(receipt['file'])['format']['duration']), 32, places=1)
        self.assertEqual(self.adapter.compose('PAR-001', [{'file': str(self.clip)}] * 4), receipt)

    def test_prepare_recipe_only_uses_four_existing_recipe_prompts(self):
        images = self.run / 'images'
        images.mkdir()
        Image.new('RGB', (32, 64)).save(images / '001_camping_05.png')
        prompts = self.run / 'prompts.json'
        prompts.write_text(json.dumps({str(n): 'Prompt de teste ' + str(n) for n in range(1, 6)}))
        folder = self.run / 'receitas'
        subprocess.run([sys.executable, str(SOURCE / 'noturno.py'), 'preparar', '--somente-receita',
                        '--imagens', str(images), '--projeto', self.plan['project'], '--prompts', str(prompts),
                        '--pasta', str(folder), '--sem-definir-atual'], check=True, capture_output=True, timeout=30)
        prepared = read(folder / 'plano-noturno.json')
        self.assertEqual(prepared['mode'], 'recipe_only')
        self.assertNotIn('hook', prepared['videos'][0])
        self.assertEqual(prepared['prompts'], {str(n): 'Prompt de teste ' + str(n + 1) for n in range(1, 5)})
        self.assertEqual(read(folder / 'entradas.json')['missing'], [])

    def test_download_corruption_quarantined_and_same_generation_downloaded(self):
        helpers = types.ModuleType('browser_harness.helpers')
        helpers.cdp, helpers.drain_events = None, None
        with patch.dict(sys.modules, {'browser_harness.helpers': helpers}):
            module = runpy.run_path(str(SOURCE / 'fundo.py'), init_globals={'FLOW_RUN_DIR': str(self.run)})
        background = module['Background'].__new__(module['Background'])
        cid, video = 'PAR-999_1', 'existing-video-id'
        result = {'ready': True, 'url': 'https://flow-content.google/video/' + video}
        payload = self.clip.read_bytes()
        calls = []
        def response(url, timeout):
            calls.append(url)
            return contextlib.closing(io.BytesIO(payload))
        with patch('urllib.request.urlopen', side_effect=response):
            receipt = background.download(cid, video, result=result, repair_corrupt=True)
            Path(receipt['file']).write_bytes(b'corrompido')
            recovered = background.download(cid, video, result=result, repair_corrupt=True)
        self.assertEqual(len(calls), 2)
        self.assertEqual(receipt['sha256'], recovered['sha256'])
        self.assertTrue(self.adapter.receipt_valid(recovered))
        self.assertEqual(len(list((self.run / 'downloads-corrompidos').glob('*.mp4'))), 1)
        unknown = self.run / 'clips' / 'PAR-998_1.mp4'
        unknown.write_bytes(b'sem recibo')
        with self.assertRaisesRegex(AssertionError, 'sem recibo'):
            background.download('PAR-998_1', video, result=result, repair_corrupt=True)
        self.assertEqual(unknown.read_bytes(), b'sem recibo')

    def test_prepare_plan_and_validate_without_changing_current_batch(self):
        images = self.run / 'images'
        images.mkdir()
        Image.new('RGB', (32, 32)).save(images / 'PAR-999_recipe.png')
        prompts = self.run / 'prompts.json'
        prompts.write_text(json.dumps({str(n): 'Prompt de teste ' + str(n) for n in range(1, 6)}))
        pointer = BASE / 'noturno-atual.json'
        before = pointer.read_bytes() if pointer.exists() else None
        folder = self.run / 'plano'
        command = [sys.executable, str(SOURCE / 'noturno.py')]
        subprocess.run([*command, 'preparar', '--imagens', str(images), '--projeto', self.plan['project'],
                        '--prompts', str(prompts), '--pasta', str(folder), '--sem-definir-atual'],
                       check=True, capture_output=True, timeout=30)
        subprocess.run([*command, 'executar', '--plano', str(folder / 'plano-noturno.json'), '--validar'],
                       check=True, capture_output=True, timeout=30)
        report = read(folder / 'RELATORIO-NOTURNO.json')
        self.assertEqual(report['stop_reason'], 'validacao_sem_geracao')
        self.assertEqual(report['complete_scenes'], 0)
        self.assertNotIn('run_started_at', read(folder / 'estado-noturno.json'))
        self.assertEqual(read(folder / 'entradas.json')['missing'], ['PAR-999: hook'])
        self.assertEqual(before, pointer.read_bytes() if pointer.exists() else None)
        original_state = (folder / 'estado-noturno.json').read_bytes()
        with (BASE / '.flow_controller.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            blocked = subprocess.run([*command, 'executar', '--plano', str(folder / 'plano-noturno.json'), '--validar'],
                                     capture_output=True, text=True, timeout=30)
            self.assertEqual(blocked.returncode, 2)
            self.assertIn('Outra automação', blocked.stderr)
        self.assertEqual((folder / 'estado-noturno.json').read_bytes(), original_state)


if __name__ == '__main__':
    unittest.main(verbosity=2)
