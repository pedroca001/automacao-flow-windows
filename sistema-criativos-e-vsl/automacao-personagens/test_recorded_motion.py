import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
from recorded_motion import MotionLibrary,check_capture,click_paths,retarget,idle_path,action_category
from mouse_motion import SmoothMouse,send_motion_points


def capture(category='geral'):
    return {'schema':1,'category':category,'duration':10,
            'points':[[0,100,100],[.1,100,100],[.3,150,80],[.5,200,100],[.7,200,100],[10,200,100]],
            'clicks':[{'t':.6,'x':200,'y':100}]}


class RecordedMotionTests(unittest.TestCase):
    def test_envio_contem_curvas_exageradas_e_pousa_sem_ultrapassar_botao(self):
        library=Mock();library.movement.return_value=[((1000,900),.1),((100,-100),.1),((400,450),.1)]
        bounds=(200,200,700,650);end=(650,600)
        steps=send_motion_points((350,300),end,bounds,library)
        self.assertTrue(all(200<=x<=700 and 200<=y<=650 for (x,y),dt in steps))
        tail=[p for p,dt in steps[-8:]]
        self.assertTrue(all(y==600 and x<=650 for x,y in tail))
        self.assertEqual([x for x,y in tail],sorted(x for x,y in tail))
        self.assertEqual(tail[-1],end)
        library.movement.assert_called_once_with((350,300),(586,600),'enviar')

    def test_envio_recusa_alvo_fora_do_compositor(self):
        with self.assertRaises(ValueError):send_motion_points((300,300),(900,600),(200,200,700,650))

    def test_entrada_externa_e_suave_e_termina_dentro_do_compositor(self):
        steps=send_motion_points((100,300),(650,600),(200,200,700,650))
        self.assertLess(steps[0][0][0],200)
        first=next(i for i,((x,y),dt) in enumerate(steps) if 200<=x<=700 and 200<=y<=650)
        self.assertTrue(all(200<=x<=700 and 200<=y<=650 for (x,y),dt in steps[first:]))
        self.assertEqual(steps[-1][0],(650,600))

    def test_prazo_e_recibo_acontecem_imediatamente_antes_do_clique_real(self):
        events=[];raw=Mock();raw.click.side_effect=lambda **kwargs:events.append('click')
        mouse=SmoothMouse(raw,lambda:(0,0),Mock(),Mock())
        mouse.before_click=lambda:events.append('gate')
        mouse.click(coords=(10,20))
        self.assertEqual(events,['gate','click'])
        raw.click.assert_called_once_with(coords=(10,20))
        mouse.before_click=Mock(side_effect=RuntimeError('cancelado'))
        with self.assertRaises(RuntimeError):mouse.click(coords=(10,20))
        self.assertEqual(raw.click.call_count,1)

    def test_reproducao_nao_acumula_custo_nativo_em_cada_amostra(self):
        clock=[0.0];moved=[]
        def sleep(seconds):clock[0]+=seconds
        def move(point):moved.append(point);clock[0]+=.01
        library=Mock();library.movement.return_value=[((10,10),.05),((20,20),.05)]
        mouse=SmoothMouse(Mock(),lambda:(0,0),move,Mock(),library)
        with patch('mouse_motion.time.monotonic',side_effect=lambda:clock[0]),patch('mouse_motion.time.sleep',side_effect=sleep):
            mouse.move((20,20))
        self.assertAlmostEqual(clock[0],.11)
        self.assertEqual(moved,[(10,10),(20,20)])

    def test_trajeto_longo_acelera_sem_remover_amostras(self):
        path=[[0,0,0],[1,50,20],[2,100,0]]
        steps=retarget(path,(0,0),(200,0))
        self.assertEqual(len(steps),2)
        self.assertAlmostEqual(sum(dt for point,dt in steps),.65)
        self.assertGreater(steps[0][0][1],0)
        self.assertEqual(steps[-1][0],(200,0))

    def test_trajeto_gravado_mantem_curva_e_chega_no_novo_alvo(self):
        paths=click_paths(capture());self.assertEqual(len(paths),1)
        steps=retarget(paths[0],(500,500),(500,700))
        self.assertEqual(steps[-1][0],(500,700))
        self.assertGreater(steps[0][0][0],500)
        self.assertAlmostEqual(sum(dt for point,dt in steps),.4)

    def test_cinco_versoes_alternam_entre_processos_e_categorias(self):
        with tempfile.TemporaryDirectory() as folder:
            for i in range(5):MotionLibrary(folder).save(capture())
            versions=[MotionLibrary(folder).select(c)[2] for c in ('texto','enviar','configuracao','espera','geral','texto')]
            self.assertEqual(versions,[1,2,3,4,5,1])

    def test_limite_cinco_e_refazer_preserva_historico(self):
        with tempfile.TemporaryDirectory() as folder:
            library=MotionLibrary(folder)
            for i in range(5):library.save(capture())
            with self.assertRaises(ValueError):library.save(capture())
            library.redo_last('geral');self.assertEqual(len(library.captures('geral')),4)
            self.assertEqual(len(list((Path(folder)/'_historico').glob('*.json'))),1)
            self.assertEqual(library.save(capture()),5)

    def test_reproducao_apenas_move_sem_repetir_cliques_gravados(self):
        with tempfile.TemporaryDirectory() as folder:
            library=MotionLibrary(folder);library.save(capture())
            raw=Mock();moved=[];stop=Mock()
            mouse=SmoothMouse(raw,lambda:(500,500),moved.append,stop,library)
            mouse.category='enviar'
            with patch('mouse_motion.time.sleep'):mouse.move((700,500))
            self.assertEqual(moved[-1],(700,500));raw.click.assert_not_called()
            self.assertEqual(stop.call_count,len(moved))

    def test_espera_adapta_na_area_sem_sair_dos_limites(self):
        result=idle_path(capture('espera'),(300,400,600,700))
        self.assertTrue(all(300<=x<=600 and 400<=y<=700 for (x,y),dt in result))
        self.assertAlmostEqual(sum(dt for point,dt in result),10)

    def test_recusa_dados_invalidos_e_caminho_fora_da_biblioteca(self):
        invalid=copy.deepcopy(capture());invalid['points'][1][1]=float('nan')
        with self.assertRaises(ValueError):check_capture(invalid)
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):MotionLibrary(folder)._file('../fora.json')

    def test_categoria_especifica_prevalece_e_sem_gravacao_retorna_none(self):
        with tempfile.TemporaryDirectory() as folder:
            library=MotionLibrary(folder);self.assertIsNone(library.select('enviar'))
            library.save(capture());library.save(capture('enviar'))
            self.assertEqual(library.select('enviar')[0]['category'],'enviar')
        self.assertEqual(action_category('Iniciar geração','Button'),'enviar')
        self.assertEqual(action_category('O que você quer criar?','Edit'),'texto')
        self.assertEqual(action_category('9:16','RadioButton'),'configuracao')


if __name__=='__main__':unittest.main()
