"""Fila persistente sem revisão humana bloqueante; sem dependência do navegador.

O adaptador executa as operações. Somente o controlador grava o estado.
Envios possivelmente clicados nunca são repetidos automaticamente.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import time
from concurrent.futures import ThreadPoolExecutor

ALLOWED_MODELS = {'veo_3_1_r2v_lite_low_priority', 'veo_3_1_i2v_lite_low_priority'}
TERMINAL = {'complete', 'failed', 'blocked', 'uncertain', 'timed_out', 'stopped'}
BUSY = {'submitting', 'submitted', 'rendering', 'downloading'}


def redact(value):
    text = str(value)
    text = re.sub(r'https?://[^\s\]\)"\']+', '[URL omitida]', text)
    text = re.sub(r'(?i)(cookie|authorization|bearer|token|api[_-]?key|password|senha)\s*[:=]\s*[^\s,;]+', r'\1=[omitido]', text)
    return text[:1600]


def read(path, default=None):
    path = Path(path)
    return json.loads(path.read_text()) if path.exists() else copy.deepcopy(default)


def atomic(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    with temp.open('w') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    # Windows readers/indexers can briefly open the destination without
    # FILE_SHARE_DELETE. Keep the flushed temporary file and retry only the
    # atomic replacement; never rewrite or expose a partial state file.
    for attempt in range(16):
        try:
            os.replace(temp, path)
            break
        except PermissionError as error:
            if os.name != 'nt' or getattr(error, 'winerror', None) not in (5, 32, 33) or attempt == 15:
                raise
            time.sleep(min(.05 * (attempt + 1), .25))


def norm(text):
    return ' '.join(text.split())


def scene_numbers(plan):
    return range(1, 5 if plan.get('mode') == 'recipe_only' else 6)


def initial_scene_count(plan):
    return 1 if plan.get('mode') == 'recipe_only' else 2


def validate_plan(plan):
    if plan.get('mode', 'hook_recipe') not in ('hook_recipe', 'recipe_only'):
        raise ValueError('Modo de produção inválido.')
    if plan.get('scheduling') not in (None, 'rolling_recipes') or (plan.get('scheduling') == 'rolling_recipes' and plan.get('mode') != 'recipe_only'):
        raise ValueError('Agendamento de receitas inválido.')
    if not re.fullmatch(r'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}', plan.get('project', '')):
        raise ValueError('Projeto inválido: informe o UUID do projeto Flow.')
    items = plan.get('videos', [])
    ids = [item['id'] for item in items]
    if not ids or len(ids) != len(set(ids)) or any(not re.fullmatch(r'PAR-\d{3,6}', key) for key in ids):
        raise ValueError('O plano deve conter vídeos PAR-001, PAR-002 etc., sem IDs repetidos.')
    for item in items:
        for role in (('recipe',) if plan.get('mode') == 'recipe_only' else ('hook', 'recipe')):
            ref = item.get(role, {})
            if not (ref.get('file') or (ref.get('id') and ref.get('name'))):
                raise ValueError(item['id'] + ': referência ausente para ' + role)
    for number in scene_numbers(plan):
        value = plan.get('prompts', {}).get(str(number), '')
        if not value.strip() or re.search(r'\{[A-Z_]+\}', value):
            raise ValueError('Prompt ausente ou placeholder na cena ' + str(number))
    limits = {**DEFAULT_LIMITS, **plan.get('limits', {})}
    for key in ('max_rendering', 'batch_size', 'prepare_attempts', 'io_attempts'):
        if type(limits[key]) is not int:
            raise ValueError('Limite deve ser inteiro: ' + key)
    if not 1 <= limits['max_rendering'] <= 3 or not 1 <= limits['batch_size'] <= 10 or limits['send_interval'] < 20:
        raise ValueError('Manter até 3 gerações, lotes de até 10 e intervalo mínimo de 20 segundos.')
    for key, value in limits.items():
        if not isinstance(value, (int, float)) or value <= 0:
            raise ValueError('Limite inválido: ' + key)
    if not 1 <= limits['io_attempts'] <= 6 or not 1 <= limits['prepare_attempts'] <= 3:
        raise ValueError('Tentativas de I/O: 1–6; preparação: 1–3.')
    return limits


DEFAULT_LIMITS = dict(max_rendering=3, batch_size=10, send_interval=20,
                      prepare_attempts=3, io_attempts=3, native_timeout=180,
                      confirmation_timeout=180, rendering_timeout=2400,
                      upload_timeout=300, io_timeout=360, poll_interval=8,
                      offline_timeout=300, max_run_seconds=43200, min_free_gb=2)


class Queue:
    def __init__(self, root, plan, adapter, clock=time.time):
        self.root, self.plan, self.adapter, self.clock = Path(root), plan, adapter, clock
        self.limits = validate_plan(plan)
        self.root.mkdir(parents=True, exist_ok=True)
        self.fingerprint = hashlib.sha256(json.dumps(plan, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        self.path = self.root / 'estado-noturno.json'
        self.state = read(self.path, {'schema': 1, 'plan_sha256': self.fingerprint, 'started_at': clock(),
                                    'status': 'created', 'scenes': {}, 'videos': {}, 'events': []})
        if self.state['plan_sha256'] != self.fingerprint:
            raise ValueError('Plano mudou em uma execução existente. Crie outra pasta para outro plano.')
        for item in plan['videos']:
            key = item['id']
            self.state['videos'].setdefault(key, {'status': 'pending'})
            for number in scene_numbers(plan):
                cid = key + '_' + str(number)
                self.state['scenes'].setdefault(cid, {'status': 'pending', 'attempts': [], 'number': number,
                                                     'pair': key, 'reference': copy.deepcopy(item.get('recipe' if plan.get('mode') == 'recipe_only' or number == 2 else 'hook')) if number <= initial_scene_count(plan) else None})
        self.pool = ThreadPoolExecutor(max_workers=6, thread_name_prefix='flow-noturno')
        self.futures = {}
        self.native = None
        self.inventory = {'sources': [], 'videos': [], 'asset_ids': []}
        self.last_inventory = 0
        self.last_good_inventory = clock()
        self.last_poll = 0
        self.last_send = max((a['started_at'] for s in self.scenes.values() for a in s['attempts']), default=0)
        self.stop_reason = None
        self.closed = False
        self.run_started = self.state.setdefault('run_started_at', clock())
        self.state['status'] = 'running'
        self.state.pop('stop_reason', None)
        self.recover_startup()
        self.save()

    @property
    def scenes(self):
        return self.state['scenes']

    def save(self):
        self.state['updated_at'] = self.clock()
        atomic(self.path, self.state)

    def event(self, kind, message, cid=None):
        item = {'at': self.clock(), 'kind': kind, 'cid': cid, 'message': redact(message)}
        self.state['events'].append(item)
        with (self.root / 'eventos-noturnos.jsonl').open('a') as stream:
            stream.write(json.dumps(item, ensure_ascii=False) + '\n')
        self.save()

    def failure(self, cid, category, detail, reserve=False):
        scene = self.scenes[cid]
        scene.update(status='uncertain' if reserve else 'failed', reason=category,
                     detail=redact(detail), finished_at=self.clock(), reserve=reserve)
        self.event(category, detail, cid)

    def recover_startup(self):
        for cid, scene in self.scenes.items():
            if scene['status'] == 'submitting':
                attempt = scene['attempts'][-1]
                result = self.adapter.recover_native(cid, attempt)
                if result.get('running'):
                    self.native = (cid, result['handle'], self.clock())
                else:
                    self.native_result(cid, result)
            elif scene['status'] in ('uploading', 'confirming_upload'):
                # Após um crash só consulta o recibo; nunca reatribui arquivos.
                scene['status'] = 'confirming_upload'
            elif scene['status'] == 'downloading':
                scene['status'] = 'rendering'
                scene['server_ready'] = True
            if scene['status'] == 'complete' and not self.adapter.receipt_valid(scene):
                if scene.get('video'):
                    scene.update(status='rendering', server_ready=True, reserve=False)
                else:
                    self.failure(cid, 'arquivo_ausente', 'Arquivo concluído não está íntegro e não há ID para recuperar.')
        for key, video in self.state['videos'].items():
            if video['status'] == 'composing':
                video['status'] = 'pending'
            if video['status'] == 'complete' and not self.adapter.delivery_valid(video):
                video.update(status='failed', reason='entrega_alterada', detail='Entrega existente diverge do recibo; preservada para conferência.')

    def retry_io(self, cid, phase, error):
        scene = self.scenes[cid]
        counters = scene.setdefault('io_errors', {})
        counters[phase] = counters.get(phase, 0) + 1
        self.event('erro_' + phase, error, cid)
        if counters[phase] >= self.limits['io_attempts']:
            self.failure(cid, phase + '_esgotado', error,
                         reserve=scene['status'] in ('submitted', 'rendering') and not scene.get('server_ready'))
            return False
        scene['next_io_at'] = self.clock() + min(60, 5 * 3 ** (counters[phase] - 1))
        return True

    def propagate(self):
        for cid, scene in self.scenes.items():
            if scene['status'] != 'pending' or scene['number'] <= initial_scene_count(self.plan):
                continue
            previous = self.scenes[scene['pair'] + '_' + str(scene['number'] - 1)]
            if previous['status'] in TERMINAL - {'complete'}:
                scene.update(status='blocked', reason='dependencia_incompleta',
                             detail='Cena anterior ' + scene['pair'] + '_' + str(scene['number'] - 1) + ': ' + previous['status'])
                self.event('dependencia_incompleta', scene['detail'], cid)
        for key, video in self.state['videos'].items():
            if video['status'] not in ('pending', 'incomplete'):
                continue
            scenes = [self.scenes[key + '_' + str(n)] for n in scene_numbers(self.plan)]
            if all(s['status'] == 'complete' for s in scenes):
                video['status'] = 'pending'
            elif all(s['status'] in TERMINAL for s in scenes):
                video.update(status='incomplete', reason='cenas_incompletas')

    def eligible(self):
        ids = [v['id'] for v in self.plan['videos']]
        result = []
        size = self.limits['batch_size']
        if self.plan.get('scheduling') == 'rolling_recipes':
            # Manter uma janela de receitas; cada continuação depende apenas
            # do frame da própria receita, sem barreira para as outras duas.
            active_statuses = BUSY | {'uploading', 'confirming_upload'}
            busy_pairs = [pair for pair in ids if any(self.scenes[f'{pair}_{n}']['status'] in active_statuses for n in scene_numbers(self.plan))]
            candidates = [pair for pair in ids if pair not in busy_pairs and any(self.scenes[f'{pair}_{n}']['status'] == 'pending' for n in scene_numbers(self.plan))]
            pairs = busy_pairs + candidates[:max(0, size - len(busy_pairs))]
            for number in scene_numbers(self.plan):
                for pair in pairs:
                    cid = f'{pair}_{number}'
                    scene = self.scenes[cid]
                    if scene['status'] != 'pending' or scene.get('next_io_at', 0) > self.clock():
                        continue
                    if number > 1:
                        previous = self.scenes[f'{pair}_{number - 1}']
                        if previous['status'] != 'complete':
                            continue
                        if not scene.get('reference') or scene['reference'].get('file') != previous['last_frame']:
                            scene['reference'] = {'file': previous['last_frame']}
                    result.append(cid)
            return result
        for offset in range(0, len(ids), size):
            pairs = ids[offset:offset + size]
            for number in scene_numbers(self.plan):
                if number > initial_scene_count(self.plan) and not all(self.scenes[p + '_' + str(number - 1)]['status'] in TERMINAL for p in pairs):
                    continue
                for pair in pairs:
                    cid = pair + '_' + str(number)
                    scene = self.scenes[cid]
                    if scene['status'] != 'pending' or scene.get('next_io_at', 0) > self.clock():
                        continue
                    if number > initial_scene_count(self.plan):
                        previous = self.scenes[pair + '_' + str(number - 1)]
                        if previous['status'] != 'complete':
                            continue
                        if not scene.get('reference') or scene['reference'].get('file') != previous['last_frame']:
                            scene['reference'] = {'file': previous['last_frame']}
                    result.append(cid)
        return result

    def launch(self, token, action, context, **params):
        if token not in self.futures:
            self.futures[token] = (action, context, self.pool.submit(getattr(self.adapter, action), **params))

    def ingest_inventory(self, inventory):
        self.inventory = inventory
        self.last_good_inventory = self.clock()
        for cid, scene in self.scenes.items():
            if scene['status'] not in ('submitted', 'uncertain') or scene.get('video'):
                continue
            if not scene['attempts']:
                continue
            attempt = scene['attempts'][-1]
            matches = [v for v in inventory['videos'] if v.get('created', [0])[0] >= attempt['started_at'] - 2
                       and norm(v.get('prompt') or '') == norm(attempt['prompt'])
                       and set(v.get('refs', [])) == {attempt['reference']['id']}]
            if len(matches) > 1:
                self.failure(cid, 'recibos_ambiguos', 'Mais de uma geração corresponde ao envio; não reenviar.', reserve=True)
            elif matches:
                video = matches[0]
                if video.get('model') not in ALLOWED_MODELS or video.get('seconds') != 8:
                    self.failure(cid, 'modelo_divergente', 'Modelo ou duração divergem da configuração autorizada.', reserve=True)
                    self.stop_reason = 'configuracao_divergente'
                    continue
                scene.update(status='rendering', video=video['id'], model=video['model'],
                             render_started_at=attempt['started_at'], reserve=False, next_io_at=0)
                attempt['video'] = video['id']
                self.event('envio_confirmado', 'Envio reconhecido no servidor sem repetir clique.', cid)

    def native_result(self, cid, result):
        scene = self.scenes[cid]
        scene['attempts'][-1]['result'] = {k: v for k, v in result.items() if k not in ('handle', 'raw')}
        if result.get('user_stop'):
            scene.update(status='stopped', reason='parada_usuario', reserve=bool(result.get('clicked')))
            self.stop_reason = 'parada_usuario'
        elif result.get('clicked'):
            scene.update(status='submitted', submitted_at=self.clock(), reserve=True)
            self.last_inventory = 0
            self.event('envio_observado', 'Consultar o servidor; nunca repetir este clique automaticamente.', cid)
            if result.get('global_error'):
                self.stop_reason = result['global_error']
                self.event(result['global_error'], result.get('error', 'Ambiente indisponível.'), cid)
        elif result.get('global_error'):
            self.failure(cid, result['global_error'], result.get('error', 'Ambiente indisponível.'))
            self.stop_reason = result['global_error']
        elif len(scene['attempts']) < scene.get('prepare_attempt_limit', self.limits['prepare_attempts']):
            scene.update(status='pending', next_io_at=self.clock() + 5 * len(scene['attempts']), refresh=True)
            self.event('preparo_sem_clique', result.get('error', 'Preparação falhou; repetir somente antes do clique.'), cid)
        else:
            self.failure(cid, 'preparacao_esgotada', result.get('error', 'Preparação não concluída.'))

    def harvest(self):
        for key, (action, context, future) in list(self.futures.items()):
            if not future.done():
                continue
            del self.futures[key]
            try:
                receipt = future.result()
            except Exception as error:
                if action == 'inventory':
                    self.event('consulta_indisponivel', error)
                elif action == 'compose':
                    video = self.state['videos'][context]
                    video['compose_errors'] = video.get('compose_errors', 0) + 1
                    video.update(status='failed' if video['compose_errors'] >= self.limits['io_attempts'] else 'pending',
                                 reason='montagem_falhou', detail=redact(error), next_io_at=self.clock() + 10)
                    self.event('montagem_falhou', error, context)
                elif action in ('upload', 'confirm_upload'):
                    for cid in context:
                        if self.scenes[cid]['status'] in TERMINAL:
                            continue
                        if self.retry_io(cid, 'upload', error):
                            self.scenes[cid]['status'] = 'confirming_upload'
                else:
                    for cid in context:
                        scene = self.scenes[cid]
                        if scene['status'] in TERMINAL:
                            continue
                        if self.retry_io(cid, 'download' if action == 'download' else 'consulta', error):
                            if action == 'download':
                                scene['status'] = 'rendering'
                continue
            if action == 'inventory':
                self.ingest_inventory(receipt)
            elif action in ('upload', 'confirm_upload'):
                for cid, ref in receipt.items():
                    if cid in context and self.scenes[cid]['status'] not in TERMINAL:
                        if ref.get('error'):
                            self.failure(cid, ref.get('category', 'referencia_invalida'), ref['error'])
                            continue
                        self.scenes[cid].update(status='pending', reference=ref, next_io_at=0, refresh=True)
                        self.event('upload_confirmado', 'Referência confirmada por nome e ID.', cid)
                missing = set(context) - set(receipt)
                for cid in missing:
                    if self.retry_io(cid, 'upload', 'Upload não confirmado; consultar novamente sem atribuir arquivo.'):
                        self.scenes[cid]['status'] = 'confirming_upload'
            elif action == 'status':
                for cid, value in receipt.items():
                    scene = self.scenes[cid]
                    if value.get('video') != scene.get('video'):
                        continue
                    if scene['status'] == 'uncertain' and scene.get('video'):
                        # Um prazo esgotado não pode reservar uma vaga para
                        # sempre. Consultar o MESMO ID, sem enviar outro clipe.
                        if value.get('ready'):
                            scene.update(status='rendering', server_ready=True, reserve=False, next_io_at=0)
                            self.event('geracao_recuperada', 'Geração antiga pronta; baixar o mesmo ID sem reenviar.', cid)
                        elif value.get('failed') or value.get('missing'):
                            self.failure(cid, 'geracao_removida' if value.get('missing') else 'geracao_falhou',
                                         'Servidor confirmou geração ausente ou encerrada; ID preservado e vaga liberada.')
                        continue
                    if scene['status'] != 'rendering':
                        continue
                    if value.get('failed'):
                        self.failure(cid, 'geracao_falhou', value.get('error_code') or 'Flow informou falha; seguir o próximo vídeo.')
                    elif value.get('ready'):
                        scene.update(server_ready=True, reserve=False)
            elif action == 'download':
                cid = context[0]
                scene = self.scenes[cid]
                if receipt.get('failed'):
                    self.failure(cid, 'geracao_falhou', 'Flow informou falha durante a consulta de download.')
                elif not receipt.get('ready'):
                    scene['status'] = 'rendering'
                elif receipt.get('video') != scene.get('video'):
                    self.failure(cid, 'recibo_incompativel', 'Download pertence a outra geração; arquivo não adotado.')
                else:
                    scene.update(receipt, status='complete', technical_qa='passed', visual_qa='not_reviewed',
                                 reserve=False, finished_at=self.clock())
                    self.event('cena_concluida', 'Download, decodificação e frame final conferidos. Revisão visual pendente.', cid)
            elif action == 'compose':
                self.state['videos'][context].update(receipt, status='complete', visual_qa='not_reviewed')
                self.event('video_concluido', 'Arquivo montado e validado tecnicamente. Revisão visual pendente.', context)
        if self.native is not None:
            cid, handle, started = self.native
            result = self.adapter.native_status(handle, timeout=self.clock() - started >= self.limits['native_timeout'])
            if result is not None:
                self.native = None
                self.native_result(cid, result)

    def deadlines(self):
        for cid, scene in self.scenes.items():
            status = scene['status']
            if status == 'submitted' and self.clock() - scene['submitted_at'] >= self.limits['confirmation_timeout']:
                self.failure(cid, 'envio_sem_confirmacao', 'Prazo de confirmação esgotado. Clique possivelmente enviado; não repetir.', reserve=True)
            if status == 'rendering' and not scene.get('server_ready') and self.clock() - scene['render_started_at'] >= self.limits['rendering_timeout']:
                self.failure(cid, 'renderizacao_demora', 'Prazo de geração esgotado. Preservar ID para retomada sem gerar de novo.', reserve=True)
        if self.clock() - self.last_good_inventory > self.limits['offline_timeout']:
            self.stop_reason = 'sessao_ou_conexao_indisponivel'
        if self.clock() - self.run_started > self.limits['max_run_seconds']:
            self.stop_reason = 'limite_da_execucao'

    def tick(self):
        self.harvest()
        self.deadlines()
        self.propagate()
        if (self.root / 'PARAR').exists():
            self.stop_reason = 'parada_usuario'
        if self.stop_reason:
            if self.native:
                cid, handle, _ = self.native
                self.native_result(cid, self.adapter.stop_native(handle))
                self.native = None
            return False
        eligible = self.eligible()
        ready_to_download = [cid for cid, s in self.scenes.items() if s['status'] == 'rendering' and s.get('server_ready') and s.get('next_io_at', 0) <= self.clock()]
        active_downloads = sum(action == 'download' for action, _, _ in self.futures.values())
        for cid in ready_to_download[:max(0, 3 - active_downloads)]:
            self.scenes[cid]['status'] = 'downloading'
            self.launch('download:' + cid, 'download', [cid], cid=cid, scene=copy.deepcopy(self.scenes[cid]))
        for key, video in self.state['videos'].items():
            if video['status'] != 'pending' or video.get('next_io_at', 0) > self.clock():
                continue
            scenes = [self.scenes[key + '_' + str(n)] for n in scene_numbers(self.plan)]
            if all(s['status'] == 'complete' for s in scenes) and sum(a == 'compose' for a, _, _ in self.futures.values()) < 2:
                video['status'] = 'composing'
                self.launch('compose:' + key, 'compose', key, key=key, scenes=copy.deepcopy(scenes))
        upload_busy = 'upload' in self.futures
        # Retomada de upload sempre consulta; não reatribui arquivos após timeout.
        confirm = [cid for cid, s in self.scenes.items() if s['status'] == 'confirming_upload' and s.get('next_io_at', 0) <= self.clock()]
        if confirm and not upload_busy:
            self.launch('upload', 'confirm_upload', confirm[:20], scenes={cid: copy.deepcopy(self.scenes[cid]) for cid in confirm[:20]})
            upload_busy = True
        if self.native is None and not upload_busy:
            missing = [cid for cid in eligible if not self.scenes[cid]['reference'].get('id')][:20]
            if missing and not any(self.scenes[cid]['reference'].get('id') for cid in eligible):
                refs = {}
                for cid in missing:
                    self.scenes[cid].update(status='uploading', upload_started_at=self.clock())
                    refs[cid] = copy.deepcopy(self.scenes[cid]['reference'])
                self.save()  # Intento gravado antes de qualquer mutação no navegador.
                self.launch('upload', 'upload', missing, references=refs)
                upload_busy = True
        reserved = sum(s.get('reserve', False) or s['status'] in ('submitting', 'submitted') or (s['status'] == 'rendering' and not s.get('server_ready')) for s in self.scenes.values())
        if self.native is None and reserved < self.limits['max_rendering'] and self.clock() - self.last_send >= self.limits['send_interval']:
            # Upload e macro compartilham o foco do Chrome. Um sinal ready da
            # operação anterior pode estar obsoleto antes do novo worker abrir
            # o seletor; nunca iniciar o macro enquanto existir upload ativo.
            can_use_ui = not upload_busy
            candidates = [cid for cid in eligible if self.scenes[cid]['reference'].get('id') and self.scenes[cid]['status'] == 'pending']
            if candidates and can_use_ui:
                cid = candidates[0]
                scene = self.scenes[cid]
                attempt = {'number': len(scene['attempts']) + 1, 'started_at': self.clock(),
                           'prompt': self.plan['prompts'].get(cid, self.plan['prompts'][str(scene['number'])]),
                           'reference': copy.deepcopy(scene['reference'])}
                scene['attempts'].append(attempt)
                scene['status'] = 'submitting'
                self.save()
                try:
                    handle = self.adapter.start_native(cid, attempt, refresh=scene.get('refresh', False))
                    self.native = (cid, handle, self.clock())
                    self.last_send = self.clock()
                except Exception as error:
                    # O adaptador reconcilia o diário se o erro aconteceu após spawn.
                    result = self.adapter.recover_native(cid, attempt, error=error)
                    if result.get('running'):
                        self.native = (cid, result['handle'], self.clock())
                    else:
                        self.native_result(cid, result)
        if self.clock() - self.last_inventory >= self.limits['poll_interval']:
            self.launch('inventory', 'inventory', None)
            self.last_inventory = self.clock()
        rendering = {cid: copy.deepcopy(s) for cid, s in self.scenes.items()
                     if ((s['status'] == 'rendering' and not s.get('server_ready'))
                         or (s['status'] == 'uncertain' and s.get('video') and s.get('reserve')))
                     and s.get('next_io_at', 0) <= self.clock()}
        if rendering and self.clock() - self.last_poll >= self.limits['poll_interval']:
            self.launch('status', 'status', list(rendering), scenes=rendering)
            self.last_poll = self.clock()
        self.save()
        self.report()
        active = self.native is not None or any(a not in ('inventory', 'status') for a, _, _ in self.futures.values())
        assembling_later = any(v['status'] == 'pending' and all(self.scenes[key + '_' + str(n)]['status'] == 'complete' for n in scene_numbers(self.plan)) for key, v in self.state['videos'].items())
        if all(s['status'] in TERMINAL for s in self.scenes.values()) and not active and not assembling_later:
            return False
        if reserved >= self.limits['max_rendering'] and not active and not any(s['status'] in BUSY for s in self.scenes.values()):
            self.stop_reason = 'vagas_reservadas_por_envios_incertos'
            return False
        return True

    def report(self):
        videos = []
        for item in self.plan['videos']:
            key = item['id']
            video = self.state['videos'][key]
            missing = [key + '_' + str(n) for n in scene_numbers(self.plan) if self.scenes[key + '_' + str(n)]['status'] != 'complete']
            videos.append({'id': key, **video, 'incomplete_scenes': missing,
                           'scenes': {str(n): {**{k: v for k, v in self.scenes[key + '_' + str(n)].items() if k in ('status', 'reason', 'detail', 'video', 'file', 'visual_qa', 'technical_qa')},
                                             'attempts': len(self.scenes[key + '_' + str(n)]['attempts'])} for n in scene_numbers(self.plan)}})
        complete = sum(v['status'] == 'complete' for v in videos)
        report = {'status': self.state['status'], 'stop_reason': self.stop_reason or self.state.get('stop_reason'),
                  'updated_at': self.clock(), 'planned_videos': len(videos), 'complete_videos': complete,
                  'incomplete_videos': len(videos) - complete, 'complete_scenes': sum(s['status'] == 'complete' for s in self.scenes.values()),
                  'planned_scenes': len(self.scenes), 'visual_review_pending': [v['id'] for v in videos if v['status'] == 'complete' and v.get('visual_qa') != 'approved'],
                  'videos': videos, 'incidents': self.state['events']}
        atomic(self.root / 'RELATORIO-NOTURNO.json', report)
        lines = ['# Relatório da execução', '', f"Estado: {report['status']}.",
                 f"Vídeos: {complete}/{len(videos)} concluídos tecnicamente. Cenas: {report['complete_scenes']}/{len(self.scenes)}.",
                 f"Motivo de encerramento: {report['stop_reason'] or 'nenhum erro global' }.", '',
                 'A conferência técnica verifica arquivos, duração, resolução, decodificação e hashes. '
                 'Não detecta mãos extras, objetos inventados ou legendas indevidas. '
                 'Os arquivos sem revisão visual permanecem identificados como tal.', '',
                 '| Vídeo | Estado | Cenas incompletas |', '|---|---|---|']
        for video in videos:
            lines.append(f"| {video['id']} | {video['status']} | {', '.join(video['incomplete_scenes']) or '—'} |")
        lines += ['', '## Falhas e pendências', '']
        for cid, scene in self.scenes.items():
            if scene['status'] in TERMINAL - {'complete'} or (self.state['status'] != 'running' and scene['status'] != 'complete'):
                lines.append(f"- {cid}: {scene['status']} — {scene.get('reason', '')}: {scene.get('detail', '')}")
        lines += ['', '## Ocorrências', '']
        for event in self.state['events']:
            if event['kind'] not in ('cena_concluida', 'upload_confirmado', 'envio_confirmado', 'envio_observado', 'video_concluido'):
                lines.append(f"- {event.get('cid') or 'Sistema'} / {event['kind']}: {event['message']}")
        (self.root / 'RELATORIO-NOTURNO.md').write_text('\n'.join(lines) + '\n')
        return report

    def finish(self, error=None):
        if error:
            self.stop_reason = 'erro_controlador'
            self.event('erro_controlador', error)
        self.state['stop_reason'] = self.stop_reason
        if self.stop_reason == 'parada_usuario':
            (self.root / 'PARAR').touch()
        self.state['status'] = 'stopped' if self.stop_reason else ('complete' if all(v['status'] == 'complete' for v in self.state['videos'].values()) else 'finished_with_errors')
        self.state['finished_at'] = self.clock()
        self.save()
        return self.report()

    def close(self):
        if not self.closed:
            self.pool.shutdown(wait=True, cancel_futures=True)
            self.closed = True
