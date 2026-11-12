#!/usr/bin/env python3
"""Preparação, execução e relatório da fila noturna. Geração só no subcomando executar."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from flow_platform import locks as fcntl
from flow_platform import native_command, process_options, stop_signals
from noturno_core import Queue, atomic, read, redact, validate_plan, scene_numbers
from noturno_adapter import Adapter, BASE, SOURCE


def prepare(args):
    images = Path(args.imagens).expanduser().resolve()
    if not images.is_dir():
        raise ValueError('Pasta de imagens não encontrada.')
    entries, ignored = {}, []
    recipe_only = getattr(args, 'somente_receita', False)
    for path in sorted(images.iterdir()):
        match = re.match(r'(\d{3,6})[_-]', path.name) if recipe_only else re.search(r'(?:PAR[-_]|novo_)(\d{3,6})[_-](hook|recipe)', path.name, re.I)
        if not match or path.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.webp'):
            if path.is_file():
                ignored.append(path.name)
            continue
        pair, role = 'PAR-' + match[1], 'recipe' if recipe_only else match[2].lower()
        if role in entries.setdefault(pair, {}):
            raise ValueError(f'{pair}: duas imagens para {role}; use nomes únicos ou edite o plano explicitamente.')
        entries[pair][role] = {'file': str(path)}
    if not entries:
        raise ValueError('Nenhum par encontrado. Use PAR-001_hook.png / PAR-001_recipe.png ou nomes novo_001_hook / novo_001_recipe.')
    root = Path(args.pasta).expanduser().resolve() if args.pasta else BASE / 'execucoes-noturnas' / datetime.now().strftime('%Y%m%d-%H%M%S')
    if (root / 'plano-noturno.json').exists():
        raise ValueError('Já existe um plano nesta pasta; use executar para retomá-lo ou escolha outra pasta.')
    root.mkdir(parents=True, exist_ok=True)
    prompts_source = Path(args.prompts).expanduser().resolve() if args.prompts else SOURCE / 'prompts-ativos.json'
    templates = read(prompts_source)
    # Não carregar exceções de IDs da produção anterior em vídeos novos.
    prompts = {str(n): templates[str(n + 1 if recipe_only else n)] for n in range(1, 5 if recipe_only else 6)}
    missing = []
    for pair, refs in entries.items():
        for role in (('recipe',) if recipe_only else ('hook', 'recipe')):
            if role not in refs:
                refs[role] = {'file': str(images / (pair + '_' + role + '_AUSENTE.png'))}
                missing.append(pair + ': ' + role)
    project = args.projeto
    if '://' in project:
        match = re.search(r'/project/([a-f0-9-]+)', project)
        project = match[1] if match else project
    plan = {'schema': 1, 'project': project, 'output': str(Path(args.saida).expanduser().resolve() if args.saida else root / 'Montados para revisar'),
            'prompts': prompts, 'videos': [{'id': key, **refs} for key, refs in sorted(entries.items())], 'limits': {}}
    if recipe_only:
        plan['mode'] = 'recipe_only'
        for item in plan['videos']:
            item['source_name'] = Path(item['recipe']['file']).name
    validate_plan(plan)
    atomic(root / 'plano-noturno.json', plan)
    atomic(root / 'entradas.json', {'missing': missing, 'ignored': ignored, 'images': str(images)})
    if not getattr(args, 'sem_definir_atual', False):
        atomic(BASE / 'noturno-atual.json', {'plan': str(root / 'plano-noturno.json')})
    print(f'Plano preparado: {len(entries)} vídeos / {len(entries) * len(scene_numbers(plan))} cenas.')
    print('Plano:', root / 'plano-noturno.json')
    print('Saída:', plan['output'])
    if missing:
        print('Entradas ausentes (a fila registrará e seguirá as outras):', ', '.join(missing))
    print('Nenhuma imagem enviada ou geração iniciada. Abra Flow Noturno' + ('.cmd' if sys.platform == 'win32' else '.command') + ' para executar.')


def get_plan(value):
    if value:
        return Path(value).expanduser().resolve()
    pointer = read(BASE / 'noturno-atual.json', {})
    if not pointer.get('plan'):
        raise ValueError('Prepare uma leva com Preparar Flow Noturno antes de iniciar.')
    return Path(pointer['plan'])


def execute(args):
    path = get_plan(args.plano)
    root, plan = path.parent, read(path)
    limits = validate_plan(plan)
    locks = []
    for filename in (BASE / '.flow_controller.lock', SOURCE / '.lote.lock', root / '.noturno.lock'):
        handle = filename.open('a')
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            handle.close()
            for old in locks:
                old.close()
            raise RuntimeError('Outra automação já está em execução. Esta instância não começou.')
        locks.append(handle)
    queue = None
    adapter = Adapter(root, plan, limits)
    interrupted = False
    def stop(signum, frame):
        nonlocal interrupted
        interrupted = True
        if queue:
            queue.stop_reason = 'parada_usuario'
    previous = {s: signal.signal(s, stop) for s in stop_signals()}
    error = None
    preflight_done = False
    try:
        queue = Queue(root, plan, adapter)
        # Execução já finalizada não abre navegador nem dispara gerações.
        if all(v['status'] == 'complete' for v in queue.state['videos'].values()):
            return 0
        if (root / 'PARAR').exists():
            queue.stop_reason = 'parada_usuario'
            return 130
        if args.validar:
            adapter.preflight(browser=False)
            # Validar hoje não deve consumir as 12 horas da produção de amanhã.
            if all(s['status'] == 'pending' and not s['attempts'] for s in queue.scenes.values()):
                queue.state.pop('run_started_at', None)
            queue.stop_reason = 'validacao_sem_geracao'
            print('Plano e ferramentas locais conferidos. Nenhum upload ou geração executado.')
            return 0
        if queue.native is None:
            subprocess.run([*native_command(), '--compilar'] if sys.platform == 'win32' else [str(BASE / 'flow-macro'), '--compilar'], cwd=BASE, check=True, timeout=120)
            adapter.preflight(browser=True)
        else:
            # Não disputar foco/configuração nem trocar o binário de um macro
            # recuperado que ainda está digitando.
            adapter.preflight(browser=False)
            adapter.inventory()
        preflight_done = True
        atomic(root / 'processo.json', {'pid': os.getpid(), 'started_at': time.time(), 'plan': str(path)})
        print('Execução noturna iniciada. Relatório:', root / 'RELATORIO-NOTURNO.md', flush=True)
        while not interrupted and queue.tick():
            if __import__('shutil').disk_usage(root).free < limits['min_free_gb'] * 1024 ** 3:
                queue.stop_reason = 'espaco_livre_insuficiente'
            time.sleep(.25)
    except (KeyboardInterrupt, SystemExit):
        interrupted = True
        if queue:
            queue.stop_reason = 'parada_usuario'
    except Exception as exception:
        error = redact(exception)
        print('Ocorrência:', error, file=sys.stderr)
    finally:
        if queue:
            if queue.native:
                cid, native, _ = queue.native
                queue.native = None
                try:
                    queue.native_result(cid, adapter.stop_native(native))
                except Exception as exception:
                    queue.failure(cid, 'macro_interrompido', exception, reserve=True)
            try:
                queue.close()
                queue.harvest()
            except Exception as exception:
                error = error or redact(exception)
                queue.event('falha_ao_finalizar', exception)
            if interrupted:
                queue.stop_reason = 'parada_usuario'
            if error and not preflight_done:
                queue.event('pre_checagem_falhou', error)
                queue.stop_reason = 'pre_checagem_falhou'
            report = queue.finish(error=error if preflight_done else None)
            print(f"Resultado: {report['complete_videos']}/{report['planned_videos']} vídeos; {report['incomplete_videos']} incompletos.", flush=True)
            print('Relatório:', root / 'RELATORIO-NOTURNO.md', flush=True)
        else:
            atomic(root / 'RELATORIO-PRE-CHECAGEM.json', {'status': 'not_started', 'reason': error or 'pré-checagem interrompida', 'at': time.time()})
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        for handle in locks:
            handle.close()
    if interrupted:
        return 130
    if error:
        return 75 if preflight_done else 2
    return 0 if report['status'] == 'complete' else 2


def report_only(args):
    path = get_plan(args.plano)
    queue = Queue.__new__(Queue)
    queue.root, queue.plan = path.parent, read(path)
    queue.state = read(queue.root / 'estado-noturno.json')
    if not queue.state:
        raise ValueError('Esta leva ainda não tem estado de execução.')
    queue.clock, queue.stop_reason = time.time, queue.state.get('stop_reason')
    report = queue.report()
    print(f"{report['complete_videos']}/{report['planned_videos']} completos; relatório atualizado em {queue.root}.")


def supervise(args):
    path = get_plan(args.plano)
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000003)
    log = path.parent / 'execucao-noturna.log'
    process, stopped = None, False
    def stop(signum, frame):
        nonlocal stopped
        stopped = True
        (path.parent / 'PARAR').touch()
        if sys.platform != 'win32' and process and process.poll() is None:
            process.send_signal(signal.SIGTERM)
    previous = {s: signal.signal(s, stop) for s in stop_signals()}
    try:
        # Somente crash inesperado. Nunca reiniciar parada do usuário ou fila com erros.
        for attempt in range(3):
            if stopped:
                return 130
            with log.open('a') as stream:
                process = subprocess.Popen([sys.executable, '-u', str(Path(__file__).resolve()), 'executar', '--plano', str(path)],
                                           stdout=stream, stderr=stream, cwd=BASE)
                code = process.wait()
            unexpected = code == 75 or (code < 0 and code not in tuple(-s for s in stop_signals())) or (sys.platform == 'win32' and code >= 0xC0000000)
            if stopped or not unexpected or (path.parent / 'PARAR').exists() or attempt == 2:
                print('Execução encerrada. Relatório:', path.parent / 'RELATORIO-NOTURNO.md')
                return 130 if stopped else code
            print('Controlador interrompido; retomada limitada em 10 segundos. Clique registrado não será repetido.')
            time.sleep(10)
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


def start_detached(args):
    path = get_plan(args.plano)
    validate_plan(read(path))
    if (path.parent / 'PARAR').exists():
        raise ValueError('Há um pedido PARAR nesta leva. Para retomá-la conscientemente, remova esse arquivo e inicie novamente.')
    if read(path.parent / 'estado-noturno.json', {}).get('status') == 'complete':
        print('Esta leva já está concluída. Prepare outra leva para gerar vídeos novos.')
        return 0
    command = [sys.executable, '-u', str(Path(__file__).resolve()), 'supervisionar', '--plano', str(path)]
    if sys.platform == 'darwin':
        command = ['/usr/bin/caffeinate', '-dims', *command]
    with (path.parent / 'supervisor.log').open('a') as stream:
        process = subprocess.Popen(command, cwd=BASE, stdout=stream, stderr=stream, stdin=subprocess.DEVNULL, **process_options(detached=True))
    atomic(path.parent / 'supervisor.json', {'pid': process.pid, 'started_at': time.time(), 'plan': str(path)})
    print('Automação iniciada em segundo plano. Pode fechar o Codex e esta janela do Terminal.')
    print('Mantenha o computador ligado e a sessão desbloqueada; não use o mouse/teclado durante o macro.')
    print('Relatório:', path.parent / 'RELATORIO-NOTURNO.md')


def request_stop(args):
    path = get_plan(args.plano)
    (path.parent / 'PARAR').touch()
    print('Parada solicitada. A execução preservará os recibos e atualizará o relatório.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('preparar')
    p.add_argument('--imagens', required=True)
    p.add_argument('--projeto', required=True)
    p.add_argument('--saida')
    p.add_argument('--pasta')
    p.add_argument('--prompts')
    p.add_argument('--somente-receita', action='store_true', help='Quatro cenas sem hook; imagens numeradas 001_nome.png. Reutiliza os prompts 2 a 5 da receita.')
    p.add_argument('--sem-definir-atual', action='store_true', help='Preparar sem trocar a leva usada pelos atalhos.')
    p.set_defaults(function=prepare)
    for name, function in [('executar', execute), ('relatorio', report_only), ('supervisionar', supervise), ('iniciar', start_detached), ('parar', request_stop)]:
        p = sub.add_parser(name)
        p.add_argument('--plano')
        p.set_defaults(function=function)
        if name == 'executar':
            p.add_argument('--validar', action='store_true', help='Somente checagens locais; sem navegador, upload ou geração.')
    args = parser.parse_args()
    try:
        return args.function(args) or 0
    except Exception as error:
        print('ERRO:', redact(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
