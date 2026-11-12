import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from core import atomic,read
from notifier import notify


class NotifierTests(unittest.TestCase):
    def test_desativar_global_impede_envio_e_preserva_evento_local(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);settings=root/'global.json'
            atomic(settings,{'enabled':False})
            atomic(root/'notificacao.json',{'thread':'example-thread','enabled':True})
            with patch('notifier.SETTINGS',settings),patch('notifier.subprocess.run') as run:
                result=notify(root,{'scene':'one','attempt':1,'reason':'sem_audio'})
            run.assert_not_called()
            self.assertFalse(result['notification']['queued'])
            self.assertEqual(result['notification']['reason'],'alertas_automaticos_desativados')
            self.assertEqual(read(root/'alertas/one__tentativa_01.json')['reason'],'sem_audio')


if __name__=='__main__':unittest.main()
