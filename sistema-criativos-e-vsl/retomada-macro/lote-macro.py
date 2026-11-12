"""Lotes de dez vídeos finais, com barreira entre as etapas 1+2, 3, 4 e 5."""
import argparse
try:
    import fcntl
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
    from flow_platform import locks as fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from compor import compose

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
OUTPUT = Path('/Users/pedrobassi/Downloads/teste 20 de outubro/Entrega')
PROJECT = 'bd52915a-92fd-4647-a49d-d61b22101d38'
MODEL = 'veo_3_1_r2v_lite_low_priority'
ALLOWED_MODELS = {MODEL, 'veo_3_1_i2v_lite_low_priority'}


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    os.replace(temporary, path)


def background(params):
    for attempt in range(3):
        code = "import runpy\nm=runpy.run_path(" + repr(str(ROOT / 'fundo.py')) + ",init_globals=globals())\nm['main'](" + repr(params) + ')\n'
        result = subprocess.run(['browser-harness'], input=code, text=True, cwd=BASE, capture_output=True)
        if not result.returncode:
            return json.loads(next(line[len('FLOW_RESULT='):] for line in result.stdout.splitlines() if line.startswith('FLOW_RESULT=')))
        transient = any(word in result.stderr for word in ('_IPCResponseTimeout', 'timed out', 'timeout', 'Download falhou', 'temporariamente indisponível'))
        if transient and params['action'] == 'upload_many':
            # Nunca atribuir arquivos outra vez: repetir apenas a confirmação.
            params = {'action': 'confirm_many', 'files': params['files']}
        elif params['action'] not in ('inventory', 'download', 'download_many', 'status_many', 'confirm_many', 'focus') or not transient or attempt == 2:
            raise RuntimeError('Operação da aba de arquivos falhou: ' + result.stderr[-1100:])
        time.sleep(1 * (attempt + 1))
    raise RuntimeError('Consulta em segundo plano esgotou as tentativas, sem reenvio de geração ou upload.')


def norm(text):
    return ' '.join((text or '').split())


