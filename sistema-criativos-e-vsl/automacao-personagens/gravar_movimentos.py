"""Gravador interativo: F8, cinco segundos de preparo, dez de captura."""
import argparse
import ctypes
from ctypes import wintypes
import math
import os
from pathlib import Path
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk,messagebox
from types import SimpleNamespace
from urllib.parse import urlparse
import sys

HERE=Path(__file__).resolve().parent;BASE=HERE.parent
sys.path.insert(0,str(BASE/'scripts'))
from core import read,project_id,atomic
from cli import locate
from controller import controller_lock
from flow_macro_windows import Macro
from recorded_motion import MotionLibrary,CATEGORIES,idle_path

LABELS={'geral':'Geral','configuracao':'Configuração','texto':'Texto','enviar':'Enviar','espera':'Espera / dança'}


def recorder_url_matches(actual,expected):
    current,wanted=urlparse(actual),urlparse(expected)
    base=wanted.path.rstrip('/')
    return (current.scheme=='https' and current.hostname=='flow.google.com'
            and current.netloc==wanted.netloc and
            (current.path.rstrip('/')==base or current.path.startswith(base+'/')))


class ClickMarkers:
    """Captura marcadores fisicos; no ensaio, impede o clique no Flow."""
    def __init__(self):
        self.active=False;self.block=True;self.window=0;self.started=0
        self.events=queue.Queue();self.ready=threading.Event();self.closed=threading.Event();self.thread_id=None;self.error=None
        self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start()
        if not self.ready.wait(3) or self.error:raise RuntimeError('Captura de cliques indisponível: '+str(self.error))

    def close(self):
        self.active=False;self.closed.set()
        if self.thread_id:ctypes.windll.user32.PostThreadMessageW(self.thread_id,0x12,0,0)
        self.thread.join(timeout=3)

    def run(self):
        u=ctypes.windll.user32;k=ctypes.windll.kernel32
        CALLBACK=ctypes.WINFUNCTYPE(ctypes.c_ssize_t,ctypes.c_int,wintypes.WPARAM,wintypes.LPARAM)
        class MOUSE(ctypes.Structure):
            _fields_=[('pt',wintypes.POINT),('mouseData',wintypes.DWORD),('flags',wintypes.DWORD),('time',wintypes.DWORD),('extra',ctypes.c_size_t)]
        u.SetWindowsHookExW.argtypes=[ctypes.c_int,CALLBACK,wintypes.HINSTANCE,wintypes.DWORD];u.SetWindowsHookExW.restype=wintypes.HANDLE
        u.CallNextHookEx.argtypes=[wintypes.HANDLE,ctypes.c_int,wintypes.WPARAM,wintypes.LPARAM];u.CallNextHookEx.restype=ctypes.c_ssize_t
        u.UnhookWindowsHookEx.argtypes=[wintypes.HANDLE];u.GetForegroundWindow.restype=wintypes.HWND
        u.WindowFromPoint.argtypes=[wintypes.POINT];u.WindowFromPoint.restype=wintypes.HWND
        u.GetAncestor.argtypes=[wintypes.HWND,wintypes.UINT];u.GetAncestor.restype=wintypes.HWND
        k.GetModuleHandleW.argtypes=[wintypes.LPCWSTR];k.GetModuleHandleW.restype=wintypes.HMODULE
        hook=None;blocked_down=False
        def on_mouse(code,message,data):
            nonlocal blocked_down
            if code>=0:
                event=ctypes.cast(data,ctypes.POINTER(MOUSE)).contents
                if not event.flags&1:
                    if message==0x202 and blocked_down:
                        blocked_down=False;return 1
                    if (self.active and self.window and u.GetForegroundWindow()==self.window and message==0x201
                            and u.GetAncestor(u.WindowFromPoint(event.pt),2)==self.window):
                        self.events.put({'t':time.monotonic()-self.started,'x':event.pt.x,'y':event.pt.y})
                        if self.block:blocked_down=True;return 1
            return u.CallNextHookEx(hook,code,message,data)
        callback=CALLBACK(on_mouse)
        try:
            hook=u.SetWindowsHookExW(14,callback,k.GetModuleHandleW(None),0)
            if not hook:raise OSError('Não foi possível instalar o gravador de cliques.')
            self.thread_id=k.GetCurrentThreadId();msg=wintypes.MSG();u.PeekMessageW(ctypes.byref(msg),None,0,0,0);self.ready.set()
            while not self.closed.is_set() and u.GetMessageW(ctypes.byref(msg),None,0,0)>0:
                u.TranslateMessage(ctypes.byref(msg));u.DispatchMessageW(ctypes.byref(msg))
        except Exception as error:self.error=str(error);self.ready.set()
        finally:
            if hook:u.UnhookWindowsHookEx(hook)


