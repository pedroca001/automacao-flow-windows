"""Notifica a mesma conversa Codex; mantém recibo local quando ela não está acessível."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from core import atomic, read, fingerprint
from client import process_options

SETTINGS=Path(__file__).resolve().parent/'notificacoes.json'


def notify(root, event):
    root=Path(root)
    event_id=event['scene']+f'__tentativa_{event["attempt"]:02d}'
    path=root/'alertas'/f'{event_id}.json'
    existing=read(path,{})
    if existing.get('notification',{}).get('queued'):
        return existing
    record={'id':event_id,'created_at':time.time(),**event,'status':'pending_review'}
    atomic(path,record)
    settings=read(root/'notificacao.json',{})
    if read(SETTINGS,{}).get('enabled',True) is False or settings.get('enabled',True) is False:
        record['notification']={'queued':False,'reason':'alertas_automaticos_desativados'}
        atomic(path,record)
        return record
    thread=settings.get('thread') or os.environ.get('CODEX_THREAD_ID')
    executable=shutil.which('codex')
    if not thread or not executable:
        record['notification']={'queued':False,'reason':'conversa_ou_codex_indisponivel'}
        atomic(path,record)
        return record
    message=('[FLOW-PERSONAGENS: ALERTA AUTOMATICO] Revisao pendente no arquivo '+str(path)+'. '
             'Leia o evento e o plano '+str(root/'plano-personagens.json')+'. '
             'O usuario autorizou revisar somente instrucoes visuais/tecnicas, preservando a frase falada byte a byte, '
             'ate tres tentativas por cena; ao esgotar, descartar o avatar e seguir. '
             'Corrija apenas ambiguidades de conteudo permitido; nao oculte conteudo proibido nem contorne verificacoes de seguranca. '
             'Use cli.py revisar-cena com o prompt revisado para devolver a decisao. '
             'Nao inicie outro controlador: a fila atual le a decisao no disco. Se este evento ja estiver resolvido, apenas confira o recibo.')
    if event.get('kind')=='reconcile_before_retry':
        message+=' ATENCAO: envio incerto. Nao autorize nova geracao. Primeiro reconcilie o ID existente ou a recusa pela interface; so depois avalie revisao.'
    if event.get('kind')=='controller_error':
        message+=' ATENCAO: erro tecnico do controlador. Corrija e confira os recibos antes de retomar. Este evento nao autoriza reenviar cenas incertas.'
    try:
        result=subprocess.run([executable,'queue','--thread',thread,'--message',message],capture_output=True,text=True,encoding='utf-8',timeout=45,**process_options())
        record['notification']={'queued':result.returncode==0,'returncode':result.returncode,'thread':thread,
                                'detail':(result.stdout or result.stderr)[-1200:]}
    except Exception as error:
        record['notification']={'queued':False,'reason':str(error)[-800:]}
    atomic(path,record)
    return record
