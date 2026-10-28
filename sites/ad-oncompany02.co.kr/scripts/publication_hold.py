"""Explicit public projection for individually held edits; never rewrites stored inputs.
Stored manuscripts remain pending. Only pinned, already-published records are
selected for held IDs. All other/new records follow the normal pipeline.
Required selection guards remain active under Python -O/PYTHONOPTIMIZE.
"""
from pathlib import Path
import copy,hashlib,json
RUNTIME_DIRS={'client','server','.openai','_appgen_meta'}
EXPECTED_HELD_IDS = ('health-4452-0281',)  # Replaced with the exact per-site hold scope during preparation

class PublicationHoldError(ValueError):
    """The pinned publication projection cannot be safely selected."""

def require(condition,message):
    if not condition:
        raise PublicationHoldError(message)

def canonical_hash(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def load_published_articles(root):
    root=Path(root);path=root/'content/reviewed-articles.json';raw=path.read_bytes();records=json.loads(raw)
    require(isinstance(records,list),'Manuscripts must be an array')
    by_id={a['id']:a for a in records}
    require(len(by_id)==len(records),'Duplicate manuscript ID')
    manifest_path=root/'content/publication-holds/manifest.json'
    require(manifest_path.exists(),'Publication hold manifest missing; refuse to publish pending manuscripts')
    manifest=json.loads(manifest_path.read_text())
    require(manifest.get('schemaVersion')==1 and manifest.get('mode')=='published-baseline-only','Invalid publication hold mode')
    # Check the actual stored pending input, not a hash of the projection.
    receipt=json.loads((root/'content/search-release.json').read_text())
    require(hashlib.sha256(raw).hexdigest()==receipt['preservedSourceHashes']['content/reviewed-articles.json'],'Stored manuscript hash does not match source receipt')
    snapshot_path=root/'content/publication-holds/published-records.json';snapshot_raw=snapshot_path.read_bytes()
    require(hashlib.sha256(snapshot_raw).hexdigest()==manifest['publishedRecordsFileSha256'],'Published snapshot file changed')
    snapshots=json.loads(snapshot_raw);snapshots_by_id={a['id']:a for a in snapshots}
    holds=manifest['holds'];held_ids=[h['id'] for h in holds]
    require(EXPECTED_HELD_IDS is not None and set(held_ids)==set(EXPECTED_HELD_IDS),'Publication hold scope changed; explicit review is required')
    require(len(held_ids)==len(set(held_ids))==len(snapshots)==len(snapshots_by_id),'Invalid hold scope')
    require(set(held_ids)==set(snapshots_by_id),'Snapshot scope differs from hold IDs')
    for hold in holds:
        ident=hold['id'];require(ident in by_id,'Held manuscript is missing: '+ident)
        pending=by_id[ident];published=snapshots_by_id[ident]
        require(canonical_hash(pending)==hold['pendingRecordSha256'],'Held pending record changed; review is required: '+ident)
        require(canonical_hash(published)==hold['publishedRecordSha256'],'Published baseline record changed: '+ident)
        require(published.get('status')=='published' and bool(published.get('publishedAt')),'Hold snapshot must already be published')
        changed={k for k in set(pending)|set(published) if pending.get(k)!=published.get(k)}
        require(changed==set(hold['changedFields']),'Held record difference changed: '+ident)
        for field in ['id','slug','category','publishedAt','status','source_id','publication_backlinks']:
            require(pending.get(field)==published.get(field),'Publication identity or links changed: '+ident)
    return [copy.deepcopy(snapshots_by_id.get(a['id'],a)) for a in records]

def publication_hold_report(root):
    root=Path(root);effective=load_published_articles(root)
    manifest=root/'content/publication-holds/manifest.json'
    held=[h['id'] for h in json.loads(manifest.read_text())['holds']]
    return {'storedManuscriptHashesVerified':True,'publishedProjectionVerified':True,'heldIds':held,'heldPendingTextPublished':False,'effectiveArticleCount':len(effective),'projectionSha256':canonical_hash(effective)}

def legacy_html_paths(out):
    out=Path(out)
    return [p for p in out.rglob('*.html') if p.relative_to(out).parts[0] not in RUNTIME_DIRS]
