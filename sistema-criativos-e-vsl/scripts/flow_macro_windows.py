"""Macro Flow for Windows: UI Automation reads; real mouse/keyboard submit once."""
import argparse
import contextlib
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import sys
import time
from urllib.parse import urlparse

from flow_platform import BASE, locks

MODEL = 'Veo 3.1 - Lite [Lower Priority]'
RADIOS = ('Vídeo', 'Elementos', '9:16', '8s', 'x1')


def options(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument('--prompt')
    inputs.add_argument('--arquivo', type=Path)
    modes = parser.add_mutually_exclusive_group()
    for name in ('preparar', 'configurar', 'inspecionar', 'compilar'):
        modes.add_argument('--' + name, action='store_true')
    for name in ('substituir', 'atualizar'):
        parser.add_argument('--' + name, action='store_true')
    typing = parser.add_mutually_exclusive_group()
    typing.add_argument('--keystrokes', action='store_true')
    typing.add_argument('--copiar', action='store_true')
    parser.add_argument('--projeto')
    parser.add_argument('--elemento')
    parser.add_argument('--recibo', type=Path)
    args = parser.parse_args(argv)
    if args.arquivo:
        args.prompt = args.arquivo.read_text(encoding='utf-8')
    args.prompt = args.prompt.replace('\r\n', '\n').replace('\r', '\n') if args.prompt else None
    if args.elemento and (Path(args.elemento).name != args.elemento or any(c in args.elemento for c in '/\\') or any(ord(c) < 32 for c in args.elemento)):
        parser.error('--elemento deve ser somente o nome do arquivo já enviado.')
    if args.inspecionar or args.configurar or args.compilar:
        if args.prompt is not None or args.elemento:
            parser.error('Este modo não aceita prompt ou elemento.')
    elif not args.prompt or not args.prompt.strip():
        parser.error('Informe --prompt ou --arquivo.')
    if args.prompt and any((ord(c) < 32 and c != '\n') or ord(c) == 127 for c in args.prompt):
        parser.error('Prompt contém controles ou tabulações.')
    return args


def journal(args, phase):
    if args.recibo:
        temporary = args.recibo.with_suffix('.tmp')
        with temporary.open('w', encoding='utf-8') as stream:
            json.dump({'phase': phase, 'pid': os.getpid(), 'at': time.time()}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, args.recibo)


def valid_url(value, project=None):
    parsed = urlparse(value)
    parts = parsed.path.strip('/').split('/')
    if parsed.scheme != 'https' or parsed.hostname != 'flow.google.com' or 'project' not in parts:
        return False
    index = parts.index('project') + 1
    return index < len(parts) and bool(parts[index]) and (not project or parts[index] == project)


class Macro:
    def __init__(self, args):
        from pywinauto import Desktop, keyboard, mouse
        import psutil
        self.desktop = Desktop(backend='uia')
        self.keyboard, self.mouse, self.args = keyboard, mouse, args
        self.user32 = ctypes.windll.user32
        self.user32.OpenInputDesktop.restype = wintypes.HANDLE
        self.user32.CloseDesktop.argtypes = [wintypes.HANDLE]
        foreground = self.user32.GetForegroundWindow()
        candidates = []
        for window in self.desktop.windows(class_name='Chrome_WidgetWin_1', visible_only=True):
            try:
                if psutil.Process(window.process_id()).name().lower() != 'chrome.exe':
                    continue
                url = self.url(window)
                if valid_url(url, args.projeto):
                    candidates.append((window, url))
            except (psutil.Error, RuntimeError):
                continue
        active = [candidate for candidate in candidates if candidate[0].handle == foreground]
        if len(active) == 1:
            candidates = active
        if len(candidates) != 1:
            raise RuntimeError('Abra o projeto na aba ativa de uma única janela do Chrome. Se os controles não aparecerem, ative chrome://accessibility/ (Native accessibility API support).')
        self.window, self.original_url = candidates[0]

    @staticmethod
    def value(node):
        try:
            return node.iface_value.CurrentValue or ''
        except Exception:
            try:
                value = node.legacy_properties().get('Value', '')
                if value:
                    return value
            except Exception:
                pass
            try:
                return node.iface_text.DocumentRange.GetText(-1) or ''
            except Exception:
                return ''

    def url(self, window=None):
        documents = (window if window is not None else self.window).descendants(control_type='Document')
        urls = {self.value(node) for node in documents if node.is_visible() and valid_url(self.value(node))}
        if len(urls) != 1:
            raise RuntimeError('Não foi possível confirmar a URL do documento ativo pela acessibilidade.')
        return urls.pop()

    def stop(self, focus=True):
        desktop = self.user32.OpenInputDesktop(0, False, 0x0100)
        if not desktop:
            raise RuntimeError('Sessão do Windows bloqueada. Nenhum novo envio autorizado.')
        self.user32.CloseDesktop(desktop)
        if self.user32.GetAsyncKeyState(0x1B) & 0x8000:
            raise RuntimeError('Interrompido por Esc.')
        point = wintypes.POINT()
        self.user32.GetCursorPos(ctypes.byref(point))
        if 0 <= point.x < 5 and 0 <= point.y < 5:
            raise RuntimeError('Interrompido: mouse no canto superior esquerdo.')
        if focus and self.user32.GetForegroundWindow() != self.window.handle:
            raise RuntimeError('O Chrome perdeu o foco. Macro interrompido.')

    def pause(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.stop()
            time.sleep(.025)

    def nodes(self):
        return [node for node in self.window.descendants() if node.is_visible()]

    def guard_activity(self, nodes=None):
        names = (node.element_info.name for node in (self.nodes() if nodes is None else nodes))
        if any('notamos uma atividade incomum' in name.lower() for name in names):
            raise RuntimeError('Flow: Notamos uma atividade incomum. Novos envios interrompidos.')

    def dismiss_product_notice(self, nodes):
        names = {node.element_info.name for node in nodes}
        # This exact non-binding release-notes dialog was observed blocking the
        # recipe editor. Do not generalize to agreements or other confirmations.
        if not {'O que há de novo', 'Ver todos os registros de alterações', 'Começar'} <= names:
            return False
        if any(word in name.lower() for name in names for word in ('concordo', 'aceito', 'terms of service', 'termos de serviço', 'termos de uso')):
            raise RuntimeError('Aviso contém possível acordo; intervenção humana necessária.')
        buttons = [node for node in nodes if node.element_info.name == 'Começar'
                   and node.element_info.control_type == 'Button']
        if len(buttons) != 1:
            raise RuntimeError('Botão do aviso de novidades ambíguo; nenhum clique.')
        count = getattr(self, 'product_notice_dismissals', 0)
        if count >= 3:
            raise RuntimeError('Aviso de novidades não fechou após três cliques limitados.')
        self.click(buttons[0])
        self.product_notice_dismissals = count + 1
        self.pause(.5)
        print('Aviso de novidades fechado pelo botão Começar.', flush=True)
        return True

    def find(self, name, types=None, required=True, timeout=5):
        end = time.monotonic() + (timeout if required else 0)
        while True:
            self.stop()
            nodes = self.nodes()
            self.guard_activity(nodes)
            found = [n for n in nodes if n.element_info.name == name and (not types or n.element_info.control_type in types)]
            if len(found) > 1:
                raise RuntimeError('Controle ambíguo: ' + name)
            if found:
                return found[0]
            if name != 'Começar' and self.dismiss_product_notice(nodes):
                end = max(end, time.monotonic() + 1)
                continue
            if time.monotonic() >= end:
                if required:
                    raise RuntimeError('Controle não encontrado: ' + name + '. A interface pode ter mudado.')
                return None
            self.pause(.15)

    @staticmethod
    def identity(node):
        return tuple(node.element_info.runtime_id)

    def click(self, node):
        self.stop()
        if self.url() != self.original_url or not node.is_enabled():
            raise RuntimeError('A aba mudou ou o controle está indisponível; clique cancelado.')
        rect = node.rectangle()
        x, y = rect.mid_point().x, rect.mid_point().y
        bounds = self.window.rectangle()
        if not (bounds.left <= x < bounds.right and bounds.top <= y < bounds.bottom):
            raise RuntimeError('Controle fora da janela.')
        self.mouse.move(coords=(x, y))
        end = time.monotonic() + 2.5
        while True:
            hit = self.desktop.from_point(x, y)
            for _ in range(10):
                if self.identity(hit) == self.identity(node):
                    break
                hit = hit.parent()
                if hit is None:
                    break
            if hit is not None and self.identity(hit) == self.identity(node):
                break
            if time.monotonic() > end:
                raise RuntimeError('O controle sob o mouse mudou. Clique cancelado.')
            self.pause(.15)
        self.stop()
        if self.url() != self.original_url or node.rectangle() != rect:
            raise RuntimeError('A aba ou a posição do controle mudou; clique cancelado.')
        self.mouse.click(coords=(x, y))
        self.pause(.25)

    def key(self, keys):
        self.stop()
        self.keyboard.send_keys(keys, pause=.02)
        self.pause(.12)

    def type_text(self, node, text):
        self.click(node)
        if not node.has_keyboard_focus():
            raise RuntimeError('O campo não recebeu o foco; digitação cancelada.')
        self.key('^a')
        for index, character in enumerate(text):
            self.stop()
            if index % 16 == 0:
                # React may replace the node; consult the focused UIA element directly.
                from pywinauto.uia_defines import IUIA
                from pywinauto.uia_element_info import UIAElementInfo
                focused = UIAElementInfo(IUIA().iuia.GetFocusedElement())
                if focused.name != node.element_info.name or self.url() != self.original_url:
                    raise RuntimeError('O campo perdeu o foco. Digitação interrompida.')
            if character == '\n':
                self.keyboard.send_keys('+{ENTER}', pause=.002)
            else:
                escaped = '{' + character + '}' if character in '{}+^%~()' else character
                self.keyboard.send_keys(escaped, with_spaces=True, vk_packet=True, pause=.002)
        self.pause(.3)

    def editor(self):
        return self.find('O que você quer criar?', ('Edit',))

    def settings(self):
        if not self.find('9:16', ('RadioButton',), required=False):
            self.click(self.find('Gatilho de configurações', ('Button',)))
        self.find('9:16', ('RadioButton',))

    def verify_settings(self):
        for name in RADIOS:
            if not self.find(name, ('RadioButton',)).is_selected():
                raise RuntimeError('Configuração divergiu: ' + name)
        if not any(n.element_info.name == '0 créditos' for n in self.nodes()):
            raise RuntimeError('O Flow não confirmou 0 créditos. Envio cancelado.')

    def close_settings(self):
        # A native Escape dismisses the popover without clicking through its backdrop.
        self.key('{ESC}')
        if self.find('9:16', ('RadioButton',), required=False):
            raise RuntimeError('O painel de configurações não fechou.')

    def configure(self):
        self.settings()
        for name in RADIOS[:3]:
            node = self.find(name, ('RadioButton',))
            if not node.is_selected():
                self.click(node)
        self.click(self.find('Selecionar família de modelos', ('Button', 'ComboBox')))
        # Restrict to actionable nodes so the duplicate text child is not ambiguous.
        self.click(self.find(MODEL, ('ListItem', 'MenuItem', 'Button', 'RadioButton')))
        for name in RADIOS[3:]:
            node = self.find(name, ('RadioButton',))
            if not node.is_selected():
                self.click(node)
        self.verify_settings()
        self.close_settings()
        print('Configurações conferidas: Vídeo / Elementos / ' + MODEL + ' / 9:16 / 8s / x1 / 0 créditos.', flush=True)

    def reference(self, name):
        clear = self.find('Apagar comando', ('Button',), required=False)
        if clear:
            self.click(clear)
        self.click(self.find('Adicionar elementos à caixa de comando', ('Button', 'ComboBox')))
        self.type_text(self.find('Pesquisar recursos', ('Edit', 'ComboBox')), name)
        self.pause(.4)
        choice = self.find(name + ' Imagem', ('ListItem',), required=False)
        if choice is None:
            choice = self.find(name, ('Text',), timeout=12)
        self.click(choice)
        if self.find('Pesquisar recursos', ('Edit', 'ComboBox'), required=False):
            self.find('Prévia de ' + name, ('Image',))
            self.click(self.find('Incluir no comando', ('Button',)))
        self.find('Elemento', ('Button',))

    def run(self):
        args = self.args
        if args.inspecionar:
            for node in self.nodes():
                if node.element_info.control_type in ('Button', 'RadioButton', 'Edit', 'ComboBox'):
                    print(node.element_info.control_type, node.element_info.name)
            return
        self.stop(focus=False)
        self.window.set_focus()
        self.pause(.3)
        if args.prompt:
            old = self.value(self.editor()).strip('\n')
            if old.strip() and old != args.prompt.strip('\n') and not args.substituir:
                raise RuntimeError('Já existe um prompt. Use --substituir para autorizar a troca.')
        if args.atualizar:
            self.key('^r')
            self.pause(1)
            self.find('Gatilho de configurações', ('Button',), timeout=30)
        self.configure()
        if args.configurar:
            return
        if args.elemento:
            self.reference(args.elemento)
        if args.copiar:
            import win32clipboard
            self.click(self.editor())
            win32clipboard.OpenClipboard()
            try:
                previous = win32clipboard.GetClipboardData(13) if win32clipboard.IsClipboardFormatAvailable(13) else None
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(args.prompt, 13)
            finally:
                win32clipboard.CloseClipboard()
            try:
                self.key('^a')
                self.key('^v')
                self.pause(.3)
            finally:
                win32clipboard.OpenClipboard()
                try:
                    win32clipboard.EmptyClipboard()
                    if previous is not None:
                        win32clipboard.SetClipboardText(previous, 13)
                finally:
                    win32clipboard.CloseClipboard()
        else:
            self.type_text(self.editor(), args.prompt)
        if self.value(self.editor()).strip('\n') != args.prompt.strip('\n'):
            raise RuntimeError('O texto digitado não confere. Nenhum clique em gerar.')
        self.settings()
        self.verify_settings()
        self.close_settings()
        if args.preparar:
            print('Preparado, sem enviar. O botão Iniciar geração não foi clicado.')
            return
        if self.value(self.editor()).strip('\n') != args.prompt.strip('\n'):
            raise RuntimeError('O prompt mudou antes do envio.')
        generate = self.find('Iniciar geração', ('Button',))
        journal(args, 'click_intent')
        print('Clicando uma única vez em Iniciar geração…', flush=True)
        self.click(generate)
        end = time.monotonic() + 15
        cleared_at = None
        while time.monotonic() < end:
            self.pause(.4)
            self.guard_activity()
            if self.url() != self.original_url:
                raise RuntimeError('A aba mudou após o clique. O envio não será repetido.')
            if not self.value(self.editor()).strip():
                if cleared_at is None:
                    journal(args, 'submitted_ui')
                    cleared_at = time.monotonic()
                if time.monotonic() - cleared_at >= 3:
                    return
        raise RuntimeError('Clique efetuado uma vez, sem confirmação em 15s. Não reenviar sem conferir o recibo.')


def main(argv=None):
    args = options(argv)
    if sys.platform != 'win32':
        raise RuntimeError('Use o flow-macro original no macOS.')
    if args.compilar:
        import pywinauto
        import psutil
        print('Macro Windows e dependências disponíveis; não requer compilação Swift.')
        return 0
    with contextlib.ExitStack() as stack:
        filenames = [Path(os.environ.get('FLOW_LOCK', BASE / '.flow_lane.lock'))]
        if os.environ.get('FLOW_CONTROLLER_CHILD') != '1':
            filenames.insert(0, BASE / '.flow_controller.lock')
        for filename in filenames:
            handle = stack.enter_context(filename.open('a'))
            try:
                locks.flock(handle, locks.LOCK_EX | locks.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError('Outra automação está usando o Flow. Aguarde terminar.') from None
        journal(args, 'preparing')
        Macro(args).run()
        if args.preparar or args.configurar:
            journal(args, 'prepared_without_click')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print('ERRO:', str(error), file=sys.stderr, flush=True)
        sys.exit(2)
