"""Operações reais do modo noturno: macro nativo + I/O já validado do fornecedor."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from PIL import Image, ImageOps
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from flow_platform import WINDOWS, native_command, process_options, terminate_tree, macro_processes
from compor import compose, probe
from noturno_core import atomic, read, redact

BASE = Path(__file__).resolve().parent.parent
SOURCE = BASE / 'retomada-macro'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def native_outcome(log, receipt, returncode=None, killed=False):
    clicked = receipt.get('phase') in ('click_intent', 'submitted_ui') or 'Clicando uma única vez' in log
    stop = any(s in log for s in ('mouse no canto superior esquerdo', 'Interrompido por Esc', 'Interrompido: Esc', 'tecla Esc', 'Interrompido pelo usuário'))
    global_error = None
    if 'notamos uma atividade incomum' in log.lower():
        global_error = 'atividade_incomum'
    if 'Sessão do macOS bloqueada' in log or 'Sessão do Windows bloqueada' in log:
        global_error = 'sessao_bloqueada'
    if 'Acessibilidade' in log and ('não liberou' in log or 'negou' in log):
        global_error = 'permissao_ausente'
    if 'créditos' in log and ('não confirmou 0 créditos' in log or 'não indica 0' in log or 'não é zero' in log or 'Créditos diferentes' in log):
        global_error = 'creditos_nao_autorizados'
    return {'clicked': clicked, 'user_stop': stop, 'global_error': global_error,
            'error': redact(log[-1400:] or ('Prazo do macro esgotado.' if killed else 'Macro terminou sem recibo de envio.')),
            'returncode': returncode, 'timeout': killed}


class Adapter:
    def __init__(self, root, plan, limits):
        self.root, self.plan, self.limits = Path(root).resolve(), plan, limits
        self.command = native_command()
        self.binary = Path(self.command[-1]) if WINDOWS else Path(self.command[0])
        for name in ('frames', 'clips', 'downloads', 'native', 'entrega', 'receipts'):
            (self.root / name).mkdir(parents=True, exist_ok=True)
        self.children = {}

    def background(self, action, **params):
        code = ('import runpy\nFLOW_RUN_DIR=' + repr(str(self.root)) + '\nFLOW_PROJECT_ID=' + repr(self.plan['project'])
                + '\nm=runpy.run_path(' + repr(str(SOURCE / 'fundo.py')) + ',init_globals=globals())\nm["main"]('
                + repr({'action': action, **params}) + ')\n')
        process = subprocess.Popen(['browser-harness'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, cwd=BASE, **process_options())
        try:
            timeout = min(self.limits['io_timeout'], self.limits['upload_timeout']) if action == 'upload_many' else self.limits['io_timeout']
            out, err = process.communicate(code, timeout=timeout)
        except subprocess.TimeoutExpired:
            terminate_tree(process.pid, force=True)
            process.communicate()
            raise RuntimeError('Prazo de I/O esgotado; preservar recibos e não repetir atribuição ou geração.') from None
        if process.returncode:
            raise RuntimeError(redact(err[-1600:]))
        try:
            return json.loads(next(line[12:] for line in out.splitlines() if line.startswith('FLOW_RESULT=')))
        except (StopIteration, json.JSONDecodeError):
            raise RuntimeError('Operação terminou sem recibo JSON válido.') from None

    def inventory(self):
        return self.background('inventory')

    def status(self, scenes):
        return self.background('status_many', items=[{'cid': cid, 'video': s['video']} for cid, s in scenes.items()])

    def stage(self, cid, ref):
        path = Path(ref['file'])
        if not path.is_file():
            raise FileNotFoundError('Imagem ou frame ausente: ' + str(path))
        digest = sha(path)
        output = self.root / 'frames' / f'B20_{cid}_fonte_{digest[:16]}.png'
        if not output.exists():
            with Image.open(path) as image:
                image.verify()
            if path.suffix.lower() == '.png':
                import shutil
                shutil.copy2(path, output)
            else:
                with Image.open(path) as image:
                    ImageOps.exif_transpose(image).convert('RGB').save(output)
        return {**ref, 'upload_file': str(output), 'source_sha256': digest}

    def upload(self, references):
        prepared, result = {}, {}
        for cid, ref in references.items():
            try:
                prepared[cid] = self.stage(cid, ref)
            except Exception as error:
                result[cid] = {'error': redact(error), 'category': 'arquivo_ausente_ou_invalido'}
        if not prepared:
            return result
        # Preparação persistida antes do seletor, inclusive para confirmar após crash.
        atomic(self.root / 'upload-contexto.json', prepared)
        receipts = self.background('upload_many', files=[r['upload_file'] for r in prepared.values()])
        by_name = {r['name']: r for r in receipts}
        for cid, ref in prepared.items():
            value = by_name.get(Path(ref['upload_file']).name)
            if value:
                result[cid] = {**ref, **value}
        return result

    def confirm_upload(self, scenes):
        context = read(self.root / 'upload-contexto.json', {})
        inventory = self.inventory()
        results = {}
        for cid, scene in scenes.items():
            try:
                ref = context.get(cid) or self.stage(cid, scene['reference'])
                name = Path(ref['upload_file']).name
                found = [r for r in inventory['sources'] if r['name'] == name]
                if len(found) > 1:
                    results[cid] = {'error': 'Referência duplicada no projeto; não escolher uma arbitrariamente.', 'category': 'upload_ambiguo'}
                elif found:
                    results[cid] = {**ref, **found[0]}
                else:
                    # Nenhum reenvio automático. Ausência no inventário não prova
                    # ausência do upload em trânsito.
                    records = read(self.root / 'upload-lotes.json', {})
                    safe = [v for v in records.values() if ref['upload_file'] in v['files'] and v.get('schema') == 2 and v.get('status') == 'not_assigned' and v.get('assignment_started') is False]
                    if safe:
                        results[cid] = {'error': 'Seletor falhou antes de atribuir o arquivo. Cena separada para retomada.', 'category': 'seletor_sem_atribuicao'}
            except Exception as error:
                results[cid] = {'error': redact(error), 'category': 'arquivo_ausente_ou_invalido'}
        return results

    def ui_available(self):
        return read(self.root / 'upload-ui.json', {}).get('ready', False)

    def paths(self, cid, attempt):
        folder = self.root / 'native' / cid
        folder.mkdir(parents=True, exist_ok=True)
        stem = folder / ('tentativa-' + str(attempt['number']))
        return stem.with_suffix('.log'), stem.with_suffix('.json'), stem.with_suffix('.txt')

    def start_native(self, cid, attempt, refresh=False):
        if not self.binary.is_file():
            raise FileNotFoundError('Aplicativo do macro ausente; execute ./flow-macro --compilar.')
        self.background('focus')
        log, journal, prompt = self.paths(cid, attempt)
        prompt.write_text(attempt['prompt'])
        if journal.exists() or log.exists():
            raise RuntimeError('Esta tentativa já tem diário. Reconciliar antes de iniciar outro processo.')
        command = [*self.command, '--projeto', self.plan['project'], '--elemento', attempt['reference']['name'],
                   '--arquivo', str(prompt), '--recibo', str(journal), '--keystrokes', '--substituir']
        if refresh:
            command.append('--atualizar')
        env = {**os.environ, 'FLOW_CONTROLLER_CHILD': '1', 'FLOW_LOCK': str(BASE / '.flow_lane.lock')}
        with log.open('w') as output:
            process = subprocess.Popen(command, stdout=output, stderr=output, cwd=BASE, env=env, **process_options())
        self.children[process.pid] = process
        return {'pid': process.pid, 'log': str(log), 'journal': str(journal), 'prompt': str(prompt)}

    def recover_native(self, cid, attempt, error=None):
        log, journal, prompt = self.paths(cid, attempt)
        # A janela entre Popen e gravação do PID é reconciliada pelo caminho
        # único do prompt. Não depender apenas de PID, que pode ser reutilizado.
        for pid in macro_processes(self.binary, prompt):
            handle = {'pid': pid, 'log': str(log), 'journal': str(journal), 'prompt': str(prompt)}
            return {'running': True, 'handle': handle}
        text = log.read_text(errors='replace') if log.exists() else ''
        if error:
            text += '\n' + redact(error)
        return native_outcome(text, read(journal, {}))

    def native_status(self, handle, timeout=False):
        process = self.children.get(handle['pid'])
        if process:
            running = process.poll() is None
        else:
            running = bool(macro_processes(self.binary, handle['prompt'], handle['pid']))
        if running and not timeout:
            return None
        if running:
            terminate_tree(handle['pid'])
            if process:
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    terminate_tree(handle['pid'], force=True)
                    process.wait(timeout=5)
            else:
                # Macro recuperado sempre foi iniciado em seu próprio grupo.
                time.sleep(.2)
                try:
                    terminate_tree(handle['pid'], force=True)
                except ProcessLookupError:
                    pass
        log = Path(handle['log'])
        return native_outcome(log.read_text(errors='replace') if log.exists() else '', read(handle['journal'], {}),
                              returncode=process.returncode if process else None, killed=timeout)

    def stop_native(self, handle):
        return self.native_status(handle, timeout=True)

    def download(self, cid, scene):
        receipt = self.background('download', cid=cid, video=scene['video'], revision=1, expected_sha=scene.get('sha256'), repair_corrupt=True)
        return {**receipt, 'video': scene['video']}

    def receipt_valid(self, scene):
        return (bool(scene.get('file') and scene.get('last_frame') and scene.get('sha256') and scene.get('last_frame_sha256'))
                and Path(scene['file']).is_file() and Path(scene['last_frame']).is_file()
                and sha(scene['file']) == scene['sha256'] and sha(scene['last_frame']) == scene['last_frame_sha256'])

    def delivery_valid(self, video):
        return bool(video.get('file') and video.get('sha256') and Path(video['file']).is_file() and sha(video['file']) == video['sha256'])

    def compose(self, key, scenes):
        # Saída exclusiva deste run: nenhuma entrega anterior é sobrescrita.
        seconds = len(scenes) * 8
        item = next((v for v in self.plan.get('videos', []) if v['id'] == key), {})
        stem = Path(item['source_name']).stem if item.get('source_name') else key
        output = Path(self.plan['output']) / (stem + f'_{seconds}s.mp4')
        receipt_path = self.root / 'receipts' / (key + '.json')
        if output.exists():
            receipt = read(receipt_path, {})
            if not self.delivery_valid(receipt) or receipt.get('file') != str(output):
                raise RuntimeError('Entrega existente sem recibo compatível; preservada sem sobrescrever.')
            return receipt
        return compose([s['file'] for s in scenes], output, self.root / 'entrega', receipt_path=receipt_path)

    def preflight(self, browser=True):
        import shutil
        if shutil.disk_usage(self.root).free < self.limits['min_free_gb'] * 1024 ** 3:
            raise RuntimeError('Espaço livre insuficiente para iniciar a execução.')
        for command in ('ffmpeg', 'ffprobe', 'browser-harness'):
            if not shutil.which(command):
                raise RuntimeError('Ferramenta não encontrada: ' + command)
        if browser:
            self.inventory()
            self.background('focus')
            for preparation in range(2):
                result = subprocess.run([*self.command, '--configurar', '--projeto', self.plan['project']],
                                        cwd=BASE, env={**os.environ, 'FLOW_CONTROLLER_CHILD': '1'}, capture_output=True,
                                        text=True, timeout=self.limits['native_timeout'], **process_options())
                detail = result.stderr or result.stdout
                # After a fresh reload the first settings popover can miss its
                # ratio control. This mode configures only; it never generates.
                # Retry that exact observed UI preparation failure once.
                if not result.returncode or preparation or 'Controle não encontrado: 9:16.' not in detail:
                    break
                time.sleep(1)
            if result.returncode:
                raise RuntimeError('Pré-checagem do macro: ' + redact(result.stderr or result.stdout))
