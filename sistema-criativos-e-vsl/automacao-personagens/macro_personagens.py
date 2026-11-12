"""Macro nativo exclusivo de personagens. Não usa referências de receitas."""
import argparse
import contextlib
import os
from pathlib import Path
import sys
import time
import json
import ctypes
from ctypes import wintypes

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(BASE / 'scripts'))
sys.path.insert(0, str(HERE))
from core import project_id
from flow_macro_windows import Macro, journal, MODEL, RADIOS
from flow_platform import locks
from mouse_motion import SmoothMouse
from recorded_motion import MotionLibrary,action_category


class CharacterMacro(Macro):
    def __init__(self, args):
        self.selected_character = None
        super().__init__(args)
        self.mouse=SmoothMouse(self.mouse,self.cursor_position,self.set_cursor_position,self.stop,
                               MotionLibrary(os.environ.get('FLOW_MOUSE_LIBRARY')))
        if self.original_url.rstrip('/') != args.project_url.rstrip('/'):
            raise RuntimeError('Abra a raiz do projeto na conta /u/N exata do plano.')

    def pause(self, seconds):
        return super().pause(min(seconds,.08))

    def stop(self,focus=True):
        flag=os.environ.get('FLOW_PAUSE_FILE')
        stop_file=os.environ.get('FLOW_STOP_FILE')
        if stop_file and Path(stop_file).exists():
            raise RuntimeError('Parada solicitada; nenhum novo clique autorizado.')
        was_paused=False
        while flag and Path(flag).exists():
            was_paused=True
            if stop_file and Path(stop_file).exists():
                raise RuntimeError('Parada solicitada durante pausa.')
            super().stop(focus=False)
            time.sleep(.05)
        if was_paused:
            self.window.set_focus()
            if self.url()!=self.original_url:
                raise RuntimeError('O projeto mudou durante a pausa; envio cancelado.')
        return super().stop(focus=focus)

    def cursor_position(self):
        point=wintypes.POINT()
        if not self.user32.GetCursorPos(ctypes.byref(point)):
            raise RuntimeError('Nao foi possivel consultar o cursor.')
        return point.x,point.y

    def set_cursor_position(self,point):
        if not self.user32.SetCursorPos(*point):
            raise RuntimeError('Nao foi possivel mover o cursor.')

    def click_stable_field(self,name,kind):
        for attempt in range(3):
            node=self.find(name,(kind,))
            try:
                self.click(node)
                return node
            except RuntimeError as error:
                if 'posição do controle mudou' not in str(error) or attempt==2:
                    raise
                self.pause(.08)

    def type_text(self,node,text):
        from pywinauto.uia_defines import IUIA
        from pywinauto.uia_element_info import UIAElementInfo
        name,kind=node.element_info.name,node.element_info.control_type
        for delay in (.003,.004):
            node=self.click_stable_field(name,kind)
            if not node.has_keyboard_focus():
                raise RuntimeError('O campo não recebeu o foco.')
            self.key('^a')
            for offset in range(0,len(text),128):
                self.stop()
                focused=UIAElementInfo(IUIA().iuia.GetFocusedElement())
                if focused.name!=name or self.url()!=self.original_url:
                    raise RuntimeError('Campo ou projeto mudou durante a digitação.')
                chunk=text[offset:offset+128]
                keys=''.join('+{ENTER}' if c=='\n' else '{'+c+'}' if c in '{}+^%~()' else c for c in chunk)
                self.keyboard.send_keys(keys,with_spaces=True,vk_packet=True,pause=delay)
            end=time.monotonic()+1.5
            while time.monotonic()<end:
                self.stop()
                if self.value(self.find(name,(kind,))).strip('\n')==text.strip('\n'):
                    return
                time.sleep(.05)
            print('Campo incompleto; repetir somente a digitação com maior intervalo.',flush=True)
        raise RuntimeError('A digitação não preservou o texto completo. Nenhum envio autorizado.')

    def configure(self):
        self.settings()
        for name in RADIOS[:3]:
            node=self.find(name,('RadioButton',))
            if not node.is_selected(): self.click(node)
        family=self.find('Selecionar família de modelos',('Button','ComboBox'))
        labels=[family.element_info.name]+[n.element_info.name for n in family.descendants()]
        if MODEL not in labels:
            self.click(family)
            self.click(self.find(MODEL,('ListItem','MenuItem','Button','RadioButton')))
        for name in RADIOS[3:]:
            node=self.find(name,('RadioButton',))
            if not node.is_selected(): self.click(node)
        self.verify_settings()
        self.close_settings()
        print('Configuração única conferida: Elementos / '+MODEL+' / 9:16 / 8s / x1 / 0 créditos.',flush=True)

    def settings(self):
        for attempt in range(3):
            if self.find('9:16',('RadioButton',),required=False):
                return
            if attempt:
                self.key('{ESC}')
            self.click(self.find('Gatilho de configurações',('Button',)))
            end=time.monotonic()+2
            while time.monotonic()<end:
                if self.find('9:16',('RadioButton',),required=False):
                    return
                self.pause(.08)
        raise RuntimeError('O painel de configuracoes nao abriu; nenhum envio autorizado.')

    def verify_settings(self):
        # Uma unica leitura da arvore confirma todos os valores do painel.
        nodes=self.nodes()
        for name in RADIOS:
            matches=[n for n in nodes if n.element_info.name==name and n.element_info.control_type=='RadioButton']
            if len(matches)!=1 or not matches[0].is_selected():
                raise RuntimeError('Configuracao divergiu: '+name)
        if not any(n.element_info.name=='0 créditos' for n in nodes):
            raise RuntimeError('O Flow nao confirmou 0 creditos. Envio cancelado.')

    def run(self):
        if self.args.inspecionar or self.args.configurar:
            return super().run()
        args=self.args
        started=time.monotonic();timings={}
        self.stop(focus=False);self.window.set_focus();self.pause(.08)
        old=self.value(self.editor()).strip('\n')
        if old.strip() and old!=args.prompt.strip('\n') and not args.substituir:
            raise RuntimeError('Já existe um prompt. Use --substituir para autorizar a troca.')
        self.configure();timings['configure_seconds']=round(time.monotonic()-started,3)
        mark=time.monotonic();self.reference(args.personagem)
        timings['reference_seconds']=round(time.monotonic()-mark,3)
        mark=time.monotonic();self.type_text(self.editor(),args.prompt)
        if self.value(self.editor()).strip('\n')!=args.prompt.strip('\n'):
            raise RuntimeError('O texto completo não confere. Nenhum clique em gerar.')
        timings['typing_seconds']=round(time.monotonic()-mark,3)
        if args.preparar:
            print('Preparado, sem enviar.',flush=True)
        else:
            generate=self.find('Iniciar geração',('Button',))
            self.click(generate)
            end=time.monotonic()+15
            while time.monotonic()<end:
                self.pause(.08)
                if self.url()!=self.original_url:
                    raise RuntimeError('A aba mudou após o clique. Não reenviar.')
                if not self.value(self.editor()).strip():
                    journal(args,'submitted_ui')
                    from core import read,atomic
                    receipt=read(args.recibo)
                    receipt['clicked_at']=self.clicked_at
                    atomic(args.recibo,receipt)
                    break
            else:
                raise RuntimeError('Clique sem confirmação em 15s. Reconciliar antes de repetir.')
        timings['total_seconds']=round(time.monotonic()-started,3)
        print('PERFORMANCE='+json.dumps(timings),flush=True)

    def reference(self, name):
        clear = self.find('Apagar comando', ('Button',), required=False)
        if clear:
            self.click(clear)
        self.click(self.find('Adicionar elementos à caixa de comando', ('Button', 'ComboBox')))
        search = self.find('Pesquisar recursos', ('Edit', 'ComboBox'))
        self.type_text(search, name)
        self.pause(.4)
        choice = self.find(name + ' Personagem', ('ListItem',), timeout=15)
        self.click(choice)
        if self.find('Pesquisar recursos', ('Edit', 'ComboBox'), required=False):
            self.click(self.find('Incluir no comando', ('Button',)))
        self.find('Imagem do elemento de personagem', ('Image',))
        self.find('Elemento', ('Button',))
        self.selected_character = name
        print('Personagem selecionado pelo macro: ' + name + ' / voz ' + self.args.voz, flush=True)

    def click(self, node):
        self.mouse.category=action_category(node.element_info.name,node.element_info.control_type)
        print('Clique nativo: '+node.element_info.name,flush=True)
        if node.element_info.name == 'Iniciar geração':
            if self.selected_character != self.args.personagem:
                raise RuntimeError('Personagem não confirmado pelo macro.')
            images = [n for n in self.nodes() if n.element_info.control_type == 'Image' and n.element_info.name == 'Imagem do elemento de personagem']
            chips = [n for n in self.nodes() if n.element_info.control_type == 'Button' and n.element_info.name == 'Elemento']
            if len(images) != 1 or len(chips) != 1 or self.url().rstrip('/') != self.args.project_url.rstrip('/'):
                raise RuntimeError('Referência de personagem ou projeto divergiu; envio cancelado.')
            return self.send_click(node)
        return super().click(node)

    def verify_send_target(self,node,point):
        hit=self.desktop.from_point(point.x,point.y)
        for _ in range(10):
            if hit is None:break
            if self.identity(hit)==self.identity(node):return
            hit=hit.parent()
        # Chrome pode devolver um Group ancestral no hit-test UIA. Nao assumir
        # que o botao esta descoberto: consultar elementFromPoint, sem clicar.
        from core import read
        from client import browser
        plan_file=os.environ.get('FLOW_PLAN_FILE')
        if not plan_file:raise RuntimeError('O controle sob o mouse mudou. Clique cancelado.')
        path=Path(plan_file);plan=read(path)
        if plan['project_url'].rstrip('/')!=self.original_url.rstrip('/'):
            raise RuntimeError('Projeto do plano divergiu; clique cancelado.')
        documents=[n for n in self.window.descendants(control_type='Document')
                   if n.is_visible() and self.value(n).rstrip('/')==self.original_url.rstrip('/')]
        if len(documents)!=1:raise RuntimeError('Viewport ambiguo; clique cancelado.')
        rect=documents[0].rectangle()
        proof=browser(plan,path.parent,'verify_send_target',document=[rect.left,rect.top,rect.right,rect.bottom],
                      point=[point.x,point.y],prompt=self.args.prompt)
        if proof.get('verified') is not True:
            print('Conferencia de alvo: '+json.dumps(proof,ensure_ascii=True),flush=True)
            raise RuntimeError('A pagina nao confirmou o botao sob o cursor. Nenhum clique enviado.')
        print('Alvo confirmado por leitura da pagina; clique permanece nativo.',flush=True)

    def send_click(self,node):
        self.stop()
        if not node.is_enabled() and os.environ.get('FLOW_WAIT_FOR_GENERATION_CAPACITY')=='1':
            print('Botao de envio indisponivel; aguardando liberacao pelo Flow, sem clicar.',flush=True)
            end=time.monotonic()+120
            while not node.is_enabled() and time.monotonic()<end:
                self.stop()
                if self.url()!=self.original_url:raise RuntimeError('A aba mudou durante a espera; nenhum clique enviado.')
                self.pause(.08)
        if self.url()!=self.original_url or not node.is_enabled():
            raise RuntimeError('Alvo indisponivel; nenhum clique enviado.')
        rect=node.rectangle();point=rect.mid_point();bounds=self.window.rectangle()
        if not (bounds.left<=point.x<bounds.right and bounds.top<=point.y<bounds.bottom):
            raise RuntimeError('Controle fora da janela.')
        self.mouse.move(coords=(point.x,point.y),safe_bounds=self.send_bounds(node))
        # O trajeto pode abrir um tooltip de midia que cobre o compositor.
        # Dispensar pela tecla normal antes de confirmar o alvo real.
        self.key('{ESC}')
        # O tooltip tem animacao de fechamento; nao clicar durante o fade.
        self.pause(.08);self.pause(.08)
        self.stop();self.verify_send_target(node,point);self.stop()
        if self.url()!=self.original_url or node.rectangle()!=rect or not node.is_enabled():
            raise RuntimeError('Alvo mudou durante a espera; nenhum clique enviado.')
        not_before=float(os.environ.get('FLOW_SEND_NOT_BEFORE','0'));waited=False
        while time.time()<not_before:
            waited=True
            self.pause(min(.02,not_before-time.time()))
        self.stop()
        if waited and (self.url()!=self.original_url or node.rectangle()!=rect or not node.is_enabled()):
            raise RuntimeError('Alvo mudou durante a espera; nenhum clique enviado.')
        journal(self.args,'click_intent')
        self.clicked_at=time.time()
        self.mouse.click(coords=(point.x,point.y))
        self.pause(.08)

    def send_bounds(self,node):
        target=node.rectangle().mid_point();editor=self.editor();anchor=editor.rectangle().mid_point()
        window=self.window.rectangle();parent=editor.parent()
        for _ in range(6):
            if parent is None:break
            rect=parent.rectangle()
            contains=lambda p:rect.left<=p.x<rect.right and rect.top<=p.y<rect.bottom
            if (contains(target) and contains(anchor)
                    and rect.width()<window.width()*.85 and rect.height()<window.height()*.85):
                margin=min(24,target.x-rect.left-2,rect.right-target.x-2,
                           target.y-rect.top-2,rect.bottom-target.y-2)
                if margin>=4:
                    return (rect.left+margin,rect.top+margin,rect.right-margin,rect.bottom-margin)
            parent=parent.parent()
        raise RuntimeError('Nao foi possivel delimitar o compositor; nenhum clique enviado.')


