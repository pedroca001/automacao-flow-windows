"""Testes de falhas sem abrir navegador ou consumir gerações."""
import copy
import json
from pathlib import Path
import tempfile
import time
import unittest

from noturno_core import Queue, ALLOWED_MODELS, atomic, read, redact, validate_plan
from noturno_adapter import native_outcome


class Clock:
    def __init__(self):
        self.value = 1000000
    def __call__(self):
        return self.value
    def advance(self):
        self.value += 5


def plan(count=3):
    return {'project': 'bd52915a-92fd-4647-a49d-d61b22101d38', 'output': '/unused',
            'prompts': {str(i): 'Prompt ' + str(i) for i in range(1, 6)},
            'videos': [{'id': f'PAR-{i:03d}', 'hook': {'file': f'/input/{i}-hook.png'},
                        'recipe': {'file': f'/input/{i}-recipe.png'}} for i in range(1, count + 1)],
            'limits': {'rendering_timeout': 150, 'confirmation_timeout': 50, 'native_timeout': 30,
                       'offline_timeout': 300, 'max_run_seconds': 10000}}


class Fake:
    def __init__(self, root, clock, failures=None):
        self.root, self.clock = root, clock
        self.failures = failures or {}
        self.assets, self.started, self.uploaded = {}, [], []
        self.download_tries, self.compose_tries = {}, {}
        self.native_poll = {}
        self.confirm_calls = 0
        self.stopped = 0

    def receipt_valid(self, scene):
        return Path(scene.get('file', '/missing')).exists() and Path(scene.get('last_frame', '/missing')).exists()

    def delivery_valid(self, scene):
        return Path(scene.get('file', '/missing')).exists()

    def inventory(self):
        if self.failures.get('offline'):
            raise RuntimeError('Conexão temporariamente indisponível')
        return {'sources': [], 'asset_ids': list(self.assets), 'videos': list(self.assets.values())}

    def upload(self, references):
        result = {}
        for cid, ref in references.items():
            self.uploaded.append(cid)
            if self.failures.get(cid) == 'missing':
                result[cid] = {'error': 'Arquivo não encontrado', 'category': 'arquivo_ausente'}
            elif self.failures.get(cid) != 'upload_confirm':
                result[cid] = {**ref, 'id': 'ref-' + cid, 'name': cid + '.png'}
        return result

    def confirm_upload(self, scenes):
        self.confirm_calls += 1
        return {cid: {**s['reference'], 'id': 'ref-' + cid, 'name': cid + '.png'} for cid, s in scenes.items()}

    def ui_available(self):
        return True

    def start_native(self, cid, attempt, refresh=False):
        self.started.append(cid)
        handle = {'cid': cid, 'attempt': copy.deepcopy(attempt)}
        self.native_poll[cid] = self.native_poll.get(cid, 0) + 1
        return handle

    def recover_native(self, cid, attempt, error=None):
        return {'clicked': True, 'error': 'Retomado de recibo click_intent'}

    def native_status(self, handle, timeout=False):
        cid, attempt = handle['cid'], handle['attempt']
        kind = self.failures.get(cid)
        if kind == 'hang':
            if not timeout:
                return None
            self.stopped += 1
            return {'clicked': False, 'error': 'Prazo nativo esgotado', 'timeout': True}
        if kind == 'escape':
            return {'clicked': False, 'user_stop': True}
        if kind == 'credits':
            return {'clicked': False, 'global_error': 'creditos_nao_autorizados'}
        if kind == 'prepare_once' and self.native_poll[cid] == 1:
            return {'clicked': False, 'error': 'Controle mudou antes do clique'}
        if kind != 'uncertain':
            video = 'video-' + cid
            self.assets[video] = {'id': video, 'created': [attempt['started_at']], 'prompt': attempt['prompt'],
                                  'refs': [attempt['reference']['id']], 'model': sorted(ALLOWED_MODELS)[0], 'seconds': 8}
        if kind == 'locked_after_click':
            return {'clicked': True, 'global_error': 'sessao_bloqueada'}
        return {'clicked': True}

    def stop_native(self, handle):
        self.stopped += 1
        return {'clicked': False, 'user_stop': True}

    def status(self, scenes):
        result = {}
        for cid, scene in scenes.items():
            kind = self.failures.get(cid)
            result[cid] = {'video': scene['video'], 'ready': kind not in ('render_fail', 'render_slow'),
                           'failed': kind == 'render_fail'}
        return result

    def download(self, cid, scene):
        self.download_tries[cid] = self.download_tries.get(cid, 0) + 1
        kind = self.failures.get(cid)
        if kind == 'corrupt' or (kind == 'download_twice' and self.download_tries[cid] <= 2):
            raise RuntimeError('Arquivo inválido ou download interrompido')
        path, frame = self.root / (cid + '.mp4'), self.root / (cid + '.png')
        path.write_text('video')
        frame.write_text('frame')
        return {'ready': True, 'video': scene['video'], 'file': str(path), 'sha256': 'sha',
                'last_frame': str(frame), 'last_frame_sha256': 'frame-sha'}

    def compose(self, key, scenes):
        self.compose_tries[key] = self.compose_tries.get(key, 0) + 1
        if self.failures.get(key) == 'compose_once' and self.compose_tries[key] == 1:
            raise RuntimeError('FFmpeg interrompido')
        if self.failures.get(key) == 'compose_always':
            raise RuntimeError('Destino indisponível')
        path = self.root / (key + '_40s.mp4')
        path.write_text('delivery')
        return {'file': str(path), 'sha256': 'delivery-sha'}


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.clock = Clock()
        self.queues = []
    def tearDown(self):
        for q in self.queues:
            q.close()
        self.temp.cleanup()
    def queue(self, failures=None, count=3, data=None, fake=None):
        fake = fake or Fake(self.root, self.clock, failures)
        q = Queue(self.root, data or plan(count), fake, clock=self.clock)
        self.queues.append(q)
        return q, fake
    def run_queue(self, q, steps=1400):
        for _ in range(steps):
            more = q.tick()
            self.clock.advance()
            time.sleep(.0005)
            if not more:
                q.close()
                q.harvest()
                return q.finish()
        self.fail('Fila entrou em espera sem fim')

    def test_all_batches_without_manual_approval(self):
        q, fake = self.queue(count=12)
        report = self.run_queue(q)
        self.assertEqual(report['complete_videos'], 12)
        self.assertEqual(len(fake.started), 60)
        self.assertEqual(len(report['visual_review_pending']), 12)
        self.assertFalse(any(s.get('visual_qa') == 'approved' for s in q.scenes.values()))
        self.assertEqual(len(fake.uploaded), 60)  # Ref confirmada não é apagada pelo scheduler.

    def test_recipe_only_four_scenes_and_last_frame_dependencies(self):
        data = plan(2)
        data['mode'] = 'recipe_only'
        data['prompts'] = {str(n): 'Recipe step ' + str(n) for n in range(1, 5)}
        for item in data['videos']:
            del item['hook']
        q, fake = self.queue(data=data)
        report = self.run_queue(q)
        self.assertEqual(report['complete_videos'], 2)
        self.assertEqual(report['planned_scenes'], 8)
        self.assertEqual(len(fake.started), 8)
        for pair in ('PAR-001', 'PAR-002'):
            self.assertEqual(q.scenes[pair + '_1']['reference']['file'], data['videos'][int(pair[-1]) - 1]['recipe']['file'])
            for number in range(2, 5):
                self.assertEqual(q.scenes[f'{pair}_{number}']['reference']['file'], q.scenes[f'{pair}_{number - 1}']['last_frame'])
            self.assertNotIn(pair + '_5', q.scenes)

    def test_recipe_only_failed_first_scene_blocks_all_its_continuations(self):
        data = plan(2)
        data['mode'] = 'recipe_only'
        q, fake = self.queue({'PAR-001_1': 'render_fail'}, data=data)
        report = self.run_queue(q)
        self.assertEqual(report['complete_videos'], 1)
        for number in range(2, 5):
            self.assertEqual(q.scenes[f'PAR-001_{number}']['status'], 'blocked')
            self.assertNotIn(f'PAR-001_{number}', fake.started)

    def test_upload_and_macro_never_start_in_the_same_tick(self):
        data = plan(2)
        data['mode'] = 'recipe_only'
        data['videos'][0]['recipe'].update(id='existing-reference', name='existing.png')
        q, fake = self.queue(data=data)
        q.tick()
        self.assertNotIn('upload', q.futures)
        self.assertEqual(fake.started, ['PAR-001_1'])

    def test_active_upload_prevents_macro_even_with_stale_ui_ready(self):
        from concurrent.futures import Future
        data = plan(2)
        data['mode'] = 'recipe_only'
        data['videos'][0]['recipe'].update(id='existing-reference', name='existing.png')
        q, fake = self.queue(data=data)
        q.scenes['PAR-002_1']['status'] = 'uploading'
        q.futures['upload'] = ('upload', ['PAR-002_1'], Future())
        q.tick()
        self.assertEqual(fake.started, [])
        self.assertIsNone(q.native)

    def test_timed_out_generation_ready_recovers_same_id_without_submission(self):
        from concurrent.futures import Future
        q, fake = self.queue(count=1)
        scene = q.scenes['PAR-001_1']
        scene.update(status='uncertain', video='old-generation', reserve=True)
        future = Future()
        future.set_result({'PAR-001_1': {'video': 'old-generation', 'ready': True}})
        q.futures['status'] = ('status', ['PAR-001_1'], future)
        q.harvest()
        self.assertEqual(scene['status'], 'rendering')
        self.assertTrue(scene['server_ready'])
        self.assertFalse(scene['reserve'])
        self.assertEqual(scene['video'], 'old-generation')
        self.assertEqual(fake.started, [])

    def test_timed_out_generation_missing_releases_slot_preserving_id(self):
        from concurrent.futures import Future
        q, fake = self.queue(count=1)
        scene = q.scenes['PAR-001_1']
        scene.update(status='uncertain', video='old-generation', reserve=True)
        future = Future()
        future.set_result({'PAR-001_1': {'video': 'old-generation', 'ready': False, 'failed': False, 'missing': True}})
        q.futures['status'] = ('status', ['PAR-001_1'], future)
        q.harvest()
        self.assertEqual(scene['status'], 'failed')
        self.assertEqual(scene['reason'], 'geracao_removida')
        self.assertFalse(scene['reserve'])
        self.assertEqual(scene['video'], 'old-generation')
        self.assertEqual(fake.started, [])

    def test_rolling_three_recipes_continue_independently(self):
        data = plan(5)
        data.update(mode='recipe_only', scheduling='rolling_recipes')
        data['limits']['batch_size'] = 3
        q, fake = self.queue(data=data)
        self.assertEqual(q.eligible(), ['PAR-001_1', 'PAR-002_1', 'PAR-003_1'])
        q.scenes['PAR-001_1'].update(status='complete', last_frame='/frames/first.png')
        q.scenes['PAR-002_1']['status'] = 'rendering'
        self.assertEqual(q.eligible(), ['PAR-003_1', 'PAR-001_2'])
        self.assertEqual(q.scenes['PAR-001_2']['reference']['file'], '/frames/first.png')
        self.assertNotIn('PAR-004_1', q.eligible())
        for n in range(1, 5):
            q.scenes[f'PAR-001_{n}']['status'] = 'complete'
        self.assertIn('PAR-004_1', q.eligible())
        self.assertNotIn('PAR-005_1', q.eligible())

    def test_rolling_three_recipes_finish_full_queue(self):
        data = plan(8)
        data.update(mode='recipe_only', scheduling='rolling_recipes')
        data['limits']['batch_size'] = 3
        q, fake = self.queue(data=data)
        report = self.run_queue(q)
        self.assertEqual(report['complete_videos'], 8)
        self.assertEqual(len(fake.started), 32)
        self.assertEqual(len(set(fake.started)), 32)

    def test_explicit_recovery_preserves_attempts_and_adds_bounded_preparation_budget(self):
        q, fake = self.queue(count=1)
        scene = q.scenes['PAR-001_1']
        scene.update(status='submitting', attempts=[{'number': n} for n in range(1, 5)], prepare_attempt_limit=6)
        q.native_result('PAR-001_1', {'clicked': False, 'error': 'before click'})
        self.assertEqual(scene['status'], 'pending')
        self.assertEqual(len(scene['attempts']), 4)
        scene['attempts'] += [{'number': 5}, {'number': 6}]
        q.native_result('PAR-001_1', {'clicked': False, 'error': 'before click'})
        self.assertEqual(scene['status'], 'failed')

    def test_missing_hook_does_not_block_recipe_or_other_pairs(self):
        q, fake = self.queue({'PAR-001_1': 'missing'})
        report = self.run_queue(q)
        self.assertEqual(report['complete_videos'], 2)
        self.assertEqual(q.scenes['PAR-001_5']['status'], 'complete')
        self.assertNotIn('PAR-001_1', fake.started)

    def test_failed_recipe_blocks_only_its_descendants(self):
        q, fake = self.queue({'PAR-001_2': 'render_fail'})
        report = self.run_queue(q)
        self.assertEqual(report['complete_videos'], 2)
        for n in (3, 4, 5):
            self.assertEqual(q.scenes['PAR-001_' + str(n)]['status'], 'blocked')
            self.assertNotIn('PAR-001_' + str(n), fake.started)

    def test_upload_only_confirm_after_missing_receipt(self):
        q, fake = self.queue({'PAR-001_1': 'upload_confirm'})
        self.assertEqual(self.run_queue(q)['complete_videos'], 3)
        self.assertEqual(fake.uploaded.count('PAR-001_1'), 1)
        self.assertGreater(fake.confirm_calls, 0)

    def test_download_retry_does_not_regenerate(self):
        q, fake = self.queue({'PAR-001_2': 'download_twice'})
        self.assertEqual(self.run_queue(q)['complete_videos'], 3)
        self.assertEqual(fake.download_tries['PAR-001_2'], 3)
        self.assertEqual(fake.started.count('PAR-001_2'), 1)

    def test_corruption_does_not_stop_other_pairs(self):
        q, fake = self.queue({'PAR-001_2': 'corrupt'})
        self.assertEqual(self.run_queue(q)['complete_videos'], 2)
        self.assertEqual(fake.started.count('PAR-001_2'), 1)
        self.assertEqual(fake.download_tries['PAR-001_2'], 3)

    def test_uncertain_click_is_not_repeated(self):
        q, fake = self.queue({'PAR-001_1': 'uncertain'})
        report = self.run_queue(q)
        self.assertEqual(fake.started.count('PAR-001_1'), 1)
        self.assertEqual(report['complete_videos'], 2)
        self.assertEqual(q.scenes['PAR-001_1']['status'], 'uncertain')

    def test_three_unknown_clicks_finish_with_report(self):
        q, fake = self.queue({'PAR-001_1': 'uncertain', 'PAR-002_1': 'uncertain', 'PAR-003_1': 'uncertain'})
        report = self.run_queue(q)
        self.assertEqual(report['stop_reason'], 'vagas_reservadas_por_envios_incertos')
        self.assertEqual(len(fake.started), 3)

    def test_slow_render_does_not_occupy_queue_forever(self):
        q, fake = self.queue({'PAR-001_1': 'render_slow'})
        report = self.run_queue(q)
        self.assertEqual(report['complete_videos'], 2)
        self.assertEqual(fake.started.count('PAR-001_1'), 1)

    def test_native_hang_has_bounded_retries(self):
        q, fake = self.queue({'PAR-001_1': 'hang'})
        self.assertEqual(self.run_queue(q)['complete_videos'], 2)
        self.assertEqual(fake.started.count('PAR-001_1'), 3)
        self.assertEqual(fake.stopped, 3)

    def test_pre_click_recovery(self):
        q, fake = self.queue({'PAR-001_1': 'prepare_once'})
        self.assertEqual(self.run_queue(q)['complete_videos'], 3)
        self.assertEqual(fake.started.count('PAR-001_1'), 2)

    def test_escape_stops_entire_run(self):
        q, fake = self.queue({'PAR-001_1': 'escape'})
        report = self.run_queue(q)
        self.assertEqual(report['stop_reason'], 'parada_usuario')
        self.assertEqual(len(fake.started), 1)

    def test_paid_configuration_stops(self):
        q, fake = self.queue({'PAR-001_1': 'credits'})
        report = self.run_queue(q)
        self.assertEqual(report['stop_reason'], 'creditos_nao_autorizados')
        self.assertEqual(len(fake.started), 1)

    def test_compose_retries_and_continues_other_videos(self):
        q, fake = self.queue({'PAR-001': 'compose_once', 'PAR-002': 'compose_always'})
        report = self.run_queue(q)
        self.assertEqual(report['complete_videos'], 2)
        self.assertEqual(fake.compose_tries['PAR-001'], 2)
        self.assertEqual(fake.compose_tries['PAR-002'], 3)

    def test_restart_after_click_does_not_send_again(self):
        q, fake = self.queue(count=1)
        for _ in range(100):
            q.tick()
            self.clock.advance()
            time.sleep(.001)
            if q.scenes['PAR-001_1']['status'] == 'submitted':
                break
        q.close()
        q2, _ = self.queue(count=1, fake=fake)
        self.assertEqual(self.run_queue(q2)['complete_videos'], 1)
        self.assertEqual(fake.started.count('PAR-001_1'), 1)

    def test_stop_file_stops_before_upload(self):
        q, fake = self.queue()
        (self.root / 'PARAR').touch()
        report = self.run_queue(q)
        self.assertEqual(report['stop_reason'], 'parada_usuario')
        self.assertFalse(fake.started)
        self.assertFalse(fake.uploaded)

    def test_plan_change_is_rejected(self):
        q, _ = self.queue()
        q.close()
        p = plan()
        p['prompts']['1'] = 'Alterado'
        with self.assertRaisesRegex(ValueError, 'Plano mudou'):
            self.queue(data=p)

    def test_native_journal_survives_empty_log(self):
        self.assertTrue(native_outcome('', {'phase': 'click_intent'})['clicked'])
        self.assertFalse(native_outcome('erro antes de clicar', {'phase': 'preparing'})['clicked'])
        self.assertTrue(native_outcome('Interrompido por Esc.', {})['user_stop'])
        self.assertEqual(native_outcome('O Flow não confirmou 0 créditos.', {})['global_error'], 'creditos_nao_autorizados')

    def test_reports_redact_credentials_and_signed_urls(self):
        text = redact('token=abc cookie=private https://flow-content.google/video/123?sig=secret')
        self.assertNotIn('abc', text)
        self.assertNotIn('private', text)
        self.assertNotIn('sig=secret', text)

    def test_invalid_throttle_is_rejected(self):
        p = plan()
        p['limits']['max_rendering'] = 4
        with self.assertRaises(ValueError):
            validate_plan(p)

    def test_fractional_batch_limit_rejected(self):
        p = plan()
        p['limits']['batch_size'] = 1.5
        with self.assertRaises(ValueError):
            validate_plan(p)

    def test_global_failure_after_click_stops_and_preserves_submission(self):
        q, fake = self.queue({'PAR-001_1': 'locked_after_click'})
        report = self.run_queue(q)
        self.assertEqual(report['stop_reason'], 'sessao_bloqueada')
        self.assertEqual(len(fake.started), 1)
        self.assertTrue(q.scenes['PAR-001_1']['reserve'])

    def test_user_stop_persists_across_supervisor_restart(self):
        q, fake = self.queue({'PAR-001_1': 'escape'})
        self.run_queue(q)
        self.assertTrue((self.root / 'PARAR').is_file())

    def test_native_locked_session_detection(self):
        self.assertEqual(native_outcome('Sessão do macOS bloqueada.', {})['global_error'], 'sessao_bloqueada')


if __name__ == '__main__':
    unittest.main(verbosity=2)
