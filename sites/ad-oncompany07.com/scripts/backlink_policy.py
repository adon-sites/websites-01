from datetime import datetime
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
POLICY=json.loads((ROOT/'content/backlink-policy.json').read_text())
PUBLICATION=json.loads((ROOT/'content/publication.json').read_text())
LEGACY_PUBLIC_IDS=set(PUBLICATION.get('existingPublicArticleIds',[]))
EFFECTIVE_AT=datetime.fromisoformat(POLICY['effective_at'].replace('Z','+00:00'))
EXCLUDED_URLS={x['url'].rstrip('/') for x in POLICY['excluded_new_targets']}
def links_for_new_publication(links):
 filtered=[x for x in links if x['url'].rstrip('/') not in EXCLUDED_URLS];expected=POLICY['new_publication_link_count'];assert len(filtered)==len({x['url'].rstrip('/') for x in filtered})==expected;return filtered
def is_new_after_pause(article):
 if article.get('id') in LEGACY_PUBLIC_IDS:return False
 published_at=article.get('publishedAt')
 if not published_at:return True
 return datetime.fromisoformat(published_at.replace('Z','+00:00'))>=EFFECTIVE_AT
def publication_links_for(article):
 links=article.get('publication_backlinks')
 if not links:return None
 if is_new_after_pause(article):return links_for_new_publication(links)
 expected=POLICY['legacy_published_link_count'];assert len(links)==len({x['url'].rstrip('/') for x in links})==expected;return links
