"""Read-only remote views, drift detection and explicit reconciliation checkpoints."""
from copy import deepcopy
from .editorial import commit_operation, content, edit_lock, head, ordered
from .storage import DATA, digest


def normalize_fields(identity, fields):
    result = deepcopy(fields)
    result.pop('updatedAt', None)
    result.setdefault('id', identity)
    result.setdefault('deleted', False)
    return result


def snapshot(metadata, existing):
    from .firestore import document_fields
    meta = document_fields(metadata) if metadata else None
    if meta is not None: meta.pop('updatedAt',None)
    return dict(metadata=meta, hymns={key:normalize_fields(key,document_fields(doc)) for key,doc in sorted(existing.items())})


def project_release(baseline, release):
    """Model exactly what the publisher writes, including retained tombstones."""
    docs = deepcopy(baseline['hymns'])
    active = {h['id']:normalize_fields(h['id'],h) for h in release['hymns']}
    for identity, fields in list(docs.items()):
        if identity not in active and not fields.get('deleted',False):
            number=fields.get('number',0); title=fields.get('title','')
            docs[identity]=dict(id=identity,number=number if type(number) is int else 0,
                                title=title if isinstance(title,str) else '', sections=[], deleted=True, version=release['version'])
    docs.update(active)
    return dict(metadata=dict(currentVersion=release['version'],totalHymns=len(active),releaseHash=digest(release)),hymns=docs)


def version_snapshot(version, data=DATA):
    from .layers import load_gold
    from .editorial import load_revision
    if version == 0: return dict(metadata=None,hymns={})
    release,manifest=load_gold(version,data)
    if manifest['schemaVersion'] == 2:
        record=load_revision(manifest['revisionId'],data)
        checkpoint=record['checkpoint']
        baseline=deepcopy(checkpoint['snapshot']) if checkpoint else version_snapshot(record['baseRelease'],data)
    else:
        # Legacy history predates explicit base-release links.
        from pathlib import Path
        versions=[int(p.name) for p in (Path(data)/'gold').iterdir() if p.is_dir() and p.name.isdigit() and int(p.name)<version]
        baseline=version_snapshot(max(versions,default=0),data)
    return project_release(baseline,release)


def publication_baseline(release, manifest, project, data=DATA):
    from .layers import load_gold
    if manifest['schemaVersion'] == 2:
        from .editorial import load_revision
        record=load_revision(manifest['revisionId'],data)
        checkpoint=record['checkpoint']
        if checkpoint and checkpoint['projectId'] == project:
            return dict(projectId=project,snapshot=deepcopy(checkpoint['snapshot']),allowMissingHash=False)
        version=record['baseRelease']
    else:
        from pathlib import Path
        versions=[int(p.name)for p in (Path(data)/'gold').iterdir() if p.is_dir()and p.name.isdigit()and int(p.name)<release['version']]
        version=max(versions,default=0)
    legacy=version > 0 and load_gold(version,data)[1]['schemaVersion'] == 1
    return dict(projectId=project,snapshot=version_snapshot(version,data),allowMissingHash=legacy)


def differences(expected, actual, allow_missing_hash=False):
    left,right=deepcopy(expected['metadata']),deepcopy(actual['metadata'])
    if allow_missing_hash and isinstance(left,dict) and isinstance(right,dict) and 'releaseHash' not in right:
        left.pop('releaseHash',None)
    changed=sorted(key for key in set(expected['hymns'])|set(actual['hymns'])
                   if expected['hymns'].get(key)!=actual['hymns'].get(key))
    return dict(changedIds=changed,metadataChanged=left!=right)


def verify_baseline(release, baseline, project, metadata, existing, unchanged=False):
    if baseline is None or baseline['projectId'] != project:
        raise ValueError('A project-specific publication baseline is required')
    expected=project_release(baseline['snapshot'],release) if unchanged else baseline['snapshot']
    diff=differences(expected,snapshot(metadata,existing),baseline.get('allowMissingHash',False) and not unchanged)
    if diff['changedIds'] or diff['metadataChanged']:
        raise ValueError('Remote content differs; run reconcile and review every difference before publishing')


def read_remote(project, identity=None, client=None):
    from .firestore import Firestore,document_fields
    from urllib.parse import quote
    client=client or Firestore(project)
    if identity is not None:
        if not identity or identity in {'.','..'} or '/' in identity or len(identity.encode())>1500: raise ValueError('Invalid document ID')
        doc=client.request('GET',client.url+'/hymns/'+quote(identity,safe=''),missing_ok=True)
        if doc is None: raise ValueError('Remote hymn not found')
        return dict(id=identity,data=document_fields(doc))
    _,existing=client.snapshot()
    result=[dict(id=key,data=document_fields(doc))for key,doc in sorted(existing.items())
            if not document_fields(doc).get('deleted',False)]
    return sorted(result,key=lambda item:(item['data'].get('number') if type(item['data'].get('number'))is int else 65536,item['id']))


