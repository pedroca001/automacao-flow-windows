"""Interface de personagens e consultas. Nunca clica em Iniciar geração."""
import json
import base64
from pathlib import Path
import re
import runpy
import sys
import time
from urllib.parse import urlparse
from urllib.parse import parse_qs
from browser_harness.helpers import cdp, drain_events

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(HERE))
from core import atomic, read, sha, page_block_reason


class Browser:
    def __init__(self, plan, root):
        self.plan, self.root = plan, Path(root)
        self.url = plan['project_url'].rstrip('/')
        tabs = [t for t in list_tabs() if t['url'].rstrip('/') in (self.url, self.url + '/character') or t['url'].startswith(self.url + '/character/')]
        if len(tabs) != 1:
            raise RuntimeError('Mantenha exatamente uma aba deste projeto e desta conta /u/N aberta.')
        self.target = tabs[0]['targetId']
        switch_tab(self.target)
        self.check()

    def evaluate(self, expression, wait=False):
        result = cdp('Runtime.evaluate', expression=expression, returnByValue=True, awaitPromise=wait, _response_timeout=45)
        if result.get('exceptionDetails'):
            raise RuntimeError('Consulta na página falhou; nenhum novo envio autorizado.')
        return result.get('result', {}).get('value')

    def check(self):
        actual = self.evaluate('location.href')
        if actual.rstrip('/') not in (self.url, self.url + '/character') and not actual.startswith(self.url + '/character/'):
            raise RuntimeError('A aba mudou de projeto ou conta /u/N.')
        page = self.evaluate('''(()=>{const copy=document.body.cloneNode(true);
            copy.querySelectorAll('flow-error-tile').forEach(e=>e.remove());
            return {text:document.body.innerText,outside:copy.textContent};})()''')
        permission=read(self.root/'operacao.json',{}).get('retry_recoverable_error_tiles',False)
        reason=page_block_reason(page['text'],page['outside'],permission)
        if reason:
            raise RuntimeError('Flow requer intervencao antes de novos envios: '+reason)

    def nodes(self):
        self.check()
        return cdp('Accessibility.getFullAXTree')['nodes']

    def find(self, role, name, timeout=10, optional=False):
        end = time.monotonic() + timeout
        while True:
            found = [n for n in self.nodes() if n.get('role', {}).get('value') == role and n.get('name', {}).get('value') == name]
            if len(found) > 1:
                raise RuntimeError('Controle ambíguo: ' + name)
            if found:
                return found[0]
            if time.monotonic() >= end:
                if optional:
                    return None
                raise RuntimeError('Controle ausente: ' + name)
            time.sleep(.2)

    def click(self, node):
        self.check()
        if node.get('name', {}).get('value') == 'Iniciar geração':
            raise RuntimeError('Geração permitida somente pelo macro nativo de personagens.')
        if any(p.get('name') == 'disabled' and p.get('value', {}).get('value') for p in node.get('properties', [])):
            raise RuntimeError('Controle desabilitado.')
        cdp('DOM.scrollIntoViewIfNeeded', backendNodeId=node['backendDOMNodeId'])
        q = cdp('DOM.getBoxModel', backendNodeId=node['backendDOMNodeId'])['model']['content']
        click_at_xy(sum(q[0::2]) / 4, sum(q[1::2]) / 4)
        time.sleep(.2)

    def value(self, node):
        obj = cdp('DOM.resolveNode', backendNodeId=node['backendDOMNodeId'])['object']['objectId']
        try:
            return cdp('Runtime.callFunctionOn', objectId=obj, functionDeclaration='function(){return this.value ?? this.innerText ?? ""}', returnByValue=True)['result'].get('value', '')
        finally:
            cdp('Runtime.releaseObject', objectId=obj)

    def fill(self, node, text):
        self.click(node)
        cdp('Input.dispatchKeyEvent', type='keyDown', key='a', code='KeyA', windowsVirtualKeyCode=65, modifiers=2)
        cdp('Input.dispatchKeyEvent', type='keyUp', key='a', code='KeyA', windowsVirtualKeyCode=65, modifiers=2)
        if text:
            cdp('Input.insertText', text=text)
        else:
            cdp('Input.dispatchKeyEvent', type='keyDown', key='Backspace', windowsVirtualKeyCode=8)
            cdp('Input.dispatchKeyEvent', type='keyUp', key='Backspace', windowsVirtualKeyCode=8)
        if self.value(node).strip() != text.strip():
            raise RuntimeError('O campo não reteve o texto exato.')

    def navigate(self, url):
        goto_url(url)
        wait_for_load()
        self.check()

    def polling(self):
        module = runpy.run_path(str(BASE / 'scripts/flow_integrado.py'))
        core = module['polling_core']().replace('return {pollAsset};', 'return {pollAsset,batch};')
        core = core.replace('x.withCredentials=true;', "x.timeout=15000;x.ontimeout=()=>res({s:0,t:'timeout'});x.onabort=()=>res({s:0,t:'aborted'});x.withCredentials=true;")
        self.evaluate(core)

    def inventory(self):
        self.polling()
        result = self.evaluate(r"""(async()=>{
          const r=await window.__flowMacroRead.batch('Zzl0ze',['projects/PROJECT',null,null,null,[1]]);
          let d;for(const line of r.t.split('\n')){try{for(const row of JSON.parse(line)){if(row[0]==='wrb.fr'&&row[1]==='Zzl0ze')d=JSON.parse(row[2]);}}catch{}}
          if(!d || !Array.isArray(d[2]))return {error:'inventory_unavailable'};
          const ids=x=>Array.isArray(x)?x.flatMap(ids):typeof x==='string'&&/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/.test(x)?[x]:[];
          return {asset_ids:d[2].map(a=>a[0]),videos:d[2].filter(a=>a[7] || String(a[5]?.[6]?.[1]?.[0]?.[0]||'').startsWith('veo_')).map(a=>({id:a[0],created:a[5]?.[0],prompt:a[5]?.[1],model:a[5]?.[6]?.[1]?.[0]?.[0],refs:ids(a[5]?.[6]),status:a[5]?.[8]}))};
        })()""".replace('PROJECT', self.plan['project']), wait=True)
        if not result or result.get('error'):
            raise RuntimeError('Inventário indisponível; nenhum envio será repetido.')
        return result

    def poll(self, videos, initialize=True):
        if initialize:self.polling()
        return self.evaluate('''(async()=>Object.fromEntries(await Promise.all(Object.entries('''+json.dumps(videos)+''').map(async([key,video])=>{
            const r=await window.__flowMacroRead.pollAsset(video,"video");let code=null;
            for(const line of r.raw.split('\\n')){try{for(const row of JSON.parse(line)){
                if(row[0]==='wrb.fr'&&row[1]==='as29s'&&row[2]===null&&Array.isArray(row[5]))code=row[5][0];
            }}catch{}}
            return [key,{ready:r.pronto,failed:r.falhou,rpc_code:code}];
        }))))()''',wait=True)

    def download(self, cid, video):
        # Reutiliza somente o download validado, sem inicializar abas/estado da receita.
        self.polling()
        module = runpy.run_path(str(BASE / 'retomada-macro/fundo.py'), init_globals={'FLOW_RUN_DIR': str(self.root), 'FLOW_PROJECT_ID': self.plan['project']})
        obj = module['Background'].__new__(module['Background'])
        obj.evaluate = self.evaluate
        return obj.download(cid, video)

    def observe_start(self):
        sid=cdp('Target.attachToTarget',targetId=self.target,flatten=True)['sessionId']
        cdp('Network.enable',session_id=sid)
        drain_events()
        return {'session':sid,'started_at':time.time()}

    def observe_end(self, observer):
        module=runpy.run_path(str(BASE/'scripts/flow_integrado.py'))
        sid=observer['session']
        found=[]
        try:
            end=time.monotonic()+12
            while time.monotonic()<end:
                for event in drain_events():
                    if event.get('method')!='Network.responseReceived' or event.get('session_id')!=sid:
                        continue
                    params=event.get('params',{})
                    address=urlparse(params.get('response',{}).get('url',''))
                    rpcs={x for v in parse_qs(address.query).get('rpcids',[]) for x in v.split(',')}
                    if address.hostname!='flow.google.com' or not rpcs.intersection(module['GENERATION_RPCS']):
                        continue
                    for _ in range(20):
                        try:
                            data=cdp('Network.getResponseBody',session_id=sid,requestId=params['requestId'])
                            body=base64.b64decode(data['body']).decode() if data.get('base64Encoded') else data['body']
                            parsed=module['receipt'](body)
                            if parsed['responses']:
                                found.append(parsed)
                            break
                        except Exception:
                            time.sleep(.1)
                if found: break
                time.sleep(.2)
            return {'responses':found}
        finally:
            cdp('Network.disable',session_id=sid)
            cdp('Target.detachFromTarget',sessionId=sid)

    def portrait_id(self, name):
        node=self.find('group',name,timeout=.5,optional=True)
        if not node: return None
        obj=cdp('DOM.resolveNode',backendNodeId=node['backendDOMNodeId'])['object']['objectId']
        try:
            value=cdp('Runtime.callFunctionOn',objectId=obj,functionDeclaration='function(){const i=this.querySelector("img");return i?new URL(i.src).pathname:null}',returnByValue=True)['result'].get('value')
            match=re.fullmatch(r'/image/([a-f0-9-]{36})',value or '')
            return match[1] if match else None
        finally:
            cdp('Runtime.releaseObject',objectId=obj)

    def failed_prompt(self, expected):
        # Reutilizar apenas recupera o texto. Nunca Tentar de novo.
        editor=self.find('textbox','O que você quer criar?')
        if self.value(editor).strip():
            raise RuntimeError('Há texto no compositor; preservar antes de ler a falha.')
        data=self.evaluate("[...document.querySelectorAll('flow-error-tile')].map(e=>({message:e.querySelector('.error-message-text')?.innerText||e.innerText}))")
        for index,error in enumerate(data):
            obj=cdp('Runtime.evaluate',expression='document.querySelectorAll("flow-error-tile")['+str(index)+'].querySelector(\'button[aria-label="Reutilizar comando"]\')')['result'].get('objectId')
            if not obj: continue
            try:
                node=cdp('DOM.describeNode',objectId=obj)['node']
                self.click({'backendDOMNodeId':node['backendNodeId'],'name':{'value':'Reutilizar comando'}})
            finally:
                cdp('Runtime.releaseObject',objectId=obj)
            time.sleep(.4)
            text=self.value(self.find('textbox','O que você quer criar?'))
            ids=self.evaluate('[...document.querySelectorAll(\'button[aria-label="Elemento"] img\')].map(i=>new URL(i.src).pathname.split("/").pop())')
            matches=[e for e in expected if text.strip()==e['prompt'].strip() and (not e.get('portrait_id') or e['portrait_id'] in ids)]
            if len(matches)==1:
                return {'scene':matches[0]['scene'],'message':error['message'],'prompt':text,'portrait_ids':ids,'observed_at':time.time()}
        raise RuntimeError('Nenhuma falha corresponde a uma única cena incerta e ao retrato esperado. Nenhum envio repetido.')

    def voice(self, character):
        if self.find('button', character['voice'].lower(), timeout=.2, optional=True):
            return
        dialog = self.find('textbox', 'Pesquisar recursos', timeout=.3, optional=True)
        if dialog is None:
            trigger = self.find('button', 'Selecionar uma voz', timeout=.2, optional=True)
            if trigger is None:
                labels = {v['name'].lower() for v in read(HERE / 'voice_catalog.json', [])}
                found = [n for n in self.nodes() if n.get('role', {}).get('value') == 'button' and n.get('name', {}).get('value') in labels]
                if len(found) != 1:
                    raise RuntimeError('Não foi possível identificar a voz selecionada.')
                trigger = found[0]
            self.click(trigger)
            dialog = self.find('textbox', 'Pesquisar recursos')
        self.fill(dialog, character['voice'])
        label = character['voice_label']
        self.click(self.find('option', label))
        add = self.find('button', 'Adicionar ao personagem', timeout=.5, optional=True)
        if add:
            self.click(add)
        self.find('button', character['voice'].lower())
        time.sleep(.4)

    def register(self, character):
        path = self.root / 'characters' / (character['id'] + '.json')
        record = read(path, {'phase': 'new', 'image_sha256': character['image_sha256']})
        if sha(character['image']) != character['image_sha256'] or record['image_sha256'] != character['image_sha256']:
            raise RuntimeError('Retrato mudou após preparar o plano.')
        if record.get('phase') == 'ready':
            if not record.get('portrait_id'):
                portrait=self.portrait_id(character['name'])
                if portrait:
                    record['portrait_id']=portrait
                    atomic(path,record)
            return record
        if record.get('character_id'):
            expected = self.url + '/character/' + record['character_id']
            if self.evaluate('location.href').rstrip('/') != expected:
                self.navigate(expected)
        elif record['phase'] in ('assigning', 'upload_uncertain'):
            raise RuntimeError('Upload incerto sem ID. Reconciliar o personagem existente antes de outro upload.')
        else:
            if self.evaluate('location.href').rstrip('/') != self.url:
                self.navigate(self.url)
            self.click(self.find('button', 'Personagens'))
            self.click(self.find('button', 'Novo personagem'))
            cdp('Page.enable')
            cdp('Page.setInterceptFileChooserDialog', enabled=True)
            try:
                drain_events()
                self.click(self.find('button', 'Enviar'))
                backend = None
                end = time.monotonic() + 10
                while time.monotonic() < end and not backend:
                    for event in drain_events():
                        if event.get('method') == 'Page.fileChooserOpened':
                            backend = event['params'].get('backendNodeId')
                    time.sleep(.1)
                if not backend:
                    raise RuntimeError('Seletor não abriu. Nenhum arquivo atribuído.')
                record.update(phase='assigning', assigned_at=time.time())
                atomic(path, record)
                cdp('DOM.setFileInputFiles', files=[character['image']], backendNodeId=backend)
            finally:
                cdp('Page.setInterceptFileChooserDialog', enabled=False)
            end = time.monotonic() + 90
            while time.monotonic() < end:
                url = self.evaluate('location.href')
                match = re.fullmatch(re.escape(self.url) + r'/character/([a-f0-9-]{36})', url)
                if match:
                    record.update(phase='portrait_uploaded', character_id=match[1], url=url)
                    atomic(path, record)
                    break
                time.sleep(.5)
            else:
                record['phase'] = 'upload_uncertain'
                atomic(path, record)
                raise RuntimeError('Upload sem ID confirmado; não repetir.')
        if self.find('textbox', 'Pesquisar recursos', timeout=.2, optional=True):
            self.click(self.find('button', 'Fechar'))
        self.find('textbox', 'Nome do personagem', timeout=30)
        self.fill(self.find('textbox', 'Nome do personagem'), character['name'])
        if self.value(self.find('textbox', 'Personalidade do personagem')).strip():
            raise RuntimeError('Informações de personagem não estão vazias; preservar para revisão.')
        self.voice(character)
        record.update(phase='voice_selected', name=character['name'], voice=character['voice'], voice_label=character['voice_label'])
        atomic(path, record)
        # Salva no botão Concluir, sem gerar corpo nem retrato novo.
        self.click(self.find('button', 'Concluir'))
        end = time.monotonic() + 20
        while time.monotonic() < end:
            if self.evaluate('location.href').rstrip('/') == self.url:
                break
            time.sleep(.3)
        else:
            raise RuntimeError('Concluir não retornou ao projeto. Recibo preservado.')
        record.update(phase='ready', completed_at=time.time())
        record['portrait_id']=self.portrait_id(character['name'])
        atomic(path, record)
        return record


