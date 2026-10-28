"""Pause one exact new backlink; preserve the frozen, deployed public-ID set."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads((ROOT / 'content/backlink-policy.json').read_text())
SNAPSHOT = json.loads((ROOT / POLICY['public_snapshot_path']).read_text())
PUBLIC = {row['id']: row for row in SNAPSHOT['public_articles']}
PUBLIC_SLUG_IDS = {row['slug']: row['id'] for row in SNAPSHOT['public_articles']}
PAIR = (POLICY['excluded_pair']['keyword'], POLICY['excluded_pair']['url'])


def _digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def is_preserved_public(article):
    if not article or article.get('id') is None:
        raise ValueError('An immutable article ID is required for article link policy')
    saved = PUBLIC.get(str(article['id']))
    if saved is None:
        if article.get('slug') in PUBLIC_SLUG_IDS:
            raise ValueError('A new article ID cannot reuse an existing public route')
        return False
    if article.get('slug') != saved['slug']:
        raise ValueError('A frozen public article ID cannot be reused for another slug')
    if article.get('source_id') != saved.get('source_id'):
        raise ValueError('A frozen public article ID cannot be reused for another source ID')
    return True


def exclude_paused_pair(links, keyword_field='keyword'):
    if not POLICY['paused']:
        return list(links)
    return [link for link in links if (link.get(keyword_field), link.get('url')) != PAIR]


def new_publication_links(links):
    active = exclude_paused_pair(links)
    if POLICY['paused']:
        if active != POLICY['new_publication_targets']:
            raise ValueError('New campaign links must equal the approved, ordered 33-target set')
    return active


def publication_links_for(article):
    links = article.get('publication_backlinks')
    if is_preserved_public(article):
        saved_digest = PUBLIC[str(article['id'])]['publication_backlinks_sha256']
        if (saved_digest and _digest(links) != saved_digest) or (not saved_digest and links):
            raise ValueError('Existing public article backlinks must be preserved exactly')
        return links or None
    if not links:
        return None
    # Allocation day, a mutable published status, or a backdated timestamp must
    # never grandfather an ID that was not in the successful deployed snapshot.
    return new_publication_links(links)


def hospital_links_for(article, links):
    # Calls without an article are existing shared navigation/category sections.
    if article is None or is_preserved_public(article):
        return links
    return exclude_paused_pair(links, 'label')