def reconciliation_report(project, data=DATA, client=None):
    from .firestore import Firestore
    from .layers import load_gold
    rid,record=head(data)
    release,manifest=load_gold(record['baseRelease'],data)
    checkpoint=record['checkpoint']
    if checkpoint and checkpoint['projectId']==project:
        expected=checkpoint['snapshot'];legacy=False
    else:
        expected=version_snapshot(record['baseRelease'],data)
        legacy=manifest['schemaVersion']==1
    client=client or Firestore(project)
    metadata,existing=client.snapshot()
    observed=snapshot(metadata,existing)
    diff=differences(expected,observed,legacy)
    return dict(expectedRevision=rid,snapshotHash=digest(observed),projectId=project,
                snapshot=observed,differences=diff)


def apply_remote(parent, operation, data):
    from .source_reconciliation import exact_keys
    from .layers import load_gold
    exact_keys(operation,['type','reason','expectedRevision','projectId','snapshot','snapshotHash','resolutions','acceptMetadata'],
               ['type','reason','expectedRevision','projectId','snapshot','snapshotHash','resolutions','acceptMetadata'])
    if operation['expectedRevision']!=digest(parent) or digest(operation['snapshot'])!=operation['snapshotHash']:
        raise ValueError('Reconciliation precondition changed')
    observed=operation['snapshot']
    exact_keys(observed,['metadata','hymns'],['metadata','hymns'])
    if not isinstance(observed['hymns'],dict):raise ValueError('Invalid remote snapshot')
    checkpoint=parent['checkpoint']
    expected=checkpoint['snapshot'] if checkpoint and checkpoint['projectId']==operation['projectId'] else version_snapshot(parent['baseRelease'],data)
    legacy=not (checkpoint and checkpoint['projectId']==operation['projectId']) and load_gold(parent['baseRelease'],data)[1]['schemaVersion']==1
    diff=differences(expected,observed,legacy)
    if not diff['changedIds'] and not diff['metadataChanged']:raise ValueError('No remote differences to reconcile')
    if type(operation['acceptMetadata'])is not bool or diff['metadataChanged'] and not operation['acceptMetadata']:
        raise ValueError('Remote metadata difference requires explicit acceptance')
    result=deepcopy(parent);by_id={h['id']:h for h in result['hymns']}
    decisions=operation['resolutions'];seen=set()
    if not isinstance(decisions,list):raise ValueError('Expected resolution list')
    for item in decisions:
        exact_keys(item,['id','choice'],['id','choice'])
        identity=item['id']
        if identity not in diff['changedIds'] or identity in seen:raise ValueError('Unexpected or duplicate reconciliation target')
        seen.add(identity)
        if item['choice']=='remote':
            remote=observed['hymns'].get(identity)
            if remote and not remote.get('deleted',False):
                if remote.get('id')!=identity or identity in parent['retiredIds']:
                    raise ValueError('Remote identity mismatch or retired identity reuse')
                by_id[identity]=content(remote)
            else:by_id.pop(identity,None)
        elif item['choice']!='local':raise ValueError('Choose local or remote explicitly')
    if seen!=set(diff['changedIds']):raise ValueError('Every remote difference needs a decision')
    result.update(parent=digest(parent),operation=deepcopy(operation),hymns=ordered(list(by_id.values())),
                  checkpoint=dict(projectId=operation['projectId'],snapshot=deepcopy(observed),snapshotHash=operation['snapshotHash']),
                  retiredIds=sorted(set(parent['retiredIds'])|({h['id']for h in parent['hymns']}-set(by_id))))
    return result


def reconcile_remote(project, review, reason, data=DATA, client=None):
    from .firestore import Firestore
    from .source_reconciliation import exact_keys
    exact_keys(review,['expectedRevision','snapshotHash','resolutions','acceptMetadata'],['expectedRevision','snapshotHash','resolutions','acceptMetadata'])
    with edit_lock(data):
        _,parent=head(data)
        client=client or Firestore(project)
        metadata,existing=client.snapshot();observed=snapshot(metadata,existing)
        if digest(observed)!=review['snapshotHash']:raise ValueError('Remote snapshot changed since review')
        operation=dict(type='remote',reason=reason,projectId=project,snapshot=observed,**deepcopy(review))
        rid,result=commit_operation(parent,operation,data)
    return dict(revision=rid,snapshotHash=operation['snapshotHash'],hymnCount=len(result['hymns']))
