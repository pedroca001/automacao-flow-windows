"""Refresh only the two recorded tabs of the authorized project; no generation."""
import json
from pathlib import Path
import time

root = Path(FLOW_RUN_DIR).resolve()
config = json.loads((root / 'config-lote.json').read_text(encoding='utf-8'))
project_url = config['project_url'].rstrip('/')
expected_email = config['expected_email']
assert expected_email, 'Configure the expected Flow account email.'
windows = json.loads((root / 'janelas.json').read_text(encoding='utf-8'))
tabs = {t['targetId']: t for t in list_tabs()}
targets = [windows['background'], windows['foreground']]
assert len(set(targets)) == 2
for target in targets:
    assert tabs[target]['url'].split('?')[0] == project_url, 'Recorded tab/account/project changed.'
refreshed = []
for target in targets:
    sid = cdp('Target.attachToTarget', targetId=target, flatten=True)['sessionId']
    try:
        cdp('Page.reload', session_id=sid)
        deadline = time.monotonic() + 35
        while time.monotonic() < deadline:
            result = cdp('Runtime.evaluate', session_id=sid, expression="({ready:document.readyState==='complete'&&!!window.WIZ_global_data?.SNlM0e,url:location.href})", returnByValue=True)['result'].get('value') or {}
            assert result.get('url', project_url).split('?')[0] == project_url, 'Login or project navigation requires review.'
            if result.get('ready'):
                if target == windows['foreground']:
                    nodes = cdp('Accessibility.getFullAXTree', session_id=sid)['nodes']
                    names = [n.get('name', {}).get('value', '') for n in nodes]
                    if any(n.startswith('Conta do Google:') for n in names):
                        break
                else:
                    break
            time.sleep(.5)
        else:
            raise RuntimeError('Project tab did not finish reloading.')
        refreshed.append(target)
    finally:
        cdp('Target.detachFromTarget', sessionId=sid)
messages = [n for n in names if 'notamos uma atividade incomum' in n.lower()]
manual = [n for n in names if any(k in n.lower() for k in ('sign in to continue', 'faça login para continuar', 'confirme que você é humano', 'verifique se você é humano', 'verify you are human', 'não sou um robô'))]
accounts = [n for n in names if n.startswith('Conta do Google:')]
assert accounts and all(expected_email in n for n in accounts), 'Flow account identity requires review.'
cdp('Target.activateTarget', targetId=windows['foreground'])
result = {'at': time.time(), 'outcome': 'manual' if manual else 'cooldown_again' if messages else 'clear',
          'refreshed': refreshed, 'project_url': project_url,
          'messages': manual or messages, 'generation_sent': False}
path = root / ('REFRESH-RETOMADA-' + str(int(result['at'])) + '.json')
path.write_text(json.dumps(result, ensure_ascii=True, indent=2), encoding='utf-8')
print('REFRESH_RESULT=' + json.dumps(result))
