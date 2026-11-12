import unittest
from gravar_movimentos import recorder_url_matches


class RecorderTests(unittest.TestCase):
    def test_gravador_aceita_telas_internas_e_parametros_do_mesmo_projeto(self):
        root='https://flow.google.com/u/1/project/abc'
        for suffix in ('','/','?selected=video','/character/example?tab=portrait','#assets'):
            self.assertTrue(recorder_url_matches(root+suffix,root))
        for other in (root.replace('/u/1/','/u/2/'),root.replace('/abc','/abcd'),root.replace('flow.google.com','flow.google.com.evil.test')):
            self.assertFalse(recorder_url_matches(other,root))


if __name__=='__main__':unittest.main()
