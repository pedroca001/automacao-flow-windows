import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch, Mock
import supervisor_30min as module


def plan():
    return {'project': '69fa2616-f380-426e-8618-25d80e722b1b', 'mode': 'recipe_only',
            'videos': [{'id': 'PAR-001', 'recipe': {'file': 'one.png'}}, {'id': 'PAR-002', 'recipe': {'file': 'two.png'}}],
            'prompts': {str(n): 'prompt ' + str(n) for n in range(1, 5)}}


def state(age=1900):
    return {'status': 'stopped', 'stop_reason': 'atividade_incomum', 'events': [],
            'videos': {'PAR-001': {'status': 'complete', 'sha256': 'final'}, 'PAR-002': {'status': 'incomplete'}},
            'scenes': {'PAR-001_1': {'status': 'complete', 'pair': 'PAR-001', 'number': 1, 'video': 'existing', 'sha256': 'keep', 'attempts': []},
                       'PAR-002_1': {'status': 'submitted', 'pair': 'PAR-002', 'number': 1, 'reserve': True,
                                     'submitted_at': 10000 - age, 'attempts': [{'started_at': 10000 - age,
                                     'prompt': 'prompt 1', 'reference': {'id': 'reference'}}]},
                       'PAR-002_2': {'status': 'blocked', 'pair': 'PAR-002', 'number': 2, 'attempts': [], 'reason': 'dependencia_incompleta'}}}


class ReconciliationTests(unittest.TestCase):
    def test_thirty_minutes_never_retries_or_releases_within_render_deadline(self):
        before = state()
        result, changes = module.reconcile(before, plan(), {'videos': []}, 10000)
        self.assertEqual(result['scenes']['PAR-002_1']['status'], 'uncertain')
        self.assertTrue(result['scenes']['PAR-002_1']['reserve'])
        self.assertEqual(result['scenes']['PAR-002_1']['attempts'], before['scenes']['PAR-002_1']['attempts'])
        self.assertEqual(result['scenes']['PAR-001_1'], before['scenes']['PAR-001_1'])
        self.assertEqual(before['scenes']['PAR-002_1']['status'], 'submitted')

    def test_expired_capacity_preserves_uncertain_click_and_history(self):
        before = state(age=2500)
        result, changes = module.reconcile(before, plan(), {'videos': []}, 10000)
        scene = result['scenes']['PAR-002_1']
        self.assertEqual(scene['status'], 'uncertain')
        self.assertFalse(scene['reserve'])
        self.assertFalse(scene['retry_allowed'])
        self.assertEqual(scene['attempts'], before['scenes']['PAR-002_1']['attempts'])
        self.assertEqual(result['scenes']['PAR-002_2']['status'], 'blocked')

    def test_late_receipt_recovers_same_id_and_only_unattempted_descendants(self):
        before = state()
        before['scenes']['PAR-002_1']['status'] = 'uncertain'
        video = {'id': 'late-generation', 'created': [8200], 'prompt': 'prompt 1',
                 'refs': ['reference'], 'model': 'veo_3_1_r2v_lite_low_priority', 'seconds': 8}
        result, changes = module.reconcile(before, plan(), {'videos': [video]}, 10000)
        self.assertEqual(result['scenes']['PAR-002_1']['status'], 'rendering')
        self.assertEqual(result['scenes']['PAR-002_1']['video'], 'late-generation')
        self.assertEqual(len(result['scenes']['PAR-002_1']['attempts']), 1)
        self.assertEqual(result['scenes']['PAR-002_2']['status'], 'pending')
        with self.assertRaisesRegex(RuntimeError, 'ambiguous'):
            module.reconcile(before, plan(), {'videos': [video, {**video, 'id': 'duplicate'}]}, 10000)

    def test_user_stop_credits_and_changed_configuration_are_not_retryable(self):
        for reason in ('parada_usuario', 'creditos_nao_autorizados', 'configuracao_divergente', 'sessao_bloqueada'):
            self.assertFalse(module.recoverable({'stop_reason': reason}))
        self.assertFalse(module.recoverable({'stop_reason': 'pre_checagem_falhou', 'events': [
            {'kind': 'pre_checagem_falhou', 'message': 'Controle não encontrado'},
            {'kind': 'pre_checagem_falhou', 'message': 'créditos diferentes de zero'}]}))


class CooldownSequenceTests(unittest.TestCase):
    def run_sequence(self, outcomes, user_stop=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            if user_stop:
                (root / 'PARAR').touch()
            now = [0]
            snapshots = []
            resumes = []
            active = [False]
            def save(path, data):
                snapshots.append(copy.deepcopy(data))
            def wait(seconds):
                self.assertLessEqual(seconds, 10)
                if active[0]:
                    raise StopIteration
                now[0] += seconds
            def prepare():
                self.assertGreaterEqual(now[0], 1800)
                resumes.append(now[0])
                return {'outcome': outcomes.pop(0)}
            def launch(*args, **kwargs):
                active[0] = True
                return SimpleNamespace(returncode=0, stdout='started', stderr='')
            with patch.multiple(module, ROOT=root, STATUS=root / 'status.json'), \
                 patch.object(module, 'read', side_effect=lambda path, default=None: {} if path.name == 'status.json' else state()), \
                 patch.object(module, 'atomic', side_effect=save), \
                 patch.object(module, 'running', side_effect=lambda path: [{'pid': 123}] if active[0] else []), \
                 patch.object(module, 'prepare_resume', side_effect=prepare) as refresh, \
                 patch.object(module.time, 'time', side_effect=lambda: now[0]), \
                 patch.object(module.time, 'sleep', side_effect=wait), \
                 patch.object(module.ctypes, 'windll', SimpleNamespace(kernel32=Mock())), \
                 patch.object(module.subprocess, 'run', side_effect=launch) as start:
                try:
                    module.main()
                except StopIteration:
                    pass
                if user_stop:
                    refresh.assert_not_called()
                    start.assert_not_called()
                    self.assertEqual(snapshots[-1]['phase'], 'user_stopped')
                else:
                    self.assertEqual(resumes[0], 1800)
                    self.assertEqual(start.call_count, 1)
                return resumes

    def test_refresh_and_resume_happen_only_after_full_thirty_minutes(self):
        self.assertEqual(self.run_sequence(['clear']), [1800])

    def test_persistent_warning_gets_another_full_cooldown(self):
        self.assertEqual(self.run_sequence(['cooldown_again', 'clear']), [1800, 3600])

    def test_explicit_user_stop_prevents_refresh_and_resume(self):
        self.run_sequence(['clear'], user_stop=True)


if __name__ == '__main__':
    unittest.main()
