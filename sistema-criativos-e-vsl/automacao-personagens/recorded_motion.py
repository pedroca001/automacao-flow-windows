"""Biblioteca de trajetos do usuario. Cliques gravados sao apenas marcadores."""
import math
from pathlib import Path
import time
import uuid
from core import read,atomic
from flow_platform import locks

DEFAULT_LIBRARY=Path(__file__).resolve().parent/'movimentos-usuario'
CATEGORIES=('geral','configuracao','texto','enviar','espera')


def action_category(name,kind=''):
    if name=='Iniciar geração':return 'enviar'
    if name in ('Gatilho de configurações','Selecionar família de modelos','Vídeo','Elementos','9:16','8s','x1') or name.startswith('Veo '):
        return 'configuracao'
    if kind in ('Edit','ComboBox'):return 'texto'
    return 'geral'


def check_capture(capture):
    if capture.get('schema')!=1 or capture.get('category') not in CATEGORIES:
        raise ValueError('Gravacao de movimento invalida.')
    points=capture.get('points',[])
    if not 2<=len(points)<=5000:raise ValueError('Gravacao sem amostras suficientes.')
    previous=-1
    for p in points:
        if len(p)!=3 or not all(isinstance(n,(int,float)) and math.isfinite(n) for n in p):
            raise ValueError('Amostra invalida.')
        if p[0]<previous or not 0<=p[0]<=10.3 or max(abs(p[1]),abs(p[2]))>65536:
            raise ValueError('Amostra fora dos limites.')
        previous=p[0]
    if points[-1][0]-points[0][0]<.25:raise ValueError('Trajeto muito curto.')
    for click in capture.get('clicks',[]):
        if not isinstance(click.get('t'),(int,float)) or not 0<=click['t']<=10.3:
            raise ValueError('Marcador de clique invalido.')
    return capture


def click_paths(capture):
    """Recorta cada aproximacao a um clique; descarta espera inicial parada."""
    check_capture(capture);points=capture['points'];paths=[];begin=0
    ends=sorted({c['t'] for c in capture.get('clicks',[])}) or [points[-1][0]]
    for end in ends:
        path=[p for p in points if begin<=p[0]<=end];begin=end
        if len(path)<2:continue
        while len(path)>2 and math.dist(path[0][1:],path[1][1:])<1:
            path=path[1:]
        while len(path)>2 and math.dist(path[-1][1:],path[-2][1:])<1:
            path=path[:-1]
        if math.dist(path[0][1:],path[-1][1:])>=12 and path[-1][0]>path[0][0]:paths.append(path)
    return paths


def retarget(path,start,end):
    a,b=path[0],path[-1];dx,dy=b[1]-a[1],b[2]-a[2];size=math.hypot(dx,dy)
    tx,ty=end[0]-start[0],end[1]-start[1];target=math.hypot(tx,ty)
    if size<12 or target<1:return []
    raw_duration=path[-1][0]-path[0][0]
    duration=min(.65,max(.16,raw_duration));result=[];last_t=0
    lateral_limit=min(120,target*.35)
    for p in path[1:]:
        px,py=p[1]-a[1],p[2]-a[2]
        along=max(-.04,min(1.04,(px*dx+py*dy)/(size*size)))
        side=max(-lateral_limit,min(lateral_limit,(-px*dy+py*dx)/(size*size)*target))
        point=(round(start[0]+along*tx-side*ty/target),round(start[1]+along*ty+side*tx/target))
        t=(p[0]-a[0])/raw_duration*duration
        result.append((point,max(0,t-last_t)));last_t=t
    if result:result[-1]=(tuple(end),result[-1][1])
    return result


def idle_path(capture,bounds):
    check_capture(capture);points=capture['points'];left,top,right,bottom=bounds
    xs=[p[1] for p in points];ys=[p[2] for p in points]
    width=max(1,max(xs)-min(xs));height=max(1,max(ys)-min(ys))
    scale=min((right-left)/width,(bottom-top)/height,1.0)
    cx=(min(xs)+max(xs))/2;cy=(min(ys)+max(ys))/2;last=points[0][0];out=[]
    for t,x,y in points:
        out.append(((round((left+right)/2+(x-cx)*scale),round((top+bottom)/2+(y-cy)*scale)),max(0,t-last)))
        last=t
    return out


class MotionLibrary:
    def __init__(self,folder=None):self.folder=Path(folder or DEFAULT_LIBRARY)

    def captures(self,category):
        return read(self.folder/'catalogo.json',{}).get('categories',{}).get(category,[])

    def _file(self,name):
        path=(self.folder/name).resolve()
        if path.parent!=self.folder.resolve() or path.suffix!='.json':raise ValueError('Caminho de gravacao invalido.')
        return path

    def save(self,capture):
        check_capture(capture);self.folder.mkdir(parents=True,exist_ok=True)
        with (self.folder/'.biblioteca.lock').open('a') as lock:
            locks.flock(lock,locks.LOCK_EX)
            catalog=read(self.folder/'catalogo.json',{'schema':1,'categories':{}})
            rows=catalog['categories'].setdefault(capture['category'],[])
            if len(rows)>=5:raise ValueError('Essa categoria ja tem cinco versoes. Use Refazer ultima.')
            filename=capture['category']+'-'+uuid.uuid4().hex[:12]+'.json'
            atomic(self._file(filename),capture)
            rows.append({'file':filename,'version':len(rows)+1,'created_at':time.time(),'click_paths':len(click_paths(capture))})
            atomic(self.folder/'catalogo.json',catalog)
        return len(rows)

    def redo_last(self,category):
        self.folder.mkdir(parents=True,exist_ok=True)
        with (self.folder/'.biblioteca.lock').open('a') as lock:
            locks.flock(lock,locks.LOCK_EX)
            catalog=read(self.folder/'catalogo.json',{'schema':1,'categories':{}})
            rows=catalog['categories'].get(category,[])
            if not rows:return
            row=rows.pop();source=self._file(row['file']);archive=self.folder/'_historico';archive.mkdir(exist_ok=True)
            if source.exists():source.rename(archive/source.name)
            atomic(self.folder/'catalogo.json',catalog)

    def select(self,category):
        rows=self.captures(category)
        actual=category
        if not rows:actual='geral';rows=self.captures(actual)
        if not rows:return None
        with (self.folder/'.biblioteca.lock').open('a') as lock:
            locks.flock(lock,locks.LOCK_EX)
            counters=read(self.folder/'selecao.json',{})
            index=counters.get(actual,0);row=rows[index%len(rows)]
            counters[actual]=index+1;atomic(self.folder/'selecao.json',counters)
        capture=check_capture(read(self._file(row['file'])))
        return capture,index//len(rows),row['version']

    def movement(self,start,end,category='geral'):
        selected=self.select(category)
        if not selected:return None
        capture,step,version=selected;paths=click_paths(capture)
        if not paths:return None
        return retarget(paths[step%len(paths)],start,end)

    def idle(self,bounds):
        selected=self.select('espera')
        return idle_path(selected[0],bounds) if selected else None
