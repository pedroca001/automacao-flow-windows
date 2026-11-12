"""Fila persistente independente; um único macro de geração por vez."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(BASE / 'scripts'))
from flow_platform import locks, macro_processes, process_options, terminate_tree
from core import atomic, build_scenes, fingerprint, read, reconcile, sha, validate_plan, validate_revision, missing_asset_failure, reserved_generation_slots, output_filename, operating_limits
from client import browser
from operator_controls import VisualOperator


@contextlib.contextmanager
def controller_lock(root):
    with contextlib.ExitStack() as stack:
        for filename in (BASE / '.flow_controller.lock', Path(root) / '.personagens.lock'):
            handle = stack.enter_context(filename.open('a'))
            try:
                locks.flock(handle, locks.LOCK_EX | locks.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError('Outra fila já está usando o Flow. Receitas e personagens compartilham a trava do navegador.') from None
        yield


def probe(file):
    return json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(file)], text=True, timeout=30, **process_options()))


def assemble(files, output, root):
    """Monta localmente e entrega por rename no mesmo volume, inclusive em S:."""
    if len(files) != 5:
        raise ValueError('A montagem exige cinco cenas em ordem.')
    output, root = Path(output), Path(root)
    work = root / 'montagem' / output.stem
    work.mkdir(parents=True, exist_ok=True)
    receipt_path = work / 'entrega.json'
    receipt = read(receipt_path, {})
    if output.exists():
        if receipt.get('sha256') and sha(output) == receipt['sha256']:
            return receipt
        raise RuntimeError('Entrega existente sem recibo íntegro; não sobrescrever: ' + output.name)
    infos = [probe(f) for f in files]
    if any(abs(float(i['format']['duration']) - 8) > .25 for i in infos):
        raise ValueError('Cena não tem oito segundos.')
    command = ['ffmpeg', '-v', 'error', '-y']
    filters, streams, silent = [], [], []
    for index, (file, info) in enumerate(zip(files, infos)):
        command += ['-i', str(file)]
        filters.append(f'[{index}:v]trim=duration=8,setpts=PTS-STARTPTS,fps=24,scale=720:1280,setsar=1[v{index}]')
        if any(s['codec_type'] == 'audio' for s in info['streams']):
            filters.append(f'[{index}:a]aresample=48000,apad,atrim=duration=8,asetpts=PTS-STARTPTS,aformat=channel_layouts=stereo[a{index}]')
        else:
            silent.append(index + 1)
            filters.append(f'anullsrc=r=48000:cl=stereo,atrim=duration=8[a{index}]')
        streams.append(f'[v{index}][a{index}]')
    filters.append(''.join(streams) + 'concat=n=5:v=1:a=1[v][a]')
    temporary = work / 'montado.mp4'
    command += ['-filter_complex', ';'.join(filters), '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-threads', '2', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-t', '40', '-movflags', '+faststart', str(temporary)]
    subprocess.run(command, check=True, capture_output=True, timeout=300, **process_options())
    info = probe(temporary)
    if abs(float(info['format']['duration']) - 40) > .1:
        raise RuntimeError('Montagem não fechou quarenta segundos.')
    subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-threads', '2', '-i', str(temporary), '-f', 'null', '-'], check=True, capture_output=True, timeout=120, **process_options())
    receipt = {'file': str(output), 'sha256': sha(temporary), 'seconds': 40, 'silent_scenes': silent,
               'scene_sha256': [sha(p) for p in files], 'visual_qa': 'not_reviewed', 'voice_qa': 'not_reviewed'}
    atomic(receipt_path, receipt)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = output.with_name('.' + output.stem + '-' + fingerprint(str(root))[:8] + '.part.mp4')
    shutil.copyfile(temporary, staging)
    if sha(staging) != receipt['sha256']:
        raise RuntimeError('Cópia para a pasta de entrega divergiu.')
    if os.name == 'nt':
        os.rename(staging, output)  # Windows recusa substituir destino existente.
    else:
        os.link(staging, output)
        staging.unlink()
    return receipt


def report(path):
    path = Path(path)
    plan, state = read(path), read(path.parent / 'estado-personagens.json', {})
    records = {c['id']: read(path.parent / 'characters' / (c['id'] + '.json'), {}) for c in plan['characters']}
    scenes = state.get('scenes', {})
    counts = {}
    for scene in scenes.values():
        counts[scene['status']] = counts.get(scene['status'], 0) + 1
    value = {'mode': plan['mode'], 'project_url': plan['project_url'], 'updated_at': time.time(),
             'status': state.get('status', 'prepared'), 'reason': state.get('reason'), 'scene_counts': counts,
             'characters': records, 'assignments': plan['assignments'], 'scenes': scenes, 'deliveries': state.get('deliveries', {}),
             'discarded':state.get('discarded',{}),'notifications':[read(p) for p in sorted((path.parent/'alertas').glob('*.json'))]}
    atomic(path.parent / 'RELATORIO-PERSONAGENS.json', value)
    qa_results={cid:s['qa'] for cid,s in scenes.items() if s['status']=='complete' and s.get('qa')}
    visual=read(path.parent/'REVISAO-VISUAL.json',{})
    reviewed={s['scene']:s['sha256'] for s in visual.get('scenes',[])}
    visual_status=visual.get('status','not_reviewed') if qa_results and all(reviewed.get(cid)==s['sha256'] for cid,s in scenes.items() if s['status']=='complete') else 'not_reviewed'
    atomic(path.parent/'QA-PERSONAGENS.json',{'checked':len(qa_results),'issues':{cid:q['issues'] for cid,q in qa_results.items() if q.get('issues')},
                                          'results':qa_results,'visual_qa':visual_status,'voice_identity_qa':'not_reviewed'})
    lines = ['# Automação de personagens', '', 'Projeto: ' + plan['project_url'], '',
             'Estado: ' + value['status'], 'Motivo: ' + str(value['reason'] or ''),
             'Cenas: ' + json.dumps(counts, ensure_ascii=False), '', '| Personagem | Voz | Conjunto | Cenas prontas | Entrega |', '|---|---|---|---|---|']
    for c in plan['characters']:
        complete = sum(s['character'] == c['id'] and s['status'] == 'complete' for s in scenes.values())
        delivery = value['deliveries'].get(c['id'], {}).get('file', 'pendente')
        lines.append(f"| {c['name']} | {c['voice']} | {plan['assignments'].get(c['id'], 'prompts pendentes')} | {complete}/5 | {delivery} |")
    lines += ['', 'As montagens aguardam revisão de imagem, fala e continuidade de voz. Arquivos silenciosos e pendências ficam no JSON. Nenhuma aprovação para publicação é implícita.']
    (path.parent / 'RELATORIO-PERSONAGENS.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({'status': value['status'], 'scenes': counts, 'deliveries': len(value['deliveries']), 'reason': value['reason']}, ensure_ascii=False), flush=True)
    return 0


def stop(path):
    (Path(path).parent / 'PARAR').write_text('Parada solicitada pelo usuário. Remova conscientemente para retomar.\n', encoding='utf-8')
    print('Parada solicitada. O envio em andamento terá seu recibo preservado.')
    return 0


def reconcile_failure(path):
    path=Path(path)
    with controller_lock(path.parent):
        plan=read(path)
        state=read(path.parent/'estado-personagens.json')
        expected=[{'scene':cid,'prompt':s['prompt'],'portrait_id':read(path.parent/'characters'/(s['character']+'.json'),{}).get('portrait_id')} for cid,s in state['scenes'].items() if s['status']=='uncertain']
        observed=browser(plan,path.parent,'failed_prompt',expected=expected)
        matches=[(cid,s) for cid,s in state['scenes'].items() if s['status']=='uncertain' and s['prompt'].strip()==observed['prompt'].strip() and cid==observed['scene']]
        if len(matches)!=1:
            raise RuntimeError('O prompt da falha não corresponde a uma única cena incerta. Nenhum estado alterado.')
        cid,scene=matches[0]
        scene.update(status='failed',reason='recusa_confirmada_na_interface',failure_evidence=observed)
        if 'polític' in observed['message'].lower():
            state.setdefault('blocked_prompts',{})[scene['prompt_sha256']]={'reason':'politica_da_plataforma','message':observed['message'],'scene':cid}
            for other in state['scenes'].values():
                if other['status']=='pending' and other['prompt_sha256']==scene['prompt_sha256']:
                    other.update(status='blocked',reason='prompt_recusado_plataforma')
        atomic(path.parent/'estado-personagens.json',state)
        atomic(path.parent/'recusa-confirmada.json',{'scene':cid,**observed})
        print('Recusa reconciliada sem reenviar: '+cid)
    return report(path)


def replace_scene(path, group, number, source):
    """Nova revisão reaproveita arquivos concluídos; original permanece auditável."""
    path=Path(path)
    with controller_lock(path.parent):
        plan=read(path)
        state=read(path.parent/'estado-personagens.json')
        if group not in plan['prompt_sets'] or number not in range(1,6):
            raise ValueError('Conjunto ou número da cena inválido.')
        text=Path(source).read_text(encoding='utf-8')
        replacement=json.loads(text) if Path(source).suffix.lower()=='.json' else text
        value=plan['prompt_sets'][group]['prompts'][number-1]
        old_text=value if isinstance(value,str) else value['text']
        new_text=replacement if isinstance(replacement,str) else replacement['text']
        if new_text.strip()==old_text.strip():
            raise ValueError('O novo prompt deve ser diferente do recusado; ele não será reenviado.')
        affected=[s for s in state['scenes'].values() if s['prompt_set']==group and s['number']==number]
        if any(s['status'] not in ('pending','blocked','failed') for s in affected):
            raise ValueError('Há envio não reconciliado ou cena concluída. Não substituir automaticamente.')
        for scene in affected:
            validate_revision(scene,new_text)
        plan['prompt_sets'][group]['prompts'][number-1]=replacement
        validate_plan(plan,require_prompts=True)
        for scene in affected:
            scene.setdefault('revisions',[]).append({'prompt':scene['prompt'],'prompt_sha256':scene['prompt_sha256'],'status':scene['status'],'reason':scene.get('reason')})
            scene.update(prompt=new_text,prompt_sha256=fingerprint(new_text),spoken=replacement.get('spoken') if isinstance(replacement,dict) else None,status='pending')
            for key in ('reason','detail','failure_evidence','video','sent_at'):
                scene.pop(key,None)
        version=2
        while path.parent.with_name(path.parent.name+f'-rev{version:02d}').exists():
            version+=1
        root=path.parent.with_name(path.parent.name+f'-rev{version:02d}')
        root.mkdir()
        state.update(plan_sha256=fingerprint(plan),status='prepared',reason=None,revision_of=str(path))
        atomic(root/'plano-personagens.json',plan)
        atomic(root/'estado-personagens.json',state)
        for c in plan['characters']:
            atomic(root/'characters'/(c['id']+'.json'),read(path.parent/'characters'/(c['id']+'.json')))
        atomic(BASE/'personagens-atual.json',{'plan':str(root/'plano-personagens.json')})
        print('Nova revisão criada; cenas concluídas preservadas:',root/'plano-personagens.json')
        return 0


def start(path):
    root = Path(path).parent
    thread=os.environ.get('CODEX_THREAD_ID')
    if thread:
        atomic(root/'notificacao.json',{'thread':thread,'transport':'codex_queue'})
    with (root / 'controlador.log').open('ab') as log:
        process = subprocess.Popen([sys.executable, '-u', str(HERE / 'cli.py'), 'executar', '--plano', str(path)],
                                   cwd=BASE, stdin=subprocess.DEVNULL, stdout=log, stderr=log, **process_options(detached=True))
    atomic(root / 'processo.json', {'pid': process.pid, 'started_at': time.time()})
    print('Fila de personagens iniciada. PID:', process.pid)
    return 0


def request_review(root, state, cid, reason, limits):
    from notifier import notify
    scene=state['scenes'][cid]
    scene['attempts'][-1]['outcome']={'reason':reason,**{key:scene[key] for key in ('video','file','sha256','qa') if key in scene}}
    if len(scene['attempts'])>=limits['generation_attempts']:
        state.setdefault('discarded',{})[scene['character']]={'scene':cid,'reason':reason,'attempts':len(scene['attempts']),'at':time.time()}
        scene.update(status='discarded',reason='tres_tentativas_esgotadas')
        for other in state['scenes'].values():
            if other['character']==scene['character'] and other['status'] in ('pending','blocked','needs_review','failed'):
                other.update(status='discarded',reason='tres_tentativas_esgotadas')
        return
    scene.update(status='needs_review',reason=reason)
    atomic(Path(root)/'estado-personagens.json',state)
    event={'scene':cid,'character':scene['character'],'attempt':len(scene['attempts']),'reason':reason,
           'prompt':scene['prompt'],'spoken':scene.get('spoken'),'prompt_sha256':scene['prompt_sha256'],
           'attempts_remaining':limits['generation_attempts']-len(scene['attempts'])}
    notify(root,event)


def submit_review(path, cid, source, share=False):
    path=Path(path)
    state=read(path.parent/'estado-personagens.json')
    scene=state['scenes'][cid]
    if scene['status']!='needs_review':
        raise ValueError('A cena não está aguardando revisão.')
    text=Path(source).read_text(encoding='utf-8')
    validate_revision(scene,text)
    event_id=cid+f'__tentativa_{len(scene["attempts"]):02d}'
    destination=path.parent/'revisoes'/(event_id+'.json')
    if destination.exists():
        raise ValueError('Já há decisão para esta tentativa; não sobrescrever.')
    atomic(destination,{'scene':cid,'attempt':len(scene['attempts']),'expected_prompt_sha256':scene['prompt_sha256'],
                        'prompt':text,'share_with_blocked':share,'status':'pending','created_at':time.time()})
    print('Revisão enviada à fila; frase falada idêntica. Nenhuma geração foi disparada pelo revisor.')
    return 0


def reject_quality_in_state(root,state,cid,reason,limits):
    scene=state['scenes'][cid]
    if scene['status']!='complete':
        raise ValueError('Somente cena concluída pode ser reprovada na inspeção.')
    delivery=state.get('deliveries',{}).get(scene['character'])
    if delivery:
        output=Path(delivery['file'])
        if sha(output)!=delivery['sha256']:
            raise ValueError('Entrega mudou; não arquivar arquivo desconhecido.')
        archive=output.parent/'_revisoes';archive.mkdir(exist_ok=True)
        destination=archive/(output.stem+'__'+delivery['sha256'][:12]+output.suffix)
        if destination.exists():
            raise ValueError('Arquivo de revisão já existe; verificar manualmente.')
        os.rename(output,destination)
        state.setdefault('delivery_history',[]).append({**delivery,'archived_file':str(destination),'reason':reason})
        del state['deliveries'][scene['character']]
    scene.setdefault('visual_issues',[]).append({'reason':reason,'at':time.time()})
    request_review(root,state,cid,reason,limits)


def submit_quality(path,cid,reason):
    path=Path(path);scene=read(path.parent/'estado-personagens.json')['scenes'][cid]
    if scene['status']!='complete': raise ValueError('Cena não está concluída para inspeção.')
    destination=path.parent/'inspecoes'/(cid+'__'+scene['sha256'][:12]+'.json')
    if destination.exists(): raise ValueError('Esta inspeção já foi enviada.')
    atomic(destination,{'scene':cid,'expected_sha256':scene['sha256'],'reason':reason,'status':'pending'})
    return 0


def apply_quality(root,state,limits,assembling=()):
    for path in sorted((Path(root)/'inspecoes').glob('*.json')):
        decision=read(path)
        if decision['status']!='pending':continue
        scene=state['scenes'][decision['scene']]
        if scene['character'] in assembling:continue
        if scene['status']!='complete' or scene['sha256']!=decision['expected_sha256']:
            decision.update(status='rejected',reason='cena_mudou')
        else:
            reject_quality_in_state(root,state,decision['scene'],decision['reason'],limits)
            decision.update(status='applied',applied_at=time.time())
        atomic(path,decision)


def reject_quality(path, cid, reason):
    """Reabre uma cena após inspeção, preservando a montagem anterior."""
    path=Path(path)
    with controller_lock(path.parent):
        plan=read(path)
        state=read(path.parent/'estado-personagens.json')
        reject_quality_in_state(path.parent,state,cid,reason,validate_plan(plan,require_prompts=True))
        state.update(status='prepared',reason=None)
        atomic(path.parent/'estado-personagens.json',state)
    return report(path)


def apply_reviews(root, state):
    for path in sorted((Path(root)/'revisoes').glob('*.json')):
        decision=read(path)
        if decision.get('status')!='pending':
            continue
        scene=state['scenes'][decision['scene']]
        if scene['status']!='needs_review' or len(scene['attempts'])!=decision['attempt'] or scene['prompt_sha256']!=decision['expected_prompt_sha256']:
            decision.update(status='rejected',reason='estado_da_cena_mudou')
            atomic(path,decision)
            continue
        validate_revision(scene,decision['prompt'])
        targets=[scene]
        if decision.get('share_with_blocked'):
            targets += [s for s in state['scenes'].values() if s is not scene and s['status']=='blocked' and s['prompt_sha256']==scene['prompt_sha256']]
        for target in targets:
            validate_revision(target,decision['prompt'])
            target.setdefault('revisions',[]).append({'prompt':target['prompt'],'sha256':target['prompt_sha256'],'reason':target.get('reason'),'at':time.time()})
            target.update(prompt=decision['prompt'],prompt_sha256=fingerprint(decision['prompt']),status='pending')
            for key in ('video','file','sha256','last_frame','last_frame_sha256','ready','server_ready','sent_at','reason','detail','qa','has_audio','missing_asset_since','failure_evidence','hold_retry'):
                target.pop(key,None)
        decision.update(status='applied',applied_at=time.time(),characters=[s['character'] for s in targets])
        atomic(path,decision)
        alert=Path(root)/'alertas'/(path.stem+'.json')
        if alert.exists():
            event=read(alert);event.update(status='reviewed',review_file=str(path));atomic(alert,event)


def run(path):
    path, root = Path(path), Path(path).parent
    plan = read(path)
    limits = validate_plan(plan, require_prompts=True)
    with controller_lock(root):
        return execute(path, plan, limits)


def execute(path, plan, limits):
    root = path.parent
    limits=operating_limits(limits,read(root/'operacao.json',{}))
    cadence=read(root/'operacao.json',{}).get('submission_interval_seconds')
    if cadence is not None and (type(cadence) not in (int,float) or not 0<=cadence<=3600):
        raise ValueError('Intervalo entre envios deve estar entre 0 e 3600 segundos.')
    state_path = root / 'estado-personagens.json'
    state = read(state_path, {'schema': 1, 'plan_sha256': fingerprint(plan), 'scenes': build_scenes(plan), 'deliveries': {}, 'started_at': time.time()})
    if state['plan_sha256'] != fingerprint(plan):
        raise ValueError('Plano mudou após materializar a fila. Crie outra execução.')
    for c in plan['characters']:
        if sha(c['image']) != c['image_sha256']:
            raise ValueError('Imagem alterada após preparar: ' + c['id'])
    state.update(status='running', reason=None,controller_pid=os.getpid(),controller_started_at=time.time())
    atomic(state_path, state)
    stopped = False
    def request_stop(signum, frame):
        nonlocal stopped
        stopped = True
    previous = {s: signal.signal(s, request_stop) for s in (signal.SIGINT, signal.SIGTERM)}
    child = None
    pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='personagens-local')
    local_jobs={}
    network_pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='personagens-download')
    download_jobs={}
    operator=VisualOperator(root)
    started = time.time()
    def save():
        state['updated_at'] = time.time()
        atomic(state_path, state)
    def collect_local():
        for key,future in list(local_jobs.items()):
            if not future.done(): continue
            kind,cid=key
            result=future.result()
            del local_jobs[key]
            if kind=='qa':
                scene=state['scenes'][cid]
                scene.update(qa=result,status='complete',has_audio=result.get('has_audio',scene.get('has_audio',True)))
                if result['issues']:
                    request_review(root,state,cid,','.join(result['issues']),limits)
            else:
                state['deliveries'][cid]=result
            save()
    def collect_downloads():
        for cid,future in list(download_jobs.items()):
            if not future.done():continue
            result=future.result();del download_jobs[cid]
            scene=state['scenes'][cid]
            if result.get('ready'):scene.update(result,status='checking',completed_at=time.time())
            else:scene['status']='rendering'
            save()
    def schedule_downloads():
        for cid,scene in state['scenes'].items():
            if scene['status']=='downloading' and cid not in download_jobs:
                key=cid if len(scene['attempts'])==1 else cid+f'__R{len(scene["attempts"]):02d}'
                download_jobs[cid]=network_pool.submit(browser,plan,root,'download',cid=key,video=scene['video'])
    def schedule_local():
        from qa import inspect as inspect_qa
        for cid,scene in state['scenes'].items():
            key=('qa',cid)
            if scene['status']=='checking' and key not in local_jobs:
                download_key=cid if len(scene['attempts'])==1 else cid+f'__R{len(scene["attempts"]):02d}'
                local_jobs[key]=pool.submit(inspect_qa,download_key,dict(scene),root)
        for c in plan['characters']:
            cid=c['id'];key=('assembly',cid)
            scenes=sorted((s for s in state['scenes'].values() if s['character']==cid),key=lambda s:s['number'])
            if all(s['status']=='complete' for s in scenes) and cid not in state['deliveries'] and cid not in state.get('discarded',{}) and key not in local_jobs:
                filename=output_filename(c,plan['assignments'][cid])
                local_jobs[key]=pool.submit(assemble,[s['file'] for s in scenes],Path(plan['output'])/filename,root)
    try:
        if (root / 'PARAR').exists():
            state.update(status='stopped', reason='parada_usuario')
            return 130
        from cli import register
        operator.start()
        operator.wait_if_paused(lambda:stopped or (root/'PARAR').exists())
        if stopped or (root/'PARAR').exists():
            state.update(status='stopped',reason='parada_usuario');return 130
        if any(not (record.get('phase')=='ready' and record.get('character_id') and record.get('voice')==c['voice']
                    and record.get('image_sha256')==c['image_sha256'])
               for c in plan['characters'] for record in [read(root/'characters'/(c['id']+'.json'),{})]):
            register(path)
        # Recuperação consulta o recibo e o ID existente; nunca volta a pending.
        for cid, scene in state['scenes'].items():
            record=read(root/'characters'/(scene['character']+'.json'),{})
            if not record.get('character_id'):
                raise RuntimeError('Cadastro sem ID de personagem: '+scene['character'])
            expected=scene.setdefault('expected_character_id',record['character_id'])
            if expected!=record['character_id']:
                raise RuntimeError('O ID de um personagem mudou durante a fila; preservar recibos.')
            if scene['status'] == 'submitting':
                attempt = scene['attempts'][-1]
                if macro_processes(HERE / 'macro_personagens.py', attempt['prompt_file']):
                    raise RuntimeError('Macro anterior ainda está ativo. Aguarde antes de retomar.')
                scene['status'] = 'confirming'
            if scene['status'] == 'downloading':
                scene['status'] = 'rendering'
            if scene['status'] == 'complete' and (not Path(scene['file']).is_file() or sha(scene['file']) != scene['sha256']):
                raise RuntimeError('Clipe concluído foi alterado; preservar e revisar: ' + cid)
            if scene['status']=='complete' and not scene.get('qa'):
                scene['status']='checking'
            if scene['status']=='failed' and scene.get('reason') in ('recusa_confirmada_na_interface','render_recusado','recusa_na_resposta'):
                request_review(root,state,cid,scene['reason'],limits)
            if scene['status']=='complete' and scene.get('spoken') and scene.get('has_audio') is False:
                request_review(root,state,cid,'sem_faixa_de_audio',limits)
        last_send=0;last_macro_finish=0
        for scene in state['scenes'].values():
            for attempt in scene['attempts']:
                receipt=read(attempt['receipt'],{}) if attempt.get('receipt') else {}
                if receipt.get('phase') in ('click_intent','submitted_ui'):
                    last_send=max(last_send,receipt.get('clicked_at',receipt['at']))
                elif not attempt.get('receipt'):
                    last_send=max(last_send,attempt.get('started_at',0))
        while True:
            collect_downloads()
            collect_local()
            apply_quality(root,state,limits,{cid for kind,cid in local_jobs if kind=='assembly'})
            apply_reviews(root,state)
            schedule_local()
            operator.wait_if_paused(lambda:stopped or (root/'PARAR').exists())
            if stopped or (root / 'PARAR').exists():
                state.update(status='stopped', reason='parada_usuario')
                return 130
            if time.time() - started > limits['max_run_seconds']:
                state.update(status='incomplete', reason='prazo_da_execucao')
                return 2
            can_prepare=(any(s['status']=='pending' for s in state['scenes'].values())
                and (limits['max_rendering'] is None or
                     sum(s['status'] in ('rendering','confirming','submitting') for s in state['scenes'].values())
                     +reserved_generation_slots(state['scenes'],state.get('uncertain_reservations',{}),time.time())<limits['max_rendering'])
                and (cadence is not None or time.time()-last_send>=limits['send_interval']))
            rendering={cid:s['video'] for cid,s in state['scenes'].items() if s['status'] in ('rendering','timed_out')}
            cycle_started=time.monotonic()
            snapshot=browser(plan,root,'snapshot',videos=rendering,focus=can_prepare)
            browser_cycle_seconds=round(time.monotonic()-cycle_started,3)
            inventory=snapshot['inventory']
            for cid, scene in state['scenes'].items():
                if scene['status'] in ('confirming', 'uncertain'):
                    receipt = read(scene['attempts'][-1]['receipt'], {})
                    reconcile(scene, inventory, receipt, time.time(), limits['confirmation_timeout'])
                    if scene['status']=='rendering':
                        event_path=root/'alertas'/(cid+f'__tentativa_{len(scene["attempts"]):02d}.json')
                        event=read(event_path,{})
                        if event and event.get('kind')=='reconcile_before_retry':
                            event.update(status='reconciled',video=scene['video'],resolved_at=time.time())
                            atomic(event_path,event)
            statuses=snapshot['statuses']
            for cid, result in statuses.items():
                scene = state['scenes'][cid]
                if missing_asset_failure(scene,result,inventory,time.time()):
                    scene['failure_evidence']={'video':scene['video'],'rpc_code':5,'absent_from_inventory':True,'since':scene['missing_asset_since'],'confirmed_at':time.time()}
                    request_review(root,state,cid,'asset_removido_rpc_5',limits)
                elif result.get('failed'):
                    scene.update(status='failed', reason='render_recusado')
                    request_review(root,state,cid,'render_recusado',limits)
                elif result.get('ready'):
                    scene['status'] = 'downloading'
                elif time.time() - scene['sent_at'] > limits['render_timeout']:
                    scene.update(status='timed_out', reason='prazo_do_render')
            schedule_downloads()
            collect_downloads()
            collect_local()
            schedule_local()
            save()
            report(path)
            uncertain = [s for s in state['scenes'].values() if s['status'] in ('uncertain', 'timed_out') and not s.get('hold_retry')]
            if uncertain:
                from notifier import notify
                for cid,scene in state['scenes'].items():
                    if scene['status'] in ('uncertain','timed_out'):
                        notify(root,{'scene':cid,'character':scene['character'],'attempt':len(scene['attempts']),
                                     'reason':scene.get('reason'),'kind':'reconcile_before_retry','prompt':scene['prompt'],
                                     'spoken':scene.get('spoken'),'prompt_sha256':scene['prompt_sha256']})
                if limits['max_rendering'] is None:
                    for scene in uncertain:
                        scene['hold_retry']=True
                        scene['held_for_reconciliation_at']=time.time()
                    save()
                else:
                    state.update(status='incomplete', reason='envio_ou_render_incerto_reconciliar')
                    return 2
            pending = [(cid,s) for cid,s in state['scenes'].items() if s['status'] == 'pending']
            busy = sum(s['status'] in ('rendering', 'confirming', 'submitting') for s in state['scenes'].values())
            reserved=reserved_generation_slots(state['scenes'],state.get('uncertain_reservations',{}),time.time())
            if not pending and not busy and not local_jobs and not download_jobs:
                if any(s['status']=='needs_review' for s in state['scenes'].values()):
                    state['status']='waiting_review'
                    save()
                    time.sleep(limits['poll_interval'])
                    continue
                finished=len(state['deliveries'])+len(state.get('discarded',{}))==len(plan['characters'])
                state['status']='complete_with_discards' if finished and state.get('discarded') else 'complete' if finished else 'incomplete'
                return 0 if finished else 2
            if pending and (limits['max_rendering'] is None or busy+reserved < limits['max_rendering']) and (cadence is not None or time.time() - last_send >= limits['send_interval']):
                cid, scene = pending[0]
                character = next(c for c in plan['characters'] if c['id'] == scene['character'])
                record = read(root / 'characters' / (character['id'] + '.json'), {})
                if record.get('phase') != 'ready' or record.get('voice') != character['voice']:
                    raise RuntimeError('Cadastro ou voz não confirmado: ' + character['id'])
                operator.set_busy(True)
                if not snapshot.get('focused'):browser(plan, root, 'focus')
                operator.bind_foreground()
                folder = root / 'native' / cid
                if scene['attempts']:
                    folder = folder / f'tentativa-{len(scene["attempts"])+1:02d}'
                folder.mkdir(parents=True, exist_ok=True)
                prompt, receipt, logfile = folder / 'prompt.txt', folder / 'recibo.json', folder / 'macro.log'
                if receipt.exists() or logfile.exists():
                    raise RuntimeError('Tentativa já tem recibo/log. Reconciliar; não reenviar: ' + cid)
                prompt.write_text(scene['prompt'], encoding='utf-8')
                attempt = {'started_at': time.time(), 'baseline': inventory['asset_ids'], 'prompt_file': str(prompt), 'receipt': str(receipt), 'log': str(logfile)}
                attempt['browser_cycle_seconds']=browser_cycle_seconds
                if last_macro_finish:attempt['handoff_seconds']=round(attempt['started_at']-last_macro_finish,3)
                if plan.get('diagnostics',{}).get('capture_responses'):
                    attempt['observer']=browser(plan,root,'observe_start')
                scene['attempts'].append(attempt)
                scene['status'] = 'submitting'
                metrics=state.setdefault('metrics',{})
                metrics['peak_inflight']=max(metrics.get('peak_inflight',0),busy+reserved+1)
                save()
                command = [sys.executable, '-u', str(HERE / 'macro_personagens.py'), '--project-url', plan['project_url'], '--personagem', character['name'], '--voz', character['voice'], '--arquivo', str(prompt), '--recibo', str(receipt), '--substituir']
                environment = {**os.environ, 'FLOW_CONTROLLER_CHILD': '1',
                               'FLOW_PAUSE_FILE':str(root/'PAUSADO'),'FLOW_STOP_FILE':str(root/'PARAR'),
                               'FLOW_PLAN_FILE':str(path.resolve())}
                if cadence is not None:
                    environment['FLOW_SEND_NOT_BEFORE']=str(last_send+cadence)
                if limits['max_rendering'] is None:
                    environment['FLOW_WAIT_FOR_GENERATION_CAPACITY']='1'
                with logfile.open('wb') as log:
                    child = subprocess.Popen(command, cwd=BASE, env=environment, stdout=log, stderr=subprocess.STDOUT, **process_options())
                    remaining=limits['native_timeout'];tick=time.monotonic()
                    while child.poll() is None:
                        try:child.wait(timeout=.1)
                        except subprocess.TimeoutExpired:pass
                        now=time.monotonic()
                        if not (root/'PAUSADO').exists():remaining-=now-tick
                        tick=now
                        if remaining<=0:
                            terminate_tree(child.pid,force=True);child.wait(timeout=10);break
                    child = None
                last_macro_finish=time.time()
                attempt['macro_finished_at']=last_macro_finish
                operator.bind_foreground()
                operator.set_busy(False)
                native_receipt = read(receipt, {})
                observed=browser(plan,root,'observe_end',observer=attempt['observer']) if attempt.get('observer') else {'responses':[]}
                attempt['response_receipts']=observed['responses']
                logtext = logfile.read_text(encoding='utf-8', errors='replace')
                performance=next((line[len('PERFORMANCE='):] for line in logtext.splitlines() if line.startswith('PERFORMANCE=')),None)
                if performance:
                    attempt['performance']=json.loads(performance)
                if native_receipt.get('phase') not in ('click_intent', 'submitted_ui'):
                    scene.update(status='failed', reason='macro_antes_do_clique', detail=logtext[-1400:])
                    state.update(status='incomplete', reason='macro_interrompido_sem_clique')
                    return 2
                errors=[error for response in observed['responses'] for error in response['errors']]
                if errors:
                    scene.update(status='failed',reason='recusa_na_resposta',response_errors=errors)
                    if any('UNUSUAL' in error or 'CAPTCHA' in error for error in errors):
                        state.update(status='incomplete',reason='bloqueio_do_servico_interromper')
                        return 2
                    if any('UNSAFE' in error or 'POLICY' in error or 'MINOR' in error for error in errors):
                        state.setdefault('blocked_prompts',{})[scene['prompt_sha256']]={'reason':'politica_da_plataforma','errors':errors,'scene':cid}
                        for other in state['scenes'].values():
                            if other['status']=='pending' and other['prompt_sha256']==scene['prompt_sha256']:
                                other.update(status='blocked',reason='prompt_recusado_plataforma')
                    request_review(root,state,cid,','.join(errors),limits)
                    last_send=native_receipt.get('clicked_at',native_receipt.get('at',attempt['started_at']))
                    save()
                    continue
                scene['status'] = 'confirming'
                last_send = native_receipt.get('clicked_at',native_receipt.get('at',attempt['started_at']))
                save()
                continue
            time.sleep(min(limits['poll_interval'],1) if local_jobs or download_jobs else limits['poll_interval'])
    except Exception as error:
        state.update(status='incomplete', reason=str(error)[-1800:])
        from notifier import notify
        notify(root,{'scene':'controller_'+fingerprint(str(error))[:10],'attempt':1,'kind':'controller_error','reason':str(error)[-1400:]})
        raise
    finally:
        operator.close()
        if child is not None and child.poll() is None:
            terminate_tree(child.pid, force=True)
        network_pool.shutdown(wait=True,cancel_futures=True)
        pool.shutdown(wait=True,cancel_futures=True)
        save()
        report(path)
        for sig, handler in previous.items():
            signal.signal(sig, handler)
