"""Operações de referência e leitura; nunca clica em Iniciar geração."""
try:
    import fcntl
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
    from flow_platform import locks as fcntl
import sys
import json
import os
from pathlib import Path
import runpy
import time
import urllib.parse
from browser_harness.helpers import cdp, _send

PROJECT = 'bd52915a-92fd-4647-a49d-d61b22101d38'
ROOT = Path(__file__).resolve().parent


def attach():
    tabs = [t for t in list_tabs() if urllib.parse.urlparse(t.get('url', '')).hostname == 'flow.google.com'
            and urllib.parse.urlparse(t['url']).path.rstrip('/').endswith('/project/' + PROJECT)]
    assert len(tabs) == 1, 'Abra exatamente uma aba do projeto.'
    sid = cdp('Target.attachToTarget', targetId=tabs[0]['targetId'], flatten=True)['sessionId']
    _send({'meta': 'set_session', 'session_id': sid, 'target_id': tabs[0]['targetId']})


def nodes():
    return cdp('Accessibility.getFullAXTree')['nodes']


def find(role, name, timeout=7, required=True):
    until = time.monotonic() + timeout
    while True:
        found = [n for n in nodes() if n.get('role', {}).get('value') == role and n.get('name', {}).get('value') == name]
        assert len(found) <= 1, 'Controle ambíguo: ' + name
        if found:
            return found[0]
        if time.monotonic() >= until:
            if required:
                raise RuntimeError('Controle não encontrado: ' + name)
            return None
        time.sleep(.2)


def click(node):
    assert node.get('name', {}).get('value') != 'Iniciar geração'
    box = cdp('DOM.getBoxModel', backendNodeId=node['backendDOMNodeId'])['model']['content']
    click_at_xy(sum(box[0::2]) / 4, sum(box[1::2]) / 4)


def prepare(name):
    assert name.startswith('B20_PAR-') and name.endswith('.png')
    # O compositor de Elementos expõe este botão; Frames expõe Início/Fim.
    if not find('button', 'Adicionar elementos à caixa de comando', timeout=1, required=False):
        click(find('button', 'Gatilho de configurações'))
        click(find('radio', 'Elementos'))
        radio = find('radio', 'Elementos')
        assert any(p.get('name') == 'checked' and str(p.get('value', {}).get('value')).lower() == 'true' for p in radio.get('properties', [])), 'Modo Elementos não confirmado.'
        cdp('Input.dispatchKeyEvent', type='keyDown', key='Escape')
        cdp('Input.dispatchKeyEvent', type='keyUp', key='Escape')
    assert find('button', 'Adicionar elementos à caixa de comando'), 'Compositor deve estar em Elementos.'
    text = js("document.querySelector('[contenteditable=true][role=textbox]')?.innerText || ''") or ''
    approved = json.loads((ROOT / 'prompts-aprovados.json').read_text())
    assert not text.strip() or ' '.join(text.split()) in {' '.join(p.split()) for p in approved.values()}, 'Há um prompt editado fora do lote; preservar.'
    clear = find('button', 'Apagar comando', timeout=.2, required=False)
    if clear:
        click(clear)
    click(find('button', 'Adicionar elementos à caixa de comando'))
    click(find('textbox', 'Pesquisar recursos'))
    cdp('Input.dispatchKeyEvent', type='keyDown', key='a', code='KeyA', windowsVirtualKeyCode=65, modifiers=4 if sys.platform == 'darwin' else 2)
    cdp('Input.dispatchKeyEvent', type='keyUp', key='a', code='KeyA', windowsVirtualKeyCode=65, modifiers=4 if sys.platform == 'darwin' else 2)
    cdp('Input.insertText', text=name)
    click(find('option', name + ' Imagem'))
    assert find('button', 'Elemento'), 'Imagem não foi adicionada como elemento.'
    return {'prepared': name, 'mode': 'Elementos'}


def inventory():
    module = runpy.run_path(str(ROOT.parent / 'scripts/flow_integrado.py'), init_globals=globals())
    js(module['polling_core']().replace('return {pollAsset};', 'return {pollAsset,batch};'))
    variable = '__retomadaInventory'
    expression = r"""window.__retomadaInventory=null;window.__flowMacroRead.batch('Zzl0ze',['projects/PROJECT',null,null,null,[1]]).then(r=>{
      let d;for(const line of r.t.split('\n')){try{for(const row of JSON.parse(line)){if(row[0]==='wrb.fr'&&row[1]==='Zzl0ze')d=JSON.parse(row[2]);}}catch{}}
      if(!d){window.__retomadaInventory=JSON.stringify({error:'inventory_parse'});return;}
      const uuids=x=>Array.isArray(x)?x.flatMap(uuids):typeof x==='string'&&/^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/.test(x)?[x]:[];
      const names=new Map(d[1].filter(x=>x[3]?.[0]?.startsWith('B20_')).map(x=>[x[3][4],x[3][0]]));
      window.__retomadaInventory=JSON.stringify({sources:[...names].map(([id,name])=>({id,name})),videos:d[2].filter(a=>a[7]&&uuids(a[5]?.[6]).some(id=>names.has(id))).map(a=>({id:a[0],created:a[5]?.[0],prompt:a[5]?.[1],model:a[5]?.[6]?.[1]?.[0]?.[0],refs:uuids(a[5]?.[6]).filter(id=>names.has(id)),status:a[5]?.[8],seconds:a[7]?.[1]?.[2]?.[0]}))});
    });'ok'""".replace('PROJECT', PROJECT)
    js(expression)
    for _ in range(100):
        time.sleep(.2)
        raw = js('window.' + variable)
        if raw:
            result = json.loads(raw)
            assert not result.get('error'), 'Inventário indisponível.'
            return result
    raise RuntimeError('Timeout do inventário.')


def main(params):
    with open(os.environ['FLOW_LOCK'], 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        attach()
        result = prepare(params['name']) if params['action'] == 'prepare' else inventory()
        print('FLOW_RESULT=' + json.dumps(result, ensure_ascii=False))
