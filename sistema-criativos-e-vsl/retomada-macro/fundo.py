"""Arquivos e consultas em aba auxiliar; nenhuma função envia gerações."""
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
import runpy
import re
import subprocess
import time
import urllib.parse
import urllib.request
import shutil
from concurrent.futures import ThreadPoolExecutor
from browser_harness.helpers import cdp, drain_events

SOURCE_ROOT = Path(__file__).resolve().parent
ROOT = Path(globals().get('FLOW_RUN_DIR', SOURCE_ROOT)).resolve()
PROJECT = globals().get('FLOW_PROJECT_ID', 'bd52915a-92fd-4647-a49d-d61b22101d38')
URL = 'https://flow.google.com/u/2/project/' + PROJECT

def save_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('w') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def acquire(lock, seconds=15):
    deadline = time.monotonic() + seconds
    while True:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except BlockingIOError:
            if time.monotonic() >= deadline:
                raise RuntimeError('Recurso temporariamente indisponível: outro trabalho ainda usa o lock.')
            time.sleep(.1)


class Background:
    def __init__(self):
        windows = json.loads((ROOT / 'janelas.json').read_text()) if (ROOT / 'janelas.json').exists() else {'foreground': None, 'background': None}
        tabs = list_tabs()
        def same_project(tab):
            parsed = urllib.parse.urlparse(tab.get('url', ''))
            return parsed.scheme == 'https' and parsed.hostname == 'flow.google.com' and re.fullmatch(r'/(?:u/\d+/)?project/' + re.escape(PROJECT) + '/?', parsed.path)
        matches = [t for t in tabs if same_project(t)]
        live_ids = {t['targetId'] for t in matches}
        role_key = '__flow_macro_role_' + PROJECT
        def inspect_role(target, assign=None):
            sid = cdp('Target.attachToTarget', targetId=target, flatten=True)['sessionId']
            try:
                if assign:
                    expression = 'sessionStorage.setItem(' + json.dumps(role_key) + ',' + json.dumps(assign) + ");'ok'"
                else:
                    expression = '({role:sessionStorage.getItem(' + json.dumps(role_key) + "),visible:document.visibilityState==='visible'})"
                return cdp('Runtime.evaluate', session_id=sid, expression=expression, returnByValue=True, _response_timeout=15).get('result', {}).get('value')
            finally:
                cdp('Target.detachFromTarget', sessionId=sid)
        if windows['foreground'] not in live_ids or windows.get('background') not in live_ids:
            if not matches:
                raise RuntimeError('Projeto temporariamente indisponível durante reconexão.')
            roles = {t['targetId']: inspect_role(t['targetId']) or {} for t in matches}
            mains = [target for target, role in roles.items() if role.get('role') == 'foreground']
            if windows['foreground'] in live_ids:
                foreground = windows['foreground']
            elif len(mains) == 1:
                foreground = mains[0]
            elif len(matches) == 1:
                foreground = matches[0]['targetId']
            elif len(matches) == 2:
                visible = [target for target, role in roles.items() if role.get('visible')]
                # As duas abas são do MESMO projeto autorizado. Reconstitui os
                # papéis na restauração do Chrome, sem escolher outro projeto.
                foreground = visible[0] if len(visible) == 1 else sorted(live_ids)[0]
            else:
                raise RuntimeError('Aba principal ambígua; preservar abas extras existentes.')
            windows['foreground'] = foreground
            auxiliaries = [target for target, role in roles.items() if target != foreground and role.get('role') == 'background']
            remaining = [target for target in live_ids if target != foreground]
            if windows.get('background') in remaining:
                auxiliary = windows['background']
            elif len(auxiliaries) == 1:
                auxiliary = auxiliaries[0]
            elif len(remaining) == 1:
                auxiliary = remaining[0]
            else:
                project_url = next(t['url'] for t in matches if t['targetId'] == foreground)
                auxiliary = cdp('Target.createTarget', url=project_url, background=True)['targetId']
                windows['background_owned'] = True
            if auxiliary != windows.get('background'):
                windows.setdefault('previous_backgrounds', []).append(windows.get('background'))
            windows['background'] = auxiliary
        for role in ('foreground', 'background'):
            if windows.get('marked_' + role) != windows[role]:
                inspect_role(windows[role], role)
                windows['marked_' + role] = windows[role]
        save_json(ROOT / 'janelas.json', windows)
        self.target = windows['background']
        self.sid = cdp('Target.attachToTarget', targetId=self.target, flatten=True)['sessionId']
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                if self.evaluate("document.readyState==='complete' && !!window.WIZ_global_data?.SNlM0e"):
                    break
            except Exception:
                pass
            time.sleep(.2)
        else:
            raise RuntimeError('Aba de arquivos não carregou a sessão do projeto.')
        module = runpy.run_path(str(SOURCE_ROOT.parent / 'scripts/flow_integrado.py'))
        core = module['polling_core']().replace('return {pollAsset};', 'return {pollAsset,batch};')
        core = core.replace('x.withCredentials=true;', "x.timeout=15000;x.ontimeout=()=>res({s:0,t:'timeout'});x.onabort=()=>res({s:0,t:'aborted'});x.withCredentials=true;")
        self.evaluate(core)

    def command(self, method, **params):
        return cdp(method, session_id=self.sid, _response_timeout=45 if method == 'Runtime.evaluate' else 15, **params)

    def evaluate(self, expression, wait=False):
        result = self.command('Runtime.evaluate', expression=expression, returnByValue=True, awaitPromise=wait)
        if result.get('exceptionDetails'):
            raise RuntimeError('Erro de consulta na aba auxiliar.')
        return result.get('result', {}).get('value')

    def inventory(self):
        result = self.evaluate(r"""(async()=>{
          const r=await window.__flowMacroRead.batch('Zzl0ze',['projects/PROJECT',null,null,null,[1]]);
          let d;for(const line of r.t.split('\n')){try{for(const row of JSON.parse(line)){if(row[0]==='wrb.fr'&&row[1]==='Zzl0ze')d=JSON.parse(row[2]);}}catch{}}
          if(!d)return {error:'inventory_parse'};
          const ids=x=>Array.isArray(x)?x.flatMap(ids):typeof x==='string'&&/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/.test(x)?[x]:[];
          if((d[1]!=null&&!Array.isArray(d[1]))||(d[2]!=null&&!Array.isArray(d[2])))return {error:'inventory_shape'};
          const sources=d[1]||[],assets=d[2]||[];
          const names=new Map(sources.filter(x=>x[3]?.[0]?.startsWith('B20_')).map(x=>[x[3][4],x[3][0]]));
          return {asset_ids:assets.map(a=>a[0]),sources:[...names].map(([id,name])=>({id,name})),videos:assets.filter(a=>a[7]&&ids(a[5]?.[6]).some(id=>names.has(id))).map(a=>({id:a[0],created:a[5]?.[0],prompt:a[5]?.[1],model:a[5]?.[6]?.[1]?.[0]?.[0],refs:ids(a[5]?.[6]).filter(id=>names.has(id)),status:a[5]?.[8],seconds:a[7]?.[1]?.[2]?.[0]}))};
        })()""".replace('PROJECT', PROJECT), wait=True)
        if not result or result.get('error'):
            raise RuntimeError('Consulta temporariamente indisponível (timeout de inventário).')
        return result

    def download(self, cid, video, revision=1, result=None, expected_sha=None, repair_corrupt=False):
        output = ROOT / 'clips' / (cid + '.mp4')
        frame = ROOT / 'frames' / ('B20_' + cid + '_ultimo' + (f'_R{revision:02d}' if revision > 1 else '') + '.png')
        receipts = ROOT / 'downloads'
        receipts.mkdir(exist_ok=True)
        receipt_path = receipts / (cid + f'_R{revision:02d}.json')
        receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else None
        def persist(value):
            save_json(receipt_path, value)
        # Reparação apenas de um download cujo recibo pertence exatamente à
        # geração solicitada. Preservar bytes avariados; jamais adotar arquivo
        # desconhecido ou substituir uma entrega.
        if (repair_corrupt and output.exists() and receipt and receipt.get('video') == video
                and receipt.get('revision') == revision and receipt.get('sha256')
                and hashlib.sha256(output.read_bytes()).hexdigest() != receipt['sha256']):
            quarantine = ROOT / 'downloads-corrompidos'
            quarantine.mkdir(exist_ok=True)
            tag = str(time.time_ns())
            os.link(output, quarantine / (cid + '-' + tag + '.mp4'))
            output.unlink()
            save_json(quarantine / (cid + '-' + tag + '.json'), receipt)
        if output.exists():
            if receipt is None and expected_sha:
                assert hashlib.sha256(output.read_bytes()).hexdigest() == expected_sha
                receipt = {'video': video, 'revision': revision, 'ready': False, 'file': str(output), 'sha256': expected_sha, 'seconds': 8}
                persist(receipt)
            assert receipt and receipt['video'] == video and receipt['revision'] == revision, 'Arquivo sem recibo compatível; conferir em vez de sobrescrever.'
            assert hashlib.sha256(output.read_bytes()).hexdigest() == receipt['sha256'], 'Download alterado no disco.'
            if frame.exists() and receipt.get('last_frame_sha256') == hashlib.sha256(frame.read_bytes()).hexdigest():
                return {k: v for k, v in receipt.items() if k not in ('video', 'revision')}
        else:
            if result is None:
                result = self.evaluate('(async()=>{const r=await window.__flowMacroRead.pollAsset(' + json.dumps(video) + ",'video');return {ready:r.pronto,url:r.url,failed:r.falhou};})()", wait=True)
            if not result.get('ready'):
                return {'ready': False, 'failed': result.get('failed', False)}
            address = urllib.parse.urlparse(result['url'])
            assert address.scheme == 'https' and address.hostname == 'flow-content.google' and address.path == '/video/' + video
            output.parent.mkdir(exist_ok=True)
            temporary = output.with_suffix('.mp4.part')
            try:
                try:
                    deadline = time.monotonic() + 90
                    with urllib.request.urlopen(result['url'], timeout=30) as response, open(temporary, 'wb') as f:
                        while True:
                            if time.monotonic() > deadline:
                                raise TimeoutError('Prazo total de download esgotado.')
                            chunk = response.read(1024 * 1024)
                            if not chunk:
                                break
                            f.write(chunk)
                except Exception:
                    raise RuntimeError('Download falhou; URL não foi registrada.') from None
                info = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(temporary)], text=True, timeout=30))
                stream = next(s for s in info['streams'] if s['codec_type'] == 'video')
                assert abs(float(info['format']['duration']) - 8) < .25 and (stream['width'], stream['height']) == (720, 1280)
                subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-threads', '2', '-i', str(temporary), '-f', 'null', '-'], check=True, capture_output=True, timeout=90)
                receipt = {'video': video, 'revision': revision, 'ready': False, 'file': str(output), 'sha256': hashlib.sha256(temporary.read_bytes()).hexdigest(), 'seconds': 8}
                persist(receipt)
                os.replace(temporary, output)
            finally:
                temporary.unlink(missing_ok=True)
        frame.parent.mkdir(exist_ok=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-threads', '2', '-sseof', '-0.25', '-i', str(output), '-vf', 'reverse', '-frames:v', '1', str(frame)], check=True, capture_output=True, timeout=30)
        receipt.update(ready=True, last_frame=str(frame), last_frame_sha256=hashlib.sha256(frame.read_bytes()).hexdigest())
        persist(receipt)
        return {k: v for k, v in receipt.items() if k not in ('video', 'revision')}

    def download_many(self, items):
        # CDP fica na thread principal. Só rede e validação local são paralelas.
        assert 1 <= len(items) <= 3 and len({i['cid'] for i in items}) == len(items)
        results = self.evaluate('(async()=>Promise.all(' + json.dumps([i['video'] for i in items]) + ".map(async id=>{const r=await window.__flowMacroRead.pollAsset(id,'video');return {ready:r.pronto,url:r.url,failed:r.falhou}})))()", wait=True)
        with ThreadPoolExecutor(max_workers=3) as pool:
            tasks = {i['cid']: pool.submit(self.download, i['cid'], i['video'], i.get('revision', 1), result)
                     for i, result in zip(items, results)}
            return {cid: task.result() for cid, task in tasks.items()}

    def status_many(self, items):
        assert len(items) <= 3
        results = self.evaluate('(async()=>Promise.all(' + json.dumps([i['video'] for i in items]) + r""".map(async id=>{
          const r=await window.__flowMacroRead.pollAsset(id,'video');let missing=false;
          if(!r.pronto){for(const line of (r.raw||'').split('\n')){try{for(const row of JSON.parse(line)){
            if(row[0]==='wrb.fr'&&row[1]==='as29s'&&row[2]===null&&row[5]?.[0]===5)missing=true;
          }}catch{}}}
          return {video:id,ready:r.pronto,failed:r.falhou,missing};
        })))()""", wait=True)
        return {item['cid']: result for item, result in zip(items, results)}

    def find(self, role, name, timeout=7):
        deadline = time.monotonic() + timeout
        while True:
            nodes = self.command('Accessibility.getFullAXTree')['nodes']
            found = [n for n in nodes if n.get('role', {}).get('value') == role and n.get('name', {}).get('value') == name]
            assert len(found) <= 1, 'Controle ambíguo na aba de arquivos.'
            if found:
                return found[0]
            if time.monotonic() >= deadline:
                raise RuntimeError('Controle de upload não encontrado: ' + name)
            time.sleep(.2)

    def click(self, node, user_gesture=False):
        assert node.get('name', {}).get('value') != 'Iniciar geração', 'Aba auxiliar não gera.'
        # O Chrome ignora os eventos de mouse nesta aba oculta. Aciona somente
        # o controle de upload observado no DOM, sem trazer a aba à frente.
        object_id = self.command('DOM.resolveNode', backendNodeId=node['backendDOMNodeId'])['object']['objectId']
        self.command('Runtime.callFunctionOn', objectId=object_id, functionDeclaration='function(){this.click();}',
                     returnByValue=True, userGesture=user_gesture)

    def click_upload(self, node):
        assert node.get('name', {}).get('value') == 'Enviar', 'Somente o controle de upload observado.'
        # O menu entra com animação. Não usar a geometria transitória do primeiro frame.
        time.sleep(.45)
        previous = None
        stable = 0
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            node = self.find('menuitem', 'Enviar')
            box = self.command('DOM.getBoxModel', backendNodeId=node['backendDOMNodeId'])['model']['content']
            x, y = sum(box[0::2]) / 4, sum(box[1::2]) / 4
            stable = stable + 1 if previous and abs(x - previous[0]) < .5 and abs(y - previous[1]) < .5 else 0
            previous = (x, y)
            obj = self.command('DOM.resolveNode', backendNodeId=node['backendDOMNodeId'])['object']['objectId']
            hit = self.command('Runtime.callFunctionOn', objectId=obj,
                functionDeclaration='function(x,y){const hit=document.elementFromPoint(x,y);return hit===this||this.contains(hit)}',
                arguments=[{'value': x}, {'value': y}], returnByValue=True)['result'].get('value')
            if stable >= 2 and hit:
                break
            time.sleep(.15)
        else:
            raise RuntimeError('Menu de upload não estabilizou; nenhum arquivo atribuído.')
        self.command('Input.dispatchMouseEvent', type='mouseMoved', x=x, y=y)
        self.command('Input.dispatchMouseEvent', type='mousePressed', x=x, y=y, button='left', clickCount=1)
        time.sleep(.06)
        self.command('Input.dispatchMouseEvent', type='mouseReleased', x=x, y=y, button='left', clickCount=1)

    def confirm_many(self, files):
        names = [Path(file).name for file in files]
        assert len(names) == len(set(names)) and all(name.startswith('B20_PAR-') for name in names)
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            inventory = self.inventory()
            found = {name: [s for s in inventory['sources'] if s['name'] == name] for name in names}
            assert all(len(v) <= 1 for v in found.values()), 'Upload duplicado.'
            if all(found.values()):
                path = ROOT / 'upload-lotes.json'
                with open(ROOT / '.fundo-upload.lock', 'a') as lock:
                    acquire(lock)
                    records = json.loads(path.read_text()) if path.exists() else {}
                    for record in records.values():
                        if set(Path(f).name for f in record['files']).issubset(names):
                            record.update(status='confirmed', finished_at=time.time(), reconciled=True)
                    save_json(path, records)
                return [found[name][0] for name in names]
            time.sleep(2)
        raise RuntimeError('Confirmação de upload pendente; nenhum arquivo reenviado.')

    def upload_many(self, paths):
        paths = [Path(p).resolve() for p in paths]
        assert 1 <= len(paths) <= 20 and len({p.name for p in paths}) == len(paths)
        assert all(p.parent == ROOT / 'frames' and p.name.startswith('B20_PAR-') and p.suffix == '.png' and p.is_file() for p in paths)
        inventory = self.inventory()
        by_name = {}
        for item in inventory['sources']:
            by_name.setdefault(item['name'], []).append(item)
        assert all(len(by_name.get(p.name, [])) <= 1 for p in paths), 'Referência duplicada no projeto.'
        missing = [p for p in paths if p.name not in by_name]
        receipt_path = ROOT / 'upload-lotes.json'
        receipts = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
        key = hashlib.sha256('\n'.join(sorted(p.name for p in missing)).encode()).hexdigest() if missing else None
        if missing:
            assert key not in receipts, 'Upload já tentado sem confirmação; conferir antes de repetir.'
            missing_names = {p.name for p in missing}
            uncertain_names = {Path(path).name for receipt in receipts.values() if receipt['status'] != 'confirmed' for path in receipt['files']}
            assert not missing_names.intersection(uncertain_names), 'Parte deste upload continua sem confirmação; não reenviar.'
            windows = json.loads((ROOT / 'janelas.json').read_text())
            restored = False
            save_json(ROOT / 'upload-ui.json', {'ready': False, 'at': time.time()})
            cdp('Target.activateTarget', targetId=self.target)
            time.sleep(.5)
            try:
                available = self.command('Accessibility.getFullAXTree')['nodes']
                upload = next((n for n in available if n.get('role', {}).get('value') == 'menuitem' and n.get('name', {}).get('value') == 'Enviar'), None)
                if upload is None:
                    picker = next((n for n in available if n.get('role', {}).get('value') == 'button' and n.get('name', {}).get('value') == 'Menu para adicionar arquivos'), None)
                    assert picker, 'Menu de envio indisponível.'
                    self.click(picker)
                    upload = self.find('menuitem', 'Enviar')
                self.command('Page.enable')
                self.command('Page.setInterceptFileChooserDialog', enabled=True)
                receipts[key] = {'status': 'opening', 'schema': 2, 'assignment_started': False, 'files': [str(p) for p in missing], 'started_at': time.time()}
                save_json(receipt_path, receipts)
                try:
                    self.click_upload(upload)
                    backend = None
                    for _ in range(50):
                        for event in drain_events():
                            if event.get('session_id') == self.sid and event.get('method') == 'Page.fileChooserOpened':
                                params = event.get('params', {})
                                assert len(missing) == 1 or params.get('mode') == 'selectMultiple', 'Seletor não permite upload conjunto.'
                                backend = params.get('backendNodeId')
                        if backend:
                            break
                        time.sleep(.1)
                    assert backend, 'Seletor não respondeu; nenhum arquivo reenviado.'
                    receipts[key].update(status='assigning', assignment_started=True)
                    save_json(receipt_path, receipts)
                    self.command('DOM.setFileInputFiles', files=[str(p) for p in missing], backendNodeId=backend)
                except Exception:
                    if not receipts[key]['assignment_started']:
                        receipts[key]['status'] = 'not_assigned'
                        save_json(receipt_path, receipts)
                    raise
                finally:
                    self.command('Page.setInterceptFileChooserDialog', enabled=False)
                cdp('Target.activateTarget', targetId=windows['foreground'])
                restored = True
                save_json(ROOT / 'upload-ui.json', {'ready': True, 'at': time.time()})
                receipts[key]['status'] = 'awaiting_confirmation'
                save_json(receipt_path, receipts)
                deadline = time.monotonic() + 180
                while time.monotonic() < deadline:
                    time.sleep(2)
                    inventory = self.inventory()
                    by_name = {}
                    for item in inventory['sources']:
                        by_name.setdefault(item['name'], []).append(item)
                    if all(p.name in by_name for p in paths):
                        assert all(len(by_name[p.name]) == 1 for p in paths), 'Upload duplicado; conferir.'
                        receipts[key]['status'] = 'confirmed'
                        receipts[key]['finished_at'] = time.time()
                        save_json(receipt_path, receipts)
                        break
                else:
                    raise RuntimeError('Upload conjunto sem confirmação; não repetir automaticamente.')
            finally:
                if not restored:
                    cdp('Target.activateTarget', targetId=windows['foreground'])
                    save_json(ROOT / 'upload-ui.json', {'ready': True, 'at': time.time()})
        return [{**by_name[p.name][0], 'source_sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]

    def upload(self, path):
        path = Path(path).resolve()
        assert path.parent == ROOT / 'frames' and path.name.startswith('B20_PAR-') and path.suffix == '.png' and path.is_file()
        old = [s for s in self.inventory()['sources'] if s['name'] == path.name]
        assert len(old) <= 1
        if old:
            return {**old[0], 'existing': True}
        available = self.command('Accessibility.getFullAXTree')['nodes']
        if not any(n.get('role', {}).get('value') == 'button' and n.get('name', {}).get('value') == 'Enviar mídia' for n in available):
            picker = next((n for n in available if n.get('role', {}).get('value') == 'button' and n.get('name', {}).get('value') in ('Início', 'Adicionar elementos à caixa de comando')), None)
            assert picker, 'Seletor de arquivos indisponível na aba auxiliar.'
            self.click(picker)
        upload = self.find('button', 'Enviar mídia')
        self.command('Page.enable')
        self.command('Page.setInterceptFileChooserDialog', enabled=True)
        try:
            self.click(upload, user_gesture=True)
            backend = None
            for _ in range(40):
                for event in drain_events():
                    if event.get('session_id') == self.sid and event.get('method') == 'Page.fileChooserOpened':
                        backend = event.get('params', {}).get('backendNodeId')
                if backend:
                    break
                time.sleep(.1)
            assert backend, 'Seletor de arquivo não respondeu; nenhum reenvio automático.'
            self.command('DOM.setFileInputFiles', files=[str(path)], backendNodeId=backend)
        finally:
            self.command('Page.setInterceptFileChooserDialog', enabled=False)
        for _ in range(30):
            time.sleep(1)
            found = [s for s in self.inventory()['sources'] if s['name'] == path.name]
            if found:
                assert len(found) == 1, 'Arquivo duplicado no projeto; conferir antes de selecionar.'
                self.command('Input.dispatchKeyEvent', type='keyDown', key='Escape')
                self.command('Input.dispatchKeyEvent', type='keyUp', key='Escape')
                return {**found[0], 'existing': False, 'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        raise RuntimeError('Upload sem confirmação; preservar estado e não repetir.')


def main(params):
    background = Background.__new__(Background)
    try:
        # Inicialização curta serializada; consultas/downloads não esperam uploads.
        with open(ROOT / '.fundo-init.lock', 'a') as lock:
            acquire(lock)
            background.__init__()
        action = params['action']
        if action == 'inventory':
            result = background.inventory()
        elif action == 'focus':
            windows = json.loads((ROOT / 'janelas.json').read_text())
            cdp('Target.activateTarget', targetId=windows['foreground'])
            result = {'focused': windows['foreground']}
        elif action == 'download':
            result = background.download(params['cid'], params['video'], params.get('revision', 1), expected_sha=params.get('expected_sha'))
        elif action == 'download_many':
            result = background.download_many(params['items'])
        elif action == 'status_many':
            result = background.status_many(params['items'])
        elif action == 'confirm_many':
            result = background.confirm_many(params['files'])
        elif action in ('upload_many', 'upload'):
            with open(ROOT / '.fundo-upload.lock', 'a') as lock:
                acquire(lock)
                result = background.upload_many(params['files']) if action == 'upload_many' else background.upload(params['file'])
        else:
            raise ValueError('Operação inválida.')
        print('FLOW_RESULT=' + json.dumps(result, ensure_ascii=False))
    finally:
        # Cada chamada criou sua própria sessão CDP; não acumular agentes no Chrome.
        if getattr(background, 'sid', None):
            try:
                cdp('Target.detachFromTarget', sessionId=background.sid)
            except Exception:
                pass
