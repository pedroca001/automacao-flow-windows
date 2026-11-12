from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from noturno_adapter import Adapter


class RefreshPreparationTests(unittest.TestCase):
    def test_ratio_popup_preparation_retries_once_without_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = Adapter(Path(directory), {'project': 'project'}, {'min_free_gb': 0, 'native_timeout': 240})
            adapter.inventory = Mock()
            adapter.background = Mock()
            failed = SimpleNamespace(returncode=2, stderr='ERRO: Controle não encontrado: 9:16. A interface pode ter mudado.', stdout='')
            ready = SimpleNamespace(returncode=0, stderr='', stdout='0 créditos')
            with patch('shutil.which', return_value='installed'), \
                 patch('noturno_adapter.subprocess.run', side_effect=[failed, ready]) as run, \
                 patch('noturno_adapter.time.sleep'):
                adapter.preflight()
                self.assertEqual(run.call_count, 2)
                self.assertTrue(all('--configurar' in call.args[0] for call in run.call_args_list))
                self.assertTrue(all('--arquivo' not in call.args[0] for call in run.call_args_list))

    def test_service_and_credit_errors_are_never_retried(self):
        for message in ('Notamos uma atividade incomum.', 'Créditos diferentes de zero.', 'Interrompido por Esc.'):
            with self.subTest(message=message), tempfile.TemporaryDirectory() as directory:
                adapter = Adapter(Path(directory), {'project': 'project'}, {'min_free_gb': 0, 'native_timeout': 240})
                adapter.inventory = Mock()
                adapter.background = Mock()
                failed = SimpleNamespace(returncode=2, stderr=message, stdout='')
                with patch('shutil.which', return_value='installed'), patch('noturno_adapter.subprocess.run', return_value=failed) as run:
                    with self.assertRaises(RuntimeError):
                        adapter.preflight()
                    self.assertEqual(run.call_count, 1)


if __name__ == '__main__':
    unittest.main()
