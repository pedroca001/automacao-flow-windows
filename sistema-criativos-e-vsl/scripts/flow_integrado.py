"""Envio pelo macro intacto; acompanhamento pelo poll do driver, sem captura de token."""
import argparse
import ast
import base64
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
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from flow_platform import WINDOWS, native_command, process_options

BASE = Path(__file__).resolve().parents[1]
UUID = re.compile(r"^[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$")
GENERATION_RPCS = {'MZZa6b', 'UpteDb'}


def save(path, data):
    temporary = path.with_suffix(path.suffix + '.tmp')
    with open(temporary, 'w', encoding='utf8') as f:
        os.chmod(temporary, 0o600)
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temporary, path)


def receipt(body):
    """Lê somente a resposta da geração; nunca lê o corpo da requisição."""
    messages = []
    for line in body.splitlines():
        try:
            value = json.loads(line)
        except (ValueError, TypeError):
            continue
        def walk(value):
            if isinstance(value, list):
                if len(value) > 2 and value[0] == 'wrb.fr' and value[1] in GENERATION_RPCS:
                    messages.append(value[2])
                else:
                    for child in value:
                        walk(child)
        walk(value)
    candidates, errors = set(), set()
    for message in messages:
        text = message if isinstance(message, str) else json.dumps(message)
        errors.update(re.findall(r'PUBLIC_ERROR_[A-Z_]+', text))
        try:
            value = json.loads(message) if isinstance(message, str) else message
        except ValueError:
            continue
        def ids(value):
            if isinstance(value, str) and UUID.fullmatch(value):
                candidates.add(value.lower())
            elif isinstance(value, list):
                for child in value:
                    ids(child)
            elif isinstance(value, dict):
                for child in value.values():
                    ids(child)
        ids(value)
    return {'candidates': sorted(candidates), 'errors': sorted(errors), 'responses': len(messages)}


def polling_core():
    """Reutiliza apenas clean/batch/pollAsset do fornecedor; não carrega geração."""
    tree = ast.parse((BASE / 'scripts/flow_driver.py').read_text())
    core = next(ast.literal_eval(n.value) for n in tree.body
                if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'CORE' for t in n.targets))
    clean = core[core.index('  const clean='):core.index('  const uuids=')]
    poll = core[core.index('  async function pollAsset('):core.index('  return {genImg, submitVid, pollAsset};')]
    clean = clean.replace("const url='/_/AiSandboxAngularFrontend", "const url=PREFIX+'/_/AiSandboxAngularFrontend")
    clean = clean.replace("'&source-path=%2Fproject%2F'+PROJ", "'&source-path='+encodeURIComponent(location.pathname)")
    return r"""window.__flowMacroRead=(function(){
      const W=window.WIZ_global_data||{};
      const at=()=>W.SNlM0e, fsid=W.FdrFJe, bl=W.cfb2h;
      const PROJ=location.pathname.split('/project/')[1].split('/')[0];
      const PREFIX=(location.pathname.match(/^\/u\/\d+/)||[''])[0];
      const RID=()=>Math.floor(1000000+Math.random()*8000000);
    """ + clean + poll + "return {pollAsset};})(); 'ok'"


