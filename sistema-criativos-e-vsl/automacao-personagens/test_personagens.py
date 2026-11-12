import copy
import contextlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import threading
import unittest
from unittest.mock import patch

from core import MODE, assign, atomic, build_scenes, choose_voices, fingerprint, read, reconcile, validate_plan, validate_revision, missing_asset_failure, reserved_generation_slots, output_filename, page_block_reason
from controller import assemble, probe, request_review, apply_reviews, submit_review, reject_quality, submit_quality, apply_quality
from mouse_motion import motion_points,SmoothMouse
from operator_controls import PauseGesture,VisualOperator


def character(cid='avatar_01', gender='female', tags=None):
    return {'id': cid, 'name': cid, 'image': cid + '.png', 'image_sha256': 'a'*64, 'gender': gender, 'tags': tags or [], 'voice': 'Female1'}


def plan():
    return {'mode': MODE, 'project_url': 'https://flow.google.com/u/1/project/e0edef62-354f-44ea-b8d5-e2730ae157b9',
            'project': 'e0edef62-354f-44ea-b8d5-e2730ae157b9', 'characters': [character()], 'output': 'output',
            'prompt_sets': {'audio_x': {'prompts': ['Scene '+str(i) for i in range(5)]}}, 'assignments': {'avatar_01':'audio_x'}}


