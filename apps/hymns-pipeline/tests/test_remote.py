from copy import deepcopy
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from hymns_pipeline.storage import DATA,digest
from hymns_pipeline.editorial import mutate,load_revision,release_revision
from hymns_pipeline.layers import load_gold
from hymns_pipeline.remote import (snapshot,version_snapshot,publication_baseline,reconciliation_report,
                                   reconcile_remote,read_remote,verify_baseline)
from hymns_pipeline.firestore import publish,PublicationError,to_value


def wire(state):
    def document(identity,fields):
        return dict(name=identity,fields={k:to_value(v)for k,v in fields.items()},updateTime='2026-11-07T00:00:00Z')
    return (document('metadata/version',state['metadata']) if state['metadata'] else None,
            {k:document(k,v)for k,v in state['hymns'].items()})


class RemoteTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.data=Path(self.temp.name)/'data';shutil.copytree(DATA,self.data)
        self.state=version_snapshot(3,self.data)
        self.client=Mock(base='projects/hinario-idc/databases/(default)/documents',url='https://example.invalid')
        self.client.snapshot.side_effect=lambda:wire(self.state)

    def build(self):
        change=mutate('update',hymn_id='145',payload={'title':'Local correction','number':464},reason='Edit',data=self.data)
        release_revision(change['revision'],4,'2026-11-08T00:00:00Z',self.data)
        return load_gold(4,self.data)

    def test_remote_queries_are_read_only(self):
        rows=read_remote('hinario-idc',client=self.client)
        self.assertEqual(len(rows),236)
        self.client.request.assert_not_called()
        self.client.request.return_value=wire(self.state)[1]['145']
        self.assertEqual(read_remote('hinario-idc','145',self.client)['data']['number'],145)
        self.assertEqual(self.client.request.call_args.args[0],'GET')
        self.assertFalse((self.data/'editorial').exists())

    def test_drift_even_at_same_version_blocks_all_writes(self):
        release,manifest=self.build()
        baseline=publication_baseline(release,manifest,'hinario-idc',self.data)
        self.state['hymns']['145']['title']='Remote correction'
        with self.assertRaises(PublicationError):
            publish(release,manifest,'hinario-idc',3,client=self.client,baseline=baseline)
        self.client.request.assert_not_called()

    def test_timestamp_only_and_legacy_metadata_hash_are_compatible(self):
        release,manifest=self.build();baseline=publication_baseline(release,manifest,'hinario-idc',self.data)
        self.state['metadata'].pop('releaseHash')
        for fields in self.state['hymns'].values():fields['updatedAt']='Different timestamp'
        result=publish(release,manifest,'hinario-idc',3,True,self.client,baseline=baseline)
        self.assertEqual(result['changedIds'],['145'])
        self.client.request.assert_not_called()

    def test_reconciliation_and_further_remote_change(self):
        release,manifest=self.build()
        self.state['hymns']['145']['title']='Remote correction'
        report=reconciliation_report('hinario-idc',self.data,self.client)
        self.assertEqual(report['differences']['changedIds'],['145'])
        review={k:report[k]for k in ['expectedRevision','snapshotHash']}
        review.update(resolutions=[{'id':'145','choice':'remote'}],acceptMetadata=False)
        accepted=reconcile_remote('hinario-idc',review,'Accept remote title',self.data,self.client)
        record=load_revision(accepted['revision'],self.data)
        self.assertEqual(next(h for h in record['hymns']if h['id']=='145')['title'],'Remote correction')
        release_revision(accepted['revision'],5,'2026-11-08T00:00:00Z',self.data)
        release,manifest=load_gold(5,self.data);baseline=publication_baseline(release,manifest,'hinario-idc',self.data)
        publish(release,manifest,'hinario-idc',3,True,self.client,baseline=baseline)
        self.state['hymns']['145']['title']='Changed again'
        with self.assertRaises(PublicationError):publish(release,manifest,'hinario-idc',3,client=self.client,baseline=baseline)
        self.client.request.assert_not_called()

    def test_incomplete_or_stale_reconciliation_does_not_change_head(self):
        from hymns_pipeline.editorial import head
        self.state['hymns']['145']['title']='Drift'
        report=reconciliation_report('hinario-idc',self.data,self.client)
        review={k:report[k]for k in ['expectedRevision','snapshotHash']};review.update(resolutions=[],acceptMetadata=False)
        with self.assertRaises(ValueError):reconcile_remote('hinario-idc',review,'Incomplete',self.data,self.client)
        self.assertFalse((self.data/'editorial/revisions').exists())
        review['resolutions']=[{'id':'145','choice':'local'}]
        self.state['hymns']['145']['title']='Changed after review'
        with self.assertRaises(ValueError):reconcile_remote('hinario-idc',review,'Stale',self.data,self.client)

    def test_unknown_remote_addition_requires_explicit_removal_decision(self):
        self.state['hymns']['extra']=dict(id='extra',number=600,title='Unexpected',sections=[],version=3,deleted=False)
        report=reconciliation_report('hinario-idc',self.data,self.client)
        review={k:report[k]for k in ['expectedRevision','snapshotHash']}
        review.update(resolutions=[dict(id='extra',choice='local')],acceptMetadata=False)
        result=reconcile_remote('hinario-idc',review,'Remove unexpected entry',self.data,self.client)
        release_revision(result['revision'],4,'2026-11-08T00:00:00Z',self.data)
        release,manifest=load_gold(4,self.data);baseline=publication_baseline(release,manifest,'hinario-idc',self.data)
        publish(release,manifest,'hinario-idc',3,False,self.client,baseline=baseline)
        writes=self.client.request.call_args.args[2]['writes']
        self.assertTrue(any(w['update']['name'].endswith('/hymns/extra') and w['update']['fields']['deleted']=={'booleanValue':True}for w in writes))

    def test_idempotent_publication_verifies_tombstones_and_ignores_timestamps(self):
        from hymns_pipeline.remote import project_release
        change=mutate('delete',hymn_id='145',reason='Remove',data=self.data)
        release_revision(change['revision'],4,'2026-11-08T00:00:00Z',self.data)
        release,manifest=load_gold(4,self.data)
        baseline=publication_baseline(release,manifest,'hinario-idc',self.data)
        self.state=project_release(baseline['snapshot'],release)
        for fields in self.state['hymns'].values():fields['updatedAt']='Different timestamp'
        self.state['metadata']['updatedAt']='Different timestamp'
        result=publish(release,manifest,'hinario-idc',4,False,self.client,baseline=baseline)
        self.assertTrue(result['unchanged']);self.client.request.assert_not_called()
        self.state['hymns']['145']['version']=3
        with self.assertRaises(PublicationError):publish(release,manifest,'hinario-idc',4,False,self.client,baseline=baseline)

    def test_metadata_and_project_scoped_checkpoint(self):
        self.state['metadata']['currentVersion']=5
        report=reconciliation_report('hinario-idc',self.data,self.client)
        review={k:report[k]for k in ['expectedRevision','snapshotHash']}
        review.update(resolutions=[],acceptMetadata=False)
        with self.assertRaises(ValueError):reconcile_remote('hinario-idc',review,'Metadata',self.data,self.client)
        review['acceptMetadata']=True
        change=reconcile_remote('hinario-idc',review,'Accept version',self.data,self.client)
        with self.assertRaises(ValueError):release_revision(change['revision'],4,'2026-11-08T00:00:00Z',self.data)
        release_revision(change['revision'],6,'2026-11-08T00:00:00Z',self.data)
        release,manifest=load_gold(6,self.data)
        checkpoint=publication_baseline(release,manifest,'hinario-idc',self.data)
        foreign=publication_baseline(release,manifest,'another-project',self.data)
        self.assertEqual(checkpoint['snapshot']['metadata']['currentVersion'],5)
        self.assertEqual(foreign['snapshot']['metadata']['currentVersion'],3)
        with self.assertRaises(ValueError):verify_baseline(release,checkpoint,'another-project',*wire(self.state))

    def test_emulator_rejects_production_project_or_external_endpoint(self):
        from unittest.mock import patch
        from hymns_pipeline.firestore import Firestore
        for host,project in [('127.0.0.1:8080','hinario-idc'),('example.com:8080','demo-hinario-idc'),('localhost:99999','demo-hinario-idc')]:
            with patch.dict('os.environ',{'FIRESTORE_EMULATOR_HOST':host}),self.assertRaises(ValueError):
                Firestore(project)