def main(params):
    browser = Browser(params['plan'], params['root'])
    action = params['action']
    if action == 'register':
        result = browser.register(params['character'])
    elif action == 'inventory':
        result = browser.inventory()
    elif action == 'snapshot':
        inventory=browser.inventory()
        statuses=browser.poll(params['videos'],initialize=False) if params['videos'] else {}
        focused=False
        if params.get('focus'):
            if browser.evaluate('location.href').rstrip('/')!=browser.url:
                raise RuntimeError('Preparacao do macro exige a raiz do projeto.')
            cdp('Target.activateTarget',targetId=browser.target);focused=True
        result={'inventory':inventory,'statuses':statuses,'focused':focused}
    elif action == 'poll':
        result = browser.poll(params['videos'])
    elif action == 'download':
        result = browser.download(params['cid'], params['video'])
    elif action == 'focus':
        if browser.evaluate('location.href').rstrip('/')!=browser.url:
            raise RuntimeError('Preparação do macro exige a raiz do projeto.')
        cdp('Target.activateTarget', targetId=browser.target)
        result = {'focused': browser.target}
    elif action == 'verify_send_target':
        # Somente leitura: confirmar o alvo fisico quando o hit-test UIA retorna um painel.
        result=browser.evaluate('''((p)=>{
            const [left,top,right,bottom]=p.document;
            const x=(p.point[0]-left)*innerWidth/(right-left),y=(p.point[1]-top)*innerHeight/(bottom-top);
            const buttons=[...document.querySelectorAll('button[aria-label="Iniciar geração"]')];
            const button=buttons.length===1?buttons[0]:null;
            const hit=document.elementFromPoint(x,y);
            const editor=document.querySelector('[role="textbox"][contenteditable="true"],textarea');
            const text=editor?.value??editor?.innerText??'';
            return {verified:!!button&&!button.disabled&&button.getAttribute('aria-disabled')!=='true'
                &&hit?.closest('button')===button&&text.replace(/\\r\\n?/g,'\\n').replace(/^\\n+|\\n+$/g,'')===p.prompt.replace(/^\\n+|\\n+$/g,''),
                x,y,hit:hit?.tagName,hit_label:hit?.closest('[aria-label]')?.getAttribute('aria-label'),
                button_count:buttons.length,button_rect:button?JSON.stringify(button.getBoundingClientRect()):null,
                text_length:text.length,expected_length:p.prompt.length,text_match:text.replace(/\\r\\n?/g,'\\n').replace(/^\\n+|\\n+$/g,'')===p.prompt.replace(/^\\n+|\\n+$/g,''),
                covering:document.elementsFromPoint(x,y).slice(0,4).map(e=>({tag:e.tagName,cls:e.className,html:e.outerHTML.slice(0,1200)}))};
        })('''+json.dumps({'document':params['document'],'point':params['point'],'prompt':params['prompt']})+')')
    elif action == 'observe_start':
        result=browser.observe_start()
    elif action == 'observe_end':
        result=browser.observe_end(params['observer'])
    elif action == 'failed_prompt':
        result=browser.failed_prompt(params['expected'])
    elif action == 'inspect':
        result = [{'role':n.get('role',{}).get('value'),'name':n.get('name',{}).get('value')} for n in browser.nodes() if n.get('role',{}).get('value') in ('button','textbox','option')]
    elif action == 'preview_state':
        result=browser.evaluate('''({video_count:document.querySelectorAll('video').length,
            playing:[...document.querySelectorAll('video')].filter(v=>!v.paused).length,
            errors:[...document.querySelectorAll('video')].filter(v=>v.error).map(v=>({code:v.error.code,message:v.error.message})),
            unavailable_thumbnails:[...document.querySelectorAll('img.thumbnail')].filter(i=>i.complete&&!i.naturalWidth).length})''')
    elif action == 'archive_draft':
        editor=browser.find('textbox','O que você quer criar?')
        text=browser.value(editor)
        draft=browser.root/'rascunhos'/('compositor-'+str(time.time_ns())+'.txt')
        draft.parent.mkdir(exist_ok=True);draft.write_text(text,encoding='utf-8')
        browser.fill(editor,'')
        result={'archived':str(draft),'characters':len(text),'cleared':not browser.value(editor).strip()}
    elif action == 'diagnose_inventory':
        browser.polling()
        result = browser.evaluate(r"""(async()=>{
          const r=await window.__flowMacroRead.batch('Zzl0ze',['projects/PROJECT',null,null,null,[1]]);
          let d;for(const line of r.t.split('\n')){try{for(const row of JSON.parse(line)){if(row[0]==='wrb.fr'&&row[1]==='Zzl0ze')d=JSON.parse(row[2]);}}catch{}}
          return {shapes:d?.map(x=>Array.isArray(x)?x.length:typeof x),assets:d?.[2]?.map(a=>({id:a[0],length:a.length,created:a[5]?.[0],prompt_head:String(a[5]?.[1]||'').slice(0,80),prompt_tail:String(a[5]?.[1]||'').slice(-200),model:a[5]?.[6]?.[1]?.[0]?.[0],status:a[5]?.[8],hasVideo:!!a[7]})),visibleText:document.body.innerText.slice(-6000)};
        })()""".replace('PROJECT', browser.plan['project']), wait=True)
    elif action == 'diagnose_failure':
        failures=[n for n in browser.nodes() if n.get('role',{}).get('value')=='StaticText' and n.get('name',{}).get('value','').startswith('Esse comando pode violar')]
        result=[]
        for node in failures:
            obj=cdp('DOM.resolveNode',backendNodeId=node['backendDOMNodeId'])['object']['objectId']
            try:
                result.append(cdp('Runtime.callFunctionOn',objectId=obj,functionDeclaration='function(){let e=this.nodeType===1?this:this.parentElement;const a=[];for(let i=0;e&&i<7;i++,e=e.parentElement)a.push({tag:e.tagName,cls:e.className,attrs:[...e.attributes].filter(x=>!x.name.startsWith("_ng")&&!x.value.includes("http")).map(x=>[x.name,x.value]),text:e.innerText?.slice(0,2000)});return a}',returnByValue=True)['result'].get('value'))
            finally:
                cdp('Runtime.releaseObject',objectId=obj)
        result.append(browser.evaluate("[...document.querySelectorAll('flow-error-tile')].map(e=>({buttons:[...e.querySelectorAll('button')].map(b=>({label:b.getAttribute('aria-label'),title:b.getAttribute('title'),text:b.innerText})),ancestors:[e.parentElement,e.parentElement?.parentElement,e.parentElement?.parentElement?.parentElement].filter(Boolean).map(p=>({tag:p.tagName,attributes:[...p.attributes].filter(a=>!a.name.startsWith('_ng')).map(a=>[a.name,a.value])}))}))"))
    else:
        raise ValueError('Ação desconhecida.')
    print('CHARACTER_RESULT=' + json.dumps(result, ensure_ascii=False))
