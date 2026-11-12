"""Install local Windows tools; no browser actions, cookies or generations."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import zipfile

BASE = Path(__file__).resolve().parents[1]


def download(url, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix('.partial')
    print('Baixando:', destination.name, flush=True)
    with urllib.request.urlopen(url, timeout=90) as source, temporary.open('wb') as output:
        shutil.copyfileobj(source, output)
    os.replace(temporary, destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sem-whisper', action='store_true')
    parser.add_argument('--rvm', action='store_true', help='Instalar também Torch/CPU e remoção de fundo (download grande).')
    args = parser.parse_args()
    for path in (BASE / 'SKILLS').iterdir():
        if path.is_dir():
            shutil.copytree(path, BASE / '.claude/skills' / path.name, dirs_exist_ok=True)
    scripts = BASE / '.venv/Scripts'
    # The scripts directory is also visible to the separately installed browser-harness.
    (BASE / '.venv/Lib/site-packages/flow_local.pth').write_text(str(BASE / 'scripts') + '\n', encoding='utf-8')
    if not args.sem_whisper:
        folder = BASE / '.local-bin/whisper'
        binary = next(folder.rglob('whisper-cli.exe'), folder / 'whisper-cli.exe')
        if not binary.is_file():
            request = urllib.request.Request('https://api.github.com/repos/ggml-org/whisper.cpp/releases?per_page=20', headers={'User-Agent': 'flow-windows-installer'})
            releases = json.load(urllib.request.urlopen(request, timeout=30))
            assets = [a for r in releases if not r['draft'] and not r['prerelease'] for a in r['assets'] if a['name'] == 'whisper-bin-x64.zip']
            if not assets:
                raise RuntimeError('Release oficial do whisper.cpp sem binário Windows x64.')
            asset = assets[0]
            archive = BASE / '.local-cache/whisper-bin-x64.zip'
            download(asset['browser_download_url'], archive)
            digest = asset.get('digest')
            if digest and digest.startswith('sha256:') and hashlib.sha256(archive.read_bytes()).hexdigest() != digest.split(':', 1)[1]:
                raise RuntimeError('Hash do binário Whisper não confere.')
            folder = binary.parent
            folder.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(archive) as package:
                for item in package.infolist():
                    destination = (folder / item.filename).resolve()
                    if not destination.is_relative_to(folder.resolve()):
                        raise RuntimeError('Caminho inválido no pacote Whisper.')
                package.extractall(folder)
            executable = next(folder.rglob('whisper-cli.exe'))
            # Preserve DLLs next to the executable; the wrapper resolves nested release layouts.
            binary = executable
        wrapper = BASE / '.local-bin/whisper-cli.cmd'
        wrapper.parent.mkdir(parents=True, exist_ok=True)
        wrapper.write_text('@echo off\n"%~dp0' + str(binary.relative_to(wrapper.parent)) + '" %*\n', encoding='utf-8')
        # Popen([...]) needs an .exe on Windows, not a .cmd shim. Add the real folder to env scripts.
        (BASE / '.local-bin/whisper-path.txt').write_text(str(binary.parent), encoding='utf-8')
        model = BASE / '.local-cache/whisper/ggml-small.bin'
        if not model.is_file():
            download('https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin', model)
        if model.stat().st_size < 400_000_000:
            raise RuntimeError('Modelo Whisper incompleto.')
    if args.rvm:
        subprocess.run(['uv', 'pip', 'install', '--python', sys.executable, 'torch', 'torchvision', 'numpy', '--index-url', 'https://download.pytorch.org/whl/cpu'], check=True)
        rvm = BASE / '.local-cache/rvm'
        if not (rvm / '.git').exists():
            subprocess.run(['git', 'clone', '--depth', '1', 'https://github.com/PeterL1n/RobustVideoMatting.git', str(rvm)], check=True)
        weights = rvm / 'rvm_mobilenetv3.pth'
        if not weights.is_file():
            download('https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_mobilenetv3.pth', weights)
    print('Ferramentas locais instaladas. Nenhuma geração iniciada.')


if __name__ == '__main__':
    main()
