import os
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
from macro_personagens import CharacterMacro


class SendTargetTests(unittest.TestCase):
    def test_sem_teto_aguarda_botao_ser_liberado_pelo_flow(self):
        macro,node=self.macro();node.is_enabled.side_effect=[False,False,False,True,True,True]
        with patch.dict(os.environ,{'FLOW_SEND_NOT_BEFORE':'0','FLOW_WAIT_FOR_GENERATION_CAPACITY':'1'}),patch('macro_personagens.journal'):
            macro.send_click(node)
        macro.mouse.click.assert_called_once_with(coords=(500,600))

    def test_botao_continua_bloqueado_nao_dispara_envio(self):
        macro,node=self.macro();node.is_enabled.return_value=False
        with patch.dict(os.environ,{'FLOW_WAIT_FOR_GENERATION_CAPACITY':'1'}),patch('macro_personagens.time.monotonic',side_effect=[0,121]),patch('macro_personagens.journal') as journal:
            with self.assertRaises(RuntimeError):macro.send_click(node)
        macro.mouse.click.assert_not_called();journal.assert_not_called()

    def macro(self):
        macro=CharacterMacro.__new__(CharacterMacro)
        point=SimpleNamespace(x=500,y=600)
        rect=SimpleNamespace(mid_point=lambda:point)
        node=Mock();node.rectangle.return_value=rect;node.is_enabled.return_value=True
        macro.window=Mock();macro.window.rectangle.return_value=SimpleNamespace(left=0,top=0,right=1000,bottom=1000)
        macro.original_url='project';macro.url=Mock(return_value='project')
        macro.stop=Mock();macro.key=Mock();macro.pause=Mock();macro.mouse=Mock()
        macro.verify_send_target=Mock();macro.args=SimpleNamespace()
        macro.send_bounds=Mock(return_value=(100,100,800,700))
        return macro,node

    def test_tooltip_fechado_e_alvo_conferido_antes_do_unico_clique(self):
        macro,node=self.macro();events=[]
        macro.mouse.move.side_effect=lambda **kw:events.append('move')
        macro.key.side_effect=lambda key:events.append(key)
        macro.verify_send_target.side_effect=lambda *a:events.append('verify')
        macro.mouse.click.side_effect=lambda **kw:events.append('click')
        with patch.dict(os.environ,{'FLOW_SEND_NOT_BEFORE':'0'}),patch('macro_personagens.journal',side_effect=lambda *a:events.append('receipt')):
            macro.send_click(node)
        self.assertEqual(events,['move','{ESC}','verify','receipt','click'])
        macro.mouse.click.assert_called_once_with(coords=(500,600))

    def test_alvo_coberto_cancela_sem_recibo_de_envio_nem_clique(self):
        macro,node=self.macro();macro.verify_send_target.side_effect=RuntimeError('alvo coberto')
        with patch.dict(os.environ,{'FLOW_SEND_NOT_BEFORE':'0'}),patch('macro_personagens.journal') as journal:
            with self.assertRaisesRegex(RuntimeError,'alvo coberto'):macro.send_click(node)
        journal.assert_not_called();macro.mouse.click.assert_not_called()

    def test_limites_usam_painel_do_compositor_e_nao_documento_inteiro(self):
        macro,node=self.macro()
        def rect(l,t,r,b):return SimpleNamespace(left=l,top=t,right=r,bottom=b,
            width=lambda:r-l,height=lambda:b-t,mid_point=lambda:SimpleNamespace(x=(l+r)//2,y=(t+b)//2))
        macro.window.rectangle.return_value=rect(0,0,1000,1000)
        editor=Mock();editor.rectangle.return_value=rect(150,150,550,450)
        panel=Mock();panel.rectangle.return_value=rect(100,100,800,700)
        editor.parent.return_value=panel;macro.editor=Mock(return_value=editor)
        self.assertEqual(CharacterMacro.send_bounds(macro,node),(124,124,776,676))


if __name__=='__main__':unittest.main()
