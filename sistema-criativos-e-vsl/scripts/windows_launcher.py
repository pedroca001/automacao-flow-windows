"""Windows entry points, including the small native macro prompt window."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import threading

from flow_platform import BASE, native_command


def verify():
    import importlib.util
    missing = []
    for name in ('PIL', 'pywinauto', 'psutil', 'edge_tts'):
        found = importlib.util.find_spec(name) is not None
        print(('OK   ' if found else 'FALTA') + ' Python: ' + name)
        if not found:
            missing.append(name)
    for name in ('ffmpeg', 'ffprobe', 'browser-harness', 'whisper-cli'):
        found = shutil.which(name)
        print(('OK   ' if found else 'FALTA') + ' ' + name + ': ' + (found or 'não instalado'))
        if not found:
            missing.append(name)
    import os
    model = Path(os.environ.get('WHISPER_MODEL', ''))
    if not model.is_file():
        missing.append('WHISPER_MODEL')
    print(('OK   ' if model.is_file() else 'FALTA') + ' modelo Whisper: ' + str(model))
    for path in (BASE / 'SKILLS').glob('*/SKILL.md'):
        installed = BASE / '.claude/skills' / path.parent.name / 'SKILL.md'
        if not installed.is_file() or installed.read_bytes() != path.read_bytes():
            missing.append(str(installed))
    result = subprocess.run(['ffmpeg', '-hide_banner', '-filters'], capture_output=True, text=True)
    if ' ass ' not in result.stdout:
        missing.append('FFmpeg/libass')
    print('OK   FFmpeg/libass' if ' ass ' in result.stdout else 'FALTA FFmpeg/libass')
    print('Pacote conferido.' if not missing else 'Pendências: ' + ', '.join(missing))
    return bool(missing)


def prepare():
    import tkinter as tk
    from tkinter import filedialog, simpledialog
    window = tk.Tk()
    window.withdraw()
    try:
        images = filedialog.askdirectory(title='Selecione a pasta com PAR-001_hook.png e PAR-001_recipe.png')
        if not images:
            return 0
        project = simpledialog.askstring('Projeto do Flow', 'Cole o link ou UUID do projeto:', parent=window)
        if not project:
            return 0
        return subprocess.call([sys.executable, str(BASE / 'retomada-macro/noturno.py'), 'preparar', '--imagens', images, '--projeto', project], cwd=BASE)
    finally:
        window.destroy()


def macro_window():
    import tkinter as tk
    from tkinter import ttk
    window = tk.Tk()
    window.title('Macro Flow — Windows')
    window.geometry('740x520')
    ttk.Label(window, text='Abra o projeto na aba ativa do Chrome. Esc ou mouse no canto superior esquerdo interrompem.').pack(padx=16, pady=12)
    text = tk.Text(window, wrap='word', font=('Segoe UI', 11), height=13)
    text.pack(fill='both', expand=True, padx=16)
    status = tk.Text(window, wrap='word', height=6, state='disabled')
    status.pack(fill='x', padx=16, pady=8)
    buttons = []
    def append(message):
        status.configure(state='normal')
        status.insert('end', message)
        status.see('end')
        status.configure(state='disabled')
    def run(mode):
        prompt = text.get('1.0', 'end-1c')
        if mode != 'configurar' and not prompt.strip():
            append('Informe um prompt.\n')
            return
        command = native_command()
        if mode == 'configurar':
            command += ['--configurar']
        else:
            command += ['--prompt', prompt]
            if mode == 'preparar':
                command += ['--preparar']
        for button in buttons:
            button.configure(state='disabled')
        def worker():
            try:
                process = subprocess.Popen(command, cwd=BASE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8')
                for line in process.stdout:
                    window.after(0, append, line)
                process.wait()
            except Exception as error:
                window.after(0, append, str(error) + '\n')
            finally:
                def enable():
                    for button in buttons:
                        button.configure(state='normal')
                window.after(0, enable)
        threading.Thread(target=worker, daemon=True).start()
    row = ttk.Frame(window)
    row.pack(pady=10)
    for label, mode in [('Configurar', 'configurar'), ('Preparar sem enviar', 'preparar'), ('Gerar uma vez', 'gerar')]:
        button = ttk.Button(row, text=label, command=lambda value=mode: run(value))
        button.pack(side='left', padx=6)
        buttons.append(button)
    window.mainloop()
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('preparar', 'macro', 'verificar', 'conexao', 'driver', 'download', 'script'))
    args, rest = parser.parse_known_args()
    if args.action == 'preparar':
        return prepare()
    if args.action == 'macro':
        return macro_window()
    if args.action == 'verificar':
        return verify()
    if args.action == 'conexao':
        code = "print({'flow_tabs': sum('flow.google.com' in t.get('url', '') for t in list_tabs())})"
        try:
            return subprocess.run(['browser-harness'], input=code, text=True, encoding='utf-8', cwd=BASE, timeout=50).returncode
        except subprocess.TimeoutExpired:
            print('Conexão pendente. Confira no Chrome a permissão Allow remote debugging e abra o projeto do Flow.')
            return 2
    if args.action in ('driver', 'download'):
        code = (BASE / 'scripts' / ('flow_' + args.action + '.py')).read_text(encoding='utf-8')
        return subprocess.run(['browser-harness'], input=code, text=True, encoding='utf-8', cwd=BASE).returncode
    if not rest:
        parser.error('Informe o nome do script.py e seus argumentos.')
    path = BASE / 'scripts' / rest[0]
    if Path(rest[0]).name != rest[0] or not path.is_file() or path.suffix != '.py':
        parser.error('Script não encontrado no pacote.')
    return subprocess.call([sys.executable, str(path), *rest[1:]], cwd=BASE)


if __name__ == '__main__':
    sys.exit(main())