def worker(config):
    # Executado dentro do browser-harness, cujos helpers estão no namespace global.
    from browser_harness.helpers import cdp, _send, drain_events
    path = Path(config['state'])
    state = json.loads(path.read_text())
    targets = [t for t in list_tabs() if urllib.parse.urlparse(t.get('url', '')).hostname == 'flow.google.com'
               and re.fullmatch(r'/(?:u/\d+/)?project/' + re.escape(state['project']) + '/?',
                                urllib.parse.urlparse(t['url']).path)]
    if len(targets) != 1:
        raise RuntimeError('Abra exatamente uma aba deste projeto; nenhuma geração enviada.')
    target = targets[0]
    sid = cdp('Target.attachToTarget', targetId=target['targetId'], flatten=True)['sessionId']
    _send({'meta': 'set_session', 'session_id': sid, 'target_id': target['targetId']})
    if config['action'] == 'enviar':
        if state['status'] != 'novo':
            raise RuntimeError('Já existe uma tentativa. Use acompanhar; envio automático repetido bloqueado.')
        cdp('Network.enable', session_id=sid)
        drain_events()
        command = ['--arquivo', state['prompt_file'], '--projeto', state['project']]
        if config.get('replace'):
            command.append('--substituir')
        if config.get('keystrokes'):
            command.append('--keystrokes')
        state.update(status='envio_iniciado', attempted_at=time.time(), target_id=target['targetId'])
        save(path, state)
        # O lock compartilhado da aba é adquirido pelo próprio macro, sem modificá-lo.
        try:
            # LaunchServices mantém a identidade do app já autorizado pelo macOS.
            # Executar o mesmo binário diretamente herda permissões diferentes.
            log = path.with_suffix('.macro.log')
            if WINDOWS:
                with log.open('w', encoding='utf-8') as stream:
                    result = subprocess.run([*native_command(), *command], stdout=stream, stderr=stream, cwd=BASE, timeout=180, check=False, **process_options())
            else:
                result = subprocess.run(['/usr/bin/open', '-W', '-n', '--stdout', str(log),
                                         '--stderr', str(log), '--env', 'FLOW_LOCK=' + os.environ['FLOW_LOCK'],
                                         str(BASE / 'Macro Flow.app'), '--args', *command],
                                        cwd=BASE, timeout=180, check=False)
            state['app_launch_exit_code'] = result.returncode
            state['macro_log'] = str(log)
        except subprocess.TimeoutExpired:
            state['status'] = 'envio_incerto'
            save(path, state)
            raise RuntimeError('Macro excedeu o prazo. Confira o Flow; não reenviar automaticamente.')
        found = []
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            for event in drain_events():
                if event.get('method') != 'Network.responseReceived' or event.get('session_id') != sid:
                    continue
                params = event.get('params', {})
                url = params.get('response', {}).get('url', '')
                parsed = urllib.parse.urlparse(url)
                rpcs = {r for value in urllib.parse.parse_qs(parsed.query).get('rpcids', []) for r in value.split(',')}
                if parsed.hostname != 'flow.google.com' or not (GENERATION_RPCS & rpcs):
                    continue
                request_id = params.get('requestId')
                # Só a resposta é lida; cabeçalhos/corpos de envio são descartados.
                body = None
                for _ in range(20):
                    try:
                        data = cdp('Network.getResponseBody', requestId=request_id, session_id=sid)
                        body = base64.b64decode(data['body']).decode() if data.get('base64Encoded') else data['body']
                        break
                    except Exception:
                        time.sleep(.1)
                if body is not None:
                    parsed_receipt = receipt(body)
                    if parsed_receipt['responses']:
                        found.append(parsed_receipt)
            if found:
                break
            time.sleep(.2)
        cdp('Network.disable', session_id=sid)
        if len(found) != 1:
            state.update(status='envio_incerto', observed_responses=len(found))
        else:
            state['receipt'] = found[0]
            state['candidates'] = [i for i in found[0]['candidates'] if i != state['project']]
            state['status'] = 'recusado' if found[0]['errors'] else 'aguardando_identificacao'
            if not state['candidates'] and state['status'] != 'recusado':
                state['status'] = 'envio_incerto'
        save(path, state)
    if state['status'] in ('novo', 'envio_iniciado', 'envio_incerto', 'recusado'):
        print(json.dumps({'status': state['status'], 'estado': str(path)}, ensure_ascii=False))
        return
    lock = open(os.environ['FLOW_LOCK'], 'a')
    fcntl.flock(lock, fcntl.LOCK_EX)
    js(polling_core())
    ready = []
    for candidate in state['candidates']:
        variable = '__macroPoll_' + uuid.uuid4().hex
        js(f"window.{variable}=null; window.__flowMacroRead.pollAsset({json.dumps(candidate)},'video').then(r=>window.{variable}=JSON.stringify({{pronto:r.pronto,url:r.url,falhou:r.falhou}})); 'ok'")
        value = None
        for _ in range(40):
            time.sleep(.25)
            raw = js('window.' + variable)
            if raw:
                value = json.loads(raw)
                break
        js('delete window.' + variable + "; 'ok'")
        if value and value.get('pronto'):
            url = urllib.parse.urlparse(value['url'])
            if url.scheme == 'https' and url.hostname == 'flow-content.google' and url.path == '/video/' + candidate:
                ready.append((candidate, value['url']))
    if len(ready) > 1:
        state['status'] = 'identificacao_ambigua'
        save(path, state)
        raise RuntimeError('Mais de um vídeo na resposta. Nenhum arquivo associado automaticamente.')
    if ready:
        video_id, url = ready[0]
        state.update(video=video_id, status='pronto')
        save(path, state)
        destination = path.parent / (state['id'] + '.mp4')
        if destination.exists():
            raise RuntimeError('Arquivo de destino já existe; não sobrescrito.')
        temporary = destination.with_suffix('.mp4.part')
        try:
            try:
                with urllib.request.urlopen(url, timeout=120) as response, open(temporary, 'wb') as f:
                    shutil_copy(response, f)
            except Exception:
                raise RuntimeError('Download falhou; use acompanhar para obter uma URL nova.') from None
            probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=codec_type,width,height', '-of', 'json', str(temporary)], capture_output=True, text=True, check=True)
            info = json.loads(probe.stdout)
            video = next(s for s in info['streams'] if s['codec_type'] == 'video')
            if abs(float(info['format']['duration']) - 8) > .25 or (video['width'], video['height']) != (720, 1280):
                raise RuntimeError('Formato do vídeo diverge de 8s / 720×1280; arquivo não entregue.')
            subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(temporary), '-f', 'null', '-'], check=True, capture_output=True)
            os.replace(temporary, destination)
            state.update(status='baixado', file=str(destination), sha256=hashlib.sha256(destination.read_bytes()).hexdigest())
            save(path, state)
        finally:
            temporary.unlink(missing_ok=True)
    print(json.dumps({'status': state['status'], 'estado': str(path), 'arquivo': state.get('file')}, ensure_ascii=False))


