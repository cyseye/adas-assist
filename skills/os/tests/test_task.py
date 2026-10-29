"""Task transitions, drift, isolation and atomic-write failure tests; no models run."""
import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('task', ROOT / 'scripts/task.py')
task = importlib.util.module_from_spec(spec); spec.loader.exec_module(task)


class TaskTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'code.txt').write_text('implementation')
        (self.root / 'check.txt').write_text('test output')
        (self.root / 'review.txt').write_text('review output')

    def tearDown(self): self.temp.cleanup()

    def run_task(self, command, **kwargs):
        values = dict(project=self.root, command=command, slug='demo', goal='deliver', mode='managed',
                      accept=['R1=works'], input=['code.txt'], independent_review=False, next='implement')
        values.update(kwargs)
        return task.operate(argparse.Namespace(**values))

    @property
    def state(self): return self.root / '.adas-assist/tasks/demo/task.json'

    def prepare(self, independent=False):
        self.run_task('init', independent_review=independent); self.run_task('start')

    def record(self, result='passed'):
        return self.run_task('record', criterion='R1', evidence=['check.txt'], result=result,
                             kind='executed', summary='declared command result')

    def test_full_task_lifecycle_and_terminal_guard(self):
        self.prepare(); self.record()
        self.assertEqual('done', self.run_task('finish')['state'])
        before = self.state.read_bytes()
        with self.assertRaises(ValueError): self.run_task('record', criterion='R1', evidence=['check.txt'])
        self.assertEqual(before, self.state.read_bytes())
        self.assertEqual('active',self.run_task('reopen', reason='new changes', next='revalidate')['state'])

    def test_missing_failed_and_unrun_evidence_block_finish(self):
        self.prepare()
        for result in (None, 'failed', 'not_run'):
            if result: self.record(result)
            before = self.state.read_bytes()
            with self.assertRaises(ValueError): self.run_task('finish')
            self.assertEqual(before, self.state.read_bytes())

    def test_evidence_drift_blocks_finish(self):
        self.prepare(); self.record(); (self.root / 'check.txt').write_text('changed')
        self.assertIn('R1', self.run_task('status')['issues'])
        with self.assertRaises(ValueError): self.run_task('finish')

    def test_input_drift_blocks_finish_and_refresh_restores(self):
        self.prepare(); self.record(); (self.root / 'code.txt').write_text('new implementation')
        with self.assertRaises(ValueError): self.run_task('finish')
        self.record(); self.assertEqual('done',self.run_task('finish')['state'])

    def test_independent_review_requires_current_declaration(self):
        self.prepare(True); self.record()
        with self.assertRaises(ValueError): self.run_task('finish')
        self.run_task('review', evidence=['review.txt'], summary='declared independent review',
                      reviewer='external reviewer', verdict='changes_required')
        with self.assertRaises(ValueError): self.run_task('finish')
        self.run_task('review', evidence=['review.txt'], summary='declared independent review',
                      reviewer='external reviewer', verdict='passed')
        self.assertEqual('done',self.run_task('finish')['state'])
        (self.root / 'code.txt').write_text('drift after completion')
        self.assertFalse(self.run_task('status')['ready_to_finish'])

    def test_block_resume_cancel_reasons(self):
        self.prepare()
        self.assertEqual('blocked',self.run_task('block',reason='missing dependency',next='obtain input')['state'])
        with self.assertRaises(ValueError): self.run_task('finish')
        self.assertEqual('active',self.run_task('resume',reason='dependency ready',next='implement')['state'])
        self.assertEqual('cancelled',self.run_task('cancel',reason='user cancelled')['state'])
        with self.assertRaises(ValueError): self.run_task('start')

    def test_status_is_read_only_and_init_never_overwrites(self):
        with self.assertRaises(FileNotFoundError): self.run_task('status')
        self.assertFalse((self.root / '.adas-assist').exists())
        self.prepare(); before=self.state.read_bytes()
        self.run_task('status'); self.assertEqual(before,self.state.read_bytes())
        with self.assertRaises(ValueError): self.run_task('init')
        self.assertEqual(before,self.state.read_bytes())

    def test_unsupported_stored_mode_is_readable_but_never_mutated(self):
        self.prepare(); self.record()
        data = json.loads(self.state.read_text())
        data['mode'] = 'retired-mode'
        self.state.write_text(json.dumps(data))
        before = self.state.read_bytes()
        result = self.run_task('status')
        self.assertIn('mode', result['issues'])
        self.assertFalse(result['ready_to_finish'])
        for command in ('start', 'finish', 'record'):
            with self.assertRaisesRegex(ValueError, 'unsupported task mode'):
                self.run_task(command, criterion='R1', evidence=['check.txt'],
                              result='passed', kind='executed', summary='x')
            self.assertEqual(before, self.state.read_bytes())

    def test_read_only_mode_compatibility_still_rejects_malformed_data(self):
        self.prepare()
        data = json.loads(self.state.read_text())
        for mode in ('', '../escape', [], None):
            data['mode'] = mode
            self.state.write_text(json.dumps(data))
            before = self.state.read_bytes()
            with self.assertRaises(ValueError): self.run_task('status')
            self.assertEqual(before, self.state.read_bytes())

    def test_evidence_escape_and_symlink_rejected(self):
        self.prepare()
        for path in ('../check.txt', '/absolute.txt'):
            with self.assertRaises(ValueError):
                self.run_task('record',criterion='R1',evidence=[path],result='passed',kind='static',summary='x')
        (self.root / 'linked.txt').symlink_to(self.root / 'check.txt')
        with self.assertRaises(ValueError):
            self.run_task('record',criterion='R1',evidence=['linked.txt'],result='passed',kind='static',summary='x')

    def test_lock_contention_preserves_state(self):
        self.prepare(); before=self.state.read_bytes()
        lock=self.state.with_suffix('.lock');lock.write_text('another writer')
        with self.assertRaises(ValueError): self.record()
        self.assertEqual(before,self.state.read_bytes());self.assertEqual('another writer',lock.read_text())

    def test_failed_atomic_write_preserves_state_and_cleans_lock(self):
        self.prepare();before=self.state.read_bytes()
        with patch.object(task.os,'replace',side_effect=OSError('injected disk failure')):
            with self.assertRaises(OSError): self.record()
        self.assertEqual(before,self.state.read_bytes())
        self.assertFalse(self.state.with_suffix('.lock').exists())
        self.assertEqual([],list(self.state.parent.glob('.task-*')))

    def test_resume_validation_error_does_not_change_state(self):
        self.prepare();self.record()
        self.run_task('block',reason='dependency',next='wait')
        before=self.state.read_bytes()
        code=self.root/'code.txt';code.unlink();code.mkdir()
        with self.assertRaises(ValueError):self.run_task('resume',reason='retry',next='verify')
        self.assertEqual(before,self.state.read_bytes())
        self.assertFalse(self.state.with_suffix('.lock').exists())

    def test_manual_task_state_is_not_duplicated(self):
        folder=self.root/'.adas-assist/tasks/demo';folder.mkdir(parents=True)
        (folder/'TASK.md').write_text('existing manual task')
        with self.assertRaises(ValueError):self.run_task('init')
        self.assertFalse(self.state.exists())

    def test_invalid_schema_and_duplicate_criteria_rejected(self):
        with self.assertRaises(ValueError): self.run_task('init',accept=['R1=x','R1=y'])
        self.assertFalse(self.state.exists())
        self.prepare();data=json.loads(self.state.read_text());data['state']='fake';self.state.write_text(json.dumps(data))
        with self.assertRaises(ValueError):self.run_task('status')


if __name__ == '__main__': unittest.main()