def options(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-url', required=True)
    parser.add_argument('--personagem')
    parser.add_argument('--voz')
    parser.add_argument('--arquivo', type=Path)
    parser.add_argument('--recibo', type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--preparar', action='store_true')
    modes.add_argument('--configurar', action='store_true')
    modes.add_argument('--inspecionar', action='store_true')
    parser.add_argument('--substituir', action='store_true')
    args = parser.parse_args(argv)
    args.projeto = project_id(args.project_url)
    args.prompt = args.arquivo.read_text(encoding='utf-8').replace('\r\n', '\n').replace('\r', '\n') if args.arquivo else None
    args.elemento = args.personagem
    args.atualizar, args.copiar, args.keystrokes = False, False, True
    if not (args.configurar or args.inspecionar):
        if not args.personagem or not args.voz or not args.prompt or not args.prompt.strip() or not args.recibo:
            parser.error('Informe --personagem, --voz, --arquivo e --recibo.')
        if any((ord(c) < 32 and c != '\n') or ord(c) == 127 for c in args.prompt):
            parser.error('Prompt contém controles ou tabulações.')
    return args


def main(argv=None):
    args = options(argv)
    if sys.platform != 'win32':
        raise RuntimeError('Este macro é específico do Windows.')
    with contextlib.ExitStack() as stack:
        filenames = [Path(os.environ.get('FLOW_LOCK', BASE / '.flow_lane.lock'))]
        if os.environ.get('FLOW_CONTROLLER_CHILD') != '1':
            filenames.insert(0, BASE / '.flow_controller.lock')
        for filename in filenames:
            handle = stack.enter_context(filename.open('a'))
            try:
                locks.flock(handle, locks.LOCK_EX | locks.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError('Outra automação usa o navegador. Receitas e personagens não operam juntos.') from None
        journal(args, 'preparing')
        CharacterMacro(args).run()
        if args.preparar or args.configurar:
            journal(args, 'prepared_without_click')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print('ERRO:', str(error), file=sys.stderr, flush=True)
        sys.exit(2)
