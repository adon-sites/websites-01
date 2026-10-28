"""Load markdown posts (content/posts/*.md) as generator article records.

Frontmatter: title, short_title (optional, used for <title>/og:title without suffix), description,
category (must be a name in content/categories.json), date (YYYY-MM-DDTHH:MM:SS+09:00).
Body: 4-7 '## ' headings; paragraphs separated by blank lines. Future-dated posts are held back.
Each post carries the fixed 46-link bundle from content/link-bundle.json (rendered by the generator).
"""
from pathlib import Path
import datetime, json, re

KST = datetime.timezone(datetime.timedelta(hours=9))


def parse_markdown(path):
    raw = path.read_text(encoding='utf-8')
    assert raw.startswith('---\n'), ('frontmatter missing', path)
    fm, body = raw[4:].split('\n---\n', 1)
    meta = {}
    for line in fm.splitlines():
        if ':' in line:
            k, v = line.split(':', 1)
            meta[k.strip()] = v.strip().strip('"').strip("'")
    sections = []
    cur = None
    para = []

    def flush():
        if cur is not None and para:
            cur['paragraphs'].append(' '.join(para))
            para.clear()
    for line in body.strip().splitlines():
        if line.startswith('## '):
            flush()
            cur = {'heading': line[3:].strip(), 'paragraphs': []}
            sections.append(cur)
        elif not line.strip():
            flush()
        elif cur is not None:
            para.append(line.strip())
        else:
            raise AssertionError(('text before first "## " heading', path))
    flush()
    return meta, sections


def load_markdown_posts(root, now=None):
    root = Path(root)
    posts_dir = root / 'content/posts'
    if not posts_dir.is_dir():
        return []
    now = now or datetime.datetime.now(datetime.timezone.utc)
    cat_file = root / 'content/categories.json'
    if cat_file.is_file():
        categories = {c['name'] for c in json.loads(cat_file.read_text(encoding='utf-8'))}
    else:  # sites without category pages: any category already used by the existing articles
        categories = set()
        for name in ('reviewed-articles.json', 'articles.json', 'health-4452-articles.json'):
            f = root / 'content' / name
            if f.is_file():
                categories |= {a['category'] for a in json.loads(f.read_text(encoding='utf-8')) if isinstance(a, dict) and a.get('category')}
    bundle = json.loads((root / 'content/link-bundle.json').read_text(encoding='utf-8'))
    assert len(bundle) == 46 and len({x['url'].rstrip('/') for x in bundle}) == 46, 'link-bundle.json must hold 46 unique urls'
    posts = []
    for path in sorted(posts_dir.glob('*.md')):
        slug = path.stem
        assert re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug), ('bad slug', path)
        meta, sections = parse_markdown(path)
        for key in ('title', 'description', 'category', 'date'):
            assert meta.get(key), (key + ' missing', path)
        assert meta['category'] in categories, ('category not allowed', meta['category'], sorted(categories), path)
        assert 4 <= len(sections) <= 7, ('need 4-7 "## " sections', len(sections), path)
        assert all(s['paragraphs'] for s in sections), ('empty section', path)
        assert re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+09:00', meta['date']), ('date must be +09:00', path)
        published = datetime.datetime.fromisoformat(meta['date'])
        if published > now:
            continue  # held back until its date passes
        published_utc = published.astimezone(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        posts.append({
            'id': slug, 'slug': slug, 'path': '/blog/' + slug + '/', 'status': 'published',
            'title': meta['title'], 'short_title': meta.get('short_title', ''), 'description': meta['description'],
            'category': meta['category'], 'publishedAt': published_utc,
            'allocation_date_kst': published.astimezone(KST).date().isoformat(),
            'editorial_review_passed': True, 'content_origin': 'markdown', 'source_urls': [],
            'body_chars': len(re.sub(r'\s+', '', ''.join(p for s in sections for p in s['paragraphs']))),
            'publication_backlinks': [dict(x) for x in bundle], 'sections': sections,
        })
    posts.sort(key=lambda a: a['publishedAt'], reverse=True)
    return posts
