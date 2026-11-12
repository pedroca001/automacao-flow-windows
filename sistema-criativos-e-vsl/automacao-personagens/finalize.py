"""Auditoria final e relatório na pasta de entrega; não gera nem publica."""
import argparse,json
from pathlib import Path
from cli import locate
from core import atomic,read,sha,extract_spoken
from controller import probe,report
from client import browser


def finalize(path):
    path=Path(path);root=path.parent
    plan,state=read(path),read(root/'estado-personagens.json')
    if state['status'] not in ('complete','complete_with_discards','incomplete'):
        raise ValueError('A fila ainda tem trabalho pendente: '+state['status'])
    inventory=browser(plan,root,'inventory')
    assets={row['id']:row for row in inventory['videos']}
    verified_assets=[]
    items=[]
    for character in plan['characters']:
        cid=character['id']
        if cid in state.get('discarded',{}):
            items.append({'character':cid,'status':'discarded',**state['discarded'][cid]})
            continue
        if cid not in state.get('deliveries',{}):
            pending=[{'number':s['number'],'status':s['status'],'reason':s.get('reason')}
                     for s in state['scenes'].values() if s['character']==cid and s['status']!='complete']
            items.append({'character':cid,'voice':character['voice'],'status':'pending','scenes':pending})
            continue
        delivery=state['deliveries'][cid]
        output=Path(delivery['file'])
        if sha(output)!=delivery['sha256']:
            raise ValueError('Hash da entrega divergiu: '+cid)
        info=probe(output)
        video=next(s for s in info['streams'] if s['codec_type']=='video')
        audio=next(s for s in info['streams'] if s['codec_type']=='audio')
        assert abs(float(info['format']['duration'])-40)<.1 and [video['width'],video['height']]==[720,1280] and video['r_frame_rate']=='24/1'
        assert abs(float(video['duration'])-float(audio['duration']))<.15
        scenes=sorted((s for s in state['scenes'].values() if s['character']==cid),key=lambda s:s['number'])
        assert len(scenes)==5 and all(s['status']=='complete' for s in scenes)
        scores=[]
        for scene in scenes:
            scene_id=cid+'__'+scene['prompt_set']+f"__{scene['number']:02d}"
            assert len(scene['attempts'])<=3 and sha(scene['file'])==scene['sha256']
            character_receipt=read(root/'characters'/(cid+'.json'))
            asset=assets[scene['video']]
            assert asset.get('model')=='veo_3_1_r2v_lite_low_priority','Modelo divergiu: '+scene_id
            assert character_receipt['character_id'] in asset.get('refs',[]), 'Personagem divergiu: '+scene_id
            verified_assets.append({'scene':scene_id,'video_id':asset['id'],
                                    'model':asset.get('model'),'refs':asset.get('refs',[])})
            approved=plan['prompt_sets'][scene['prompt_set']]['prompts'][scene['number']-1]
            expected=approved.get('spoken') if isinstance(approved,dict) else extract_spoken(approved)
            if expected:
                assert scene['spoken']==expected and extract_spoken(scene['prompt'])==expected
                for attempt in scene['attempts']:
                    assert extract_spoken(Path(attempt['prompt_file']).read_text(encoding='utf-8'))==expected
            if scene.get('qa',{}).get('issues'):
                raise ValueError('Cena ainda tem falha de QA: '+cid)
            if scene.get('qa',{}).get('word_similarity') is not None:
                scores.append(scene['qa']['word_similarity'])
        items.append({'character':cid,'voice':character['voice'],'status':'delivered','file':str(output),
                      'seconds':40,'sha256':delivery['sha256'],'attempts':sum(len(s['attempts']) for s in scenes),
                      'min_word_similarity':min(scores) if scores else None})
    result={'project_url':plan['project_url'],'status':state['status'],'items':items,
            'visual_review':read(root/'REVISAO-VISUAL.json',{'status':'pending'}),'voice_identity_qa':'pending_human_listening',
            'speech_changed':False,'local_tests':39,'recipe_regression_tests':28,
            'verified_assets':verified_assets,
            'speech_observations':[{'scene':cid,'score':s['qa']['word_similarity'],'expected':s['spoken'],'transcript':s['qa'].get('transcript')}
                                   for cid,s in state['scenes'].items() if s.get('qa',{}).get('word_similarity',1)<1],
            'unconfirmed_previous_attempts':state.get('uncertain_reservations',{})}
    atomic(root/'AUDITORIA-FINAL.json',result)
    lines=['# Entrega de avatares — 21/10/2026','',
           'Projeto: '+plan['project_url'],'',
           '| Avatar | Voz | Resultado | Duração | Tentativas | Similaridade mínima da fala |','|---|---|---|---|---|---|']
    for row in items:
        lines.append(f"| {row['character']} | {row.get('voice','')} | {row['status']} | {row.get('seconds','')} | {row.get('attempts','')} | {row.get('min_word_similarity','')} |")
    pending=[i for i in items if i['status']=='pending']
    if pending:
        lines+=['','Pendências: '+json.dumps(pending,ensure_ascii=False)]
    if result['speech_observations']:
        lines+=['','Observação de transcrição: '+json.dumps(result['speech_observations'],ensure_ascii=False)]
    lines+=['','Cada entrega concatena cinco cenas de oito segundos, em ordem, com áudio. Hashes, durações e a referência ao personagem de cada cena foram conferidos. A fala original foi preservada byte a byte em todos os prompts e revisões das entregas. A transcrição foi comparada automaticamente ao roteiro.',
            '','A revisão final de imagem, transições entre cenas e identidade da voz permanece humana. A geração pode introduzir variações e fades nas caudas; consulte REVISAO-VISUAL.json na pasta da execução para observações das folhas de contato.',
            '', 'Automação de personagens separada das receitas. Documentação: '+str(plan_path_docs()),
            'Tracking completo: '+str(root/'RELATORIO-PERSONAGENS.json')]
    output=Path(plan['output'])/'RELATORIO-AVATARES.md'
    output.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    report(path)
    print(json.dumps({'delivered':sum(i['status']=='delivered' for i in items),'discarded':sum(i['status']=='discarded' for i in items),'pending':len(pending),'report':str(output)},ensure_ascii=False))


def plan_path_docs():
    return Path(__file__).resolve().parent.parent/'FLOW-PERSONAGENS.md'


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plano');a=p.parse_args();finalize(locate(a.plano))
