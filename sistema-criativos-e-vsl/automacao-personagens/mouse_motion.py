"""Movimento visual suave do cursor, sem alterar o alvo nem disparar cliques."""
import math
import time
import random


def motion_points(start,end,rng=None):
    distance=math.hypot(end[0]-start[0],end[1]-start[1])
    if distance<1:
        return []
    rng=rng or random
    duration=min(.38,max(.20,distance/4200))*rng.uniform(.94,1.06)
    frames=max(10,math.ceil(duration*60))
    dx,dy=end[0]-start[0],end[1]-start[1]
    bend=rng.uniform(-1,1)*min(65,distance*.12)
    normal=(-dy/distance,dx/distance)
    c1=(start[0]+dx*.28+normal[0]*bend,start[1]+dy*.28+normal[1]*bend)
    c2=(start[0]+dx*.75+normal[0]*bend*.65,start[1]+dy*.75+normal[1]*bend*.65)
    result=[]
    for i in range(1,frames+1):
        t=i/frames;eased=t*t*(3-2*t)
        u=1-eased
        point=tuple(round(u*u*u*start[j]+3*u*u*eased*c1[j]+3*u*eased*eased*c2[j]+eased**3*end[j]) for j in (0,1))
        result.append((point,duration/frames))
    result[-1]=(tuple(end),duration/frames)
    return result


def send_motion_points(start,end,bounds,library=None):
    """Trajeto gravado dentro do compositor e pouso reto pela esquerda."""
    left,top,right,bottom=bounds
    if not (left<right and top<bottom and left<=end[0]<=right and top<=end[1]<=bottom):
        raise ValueError('Botao de envio fora da area segura do compositor.')
    def clamp(point):return (round(max(left,min(right,point[0]))),round(max(top,min(bottom,point[1]))))
    entry=clamp(start)
    result=motion_points(start,entry) if tuple(start)!=entry else []
    landing=(round(max(left,end[0]-64)),end[1])
    recorded=library.movement(entry,landing,'enviar') if library else None
    approach=recorded if recorded is not None else motion_points(entry,landing)
    # Nem o overshoot nem as curvas laterais gravadas podem sair do painel.
    result.extend((clamp(point),dt) for point,dt in approach)
    # Ultimos pixels sem curva lateral, recuo ou ultrapassagem do botao.
    frames=8
    for i in range(1,frames+1):
        t=i/frames;eased=t*t*(3-2*t)
        point=(round(landing[0]+(end[0]-landing[0])*eased),end[1])
        result.append((point,.12/frames))
    result[-1]=(tuple(end),result[-1][1])
    return result


class SmoothMouse:
    def __init__(self,mouse,position,set_position,stop,library=None):
        self.mouse,self.position,self.set_position,self.stop=mouse,position,set_position,stop
        self.library=library;self.category='geral';self.before_click=None

    def move(self,coords=(0,0),safe_bounds=None):
        start=self.position()
        if safe_bounds is not None:
            points=send_motion_points(start,coords,safe_bounds,self.library)
        else:
            points=self.library.movement(start,coords,self.category) if self.library else None
        deadline=time.monotonic()
        for point,interval in (points if points is not None else motion_points(start,coords)):
            before=time.monotonic()
            self.stop()
            # Uma pausa do operador suspende tambem o relogio da animacao.
            elapsed=time.monotonic()-before
            if elapsed>.1:deadline+=elapsed
            deadline+=interval
            remaining=deadline-time.monotonic()
            if remaining>0:time.sleep(remaining)
            self.set_position(point)

    def click(self,*args,**kwargs):
        if self.before_click is not None:self.before_click()
        return self.mouse.click(*args,**kwargs)

    def __getattr__(self,name):
        return getattr(self.mouse,name)
