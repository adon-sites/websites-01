"""Apply the current publication backlink policy without rewriting public legacy posts."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads((ROOT / 'content/publication-backlink-policy.json').read_text())


def effective_publication_backlinks(article):
    links = article.get('publication_backlinks')
    if not links:
        return None
    assert len({x['url'].rstrip('/') for x in links}) == len(links), article.get('id')
    suspended = POLICY['suspended_url'].rstrip('/')
    allocation_date = article.get('allocation_date_kst') or ''
    if allocation_date and allocation_date <= POLICY['legacy_allocation_cutoff_kst']:
        assert len(links) == POLICY['legacy_public_link_count'], article.get('id')
        assert sum(x['url'].rstrip('/') == suspended for x in links) == 1, article.get('id')
        return links
    active = [x for x in links if x['url'].rstrip('/') != suspended]
    assert len(active) == POLICY['new_article_link_count'], article.get('id')
    assert all(x['url'].rstrip('/') != suspended for x in active), article.get('id')
    return active