def shutil_copy(source, target):
    import shutil
    shutil.copyfileobj(source, target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    send = sub.add_parser('enviar', help='Macro envia uma vez; poll tenta identificar e baixar.')
    send.add_argument('--arquivo', type=Path, required=True)
    send.add_argument('--projeto', required=True)
    send.add_argument('--id', required=True)
    send.add_argument('--saida', type=Path, required=True)
    send.add_argument('--substituir', action='store_true')
    send.add_argument('--keystrokes', action='store_true', help='Press/release; padrão copiar/colar.')
    send.add_argument('--aguardar', type=int, default=0, metavar='SEGUNDOS')
    follow = sub.add_parser('acompanhar', help='Retoma somente leitura/download; nunca gera.')
    follow.add_argument('--estado', type=Path, required=True)
    follow.add_argument('--aguardar', type=int, default=0, metavar='SEGUNDOS')
    check = sub.add_parser('verificar', help='Confere app autorizado e controles, sem gerar.')
    check.add_argument('--projeto', required=True)
    args = parser.parse_args()
    if args.action == 'verificar':
        with tempfile.TemporaryDirectory(prefix='flow-macro-check-') as directory:
            log = Path(directory) / 'app.log'
            if WINDOWS:
                with log.open('w', encoding='utf-8') as stream:
                    result = subprocess.run([*native_command(), '--inspecionar', '--projeto', args.projeto], stdout=stream, stderr=stream, timeout=30, **process_options())
            else:
                result = subprocess.run(['/usr/bin/open', '-W', '-n', '--stdout', str(log),
                                         '--stderr', str(log), str(BASE / 'Macro Flow.app'),
                                         '--args', '--inspecionar', '--projeto', args.projeto], timeout=30)
            text = log.read_text() if log.exists() else ''
            if result.returncode or 'ERRO:' in text or 'Iniciar geração' not in text:
                raise RuntimeError('A inspeção do app falhou. Confira a aba e a autorização do Macro Flow.')
            print('Macro Flow autorizado; projeto e controles encontrados. Nenhuma geração enviada.')
        return
    if args.action == 'enviar':
        if not UUID.fullmatch(args.projeto) or not re.fullmatch(r'[A-Za-z0-9_-]+', args.id):
            parser.error('Projeto deve ser UUID; id aceita apenas letras, números, _ e -.')
        prompt = args.arquivo.resolve().read_text()
        if not prompt.strip():
            parser.error('Prompt vazio.')
        args.saida.mkdir(parents=True, exist_ok=True)
        state_path = args.saida.resolve() / (args.id + '.estado.json')
    else:
        state_path = args.estado.resolve()
    # Lock separado para serializar esta integração sem bloquear o lock do macro filho.
    operation_lock = open(BASE / '.flow_integracao.lock', 'a')
    fcntl.flock(operation_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if args.action == 'enviar':
        if state_path.exists():
            parser.error('Já existe estado deste id. Use acompanhar; não reenviar.')
        prompt_path = state_path.parent / (args.id + '.prompt.txt')
        with open(prompt_path, 'x', encoding='utf8') as f:
            f.write(prompt)
        save(state_path, {'id': args.id, 'project': args.projeto.lower(), 'status': 'novo',
                          'transport': 'macro_nativo', 'input_method': 'keystrokes' if args.keystrokes else 'copy_paste', 'prompt_file': str(prompt_path),
                          'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest()})
    else:
        state = json.loads(state_path.read_text())
        if state['status'] == 'baixado':
            p = Path(state['file'])
            if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != state['sha256']:
                raise RuntimeError('Arquivo entregue ausente ou alterado.')
            print('Já baixado e conferido:', p)
            return
    config = {'action': args.action, 'state': str(state_path), 'replace': getattr(args, 'substituir', False), 'keystrokes': getattr(args, 'keystrokes', False)}
    deadline = time.monotonic() + max(0, args.aguardar)
    while True:
        code = 'import runpy\nm=runpy.run_path(' + repr(str(Path(__file__).resolve())) + ",init_globals=globals())\nm['worker'](" + repr(config) + ')\n'
        result = subprocess.run(['browser-harness'], input=code, text=True, cwd=BASE)
        current = json.loads(state_path.read_text())
        if result.returncode or current['status'] not in ('aguardando_identificacao', 'pronto') or time.monotonic() >= deadline:
            raise SystemExit(result.returncode)
        config['action'] = 'acompanhar'
        time.sleep(min(20, max(0, deadline - time.monotonic())))


if __name__ == '__main__':
    main()
