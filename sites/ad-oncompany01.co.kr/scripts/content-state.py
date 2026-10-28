"""Shared article fingerprints and public-release eligibility.

This code verifies review evidence. It never writes a semantic pass decision.
"""
import hashlib
import json


def content_hash(article):
    fields = {key: article[key] for key in
              ('source_id', 'slug', 'category', 'title', 'description', 'sections')}
    return hashlib.sha256(json.dumps(fields, ensure_ascii=False,
                                    sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def body_hash(article):
    return hashlib.sha256('\n'.join(s['text'] for s in article['sections']).encode()).hexdigest()


def eligible_articles(root, articles, release):
    reviews_path = root / 'content/semantic-reviews.json'
    audit_path = root / 'content/rewrite-audit.json'
    reviews = json.loads(reviews_path.read_text()) if reviews_path.exists() else {'articles': []}
    audit = json.loads(audit_path.read_text()) if audit_path.exists() else {'articles': []}
    by_review = {r['source_id']: r for r in reviews['articles']}
    by_audit = {r['source_id']: r for r in audit['articles']}
    selected = set(release.get('sourceIds', []))
    decisions, approved = {}, []
    for a in articles:
        r, m = by_review.get(a['source_id']), by_audit.get(a['source_id'])
        ok = bool(r and m and r.get('decision') == 'pass'
                  and r.get('contentSHA256') == content_hash(a)
                  and m.get('bodySHA256') == body_hash(a)
                  and m.get('mechanicalPass')
                  and r.get('coreQuestion') and r.get('distinctAnswer')
                  and r.get('comparisonNotes') and r.get('topicPreserved') is True)
        decisions[a['source_id']] = ok
        if ok and a['source_id'] in selected:
            approved.append(a)
    missing = selected - {a['source_id'] for a in approved}
    if release.get('enabled') and missing:
        raise ValueError('Selected articles have missing, stale, or failed review: ' + str(sorted(missing)))
    return approved, decisions