def main(args):
    controller = open(BASE / '.flow_controller.lock', 'a')
    fcntl.flock(controller, fcntl.LOCK_EX | fcntl.LOCK_NB)
    lane = open(ROOT / '.lote.lock', 'a')
    fcntl.flock(lane, fcntl.LOCK_EX | fcntl.LOCK_NB)
    state_path = ROOT / 'spec.json.state.json'
    jobs_path = ROOT / 'tarefas-macro.json'
    state = json.loads(state_path.read_text())
    prompts_path = ROOT / 'prompts-ativos.json'
    prompts = json.loads((prompts_path if prompts_path.exists() else ROOT / 'prompts-aprovados.json').read_text())
    jobs = json.loads(jobs_path.read_text()) if jobs_path.exists() else {}
    overrides_path = ROOT / 'referencias-novas.json'
    overrides = json.loads(overrides_path.read_text()) if overrides_path.exists() else {}
    for name, digest in state['baseline'].items():
        assert hashlib.sha256((OUTPUT / name).read_bytes()).hexdigest() == digest, 'Entrega anterior modificada.'
    active = None
    active_cid = None
    last_send = 0
    pilot_passed = any(j.get('status') == 'done' for j in jobs.values())
    subprocess.run([str(BASE / 'flow-macro'), '--compilar'], cwd=BASE, check=True)
    inv = background({'action': 'inventory'})
    last_inventory = time.monotonic()
    last_poll = 0
    start_count = sum(bool(s.get('done')) for s in state['cenas'].values())
    incomplete_pairs = [p for p in range(66, 121) if not all(state['cenas'].get(f'PAR-{p:03d}_{n}', {}).get('done') for n in range(1, 6))]
    plan_path = ROOT / 'lotes-etapas.json'
    if plan_path.exists():
        batches = json.loads(plan_path.read_text())
    else:
        batches = [incomplete_pairs[i:i + 10] for i in range(0, len(incomplete_pairs), 10)]
        save(plan_path, batches)
    planned_pairs = [p for batch in batches for p in batch]
    assert all(1 <= len(batch) <= 10 for batch in batches)
    assert len(planned_pairs) == len(set(planned_pairs)) and all(66 <= p <= 120 for p in planned_pairs)
    assert set(incomplete_pairs).issubset(planned_pairs), 'Há vídeos pendentes fora do plano salvo.'
    current_stage = None
    prepared_stage = None
    refresh_native_required = False
    preparation_retries_path = ROOT / 'tentativas-preparo.json'
    preparation_retries = json.loads(preparation_retries_path.read_text()) if preparation_retries_path.exists() else {}

    def next_stage():
        for index, pairs in enumerate(batches, 1):
            for numbers in ((1, 2), (3,), (4,), (5,)):
                cids = [f'PAR-{p:03d}_{n}' for n in numbers for p in pairs]
                if any(not state['cenas'].get(cid, {}).get('done') for cid in cids):
                    return (index, tuple(pairs), numbers), cids
        return None, []


    def persist(status='running'):
        save(state_path, state)
        save(jobs_path, jobs)
        progress = {'status': status, 'done_scenes': sum(bool(s.get('done')) for s in state['cenas'].values()),
                    'planned_scenes': 275, 'remaining_scenes': 275 - sum(bool(s.get('done')) for s in state['cenas'].values()),
                    'delivered_videos': len(list(OUTPUT.glob('PAR-???_40s.mp4'))), 'planned_videos': 55,
                    'pending': [cid for cid, j in jobs.items() if j['status'] not in ('done', 'not_sent')],
                    'updated_at': time.time(), 'input_method': 'keystrokes', 'mode': 'Elementos',
                    'batch_size': 10, 'stage': current_stage}
        save(ROOT / 'PROGRESSO.json', progress)
        save(OUTPUT / 'PROGRESSO.json', progress)

    def event(message):
        print(time.strftime('%H:%M:%S'), message, flush=True)
        with open(ROOT / 'eventos-macro.jsonl', 'a') as f:
            f.write(json.dumps({'at': time.time(), 'message': message}, ensure_ascii=False) + '\n')

    def isolate_failed_generation(cid):
        job = jobs[cid]
        archive = ROOT / 'erros-servidor' / (cid + '_' + job['video'])
        archive.mkdir(parents=True, exist_ok=True)
        save(archive / 'falha.json', {'job': job, 'reason': 'Flow informou falha na geração; revisar antes de nova tentativa.'})
        job['status'] = 'needs_review'
        persist()
        event('Falha de geração isolada para revisão; demais vagas continuam: ' + cid)

    def recover_preparation(cid, job, log_text):
        nonlocal refresh_native_required
        launcher_path = Path(job['launcher_log']) if job.get('launcher_log') else None
        launcher_text = launcher_path.read_text() if launcher_path and launcher_path.exists() else ''
        launch_failed = not log_text.strip() and '_LSOpenURLsWithCompletionHandler() failed with error -10810' in launcher_text
        safe_error = launch_failed or 'Controle não encontrado: Veo 3.1 - Lite [Lower Priority].' in log_text or 'O campo de prompt perdeu o foco.' in log_text or 'O Chrome perdeu o foco.' in log_text or 'Já existe um prompt. Use --substituir' in log_text or 'A aba mudou; clique cancelado.' in log_text or 'controle sob o mouse mudou' in log_text or 'controle mudou de posição durante a espera' in log_text or 'Configuração mudou depois da preparação:' in log_text or 'Não achei o conteúdo da aba.' in log_text
        count = preparation_retries.get(cid, 0)
        if 'Clicando uma única vez' in log_text or not safe_error or count >= 3:
            return False
        count += 1
        archive = ROOT / 'logs' / f'{cid}.preparo-{count}'
        save(archive.with_suffix(archive.suffix + '.json'), job)
        archive.with_suffix(archive.suffix + '.log').write_text(log_text)
        preparation_retries[cid] = count
        save(preparation_retries_path, preparation_retries)
        del jobs[cid]
        refresh_native_required = True
        event('Preparação sem clique será refeita após atualizar a aba: ' + cid + ' (recuperação ' + str(count) + '/3).')
        persist()
        return True

    def apply_final_retries():
        nonlocal prepared_stage, refresh_native_required
        requests = {}
        for filename in ('regerar-finais.json', 'regerar-cadeia.json'):
            path = ROOT / 'qa' / filename
            if path.exists():
                requests.update(json.loads(path.read_text()))
        processed_path = ROOT / 'qa' / 'regeracoes-processadas.json'
        processed = json.loads(processed_path.read_text()) if processed_path.exists() else []
        for cid, request in requests.items():
            if request['video'] in processed:
                continue
            pair, number = cid.rsplit('_', 1)
            n = int(number)
            assert 1 <= n <= 5 and cid in state['cenas']
            item = state['cenas'][cid]
            assert item.get('done') and item.get('video') == request['video'], 'Revisão aponta versão antiga/incompleta.'
            affected = [cid] if n == 1 else [pair + '_' + str(k) for k in range(n, 6)]
            # Espera somente tentativas da própria cadeia, sem bloquear outras gerações.
            if pair in deliveries or any(c in repair_futures for c in affected) or any(jobs.get(c, {}).get('status') in ('native_inflight', 'submitted', 'rendering', 'uncertain') for c in affected):
                continue
            assert not (OUTPUT / (pair + '_40s.mp4')).exists(), 'Não substituir entrega aprovada.'
            for target in affected:
                old = state['cenas'].get(target, {})
                revision = old.get('generation_revision', 1)
                if old.get('video'):
                    archive = ROOT / 'qa' / 'rejeitados' / (target + f'_R{revision:02d}_' + old['video'][:8])
                    archive.mkdir(parents=True, exist_ok=False)
                    job = jobs.get(target)
                    save(archive / 'registro.json', {'state': old, 'job': job, 'reason': request['reason']})
                    for name in ('file', 'last_frame'):
                        path = Path(old[name]) if old.get(name) else None
                        if path and path.exists():
                            path.rename(archive / path.name)
                    if job:
                        log = Path(job['log'])
                        if log.exists():
                            log.rename(archive / log.name)
                        prompt = Path(job['prompt_file'])
                        if prompt.exists():
                            (archive / 'prompt.txt').write_text(prompt.read_text())
                    state['cenas'][target] = {'done': False, 'generation_revision': revision + 1, 'qa_reason': request['reason']}
                jobs.pop(target, None)
            processed.append(request['video'])
            prepared_stage = None
            refresh_native_required = True
            persist()
            save(processed_path, processed)
            event('Correção visual enfileirada: ' + cid + ' e suas dependências; demais gerações continuam.')

    def source_name(cid):
        pair, number = cid.rsplit('_', 1)
        n = int(number)
        if n > 2:
            previous = state['cenas'].get(pair + '_' + str(n - 1), {})
            revision = previous.get('generation_revision', 1)
            if revision > 1:
                return 'B20_' + pair + '_' + str(n - 1) + f'_ultimo_R{revision:02d}.png'
        if cid in overrides:
            return overrides[cid]['name']
        return 'B20_' + pair + ('_hook.png' if n == 1 else '_recipe.png' if n == 2 else f'_{n-1}_ultimo.png')

    # As filas de I/O devolvem resultados; só esta thread modifica o estado.
    from concurrent.futures import ThreadPoolExecutor
    pool = ThreadPoolExecutor(max_workers=6, thread_name_prefix='flow-io')
    inventory_future = None
    download_future = None
    status_future = None
    last_status_poll = 0
    upload_future = None
    upload_context = None
    deliveries = {}
    repair_futures = {}
    last_download_poll = 0
    last_delivery_poll = 0

    def read_future(future, label):
        try:
            return future.result()
        except RuntimeError as error:
            transient = any(word in str(error) for word in ('_IPCResponseTimeout', 'timed out', 'timeout', 'Download falhou', 'temporariamente indisponível', 'Confirmação de upload pendente'))
            if not transient:
                raise
            event('Consulta/transferência será retomada sem parar a geração: ' + label)
            return None

    def merge_inventory(receipt):
        nonlocal inv, last_inventory
        sources = {s['name']: s for s in inv['sources']}
        for source in receipt['sources']:
            assert source['name'] not in sources or sources[source['name']]['id'] == source['id'], 'Referência duplicada.'
            sources[source['name']] = source
        inv = {**receipt, 'sources': list(sources.values())}
        last_inventory = time.monotonic()
        if receipt.get('asset_ids'):
            ids = set(receipt['asset_ids'])
            for job in jobs.values():
                if job['status'] == 'rendering' and job.get('video'):
                    job['catalog_missing_checks'] = job.get('catalog_missing_checks', 0) + 1 if job['video'] not in ids else 0

    def recover_removed_assets():
        nonlocal prepared_stage, refresh_native_required
        path = ROOT / 'recuperacoes-servidor.json'
        counts = json.loads(path.read_text()) if path.exists() else {}
        for cid, job in list(jobs.items()):
            # RPC NOT_FOUND sozinho também ocorre enquanto um vídeo processa.
            # Exigir ausência persistente no catálogo COMPLETO do projeto evita
            # repetir uma renderização apenas demorada ou uma consulta transitória.
            if (job['status'] != 'rendering' or job.get('server_ready')
                    or time.time() - job['started_at'] < 120
                    or job.get('catalog_missing_checks', 0) < 3
                    or job.get('server_missing_checks', 0) < 3):
                continue
            count = counts.get(cid, 0)
            if count >= 2:
                job['status'] = 'needs_review'
                persist()
                event('Falha repetida isolada para revisão; demais vagas continuam: ' + cid)
                continue
            archive = ROOT / 'erros-servidor' / (cid + '_' + job['video'])
            archive.mkdir(parents=True, exist_ok=True)
            save(archive / 'registro.json', {'job': job, 'state': state['cenas'][cid],
                'reason': 'Ausente em pelo menos três inventários completos e três consultas RPC NOT_FOUND.'})
            for key in ('log', 'prompt_file'):
                source = Path(job[key])
                if source.is_file():
                    shutil.copy2(source, archive / source.name)
            state['cenas'][cid] = {'done': False, 'generation_revision': job.get('generation_revision', 1) + 1,
                'qa_reason': 'Asset confirmado ausente no servidor; recuperação sem bloquear outras cenas.'}
            del jobs[cid]
            counts[cid] = count + 1
            save(path, counts)
            prepared_stage = None
            refresh_native_required = True
            persist()
            event('Asset ausente confirmado; vaga e cena recuperadas: ' + cid)

    def match_jobs():
        nonlocal pilot_passed
        for cid, job in jobs.items():
            if job['status'] not in ('submitted', 'uncertain') or job.get('video'):
                continue
            matches = [v for v in inv['videos'] if v['created'][0] >= job['started_at'] - 2
                       and norm(v['prompt']) == norm(Path(job['prompt_file']).read_text())
                       and set(v['refs']) == {job['reference_id']}]
            assert len(matches) <= 1, 'Mais de um vídeo corresponde ao envio: ' + cid
            if matches:
                video = matches[0]
                assert video['model'] in ALLOWED_MODELS and video['seconds'] == 8, 'Modelo/duração divergentes.'
                job.update(video=video['id'], status='rendering')
                state['cenas'][cid] = {'video': video['id'], 'img': job['reference_id'], 'done': False,
                    'model': video['model'], 'seconds': 8, 'generation_revision': job.get('generation_revision', 1),
                    'transport': 'macro_nativo_completo', 'input_method': 'keystrokes'}
                event('Envio confirmado no servidor: ' + cid)
                persist()
            elif job['status'] != 'uncertain' and time.time() - job.get('finished_at', time.time()) > 90:
                job['status'] = 'uncertain'
                persist()
                event('Envio sem confirmação isolado; consultar sem repetir, demais vagas continuam: ' + cid)

    def schedule_repair(cid):
        if cid not in repair_futures:
            item = state['cenas'][cid]
            repair_futures[cid] = pool.submit(background, {'action': 'download', 'cid': cid, 'video': item['video'], 'revision': item.get('generation_revision', 1), 'expected_sha': item.get('sha256')})
            event('Recuperando arquivo/frame ausente em paralelo: ' + cid)

    def start_deliveries():
        approval_path = ROOT / 'qa' / 'etapa5-aprovada.json'
        approvals = json.loads(approval_path.read_text()) if approval_path.exists() else {}
        holds_path = ROOT / 'qa' / 'bloqueios.json'
        holds = json.loads(holds_path.read_text()) if holds_path.exists() else {}
        for pair in range(66, 121):
            key = f'PAR-{pair:03d}'
            output = OUTPUT / (key + '_40s.mp4')
            if key in holds or key in deliveries or output.exists() or len(deliveries) >= 2:
                continue
            cids = [key + '_' + str(n) for n in range(1, 6)]
            if not all(state['cenas'].get(cid, {}).get('done') for cid in cids):
                continue
            if approvals.get(cids[-1]) != state['cenas'][cids[-1]].get('video'):
                continue
            files = [state['cenas'][cid]['file'] for cid in cids]
            missing = [cid for cid in cids if not Path(state['cenas'][cid]['file']).is_file()]
            if missing:
                for cid in missing:
                    schedule_repair(cid)
                continue
            deliveries[key] = pool.submit(compose, files, output, ROOT / 'entrega')
            event('Montagem iniciada em paralelo: ' + key)

    def prepare_stage_async(key, cids):
        nonlocal prepared_stage, upload_future, upload_context, refresh_native_required
        required = [cid for cid in cids if not state['cenas'].get(cid, {}).get('done') and cid not in jobs]
        names = {s['name'] for s in inv['sources']}
        files = []
        for cid in required:
            if source_name(cid) in names:
                continue
            pair, number = cid.rsplit('_', 1)
            assert int(number) > 2, 'Imagem inicial ausente: ' + source_name(cid)
            previous_cid = pair + '_' + str(int(number) - 1)
            previous = state['cenas'][previous_cid]
            assert previous.get('done'), 'Dependência ainda não baixada.'
            frame = previous['last_frame']
            if not Path(frame).is_file():
                schedule_repair(previous_cid)
                return
            assert hashlib.sha256(Path(frame).read_bytes()).hexdigest() == previous['last_frame_sha256'], 'Frame-ponte alterado.'
            files.append((cid, frame))
        if files:
            save(ROOT / 'upload-ui.json', {'ready': False, 'at': time.time()})
            upload_context = (key, files)
            upload_future = pool.submit(background, {'action': 'upload_many', 'files': [f for _, f in files]})
            event('Upload da próxima etapa em paralelo: ' + ', '.join(cid for cid, _ in files))
        else:
            prepared_stage = key
            refresh_native_required = True
            event('Referências conferidas: lote ' + str(key[0]) + ', etapas ' + '+'.join(map(str, key[2])))

    def work_stages():
        approvals_path = ROOT / 'qa' / 'etapa4-aprovada.json'
        approvals = json.loads(approvals_path.read_text()) if approvals_path.exists() else {}
        stages = []
        for index, pairs in enumerate(batches, 1):
            for numbers in ((1, 2), (3,), (4,), (5,)):
                cids = [f'PAR-{p:03d}_{n}' for n in numbers for p in pairs]
                if all(state['cenas'].get(cid, {}).get('done') for cid in cids):
                    continue
                eligible = [cid for cid in cids if not state['cenas'].get(cid, {}).get('done') and cid not in jobs]
                gate = numbers != (5,) or all(approvals.get(f'PAR-{p:03d}_4') == state['cenas'].get(f'PAR-{p:03d}_4', {}).get('video') for p in pairs)
                if eligible and gate:
                    stages.append(((index, tuple(pairs), numbers), cids, eligible))
                # O hook não fornece frame para a receita. Sua falha isolada
                # não deve bloquear o lote cuja segunda cena já está baixada.
                if numbers == (1, 2) and all(state['cenas'].get(f'PAR-{p:03d}_2', {}).get('done') for p in pairs):
                    continue
                break
        return stages

    def ui_available():
        if upload_future is None:
            return True
        marker = ROOT / 'upload-ui.json'
        return marker.exists() and json.loads(marker.read_text()).get('ready', False)

    try:
        for cid, job in list(jobs.items()):
            text = Path(job['log']).read_text() if Path(job['log']).exists() else ''
            if job['status'] == 'native_inflight':
                if 'O Flow limpou o prompt' in text:
                    job.update(status='submitted', finished_at=time.time())
                elif 'Clicando uma única vez' in text:
                    job.update(status='submitted', finished_at=time.time())
                    refresh_native_required = True
                    event('Interface indisponível após clique; conferir somente recibo no servidor: ' + cid)
                elif recover_preparation(cid, job, text):
                    continue
                else:
                    raise RuntimeError('Tentativa anterior precisa de conferência: ' + cid)
            if job['status'] == 'not_sent' and recover_preparation(cid, job, text):
                continue
            if job['status'] == 'uncertain' and 'Clicando uma única vez' in text:
                job.update(status='submitted', finished_at=time.time())
                refresh_native_required = True
                event('Envio incerto será reconciliado pelo servidor, sem novo clique: ' + cid)
            if job['status'] in ('uncertain', 'not_sent'):
                raise RuntimeError('Resolver tentativa registrada antes de retomar: ' + cid)
        persist()
        event('Filas simultâneas ativas: geração, download, upload e montagem independentes.')
        while True:
            if inventory_future is not None and inventory_future.done():
                receipt = read_future(inventory_future, 'inventário')
                inventory_future = None
                if receipt is not None:
                    merge_inventory(receipt)
                    match_jobs()
            if status_future is not None and status_future.done():
                receipts = read_future(status_future, 'status das renderizações')
                for cid, receipt in (receipts or {}).items():
                    if cid not in jobs or jobs[cid].get('video') != receipt.get('video'):
                        continue
                    jobs[cid]['server_missing_checks'] = jobs[cid].get('server_missing_checks', 0) + 1 if receipt.get('missing') else 0
                    if receipt.get('failed'):
                        isolate_failed_generation(cid)
                        continue
                    if receipt['ready']:
                        jobs[cid]['server_ready'] = True
                        event('Vaga de renderização liberada antes do download: ' + cid)
                status_future = None
                persist()
            if download_future is not None and download_future.done():
                receipts = read_future(download_future, 'downloads')
                download_future = None
                for cid, receipt in (receipts or {}).items():
                    if receipt.get('failed'):
                        isolate_failed_generation(cid)
                        continue
                    if receipt['ready']:
                        state['cenas'][cid].update(receipt, done=True)
                        jobs[cid]['status'] = 'done'
                        pilot_passed = True
                        event('Cena pronta e baixada: ' + cid)
                        persist()
            for cid, future in list(repair_futures.items()):
                if future.done():
                    receipt = future.result()
                    assert receipt.get('ready'), 'Arquivo original indisponível para recuperação: ' + cid
                    state['cenas'][cid].update(receipt, done=True)
                    del repair_futures[cid]
                    event('Arquivo/frame recuperado sem interromper geração: ' + cid)
                    persist()
            if upload_future is not None and upload_future.done():
                receipts = read_future(upload_future, 'confirmação de upload')
                key, files = upload_context
                if receipts is None:
                    # Repete só consulta. Os arquivos nunca são atribuídos outra vez.
                    upload_future = pool.submit(background, {'action': 'confirm_many', 'files': [file for _, file in files]})
                else:
                    by_name = {s['name']: s for s in receipts}
                    sources = {s['name']: s for s in inv['sources']}
                    for cid, file in files:
                        ref = by_name[Path(file).name]
                        overrides[cid] = ref
                        sources[ref['name']] = ref
                    inv['sources'] = list(sources.values())
                    save(overrides_path, overrides)
                    prepared_stage = key
                    refresh_native_required = True
                    upload_future = None
                    upload_context = None
                    event('Referências confirmadas; etapa liberada: lote ' + str(key[0]) + ', ' + '+'.join(map(str, key[2])))
                    persist()
            for key, future in list(deliveries.items()):
                if future.done():
                    state['deliveries'][key] = future.result()
                    del deliveries[key]
                    event('Vídeo entregue: ' + key + ' (40s)')
                    persist()
            if active is not None and active.poll() is not None:
                job = jobs[active_cid]
                text = Path(job['log']).read_text() if Path(job['log']).exists() else ''
                job['finished_at'] = time.time()
                if 'O Flow limpou o prompt' not in text:
                    if recover_preparation(active_cid, job, text):
                        active = None
                        active_cid = None
                        continue
                    if 'Clicando uma única vez' in text:
                        refresh_native_required = True
                        event('Interface não confirmou após clique; consultando servidor sem repetir: ' + active_cid)
                    else:
                        job['status'] = 'not_sent'
                        persist('stopped_native_error')
                        raise RuntimeError('Macro não confirmou envio: ' + active_cid + '. Conferir ' + job['log'])
                job['status'] = 'submitted'
                event('Macro concluiu seleção, digitação e clique: ' + active_cid)
                active = None
                active_cid = None
                persist()
                # Confirmação em segundo plano não bloqueia o próximo envio.
                last_inventory = 0
            if active is None and upload_future is None:
                apply_final_retries()
            recover_removed_assets()
            stopping = (ROOT / 'PARAR').exists()
            if inventory_future is None and time.monotonic() - last_inventory > 5:
                inventory_future = pool.submit(background, {'action': 'inventory'})
                last_inventory = time.monotonic()
            rendering = [dict(cid=cid, video=j['video']) for cid, j in jobs.items()
                         if j['status'] == 'rendering' and j.get('video') and not j.get('server_ready')]
            if status_future is None and rendering and time.monotonic() - last_status_poll > 5:
                assert len(rendering) <= 3
                status_future = pool.submit(background, {'action': 'status_many', 'items': rendering})
                last_status_poll = time.monotonic()
            waiting = [dict(cid=cid, video=j['video'], revision=j.get('generation_revision', 1))
                       for cid, j in jobs.items() if j['status'] == 'rendering' and j.get('server_ready')]
            if download_future is None and waiting and time.monotonic() - last_download_poll > 1:
                download_future = pool.submit(background, {'action': 'download_many', 'items': waiting[:3]})
                last_download_poll = time.monotonic()
            if time.monotonic() - last_delivery_poll > 2:
                start_deliveries()
                last_delivery_poll = time.monotonic()
            if stopping and active is None and download_future is None and upload_future is None and status_future is None and not deliveries and not repair_futures:
                persist('stopped_by_file')
                return
            if len(list(OUTPUT.glob('PAR-???_40s.mp4'))) == 55:
                assert all(state['cenas'].get(f'PAR-{p:03d}_{n}', {}).get('done') for p in range(66, 121) for n in range(1, 6))
                persist('complete')
                event('Lote completo: 275 cenas e 55 vídeos.')
                return
            stage_key, stage_cids = next_stage()
            if stage_key != current_stage:
                current_stage = stage_key
                event('Etapa prioritária: ' + str(stage_key))
                persist()
            stages = work_stages()
            names = {source['name'] for source in inv['sources']}
            if upload_future is not None and upload_context is not None:
                # Metadados podem aparecer antes de a biblioteca terminar o upload.
                # Outras etapas podem gerar; estas referências aguardam confirmação.
                names.difference_update(Path(file).name for _, file in upload_context[1])
            if active is None and upload_future is None and not stopping:
                missing_stage = next(((key, cids) for key, cids, eligible in stages if any(source_name(cid) not in names for cid in eligible)), None)
                if missing_stage:
                    prepare_stage_async(*missing_stage)
            # Um vídeo já renderizado deixa de ocupar vaga mesmo enquanto transfere.
            pending = sum(j['status'] in ('native_inflight', 'submitted', 'uncertain') or (j['status'] == 'rendering' and not j.get('server_ready')) for j in jobs.values())
            if active is None and pending < 3 and ui_available() and time.time() - last_send >= 20 and not stopping:
                eligible = next((eligible for key, cids, eligible in stages if all(source_name(cid) in names for cid in eligible)), [])
                if eligible:
                    cid = args.first if args.first in eligible else eligible[0]
                    name = source_name(cid)
                    found = [s for s in inv['sources'] if s['name'] == name]
                    assert len(found) == 1, 'Referência não confirmada: ' + name
                    ref = found[0]
                    blocked_path = ROOT / 'qa' / 'referencias-bloqueadas.json'
                    blocked = json.loads(blocked_path.read_text()) if blocked_path.exists() else {}
                    if ref['id'] in blocked:
                        jobs[cid] = {'status': 'needs_review', 'reference_id': ref['id'], 'reference_name': ref['name'],
                            'generation_revision': state['cenas'].get(cid, {}).get('generation_revision', 1),
                            'log': str(ROOT / 'logs' / (cid + '.log')), 'reason': blocked[ref['id']]['reason']}
                        event('Referência bloqueada isolada antes do envio: ' + cid)
                        persist()
                        continue
                    background({'action': 'focus'})
                    prompt_file = ROOT / 'prompts' / (cid + '.txt')
                    prompt_file.parent.mkdir(exist_ok=True)
                    current_prompts = json.loads((prompts_path if prompts_path.exists() else ROOT / 'prompts-aprovados.json').read_text())
                    prompt_file.write_text(current_prompts.get(cid, current_prompts[cid.rsplit('_', 1)[1]]))
                    log = ROOT / 'logs' / (cid + '.log')
                    log.parent.mkdir(exist_ok=True)
                    log.write_text('')
                    jobs[cid] = {'generation_revision': state['cenas'].get(cid, {}).get('generation_revision', 1), 'status': 'native_inflight', 'started_at': time.time(), 'reference_id': ref['id'], 'reference_name': ref['name'], 'log': str(log), 'prompt_file': str(prompt_file)}
                    persist()
                    command = [str(Path.home() / 'Library/Application Support/Flow Macro/Macro Flow.app/Contents/MacOS/flow-macro'),
                               '--projeto', PROJECT, '--elemento', ref['name'], '--arquivo', str(prompt_file), '--keystrokes', '--substituir']
                    if refresh_native_required:
                        command.append('--atualizar')
                        refresh_native_required = False
                    with open(log, 'w') as output:
                        active = subprocess.Popen(command, cwd=BASE, stdout=output, stderr=output,
                                                  env={**os.environ, 'FLOW_CONTROLLER_CHILD': '1'})
                    active_cid = cid
                    jobs[cid]['launcher_pid'] = active.pid
                    last_send = time.time()
                    event('Iniciado macro completo: ' + cid)
                    persist()
                    if args.first == cid:
                        args.first = None
            if not stage_key and not deliveries:
                persist('waiting_visual_review_stage5')
            time.sleep(.25)
    except BaseException:
        persist('stopped_error')
        raise
    finally:
        pool.shutdown(wait=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--first', help='Cena prioritária, preservando dependências.')
    main(parser.parse_args())
