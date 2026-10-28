from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads((ROOT / 'content/publication-backlink-policy.json').read_text())


def effective_publication_backlinks(article):
    links = article.get('publication_backlinks')
    if not links:
        return None
    assert len({x['url'].rstrip('/') for x in links}) == len(links), article.get('id') or article.get('source_id')
    suspended = POLICY['suspended_url'].rstrip('/')
    allocation_date = article.get('allocation_date_kst') or article.get('publish_date_kst') or ''
    legacy_public = bool(allocation_date and allocation_date <= POLICY['legacy_allocation_cutoff_kst'])
    if not allocation_date:
        legacy_public = bool(article.get('publishedAt')) and article.get('status') in ('published', 'publicly_published')
    if legacy_public:
        assert len(links) == POLICY['legacy_public_link_count']
        assert sum(x['url'].rstrip('/') == suspended for x in links) == 1
        return links
    active = [x for x in links if x['url'].rstrip('/') != suspended]
    assert len(active) == POLICY['new_article_link_count']
    assert all(x['url'].rstrip('/') != suspended for x in active)
    return active
