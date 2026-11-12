"""Only the observed release-notes notice can be automatically dismissed."""
from types import SimpleNamespace
import unittest
from flow_macro_windows import Macro


def node(name, kind='Text'):
    return SimpleNamespace(element_info=SimpleNamespace(name=name, control_type=kind))


class NoticeTests(unittest.TestCase):
    def make_macro(self):
        macro = Macro.__new__(Macro)
        macro.clicked = []
        macro.click = macro.clicked.append
        macro.pause = lambda seconds: None
        macro.stop = lambda: None
        return macro

    def notice(self):
        return [node('O que há de novo'), node('Ver todos os registros de alterações', 'Button'), node('Começar', 'Button')]

    def test_only_exact_observed_notice_is_dismissed(self):
        macro = self.make_macro()
        notice = self.notice()
        self.assertTrue(macro.dismiss_product_notice(notice))
        self.assertEqual(macro.clicked, [notice[-1]])
        macro.clicked.clear()
        self.assertFalse(macro.dismiss_product_notice([node('Começar', 'Button')]))
        self.assertEqual(macro.clicked, [])

    def test_legal_agreement_is_never_accepted(self):
        macro = self.make_macro()
        with self.assertRaisesRegex(RuntimeError, 'acordo'):
            macro.dismiss_product_notice(self.notice() + [node('Concordo com os termos de uso')])
        self.assertEqual(macro.clicked, [])

    def test_find_recovers_editor_after_notice(self):
        macro = self.make_macro()
        notice = self.notice()
        editor = node('O que você quer criar?', 'Edit')
        macro.nodes = lambda: [editor] if macro.clicked else notice
        self.assertIs(macro.find('O que você quer criar?', ('Edit',)), editor)
        self.assertEqual(macro.clicked, [notice[-1]])

    def test_notice_clicks_are_bounded(self):
        macro = self.make_macro()
        notice = self.notice()
        for _ in range(3):
            self.assertTrue(macro.dismiss_product_notice(notice))
        with self.assertRaisesRegex(RuntimeError, 'três'):
            macro.dismiss_product_notice(notice)
        self.assertEqual(len(macro.clicked), 3)

    def test_unusual_activity_stops_before_any_control_click(self):
        macro = self.make_macro()
        editor = node('O que voc\u00ea quer criar?', 'Edit')
        macro.nodes = lambda: [editor, node('Notamos uma atividade incomum. Aguarde alguns instantes')]
        with self.assertRaisesRegex(RuntimeError, 'atividade incomum'):
            macro.find('O que voc\u00ea quer criar?', ('Edit',))
        self.assertEqual(macro.clicked, [])

    def test_general_flow_accuracy_notice_does_not_stop(self):
        macro = self.make_macro()
        macro.guard_activity([node('O Google Flow pode cometer erros. Por isso, \u00e9 bom checar as respostas.')])
        self.assertEqual(macro.clicked, [])


if __name__ == '__main__':
    unittest.main()
