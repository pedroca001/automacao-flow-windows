import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
sys.path.insert(0, str(BASE / 'retomada-macro'))
from noturno_core import atomic
from test_noturno import Fake, Clock, plan

spec = importlib.util.spec_from_file_location('scoped_queue', HERE / 'executar-lote.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SyncAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.plan = plan(4)
        self.plan.update(mode='recipe_only', scheduling='rolling_recipes')
        self.clock = Clock()
        self.queue = module.SyncQueue(self.root, self.plan, Fake(self.root, self.clock), self.clock)

    def tearDown(self):
        self.queue.close()
        self.tmp.cleanup()

    def allow(self, number):
        path = self.root / f'{number}.png'
        path.write_bytes(b'checked-source-fixture')
        inventory = __import__('json').loads((self.root / 'inventario-imagens.json').read_text()) if (self.root / 'inventario-imagens.json').exists() else {}
        inventory[f'{number:03d}'] = {'file': str(path), 'bytes': path.stat().st_size}
        atomic(self.root / 'inventario-imagens.json', inventory)

    def test_not_synced_inputs_remain_pending(self):
        self.assertEqual(self.queue.eligible(), [])
        self.assertTrue(all(s['status'] == 'pending' for s in self.queue.scenes.values()))

    def test_missing_first_source_does_not_block_verified_second(self):
        self.allow(2)
        self.assertEqual(self.queue.eligible(), ['PAR-002_1'])
        self.assertIs(self.queue.plan, self.plan)
        self.assertEqual(len(self.queue.plan['videos']), 4)

    def test_fourth_source_waits_for_pilot_approval(self):
        self.allow(4)
        self.assertEqual(self.queue.eligible(), [])
        atomic(self.root / 'PILOTOS-APROVADOS.json', {'approved': True})
        self.assertEqual(self.queue.eligible(), ['PAR-004_1'])
        self.assertEqual(self.queue.scenes['PAR-004_2']['status'], 'pending')

    def test_account_hold_blocks_new_submission_without_resetting_scenes(self):
        self.allow(2)
        atomic(self.root / 'PILOTOS-APROVADOS.json', {'approved': True})
        atomic(self.root / 'BLOQUEIO-FLOW.json', {'status': 'active'})
        before = __import__('copy').deepcopy(self.queue.scenes)
        self.assertEqual(self.queue.eligible(), [])
        self.assertEqual(self.queue.scenes, before)
        atomic(self.root / 'BLOQUEIO-FLOW.json', {'status': 'resolved'})
        self.assertEqual(self.queue.eligible(), ['PAR-002_1'])


if __name__ == '__main__':
    unittest.main()
