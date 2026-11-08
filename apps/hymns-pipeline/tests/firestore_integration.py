"""Destructive tests only in a fresh loopback Firestore emulator and a demo project."""
from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from editorial_fixtures import copy_baseline
from hymns_pipeline.editorial import mutate,release_revision
from hymns_pipeline.firestore import Firestore,publish,PublicationError,to_value
from hymns_pipeline.layers import load_gold
from hymns_pipeline.remote import publication_baseline,read_remote,reconciliation_report,reconcile_remote
from hymns_pipeline.seed import export_seed
from hymns_pipeline.storage import digest

PROJECT='demo-hinario-idc'


class FirestoreIntegration(unittest.TestCase):
    def test_full_editorial_lifecycle(self):
        self.assertTrue(os.environ.get('FIRESTORE_EMULATOR_HOST'),'Run via firebase emulators:exec')
        client=Firestore(PROJECT)
        metadata,existing=client.snapshot()
        self.assertIsNone(metadata,'Integration test requires an empty demo project')
        self.assertEqual(existing,{},'Refusing to modify existing emulator data')
        try:
            with tempfile.TemporaryDirectory() as temp:
                data=copy_baseline(Path(temp)/'data')
                release,manifest=load_gold(3,data)
                baseline=publication_baseline(release,manifest,PROJECT,data)
                publish(release,manifest,PROJECT,0,client=client,baseline=baseline)
                mutate('update',hymn_id='145',payload={'number':464},reason='Integration renumber',data=data)
                added=mutate('create',payload=dict(number=465,title='Integration fixture',sections=[dict(type='verse',number=1,lines=['Fixture verse'])]),reason='Integration create',data=data)
                deleted=mutate('delete',hymn_id='445',reason='Integration removal',data=data)
                release_revision(deleted['revision'],4,'2026-11-08T00:00:00Z',data)
                release,manifest=load_gold(4,data)
                with patch('hymns_pipeline.seed.SEED',Path(temp)/'seed.ts'):
                    export_seed(release);export_seed(release,check=True)
                baseline=publication_baseline(release,manifest,PROJECT,data)
                before=digest(client.snapshot())
                publish(release,manifest,PROJECT,3,True,client,baseline=baseline)
                self.assertEqual(digest(client.snapshot()),before,'Dry-run must not write')
                publish(release,manifest,PROJECT,3,client=client,baseline=baseline)
                self.assertEqual(read_remote(PROJECT,'145',client)['data']['number'],464)
                self.assertEqual(read_remote(PROJECT,added['id'],client)['data']['title'],'Integration fixture')
                self.assertTrue(read_remote(PROJECT,'445',client)['data']['deleted'])
                before=digest(client.snapshot())
                self.assertTrue(publish(release,manifest,PROJECT,4,client=client,baseline=baseline)['unchanged'])
                self.assertEqual(digest(client.snapshot()),before)
                (data/'current.json').write_text('{"release":4}')
                edited=mutate('update',hymn_id='145',payload={'title':'Local reviewed title'},reason='Next edit',data=data)
                release_revision(edited['revision'],5,'2026-11-08T00:00:00Z',data)
                release,manifest=load_gold(5,data)
                doc=client.request('GET',client.url+'/hymns/145')
                doc['fields']['title']=to_value('Unexpected remote title')
                client.request('PATCH',client.url+'/hymns/145',{'fields':doc['fields']})
                with self.assertRaises(PublicationError):
                    publish(release,manifest,PROJECT,4,client=client,baseline=publication_baseline(release,manifest,PROJECT,data))
                report=reconciliation_report(PROJECT,data,client)
                review={k:report[k]for k in ('expectedRevision','snapshotHash')}
                review.update(resolutions=[dict(id='145',choice='local')],acceptMetadata=False)
                reviewed=reconcile_remote(PROJECT,review,'Keep local correction',data,client)
                release_revision(reviewed['revision'],6,'2026-11-08T00:00:00Z',data)
                release,manifest=load_gold(6,data)
                publish(release,manifest,PROJECT,4,client=client,baseline=publication_baseline(release,manifest,PROJECT,data))
                self.assertEqual(read_remote(PROJECT,'145',client)['data']['title'],'Local reviewed title')
        finally:
            _,existing=client.snapshot()
            writes=[{'delete':doc['name']}for doc in existing.values()]+[{'delete':client.base+'/metadata/version'}]
            if writes:client.request('POST',client.url+':commit',{'writes':writes})


if __name__=='__main__':unittest.main()