class Recorder:
    def __init__(self,window,plan,library):
        self.ui=window;self.plan=plan;self.library=library;self.markers=ClickMarkers()
        self.state='ready';self.points=[];self.clicks=[];self.f8=False;self.escape=False;self.flow=None
        self.ui.title('Seu movimento • Flow');self.ui.geometry('460x520+25+110');self.ui.attributes('-topmost',True)
        self.ui.configure(bg='#111827');self.ui.protocol('WM_DELETE_WINDOW',self.close)
        style=ttk.Style();style.theme_use('clam')
        style.configure('TFrame',background='#111827');style.configure('TLabel',background='#111827',foreground='#e5e7eb',font=('Segoe UI',10))
        style.configure('TButton',font=('Segoe UI',10),padding=7)
        style.configure('TCheckbutton',background='#111827',foreground='#cbd5e1',font=('Segoe UI',9))
        style.configure('Horizontal.TProgressbar',background='#34d399',troughcolor='#1f2937')
        frame=ttk.Frame(self.ui,padding=20);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='Grave o seu jeito de mover o mouse',font=('Segoe UI',15,'bold')).pack(anchor='w')
        ttk.Label(frame,text='F8 inicia • 5 s de preparo • 10 s de gravação').pack(anchor='w',pady=(8,16))
        self.category=tk.StringVar(value=LABELS['geral'])
        self.categories=ttk.Combobox(frame,textvariable=self.category,values=list(LABELS.values()),state='readonly');self.categories.pack(fill='x')
        self.categories.bind('<<ComboboxSelected>>',lambda e:self.refresh())
        self.real_clicks=tk.BooleanVar(value=False)
        ttk.Checkbutton(frame,text='Aplicar cliques na tela durante a gravação',variable=self.real_clicks).pack(anchor='w',pady=10)
        ttk.Label(frame,text='Desmarcado: seus cliques só marcam os trajetos.\nNão acionam os botões do Flow.').pack(anchor='w')
        self.status=tk.StringVar(value='');ttk.Label(frame,textvariable=self.status,font=('Segoe UI',13,'bold'),wraplength=410).pack(anchor='w',pady=18)
        self.progress=ttk.Progressbar(frame,maximum=10);self.progress.pack(fill='x')
        row=ttk.Frame(frame);row.pack(fill='x',pady=(14,5))
        self.record_button=ttk.Button(row,text='Gravar próxima • F8',command=self.arm);self.record_button.pack(side='left')
        ttk.Button(row,text='Cancelar • Esc',command=self.cancel).pack(side='right')
        row=ttk.Frame(frame);row.pack(fill='x',pady=5)
        ttk.Button(row,text='Refazer última',command=self.redo).pack(side='left')
        ttk.Button(row,text='Ver movimento no Flow',command=self.preview).pack(side='right')
        self.refresh();self.ui.after(8,self.tick)

    def key(self):return next(k for k,v in LABELS.items() if v==self.category.get())

    def refresh(self):
        count=len(self.library.captures(self.key()))
        self.status.set(f'{LABELS[self.key()]}: {count}/5 versões salvas'+('\nPronto. Pode fechar o gravador.' if count==5 else '\nPosicione o Flow e pressione F8.'))
        self.record_button.configure(state='disabled' if count>=5 else 'normal')

    def find_flow(self):
        native=Macro(SimpleNamespace(projeto=project_id(self.plan['project_url'])))
        if not recorder_url_matches(native.original_url,self.plan['project_url']):
            raise RuntimeError('Abra uma tela do projeto de avatares indicado no plano.')
        return native.window

    def arm(self):
        if self.state!='ready' or len(self.library.captures(self.key()))>=5:return
        try:self.flow=self.find_flow()
        except Exception as error:messagebox.showerror('Flow',str(error));return
        self.state='countdown';self.deadline=time.monotonic()+5;self.recording_category=self.key();self.progress['value']=0
        self.categories.configure(state='disabled');self.record_button.configure(state='disabled')

    def cancel(self):
        if self.state=='ready':return
        self.markers.active=False;self.state='ready';self.points=[];self.clicks=[]
        self.categories.configure(state='readonly');self.refresh()

    def redo(self):
        if self.state!='ready':return
        self.library.redo_last(self.key());self.refresh()

    def begin(self):
        try:self.flow.set_focus()
        except Exception as error:self.cancel();messagebox.showerror('Flow',str(error));return
        self.started=time.monotonic();self.state='recording';self.points=[];self.clicks=[]
        while not self.markers.events.empty():self.markers.events.get_nowait()
        self.markers.window=self.flow.handle;self.markers.started=self.started;self.markers.block=not self.real_clicks.get();self.markers.active=True
        rect=self.flow.rectangle();self.window_bounds=[rect.left,rect.top,rect.right,rect.bottom]

    def finish(self):
        self.markers.active=False
        while not self.markers.events.empty():self.clicks.append(self.markers.events.get_nowait())
        capture={'schema':1,'category':self.recording_category,'duration':10,'recorded_at':time.time(),
                 'window_bounds':self.window_bounds,'points':self.points,'clicks':self.clicks,'real_clicks':not self.markers.block}
        try:
            if self.recording_category!='espera':
                from recorded_motion import click_paths
                if not click_paths(capture):raise ValueError('Faça um trajeto até um botão e clique para marcar o final. Nenhuma versão foi salva.')
            self.library.save(capture)
        except Exception as error:messagebox.showerror('Gravação',str(error))
        self.state='ready';self.categories.configure(state='readonly');self.refresh()

    def preview(self):
        if self.state!='ready':return
        rows=self.library.captures(self.key())
        if not rows:messagebox.showinfo('Prévia','Grave uma versão primeiro.');return
        try:
            self.flow=self.find_flow();self.flow.set_focus();rect=self.flow.rectangle()
            capture=read(self.library._file(rows[-1]['file']))
            path=idle_path(capture,(rect.left+260,rect.top+180,rect.right-50,rect.bottom-180))
            self.preview_steps=[];elapsed=0
            for point,dt in path:elapsed+=dt;self.preview_steps.append((elapsed,point))
            self.started=time.monotonic();self.state='preview';self.status.set('Reproduzindo movimento • sem cliques • Esc cancela')
        except Exception as error:messagebox.showerror('Prévia',str(error))

    def tick(self):
        u=ctypes.windll.user32
        if self.markers.error:
            self.cancel();self.status.set('O gravador de cliques parou. Feche e abra novamente.');return
        f8=bool(u.GetAsyncKeyState(0x77)&0x8000);esc=bool(u.GetAsyncKeyState(0x1B)&0x8000)
        if esc and not self.escape:self.cancel()
        if f8 and not self.f8:self.arm()
        self.f8,self.escape=f8,esc
        now=time.monotonic()
        if self.state=='countdown':
            remaining=self.deadline-now;self.status.set(f'Começa em {max(1,math.ceil(remaining))}…\nPrepare o mouse sobre o Flow.')
            if remaining<=0:self.begin()
        elif self.state=='recording':
            if u.GetForegroundWindow()!=self.flow.handle:
                self.cancel();self.status.set('Gravação cancelada: o Flow perdeu o foco. F8 para tentar novamente.')
            else:
                elapsed=now-self.started;point=wintypes.POINT();u.GetCursorPos(ctypes.byref(point))
                self.points.append([min(10,elapsed),point.x,point.y]);self.progress['value']=min(10,elapsed)
                self.status.set(f'GRAVANDO • {max(0,10-elapsed):.1f} s\nMova e clique para marcar seus trajetos.')
                if elapsed>=10:self.finish()
        elif self.state=='preview':
            if u.GetForegroundWindow()!=self.flow.handle:self.cancel()
            else:
                elapsed=now-self.started
                while self.preview_steps and self.preview_steps[0][0]<=elapsed:
                    _,point=self.preview_steps.pop(0);u.SetCursorPos(*point)
                if not self.preview_steps:self.state='ready';self.refresh()
        self.ui.after(8,self.tick)

    def close(self):
        self.markers.close();self.ui.destroy()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--plano');parser.add_argument('--biblioteca');parser.add_argument('--snapshot');args=parser.parse_args()
    plan_path=locate(args.plano);root=plan_path.parent;plan=read(plan_path)
    ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    ui=tk.Tk()
    try:
        with controller_lock(root):
            app=Recorder(ui,plan,MotionLibrary(args.biblioteca))
            def ready():
                ui.update_idletasks()
                status={'pid':os.getpid(),'status':'ready','capture_started':False,'library':str(app.library.folder),
                        'versions':{key:len(app.library.captures(key)) for key in CATEGORIES}}
                if args.snapshot:
                    from PIL import ImageGrab
                    box=(ui.winfo_rootx(),ui.winfo_rooty(),ui.winfo_rootx()+ui.winfo_width(),ui.winfo_rooty()+ui.winfo_height())
                    ImageGrab.grab(bbox=box).save(args.snapshot)
                    status['snapshot']=args.snapshot
                atomic(root/'gravador.json',status)
            ui.after(350,ready);ui.mainloop()
            atomic(root/'gravador.json',{'pid':os.getpid(),'status':'closed'})
    except Exception as error:messagebox.showerror('Gravador',str(error));ui.destroy();raise


if __name__=='__main__':main()
