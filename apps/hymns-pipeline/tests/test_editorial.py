from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from hymns_pipeline.editorial import head, mutate, load_revision, edit_lock
from hymns_pipeline.storage import DATA, read_json


def payload(number=464):
    return dict(number=number, title='Novo Hino', sections=[dict(type='verse', number=1, lines=['Verso'])])


class EditorialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name)/'data'; shutil.copytree(DATA, self.data)

    def test_crud_and_replay_preserve_ids(self):
        created = mutate('create', payload=payload(), reason='Create', data=self.data)
        self.assertRegex(created['id'], r'^[a-f0-9-]{36}$')
        changed = mutate('update', hymn_id='145', payload={'title':'Corrected', 'number':465}, reason='Renumber', data=self.data)
        self.assertEqual(changed['after']['id'], '145')
        self.assertIn('Links', changed['warning'])
        deleted = mutate('delete', hymn_id=created['id'], reason='Remove', data=self.data)
        record = load_revision(deleted['revision'], self.data)
        self.assertIn(created['id'], record['retiredIds'])
        self.assertEqual(len(record['hymns']), 236)
        self.assertEqual(next(h for h in record['hymns'] if h['id']=='145')['number'],465)

    def test_invalid_operations_do_not_create_revisions(self):
        for kind, options in [
            ('create', {'payload':payload(145)}),
            ('create', {'payload':payload(70000)}),
            ('update', {'hymn_id':'missing','payload':{'title':'x'}}),
            ('update', {'hymn_id':'145','payload':{'title':'Rocha Eterna'}}),
            ('delete', {'hymn_id':'missing'}),
            ('create', {'payload':payload(), 'reason':''}),
        ]:
            with self.subTest(kind=kind, options=options), self.assertRaises(Exception):
                mutate(kind, reason=options.pop('reason','Test'), data=self.data, **options)
            self.assertFalse((self.data/'editorial/revisions').exists())

    def test_number_conflict_and_deleted_target_rejected(self):
        first=mutate('delete',hymn_id='145',reason='Delete',data=self.data)
        for kind,opts in [('delete',{}),('update',{'payload':{'title':'x'}})]:
            with self.assertRaises(ValueError):mutate(kind,hymn_id='145',reason='Again',data=self.data,**opts)
        self.assertEqual(head(self.data)[0],first['revision'])
        with self.assertRaises(ValueError):mutate('update',hymn_id='146',payload={'number':149},reason='Conflict',data=self.data)

    def test_head_lock_and_tampering(self):
        with edit_lock(self.data), self.assertRaises(ValueError):
            mutate('create',payload=payload(),reason='Concurrent',data=self.data)
        result=mutate('create',payload=payload(),reason='Create',data=self.data)
        path=self.data/'editorial/revisions'/result['revision']/'revision.json'
        path.write_text(path.read_text().replace('Novo Hino','Tampered'))
        with self.assertRaises(ValueError):load_revision(result['revision'],self.data)

    def test_cli_file_and_flags_and_log_privacy(self):
        import json, subprocess
        app=Path(__file__).resolve().parents[1]
        patch=self.data/'patch.json';patch.write_text(json.dumps({'sections':payload()['sections']}))
        command=[sys.executable,str(app/'run.py'),'--data-dir',str(self.data),'update','--id','145',
                 '--title','PRIVATE_TITLE','--file',str(patch),'--reason','PRIVATE_REASON']
        result=subprocess.run(command,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['after']['title'],'PRIVATE_TITLE')
        self.assertNotIn('PRIVATE',result.stderr)
        patch.write_text(json.dumps({'title':'FILE_TITLE'}))
        before=head(self.data)[0]
        result=subprocess.run(command,capture_output=True,text=True)
        self.assertEqual(result.returncode,1)
        self.assertEqual(head(self.data)[0],before)