class CharacterTests(unittest.TestCase):
    def test_espera_fica_no_campo_visivel_sem_botoes_ou_galeria(self):
        from operator_controls import composer_idle_bounds
        from types import SimpleNamespace as R
        self.assertEqual(composer_idle_bounds(R(left=571,top=811,right=1133,bottom=1311),
                                             R(left=552,top=899,right=1152,bottom=1359)),(579,903,1125,1307))
        self.assertIsNone(composer_idle_bounds(R(left=10,top=10,right=20,bottom=15),R(left=0,top=0,right=30,bottom=30)))

    def test_sem_teto_local_envia_sexta_cena_sem_alterar_plano(self):
        from core import sha
        from controller import run
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);p=plan();image=root/'image.png';image.write_bytes(b'image')
            p['characters']=[character('A'),character('B')];p['assignments']={'A':'audio_x','B':'audio_x'}
            for c in p['characters']:
                c.update(image=str(image),image_sha256=sha(image))
                atomic(root/'characters'/(c['id']+'.json'),{'phase':'ready','voice':c['voice'],'character_id':c['id'],'image_sha256':sha(image)})
            path=root/'plan.json';atomic(path,p);atomic(root/'operacao.json',{'max_rendering':None,'submission_interval_seconds':25})
            scenes=build_scenes(p);ids=list(scenes)
            for cid in ids[:5]:scenes[cid].update(status='rendering',video=cid,sent_at=time.time(),attempts=[{'started_at':time.time()-60}])
            old_receipt=root/'uncertain.json';atomic(old_receipt,{'phase':'submitted_ui','at':time.time()-600})
            scenes[ids[4]].update(status='uncertain',reason='clique_sem_id',attempts=[{'started_at':time.time()-600,'receipt':str(old_receipt),'baseline':[]}])
            scenes[ids[4]].pop('video',None)
            atomic(root/'estado-personagens.json',{'plan_sha256':fingerprint(p),'scenes':scenes,'deliveries':{}})
            def fake_browser(plan,root,action,**kw):
                if action=='snapshot':return {'inventory':fake_browser(plan,root,'inventory'),'statuses':fake_browser(plan,root,'poll',videos=kw['videos']),'focused':kw.get('focus',False)}
                if action=='inventory':return {'asset_ids':[],'videos':[]}
                if action=='poll':return {cid:{'ready':False,'failed':False} for cid in kw['videos']}
                if action=='focus':return {}
                raise AssertionError(action)
            class Native:
                pid=99999
                def __init__(self,command,**kw):self.command=command;self.done=False
                def poll(self):return 0 if self.done else None
                def wait(self,timeout):
                    receipt=Path(self.command[self.command.index('--recibo')+1]);atomic(receipt,{'phase':'submitted_ui','at':time.time()})
                    (root/'PARAR').write_text('test');self.done=True;return 0
            with patch('controller.controller_lock',return_value=contextlib.nullcontext()),patch('controller.browser',side_effect=fake_browser),patch('controller.subprocess.Popen',side_effect=Native):
                self.assertEqual(run(path),130)
            state=read(root/'estado-personagens.json')
            self.assertEqual(state['scenes'][ids[5]]['status'],'confirming')
            self.assertTrue(state['scenes'][ids[4]]['hold_retry'])
            self.assertEqual(len(state['scenes'][ids[4]]['attempts']),1)
            self.assertEqual(state['metrics']['peak_inflight'],6)
            self.assertEqual(read(path),p)

    def test_mouse_suave_atinge_alvo_sem_saltos_ou_overshoot(self):
        import random
        points=motion_points((100,200),(1100,700),rng=random.Random(42))
        coords=[(100,200)]+[p for p,dt in points]
        self.assertEqual(coords[-1],(1100,700))
        self.assertTrue(all(100<=x<=1100 and 200<=y<=700 for x,y in coords))
        self.assertLessEqual(max(abs(b[0]-a[0]) for a,b in zip(coords,coords[1:])),150)
        self.assertGreater(len(points),10)
        self.assertLessEqual(sum(dt for p,dt in points),.403)
        second=motion_points((100,200),(1100,700),rng=random.Random(43))
        self.assertNotEqual([p for p,dt in points],[p for p,dt in second])

    def test_atalho_duplo_ignora_teclas_injetadas_e_auto_repeticao(self):
        gesture=PauseGesture()
        self.assertFalse(gesture.key(0x6B,True,True,0))
        self.assertFalse(gesture.key(0x6B,True,True,.1))
        self.assertFalse(gesture.key(0x6B,False,True,.15))
        self.assertFalse(gesture.key(0x6B,True,True,.2,injected=True))
        self.assertTrue(gesture.key(0x6B,True,True,.3))
        gesture.key(0x6B,False,True,.4)
        self.assertFalse(gesture.key(0x6B,True,True,1))
        gesture.key(0x6B,False,True,1.1)
        self.assertFalse(gesture.key(0x6B,True,True,2))

    def test_pausa_duravel_aguarda_retomada_sem_mover_cursor(self):
        with tempfile.TemporaryDirectory() as folder:
            op=VisualOperator(folder);op.enabled=True;op.pause_file.write_text('pausa')
            done=threading.Event()
            worker=threading.Thread(target=lambda:(op.wait_if_paused(lambda:False),done.set()))
            worker.start();self.assertFalse(done.wait(.12))
            op.pause_file.unlink();self.assertTrue(done.wait(1));worker.join()

    def test_mouse_suave_obedece_interrupcao_sem_clique(self):
        from unittest.mock import Mock
        mouse=Mock();set_position=Mock();stop=Mock(side_effect=RuntimeError('parar'))
        wrapped=SmoothMouse(mouse,lambda:(100,100),set_position,stop)
        with self.assertRaises(RuntimeError):wrapped.move((600,600))
        set_position.assert_not_called();mouse.click.assert_not_called()

    def test_retentativa_identica_somente_falha_recuperavel_confirmada(self):
        text='A continuous camera shot.\nSpoken audio only:\n"Hello there."'
        row={'prompt':text,'spoken':'Hello there.'}
        with self.assertRaises(ValueError):validate_revision(row,text)
        row.update(reason='falha_recuperavel_do_servico_confirmada_na_interface')
        with self.assertRaises(ValueError):validate_revision(row,text)
        row['failure_evidence']={'message':'Notamos uma atividade incomum.'}
        self.assertEqual(validate_revision(row,text),'Hello there.')
        with self.assertRaises(ValueError):validate_revision(row,text.replace('Hello there.','Hi there.'))

    def test_cartao_recuperavel_exige_autorizacao_e_nao_ignora_desafio_global(self):
        full='Falha: Notamos uma atividade incomum. Tentar de novo'
        self.assertEqual(page_block_reason(full,'Projeto',False),'atividade_incomum_cartao_sem_autorizacao')
        self.assertIsNone(page_block_reason(full,'Projeto',True))
        self.assertEqual(page_block_reason(full,full,True),'atividade_incomum_global')
        self.assertEqual(page_block_reason('Verify you are human','Projeto',True),'verificacao_humana')

    def test_inspecao_assincrona_aguarda_montagem_e_rejeita_hash_antigo(self):
        with tempfile.TemporaryDirectory() as folder,patch('notifier.notify'):
            root=Path(folder);path=root/'plan.json'
            scene={'character':'one','status':'complete','sha256':'a'*64,'attempts':[{}],'prompt':'x','spoken':'y','prompt_sha256':'p'}
            state={'scenes':{'scene_1':scene},'deliveries':{}}
            atomic(root/'estado-personagens.json',state)
            submit_quality(path,'scene_1','produto_mudou')
            apply_quality(root,state,{'generation_attempts':3},assembling={'one'})
            self.assertEqual(scene['status'],'complete')
            apply_quality(root,state,{'generation_attempts':3})
            self.assertEqual(scene['status'],'needs_review')
            scene.update(status='complete',sha256='b'*64)
            atomic(root/'estado-personagens.json',state)
            submit_quality(path,'scene_1','produto_mudou')
            scene['sha256']='c'*64
            apply_quality(root,state,{'generation_attempts':3})
            self.assertEqual(scene['status'],'complete')

    def test_entrega_inclui_nome_cadastrado_e_versao_sem_permitir_outro_diretorio(self):
        self.assertEqual(output_filename({'name':'AV20261021_16_mulher_01'},'v1_esposa'),'AV20261021_16_mulher_01__v1_esposa__40s.mp4')
        with self.assertRaises(ValueError): output_filename({'name':'../fora'},'v1')

    def test_receita_nao_aceita_plano_personagens_e_inverso(self):
        p=plan()
        p['mode']='recipe'
        with self.assertRaises(ValueError): validate_plan(p)

    def test_url_tem_conta_exata_e_rejeita_host_falso(self):
        for url in ('https://flow.google.com.evil.test/u/1/project/e0edef62-354f-44ea-b8d5-e2730ae157b9',
                    'http://flow.google.com/u/1/project/e0edef62-354f-44ea-b8d5-e2730ae157b9'):
            p=plan();p['project_url']=url
            with self.assertRaises(ValueError): validate_plan(p)
        p=plan(); h=fingerprint(p);p['project_url']=p['project_url'].replace('/u/1/','/u/2/')
        self.assertNotEqual(h,fingerprint(p))

    def test_cinco_cenas_por_personagem_com_prompts_e_tracking_separados(self):
        p=plan();p['characters'].append(character('avatar_02'))
        p['prompt_sets']['audio_y']={'prompts':[{'text':'Other '+str(i),'spoken':'words '+str(i)} for i in range(5)]}
        p['assignments']['avatar_02']='audio_y'
        scenes=build_scenes(p)
        self.assertEqual(len(scenes),10)
        self.assertEqual(scenes['avatar_02__audio_y__03']['prompt'],'Other 2')
        self.assertEqual(scenes['avatar_02__audio_y__03']['spoken'],'words 2')
        self.assertNotEqual(scenes['avatar_01__audio_x__03']['prompt_sha256'],scenes['avatar_02__audio_y__03']['prompt_sha256'])

    def test_cotas_cinco_personagens_por_audio(self):
        chars=[character('av'+str(i)) for i in range(10)]
        config={'prompt_sets':{'x':{'prompts':list('abcde')},'y':{'prompts':list('fghij')}},'distribution':{'mode':'quota','quotas':{'x':5,'y':5}}}
        mapping=assign(chars,config)
        self.assertEqual(list(mapping.values()).count('x'),5)
        self.assertEqual(list(mapping.values()).count('y'),5)

    def test_cotas_nao_consume_vaga_reservada_a_outro_genero(self):
        chars=[character('woman'),character('man','male')]
        config={'prompt_sets':{'x':{'prompts':list('abcde')},'y':{'genders':['female'],'prompts':list('fghij')}},'distribution':{'mode':'quota','quotas':{'x':1,'y':1}}}
        self.assertEqual(assign(chars,config),{'woman':'y','man':'x'})

    def test_sorteio_respeita_genero_e_tags_e_repetivel(self):
        chars=[character('female','female',['kitchen']),character('male','male',['office'])]
        config={'prompt_sets':{'x':{'genders':['female'],'required_tags':['kitchen'],'prompts':list('abcde')},'y':{'genders':['male'],'required_tags':['office'],'prompts':list('fghij')}},'distribution':{'mode':'random','seed':15}}
        self.assertEqual(assign(chars,config),{'female':'x','male':'y'})
        self.assertEqual(assign(chars,config),assign(chars,config))
        config['assignments']={'female':'y'}
        with self.assertRaises(ValueError): assign(chars,config)

    def test_faltam_prompts_cadastro_permitido_geracao_bloqueada(self):
        p=plan();p.update(prompt_sets={},assignments={})
        validate_plan(p)
        with self.assertRaises(ValueError): build_scenes(p)
        p=plan();p['prompt_sets']['audio_x']['prompts']=['only one']
        with self.assertRaises(ValueError): validate_plan(p)

    def test_nao_sorteia_voz_do_genero_errado_e_esgota_sem_travar(self):
        catalog=[{'name':'F1','gender':'female'},{'name':'F2','gender':'female'},{'name':'M1','gender':'male'},{'name':'U1','gender':'unknown'}]
        chars=[character('f1'),character('f2'),character('f3'),character('m','male')]
        voices=choose_voices(chars,catalog,seed=5)
        self.assertEqual(len({voices['f1'],voices['f2']}),2)
        self.assertIn(voices['f3'],('F1','F2'))
        self.assertEqual(voices['m'],'M1')
        again=choose_voices(chars,catalog,prior=voices,seed=999)
        self.assertEqual(voices,again)

    def test_recibo_incerto_nunca_volta_a_pending(self):
        s={'prompt':'exact','status':'submitting','attempts':[{'baseline':['old'],'started_at':100}]}
        reconcile(s,{'videos':[]},{'phase':'click_intent'},120,180)
        self.assertEqual(s['status'],'confirming')
        reconcile(s,{'videos':[]},{'phase':'submitted_ui'},400,180)
        self.assertEqual(s['status'],'uncertain')
        inv={'videos':[{'id':'new','prompt':'exact','model':'veo_3_1_r2v_lite_low_priority'}]}
        reconcile(s,inv,{'phase':'submitted_ui'},410,180)
        self.assertEqual((s['status'],s['video']),('rendering','new'))
        self.assertEqual(len(s['attempts']),1)

    def test_asset_removido_exige_rpc_5_ausencia_e_duas_consultas(self):
        scene={'video':'asset-A'};result={'rpc_code':5}
        self.assertFalse(missing_asset_failure(scene,result,{'asset_ids':['asset-A']},100))
        self.assertFalse(missing_asset_failure(scene,result,{'asset_ids':[]},100))
        self.assertFalse(missing_asset_failure(scene,result,{'asset_ids':[]},109))
        self.assertTrue(missing_asset_failure(scene,result,{'asset_ids':[]},110))
        self.assertFalse(missing_asset_failure(scene,{'rpc_code':7},{'asset_ids':[]},120))
        self.assertNotIn('missing_asset_since',scene)

    def test_reserva_incerta_conta_tentativas_distintas_e_expira(self):
        scenes={'scene-A':{'status':'uncertain','attempts':[{}]}}
        reservation={'old':{'scene':'scene-A','attempt':1,'expires_at':200}}
        self.assertEqual(reserved_generation_slots(scenes,reservation,100),1)
        scenes['scene-A']['attempts'].append({})
        self.assertEqual(reserved_generation_slots(scenes,reservation,100),2)
        scenes['scene-A']['status']='pending'
        self.assertEqual(reserved_generation_slots(scenes,reservation,100),1)
        self.assertEqual(reserved_generation_slots(scenes,reservation,201),0)

    def test_reserva_antiga_so_libera_apos_prazo_e_conferencia_dessa_tentativa(self):
        scene={'status':'uncertain','attempts':[{}]};scenes={'A':scene}
        scene['reservation_release']={'attempt':1,'expires_at':200,'absence_confirmed_at':210}
        self.assertEqual(reserved_generation_slots(scenes,{},209),1)
        self.assertEqual(reserved_generation_slots(scenes,{},210),0)
        self.assertEqual(scene['status'],'uncertain')
        scene['attempts'].append({})
        self.assertEqual(reserved_generation_slots(scenes,{},220),1)
        scene['reservation_release']={'attempt':2,'expires_at':300,'absence_confirmed_at':250}
        self.assertEqual(reserved_generation_slots(scenes,{},350),1)

    def test_id_ambiguo_ou_modelo_errado_nao_adotado(self):
        s={'prompt':'exact','status':'confirming','attempts':[{'baseline':['old'],'started_at':100}]}
        inv={'videos':[{'id':'new1','prompt':'exact','model':'veo_3_1_r2v_lite_low_priority'},{'id':'new2','prompt':'exact','model':'veo_3_1_r2v_lite_low_priority'}]}
        reconcile(s,inv,{},120,180)
        self.assertEqual(s['status'],'uncertain')
        inv['videos']=inv['videos'][:1];inv['videos'][0]['model']='expensive'
        reconcile(s,inv,{},120,180)
        self.assertEqual(s['reason'],'modelo_divergente')

    def test_mesmo_prompt_concorrente_separado_pelo_id_do_personagem(self):
        scene={'prompt':'same prompt','status':'uncertain','expected_character_id':'character-A','attempts':[{'baseline':[],'started_at':100}]}
        inv={'videos':[{'id':'video-B','prompt':'same prompt','refs':['character-B'],'model':'veo_3_1_r2v_lite_low_priority'},
                       {'id':'video-A','prompt':'same prompt','refs':['character-A'],'model':'veo_3_1_r2v_lite_low_priority'}]}
        reconcile(scene,inv,{'phase':'submitted_ui'},500,180)
        self.assertEqual((scene['status'],scene['video']),('rendering','video-A'))

    def test_estado_unicode_em_disco_e_fingerprint_de_prompts(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'ação.json'
            atomic(path,{'voice':'voz','name':'Personagem da cozinha — ação'})
            self.assertEqual(read(path)['name'],'Personagem da cozinha — ação')
            self.assertFalse(path.with_name(path.name+'.tmp').exists())
        p=plan();old=fingerprint(p);p['prompt_sets']['audio_x']['prompts'][0]='changed'
        self.assertNotEqual(fingerprint(p),old)

    def test_proibe_limites_invalidos_ou_rajada(self):
        for limits in ({'max_rendering':0},{'max_rendering':True},{'max_rendering':1.5},{'send_interval':0},{'generation_attempts':4}):
            p=plan();p['limits']=limits
            with self.assertRaises(ValueError): validate_plan(p)

    def test_vagas_configuraveis_e_sem_teto_preservam_plano_original(self):
        from core import operating_limits
        original=validate_plan(plan())
        for count in (5,None):
            p=plan();p['limits']={'max_rendering':count}
            self.assertEqual(validate_plan(p)['max_rendering'],count)
            self.assertEqual(operating_limits(original,{'max_rendering':count})['max_rendering'],count)
        self.assertEqual(original['max_rendering'],3)
        for count in (False,0,-1,1.5):
            with self.assertRaises(ValueError):operating_limits(original,{'max_rendering':count})

    def test_revisao_preserva_fala_exata(self):
        old='Fixed camera.\nSpoken audio only, not on-screen text:\n"The original sentence."'
        scene={'prompt':old,'spoken':'The original sentence.'}
        validate_revision(scene,'Adult woman, fixed camera.\nSpoken audio only, not on-screen text:\n"The original sentence."')
        for text in ('Adult woman.\nSpoken audio only, not on-screen text:\n"The changed sentence."',old):
            with self.assertRaises(ValueError): validate_revision(scene,text)

    def test_tres_tentativas_descarta_so_o_avatar_afetado(self):
        with tempfile.TemporaryDirectory() as folder,patch('notifier.notify') as notify:
            scene={'character':'one','status':'complete','attempts':[{}, {}, {}],'prompt':'x','spoken':'y','prompt_sha256':'hash'}
            state={'scenes':{'one_1':scene,'one_2':{'character':'one','status':'pending'},'two_1':{'character':'two','status':'pending'}}}
            request_review(Path(folder),state,'one_1','failed',{'generation_attempts':3})
            self.assertEqual(state['scenes']['one_1']['status'],'discarded')
            self.assertEqual(state['scenes']['one_2']['status'],'discarded')
            self.assertEqual(state['scenes']['two_1']['status'],'pending')
            notify.assert_not_called()

    def test_alerta_e_resposta_retomam_sem_alterar_fala(self):
        with tempfile.TemporaryDirectory() as folder,patch('notifier.notify') as notify:
            root=Path(folder)
            text='Fixed camera.\nSpoken audio only, not on-screen text:\n"Exact dialogue."'
            revised='Clearly adult woman, fixed camera.\nSpoken audio only, not on-screen text:\n"Exact dialogue."'
            scene={'character':'one','status':'failed','attempts':[{}],'prompt':text,'spoken':'Exact dialogue.','prompt_sha256':fingerprint(text),'video':'old'}
            state={'scenes':{'one_1':scene}}
            request_review(root,state,'one_1','failed',{'generation_attempts':3})
            self.assertEqual(scene['status'],'needs_review')
            notify.assert_called_once()
            source=root/'revision.txt';source.write_text(revised,encoding='utf-8')
            submit_review(root/'plan.json','one_1',source)
            apply_reviews(root,state)
            self.assertEqual(scene['status'],'pending')
            self.assertEqual(scene['spoken'],'Exact dialogue.')
            self.assertEqual(len(scene['attempts']),1)
            self.assertEqual(scene['attempts'][0]['outcome']['video'],'old')
            self.assertNotIn('video',scene)

    def test_controlador_baixa_confere_e_monta_sem_reenviar_concluidas(self):
        from controller import run
        from core import sha
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);p=plan()
            image=root/'portrait.png';image.write_bytes(b'portrait fixture')
            p['characters'][0].update(image=str(image),image_sha256=sha(image))
            p['output']=str(root/'delivery')
            path=root/'plano-personagens.json';atomic(path,p)
            atomic(root/'characters'/'avatar_01.json',{'phase':'ready','character_id':'character-A'})
            scenes=build_scenes(p)
            paths={}
            for index,(cid,s) in enumerate(scenes.items()):
                file=root/(cid+'.mp4');file.write_bytes(cid.encode());paths[cid]=file
                s.update(video='video'+str(index),sent_at=time.time()-30,attempts=[{'started_at':time.time()-30}])
                if index<3:
                    s['status']='rendering'
                else:
                    s.update(status='complete',file=str(file),sha256=sha(file),has_audio=True)
            atomic(root/'estado-personagens.json',{'plan_sha256':fingerprint(p),'scenes':scenes,'deliveries':{}})
            def fake_browser(plan_arg,root_arg,action,**kwargs):
                if action=='snapshot':return {'inventory':fake_browser(plan_arg,root_arg,'inventory'),'statuses':fake_browser(plan_arg,root_arg,'poll',videos=kwargs['videos']),'focused':kwargs.get('focus',False)}
                if action=='inventory': return {'asset_ids':[],'videos':[]}
                if action=='poll': return {cid:{'ready':True,'failed':False} for cid in kwargs['videos']}
                if action=='download':
                    file=paths[kwargs['cid']]
                    return {'ready':True,'file':str(file),'sha256':sha(file)}
                raise AssertionError('Ação não esperada: '+action)
            with patch('controller.controller_lock',return_value=contextlib.nullcontext()),patch('cli.register',return_value=0),patch('controller.browser',side_effect=fake_browser),patch('controller.probe',return_value={'streams':[{'codec_type':'audio'}]}),patch('qa.inspect',return_value={'issues':[]}),patch('controller.assemble',return_value={'file':'finished.mp4'}) as compose:
                self.assertEqual(run(path),0)
            compose.assert_called_once()
            self.assertEqual(compose.call_args.args[0],[str(paths[cid]) for cid in scenes])
            self.assertEqual(read(root/'estado-personagens.json')['status'],'complete')

    def test_reprovacao_visual_preserva_entrega_e_reabre_so_cena_afetada(self):
        from core import sha
        with tempfile.TemporaryDirectory() as folder,patch('notifier.notify'):
            root=Path(folder);p=plan();path=root/'plan.json';atomic(path,p)
            scenes=build_scenes(p);cid=next(iter(scenes))
            scenes[cid].update(status='complete',attempts=[{}])
            output=root/'avatar.mp4';output.write_bytes(b'previous montage')
            receipt={'file':str(output),'sha256':sha(output)}
            atomic(root/'estado-personagens.json',{'status':'complete','scenes':scenes,'deliveries':{'avatar_01':receipt}})
            with patch('controller.controller_lock',return_value=contextlib.nullcontext()):
                reject_quality(path,cid,'unwanted_caption')
            state=read(root/'estado-personagens.json')
            self.assertEqual(state['scenes'][cid]['status'],'needs_review')
            self.assertEqual(state['deliveries'],{})
            self.assertFalse(output.exists())
            self.assertEqual(Path(state['delivery_history'][0]['archived_file']).read_bytes(),b'previous montage')
            self.assertEqual(len(state['scenes'][cid]['attempts']),1)

    def test_repoe_tres_vagas_enquanto_qa_anterior_continua_em_paralelo(self):
        self._check_refill_cadence(25)

    def test_intervalo_zero_prepara_proximo_envio_sem_espera_programada(self):
        self._check_refill_cadence(0)

    def _check_refill_cadence(self,cadence):
        from controller import run
        from core import sha
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);p=plan();image=root/'portrait.png';image.write_bytes(b'portrait')
            p['characters'][0].update(image=str(image),image_sha256=sha(image));p['output']=str(root/'out')
            path=root/'plan.json';atomic(path,p)
            atomic(root/'characters'/'avatar_01.json',{'phase':'ready','voice':'Female1','character_id':'character-A'})
            scenes=build_scenes(p);ids=list(scenes);active=set(ids[:3]);submitted=[];replacement=threading.Event()
            assets=[];files={};events=[];deadlines=[];submitted_times=[]
            atomic(root/'operacao.json',{'submission_interval_seconds':cadence})
            for i,(cid,scene) in enumerate(scenes.items()):
                file=root/(cid+'.mp4');file.write_bytes(cid.encode());files[cid]=file
                if i<3:
                    scene.update(status='rendering',video=cid,sent_at=time.time()-30,attempts=[{'started_at':time.time()-30}])
                    assets.append({'id':cid,'prompt':scene['prompt'],'refs':['character-A'],'model':'veo_3_1_r2v_lite_low_priority'})
            atomic(root/'estado-personagens.json',{'plan_sha256':fingerprint(p),'scenes':scenes,'deliveries':{}})
            def fake_browser(_plan,_root,action,**kwargs):
                if action=='snapshot':return {'inventory':fake_browser(_plan,_root,'inventory'),'statuses':fake_browser(_plan,_root,'poll',videos=kwargs['videos']),'focused':kwargs.get('focus',False)}
                if action=='inventory': return {'asset_ids':[v['id'] for v in assets],'videos':list(assets)}
                if action=='focus': return {}
                if action=='download':
                    cid=kwargs['cid']
                    if cid==ids[0]:
                        events.append(('download_started',cid))
                        self.assertTrue(replacement.wait(3),'Download bloqueou o proximo envio')
                        events.append(('download_finished',cid))
                    return {'ready':True,'file':str(files[cid]),'sha256':sha(files[cid])}
                if action=='poll':
                    result={}
                    for cid in kwargs['videos']:
                        ready=cid==ids[0] or cid==ids[3] or len(submitted)==2
                        result[cid]={'ready':ready,'failed':False}
                        if ready: active.discard(cid)
                    return result
                raise AssertionError(action)
            class Native:
                pid=99999
                def __init__(self,command,**kwargs):
                    self.command=command
                    self.finished=False
                    deadlines.append(float(kwargs['env']['FLOW_SEND_NOT_BEFORE']))
                def poll(self):
                    return 0 if self.finished else None
                def wait(self,timeout):
                    receipt=Path(self.command[self.command.index('--recibo')+1])
                    # First attempts use native/CID; retry folders are not used in this test.
                    cid=receipt.parent.name
                    if len(active)>=3: raise AssertionError('Quarta geração simultânea')
                    active.add(cid);submitted.append(cid);events.append(('submit',cid,len(active)))
                    assets.append({'id':cid,'prompt':scenes[cid]['prompt'],'refs':['character-A'],'model':'veo_3_1_r2v_lite_low_priority'})
                    submitted_times.append(time.time())
                    atomic(receipt,{'phase':'submitted_ui','at':submitted_times[-1]+.5,'clicked_at':submitted_times[-1]});replacement.set();self.finished=True;return 0
            def fake_qa(cid,scene,_root):
                if cid==ids[0]:
                    self.assertTrue(replacement.wait(3),'QA bloqueou a reposição da vaga')
                    events.append(('qa_finished',cid))
                return {'issues':[],'has_audio':True}
            real_sleep=time.sleep
            with patch('controller.controller_lock',return_value=contextlib.nullcontext()),patch('cli.register',return_value=0),patch('controller.browser',side_effect=fake_browser),patch('controller.subprocess.Popen',side_effect=Native),patch('qa.inspect',side_effect=fake_qa),patch('controller.assemble',return_value={'file':'finished.mp4'}),patch('controller.time.sleep',side_effect=lambda seconds:real_sleep(min(seconds,.02))):
                self.assertEqual(run(path),0)
            self.assertEqual(submitted,ids[3:])
            self.assertAlmostEqual(deadlines[1],submitted_times[0]+cadence)
            self.assertTrue(all(e[2]<=3 for e in events if e[0]=='submit'))
            self.assertLess(next(i for i,e in enumerate(events) if e[0]=='submit'),next(i for i,e in enumerate(events) if e[0]=='qa_finished'))
            self.assertLess(next(i for i,e in enumerate(events) if e[0]=='submit'),next(i for i,e in enumerate(events) if e[0]=='download_finished'))


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg necessário')
class DeliveryTests(unittest.TestCase):
    def test_monta_cinco_cenas_40s_entrega_retomavel_e_nao_sobrescreve(self):
        with tempfile.TemporaryDirectory(prefix='personagens ação ') as folder:
            root=Path(folder);files=[]
            for index,color in enumerate(('red','green','blue','white','black')):
                target=root/f'{index}.mp4'
                command=['ffmpeg','-v','error','-f','lavfi','-i',f'color=c={color}:s=128x224:r=24:d=8']
                if index!=2: command+=['-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-shortest']
                command+=['-c:v','libx264','-threads','1','-pix_fmt','yuv420p','-t','8',str(target)]
                subprocess.run(command,check=True,capture_output=True,timeout=30)
                files.append(str(target))
            output=root/'outra pasta'/'avatar__audio__40s.mp4'
            receipt=assemble(files,output,root/'estado')
            self.assertEqual(receipt['silent_scenes'],[3])
            self.assertAlmostEqual(float(probe(output)['format']['duration']),40,places=1)
            self.assertEqual(assemble(files,output,root/'estado')['sha256'],receipt['sha256'])
            output.write_bytes(b'preserve altered output')
            with self.assertRaises(RuntimeError): assemble(files,output,root/'estado')
            self.assertEqual(output.read_bytes(),b'preserve altered output')


if __name__=='__main__': unittest.main(verbosity=2)
