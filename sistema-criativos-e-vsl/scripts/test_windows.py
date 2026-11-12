"""Platform regressions. No Flow requests, uploads or video generation."""
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from flow_platform import BASE, WINDOWS, filter_path, locks, macro_processes, process_options, terminate_tree
from flow_macro_windows import journal, options, valid_url


class PortTests(unittest.TestCase):
    def test_project_and_host_are_exact(self):
        project = '12345678-1234-1234-1234-123456789abc'
        for prefix in ('', '/u/0', '/u/2'):
            self.assertTrue(valid_url('https://flow.google.com' + prefix + '/project/' + project, project))
        self.assertFalse(valid_url('https://flow.google.com.evil.test/project/' + project))
        self.assertFalse(valid_url('https://flow.google.com/project/'))
        self.assertFalse(valid_url('https://flow.google.com/project/other', project))

    def test_macro_rejects_conflicting_modes_and_paths(self):
        with contextlib.redirect_stderr(__import__('io').StringIO()):
            for args in (['--preparar', '--configurar'], ['--prompt', 'x', '--inspecionar'],
                         ['--prompt', 'x', '--elemento', '../image.png'], ['--prompt', 'x\tbad']):
                with self.assertRaises(SystemExit):
                    options(args)
        self.assertEqual(options(['--prompt', 'ação\nreceita', '--preparar']).prompt, 'ação\nreceita')

    def test_receipt_is_persistent_before_click(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'receipt.json'
            args = options(['--prompt', 'teste', '--recibo', str(path)])
            journal(args, 'click_intent')
            self.assertEqual(json.loads(path.read_text())['phase'], 'click_intent')
            self.assertFalse(path.with_suffix('.tmp').exists())

    def test_lock_blocks_a_second_process_and_releases_on_close(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'lane.lock'
            code = ('from flow_platform import locks\nimport sys\n'
                    'with open(sys.argv[1], "a") as f:\n locks.flock(f, locks.LOCK_EX | locks.LOCK_NB)\n')
            with path.open('a') as handle:
                locks.flock(handle, locks.LOCK_EX | locks.LOCK_NB)
                result = subprocess.run([sys.executable, '-c', code, str(path)], capture_output=True, timeout=10)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'BlockingIOError', result.stderr)
            result = subprocess.run([sys.executable, '-c', code, str(path)], capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(WINDOWS, 'Windows process flags')
    def test_detached_process_survives_its_launcher(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'complete.txt'
            child = 'import time,pathlib;time.sleep(.3);pathlib.Path(' + repr(str(output)) + ').write_text("done")'
            parent = 'import subprocess,sys;from flow_platform import process_options;subprocess.Popen([sys.executable,"-c",' + repr(child) + '],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,**process_options(detached=True))'
            subprocess.run([sys.executable, '-c', parent], check=True, timeout=10)
            import time
            end = time.monotonic() + 10
            while not output.exists() and time.monotonic() < end:
                time.sleep(.05)
            self.assertEqual(output.read_text(), 'done')

    def test_process_identity_and_termination(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / 'fake_macro.py'
            script.write_text('import time; time.sleep(60)')
            process = subprocess.Popen([sys.executable, str(script), '--arquivo', 'unique_prompt.txt'], **process_options())
            try:
                self.assertIn(process.pid, macro_processes(script, 'unique_prompt.txt'))
                self.assertFalse(macro_processes(script, 'other_prompt.txt'))
                terminate_tree(process.pid)
                process.wait(timeout=10)
            finally:
                if process.poll() is None:
                    process.kill()

    def test_ass_filter_accepts_windows_drive_spaces_and_accents(self):
        with tempfile.TemporaryDirectory(prefix='flow ação ') as directory:
            ass = Path(directory) / 'legenda ação.ass'
            ass.write_text('[Script Info]\nScriptType: v4.00+\nPlayResX: 320\nPlayResY: 240\n'
                           '[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n'
                           'Style: Default,Arial,24,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1,0,2,10,10,10,1\n'
                           '[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'
                           'Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,Teste de ação\n', encoding='utf-8')
            result = subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=s=320x240:d=1',
                                     '-vf', 'ass=' + filter_path(ass), '-f', 'null', '-'], capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))

    @unittest.skipUnless(shutil.which('whisper-cli') and Path(os.environ.get('WHISPER_MODEL', '')).is_file(), 'Whisper/model not installed')
    def test_whisper_loads_model_and_transcribes_local_wav(self):
        with tempfile.TemporaryDirectory() as directory:
            wav = Path(directory) / 'silencio.wav'
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=16000:cl=mono', '-t', '1', str(wav)], check=True, timeout=15)
            result = subprocess.run(['whisper-cli', '-m', os.environ['WHISPER_MODEL'], '-f', str(wav), '-nt'], capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace')[-1500:])

    @unittest.skipUnless((Path(os.environ.get('RVM_DIR', '')) / 'rvm_mobilenetv3.pth').is_file(), 'Optional RVM not installed')
    def test_rvm_loads_model_and_exports_local_video(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory) / 'in.mp4', Path(directory) / 'out.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=s=128x128:r=2:d=1', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(source)], check=True, timeout=15)
            result = subprocess.run([sys.executable, str(BASE / '02-VSL/scripts-referencia/rvm_matte.py'), str(source), str(target)], capture_output=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace')[-1500:])
            self.assertTrue(target.is_file())
            subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(target), '-f', 'null', '-'], check=True, timeout=15)


if __name__ == '__main__':
    unittest.main(verbosity=2)
