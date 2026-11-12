"""State replacement survives transient Windows sharing violations."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import noturno_core


@unittest.skipUnless(os.name == 'nt', 'Windows sharing semantics')
class AtomicWindowsTests(unittest.TestCase):
    def denied(self):
        error = PermissionError('destination is briefly open by a reader')
        error.winerror = 5
        return error

    def test_retries_replacement_without_exposing_partial_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'state.json'
            noturno_core.atomic(target, {'version': 1})
            original_replace = os.replace
            calls = []
            def replace(source, destination):
                calls.append(1)
                self.assertEqual(json.loads(target.read_text()), {'version': 1})
                if len(calls) <= 3:
                    raise self.denied()
                return original_replace(source, destination)
            with patch.object(noturno_core.os, 'replace', side_effect=replace), patch.object(noturno_core.time, 'sleep'):
                noturno_core.atomic(target, {'version': 2})
            self.assertEqual(len(calls), 4)
            self.assertEqual(json.loads(target.read_text()), {'version': 2})

    def test_persistent_failure_preserves_old_state_and_flushed_temporary(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'state.json'
            noturno_core.atomic(target, {'version': 1})
            with patch.object(noturno_core.os, 'replace', side_effect=self.denied()) as replace, patch.object(noturno_core.time, 'sleep'):
                with self.assertRaises(PermissionError):
                    noturno_core.atomic(target, {'version': 2})
            self.assertEqual(replace.call_count, 16)
            self.assertEqual(json.loads(target.read_text()), {'version': 1})
            self.assertEqual(json.loads((Path(tmp) / 'state.json.tmp').read_text()), {'version': 2})


if __name__ == '__main__':
    unittest.main()
