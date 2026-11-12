import unittest
from noturno_adapter import native_outcome


class ActivityHoldTests(unittest.TestCase):
    def test_warning_after_click_preserves_submission_and_stops_queue(self):
        result = native_outcome('ERRO: Flow: Notamos uma atividade incomum.', {'phase': 'submitted_ui'})
        self.assertTrue(result['clicked'])
        self.assertEqual(result['global_error'], 'atividade_incomum')

    def test_warning_before_click_never_becomes_retryable_preparation(self):
        result = native_outcome('Flow: Notamos uma atividade incomum.', {'phase': 'preparing'})
        self.assertFalse(result['clicked'])
        self.assertEqual(result['global_error'], 'atividade_incomum')


if __name__ == '__main__':
    unittest.main()
