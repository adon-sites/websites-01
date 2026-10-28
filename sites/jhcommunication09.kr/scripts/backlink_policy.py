from datetime import datetime, timezone
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads((ROOT / 'content/backlink-policy.json').read_text())
PUBLICATION = json.loads((ROOT / 'content/publication.json').read_text())
EFFECTIVE_AT = datetime.fromisoformat(POLICY['effective_at'].replace('Z', '+00:00'))
EXCLUDED_NEW_URLS = {x['url'].rstrip('/') for x in POLICY['excluded_new_targets']}
LEGACY_PUBLIC_IDS = set(PUBLICATION.get('existingPublicArticleIds', []))


def is_new_after_pause(article):
    if article.get('id') in LEGACY_PUBLIC_IDS:
        return False
    published_at = article.get('publishedAt')
    if not published_at:
        return True
    parsed = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
    assert parsed.tzinfo, 'publishedAt must include a timezone'
    return parsed.astimezone(timezone.utc) >= EFFECTIVE_AT.astimezone(timezone.utc)


def future_publication_links(links):
    filtered = [x for x in links if x['url'].rstrip('/') not in EXCLUDED_NEW_URLS]
    assert len(filtered) == len({x['url'].rstrip('/') for x in filtered}) == POLICY['new_publication_link_count']
    assert not any(x['url'].rstrip('/') in EXCLUDED_NEW_URLS for x in filtered)
    return filtered


def publication_links_for(article):
    links = article.get('publication_backlinks') or []
    if not links:
        return []
    if is_new_after_pause(article):
        return future_publication_links(links)
    assert len(links) == len({x['url'].rstrip('/') for x in links}) == POLICY['legacy_published_link_count']
    return links
