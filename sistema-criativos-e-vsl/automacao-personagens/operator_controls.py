"""Atalho fisico ++ e animacao visual ociosa, sem cliques ou geracoes."""
import ctypes
from ctypes import wintypes
import math
import os
from pathlib import Path
import threading
import time
from core import read,atomic
from mouse_motion import motion_points,send_motion_points
from recorded_motion import MotionLibrary


class PauseGesture:
    def __init__(self,window=.5):
        self.window=window;self.last=None;self.held=set()

    def key(self,vk,down,plus,now,injected=False):
        if injected:return False
        if not down:
            self.held.discard(vk);return False
        if not plus or vk in self.held:return False
        self.held.add(vk)
        if self.last is not None and now-self.last<=self.window:
            self.last=None;return True
        self.last=now;return False


def composer_idle_bounds(editor,container):
    """Usa apenas o campo visivel, excluindo botoes e cards da galeria."""
    left=max(editor.left,container.left)+8;right=min(editor.right,container.right)-8
    top=max(editor.top,container.top)+4;bottom=min(editor.bottom,container.bottom)-4
    return (left,top,right,bottom) if right-left>=30 and bottom-top>=12 else None


class VisualOperator:
    def __init__(self,root):
        self.root=Path(root);self.pause_file=self.root/'PAUSADO'
        self.enabled=os.name=='nt' and read(self.root/'operacao.json',{}).get('visual_controls',False)
        self.busy=threading.Event();self.busy.set()
        self.closed=threading.Event();self.ready=threading.Event();self.lock=threading.Lock()
        self.thread=None;self.animation=None;self.thread_id=None;self.window=0;self.title='';self.error=None;self.frames=0
        self.motion=MotionLibrary(os.environ.get('FLOW_MOUSE_LIBRARY'))
        self.idle_bounds=None;self.composer_bounds=None

    def start(self):
        if not self.enabled:return
        self.thread=threading.Thread(target=self._run,name='flow-visual-operator',daemon=True)
        self.thread.start()
        if not self.ready.wait(3) or self.error:
            raise RuntimeError('Atalho ++ indisponivel: '+str(self.error))

    def set_busy(self,value):
        if value:self.busy.set()
        else:self.busy.clear()
        with self.lock:pass

    def bind_foreground(self):
        if not self.enabled:return
        u=ctypes.windll.user32;u.GetForegroundWindow.restype=wintypes.HWND
        u.GetClassNameW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
        u.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
        hwnd=u.GetForegroundWindow();name=ctypes.create_unicode_buffer(256);title=ctypes.create_unicode_buffer(2048)
        u.GetClassNameW(hwnd,name,len(name));u.GetWindowTextW(hwnd,title,len(title))
        if name.value=='Chrome_WidgetWin_1' and 'flow' in title.value.lower():
            self.window,self.title=hwnd,title.value
            self.idle_bounds=None;self.composer_bounds=None
            from pywinauto import Desktop
            try:
                window=Desktop(backend='uia').window(handle=hwnd)
                editors=[node for node in window.descendants(control_type='Edit')
                         if node.is_visible() and node.element_info.name=='O que você quer criar?']
                if len(editors)==1:
                    editor=editors[0];container=editor.parent().rectangle()
                    self.idle_bounds=composer_idle_bounds(editor.rectangle(),container)
                    self.composer_bounds=(container.left+4,container.top+4,container.right-4,container.bottom-4)
            except Exception:
                # Sem area reconhecida, apenas a animacao fica parada.
                self.idle_bounds=None;self.composer_bounds=None

    def wait_if_paused(self,should_stop):
        if self.error:raise RuntimeError('Controles do operador interrompidos: '+self.error)
        while self.enabled and self.pause_file.exists() and not should_stop():
            if self.error:raise RuntimeError('Controles do operador interrompidos: '+self.error)
            time.sleep(.05)

    def close(self):
        self.closed.set();self.busy.set()
        if self.enabled and self.thread_id:
            ctypes.windll.user32.PostThreadMessageW(self.thread_id,0x12,0,0)
        if self.thread:self.thread.join(timeout=3)
        if self.animation:self.animation.join(timeout=3)

    def _status(self,hook):
        atomic(self.root/'operador.json',{'hook_installed':bool(hook),'paused':self.pause_file.exists(),
            'idle_animation_frames':self.frames,'bound_flow_window':bool(self.window),'updated_at':time.time(),
            'idle_area':'composer_only','idle_bounds':self.idle_bounds,
            'shortcut':'Duas teclas + fisicas em ate 500 ms; repetir para retomar.'})

    def _run(self):
        u=ctypes.windll.user32;k=ctypes.windll.kernel32
        CALLBACK=ctypes.WINFUNCTYPE(ctypes.c_ssize_t,ctypes.c_int,wintypes.WPARAM,wintypes.LPARAM)
        class KEY(ctypes.Structure):
            _fields_=[('vkCode',wintypes.DWORD),('scanCode',wintypes.DWORD),('flags',wintypes.DWORD),('time',wintypes.DWORD),('extra',ctypes.c_size_t)]
        u.SetWindowsHookExW.argtypes=[ctypes.c_int,CALLBACK,wintypes.HINSTANCE,wintypes.DWORD]
        u.SetWindowsHookExW.restype=wintypes.HANDLE
        u.CallNextHookEx.argtypes=[wintypes.HANDLE,ctypes.c_int,wintypes.WPARAM,wintypes.LPARAM]
        u.CallNextHookEx.restype=ctypes.c_ssize_t
        u.UnhookWindowsHookEx.argtypes=[wintypes.HANDLE]
        u.GetForegroundWindow.restype=wintypes.HWND
        u.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
        u.GetClientRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)]
        u.ClientToScreen.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.POINT)]
        k.GetModuleHandleW.argtypes=[wintypes.LPCWSTR];k.GetModuleHandleW.restype=wintypes.HMODULE
        gesture=PauseGesture();hook=None
        def on_key(code,wparam,lparam):
            if code>=0:
                key=ctypes.cast(lparam,ctypes.POINTER(KEY)).contents
                down=wparam in (0x100,0x104);up=wparam in (0x101,0x105)
                plus=key.vkCode==0x6B or (key.vkCode==0xBB and bool(u.GetAsyncKeyState(0x10)&0x8000))
                held=key.vkCode in gesture.held
                if (down or up) and gesture.key(key.vkCode,down,plus,time.monotonic(),bool(key.flags&0x10)):
                    if self.pause_file.exists():self.pause_file.unlink()
                    else:self.pause_file.write_text('Pausa por ++. Pressione ++ novamente para retomar.\n',encoding='utf-8')
                    self._status(hook)
                # No Flow, o atalho nao insere sinais + no prompt.
                if not key.flags&0x10 and (plus or held) and self.window and u.GetForegroundWindow()==self.window:
                    return 1
            return u.CallNextHookEx(hook,code,wparam,lparam)
        callback=CALLBACK(on_key)
        try:
            hook=u.SetWindowsHookExW(13,callback,k.GetModuleHandleW(None),0)
            if not hook:raise OSError('SetWindowsHookExW falhou: '+str(k.GetLastError()))
            self.thread_id=k.GetCurrentThreadId()
            message=wintypes.MSG()
            u.PeekMessageW(ctypes.byref(message),None,0,0,0)
            self._status(hook)
            self.animation=threading.Thread(target=self._animate,args=(hook,),name='flow-idle-motion',daemon=True)
            self.animation.start();self.ready.set()
            # GetMessage acorda imediatamente para cada tecla; nao compartilhar
            # o intervalo dos frames da animacao com o hook de teclado.
            while not self.closed.is_set() and u.GetMessageW(ctypes.byref(message),None,0,0)>0:
                u.TranslateMessage(ctypes.byref(message));u.DispatchMessageW(ctypes.byref(message))
        except Exception as error:
            self.error=str(error);self.ready.set()
        finally:
            self.closed.set()
            if hook:u.UnhookWindowsHookEx(hook)
            self._status(False)

    def _animate(self,hook):
        u=ctypes.windll.user32;last_status=time.monotonic();active=False;entry=[];phase=0.0;recorded=[];replay_start=None
        try:
            while not self.closed.is_set():
                title=ctypes.create_unicode_buffer(2048)
                if self.window:u.GetWindowTextW(self.window,title,len(title))
                allowed=(not self.busy.is_set() and not self.pause_file.exists() and self.window
                         and self.idle_bounds is not None and u.GetForegroundWindow()==self.window and title.value==self.title)
                if allowed:
                    left,top,right,bottom=self.idle_bounds
                    cx=(left+right)/2;cy=(top+bottom)/2
                    rx=(right-left)*.4;ry=(bottom-top)*.4
                    if not active:
                        pos=wintypes.POINT();u.GetCursorPos(ctypes.byref(pos))
                        path=self.motion.idle(self.idle_bounds)
                        recorded=[];elapsed=0
                        for point,dt in path or []:
                            elapsed+=dt;recorded.append((elapsed,point))
                        target=recorded[0][1] if recorded else (round(cx),round(cy))
                        entry=[p for p,dt in send_motion_points((pos.x,pos.y),target,self.composer_bounds)];phase=0;replay_start=None
                    with self.lock:
                        if not self.busy.is_set() and not self.pause_file.exists():
                            if entry:point=entry.pop(0)
                            elif recorded:
                                if replay_start is None:replay_start=time.monotonic()
                                elapsed=time.monotonic()-replay_start
                                point=recorded[0][1]
                                while recorded and recorded[0][0]<=elapsed:
                                    _,point=recorded.pop(0)
                            else:
                                if replay_start is not None:
                                    active=False
                                    continue
                                phase+=.018
                                point=(round(cx+rx*math.sin(phase)*math.cos(phase*.23)),round(cy+ry*math.sin(phase*1.7)))
                            u.SetCursorPos(*point);self.frames+=1
                    active=True
                else:active=False
                if time.monotonic()-last_status>=3:
                    self._status(hook);last_status=time.monotonic()
                self.closed.wait(.016)
        except Exception as error:
            self.error=str(error);self.closed.set()
            u.PostThreadMessageW(self.thread_id,0x12,0,0)
