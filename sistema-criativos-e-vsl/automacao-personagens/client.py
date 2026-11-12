import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(BASE / 'scripts'))
from flow_platform import process_options


def browser(plan, root, action, **params):
    code = ('import runpy\nm=runpy.run_path(' + repr(str(HERE / 'browser_worker.py')) + ',init_globals=globals())\n'
            'm["main"](' + repr({'plan': plan, 'root': str(root), 'action': action, **params}) + ')\n')
    result = subprocess.run(['browser-harness'], input=code, capture_output=True, text=True, encoding='utf-8',
                            cwd=BASE, timeout=180, **process_options())
    if result.returncode:
        raise RuntimeError(result.stderr[-1800:] or 'Operação do navegador falhou.')
    for line in result.stdout.splitlines():
        if line.startswith('CHARACTER_RESULT='):
            return json.loads(line[len('CHARACTER_RESULT='):])
    raise RuntimeError('Operação sem recibo JSON. Não repetir upload/envio sem reconciliar.')
