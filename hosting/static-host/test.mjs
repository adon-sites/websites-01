// node test.mjs — mock R2 로 worker.js 동작 확인 (네트워크 불필요)
import worker, { keyCandidates, parseHeaders, parseRedirects, matchPattern, defaultCacheControl } from './worker.js';

class MockR2 {
  constructor(objs) { this.objs = objs; }
  async head(key) { return key in this.objs ? { httpEtag: '"e"' } : null; }
  async get(key, opts) {
    if (!(key in this.objs)) return null;
    const body = this.objs[key];
    const inm = opts?.onlyIf?.get?.('if-none-match');
    const tag = '"' + [...key].reduce((a, c) => (a * 31 + c.charCodeAt(0)) >>> 0, 7).toString(16) + '"';
    if (inm === tag) return { httpEtag: tag, body: null };
    return { httpEtag: tag, body, async text() { return body; } };
  }
}
const bucket = new MockR2({
  'sites/a.co.kr/index.html': '<html>home</html>',
  'sites/a.co.kr/journal/post-1.html': '<html>p1</html>',
  'sites/a.co.kr/blog/x/index.html': '<html>x</html>',
  'sites/a.co.kr/images/c-860.jpg': 'JPG',
  'sites/a.co.kr/images/first-visit/a.0123456789ab-800.webp': 'WEBP',
  'sites/a.co.kr/sitemap.xml': '<x/>',
  'sites/a.co.kr/404.html': '<html>404</html>',
  'sites/a.co.kr/_headers': '/images/*\n  Cache-Control: public, max-age=3600\n/sitemap.xml\n  Content-Type: application/xml; charset=utf-8\n',
  'sites/a.co.kr/_redirects': '/journal /blog 301\n/평택치과 /평택치과/ 301\n',
  'sites/a.co.kr/평택치과/index.html': '<html>kr</html>',
  'sites/a.co.kr/manifest.json': '{}',
});
const env = { SITES: bucket };
const req = (u, h = {}, m = 'GET') => new Request(u, { method: m, headers: h });
let fails = 0;
async function t(name, u, exp, h, m) {
  const r = await worker.fetch(req(u, h, m), env);
  const got = { status: r.status, loc: r.headers.get('location'), ct: r.headers.get('content-type'), cc: r.headers.get('cache-control'), body: r.body ? await r.text() : null };
  const ok = Object.entries(exp).every(([k, v]) => got[k] === v);
  if (!ok) fails++;
  console.log(ok ? 'ok  ' : 'FAIL', name, ok ? '' : JSON.stringify({ exp, got }));
}
await t('home', 'https://a.co.kr/', { status: 200, body: '<html>home</html>', cc: 'public, max-age=300' });
await t('www→apex', 'https://www.a.co.kr/p?q=1', { status: 301, loc: 'https://a.co.kr/p?q=1' });
await t('extensionless → .html', 'https://a.co.kr/journal/post-1', { status: 200, body: '<html>p1</html>', ct: 'text/html; charset=utf-8' });
await t('dir without slash → 301 slash', 'https://a.co.kr/blog/x', { status: 301, loc: 'https://a.co.kr/blog/x/' });
await t('dir with slash', 'https://a.co.kr/blog/x/', { status: 200, body: '<html>x</html>' });
await t('image default 86400 overridden by _headers 3600', 'https://a.co.kr/images/c-860.jpg', { status: 200, ct: 'image/jpeg', cc: 'public, max-age=3600' });
await t('hashed filename under /images/* → _headers 3600 wins', 'https://a.co.kr/images/first-visit/a.0123456789ab-800.webp', { status: 200, cc: 'public, max-age=3600' });
await t('sitemap ct from _headers', 'https://a.co.kr/sitemap.xml', { status: 200, ct: 'application/xml; charset=utf-8', cc: 'public, max-age=300' });
await t('_redirects exact', 'https://a.co.kr/journal', { status: 301, loc: 'https://a.co.kr/blog' });
await t('korean _redirects', 'https://a.co.kr/%ED%8F%89%ED%83%9D%EC%B9%98%EA%B3%BC', { status: 301, loc: 'https://a.co.kr/%ED%8F%89%ED%83%9D%EC%B9%98%EA%B3%BC/' });
await t('korean path file', 'https://a.co.kr/%ED%8F%89%ED%83%9D%EC%B9%98%EA%B3%BC/', { status: 200, body: '<html>kr</html>' });
await t('hidden manifest.json → 404 page', 'https://a.co.kr/manifest.json', { status: 404, body: '<html>404</html>' });
await t('hidden _headers → 404', 'https://a.co.kr/_headers', { status: 404 });
await t('missing → 404.html', 'https://a.co.kr/nope/', { status: 404, body: '<html>404</html>', ct: 'text/html; charset=utf-8' });
const tagOf = k => '"' + [...k].reduce((a, c) => (a * 31 + c.charCodeAt(0)) >>> 0, 7).toString(16) + '"';
await t('304 on matching etag', 'https://a.co.kr/', { status: 304 }, { 'if-none-match': tagOf('sites/a.co.kr/index.html') });
await t('HEAD', 'https://a.co.kr/', { status: 200, body: null }, {}, 'HEAD');
await t('POST 405', 'https://a.co.kr/', { status: 405 }, {}, 'POST');
await t('preview home', 'https://static-host-01.x.workers.dev/a.co.kr/', { status: 200, body: '<html>home</html>' });
await t('preview post', 'https://static-host-01.x.workers.dev/a.co.kr/journal/post-1', { status: 200, body: '<html>p1</html>' });
await t('preview dir slash redirect keeps prefix', 'https://static-host-01.x.workers.dev/a.co.kr/blog/x', { status: 301, loc: 'https://static-host-01.x.workers.dev/a.co.kr/blog/x/' });
await t('preview _redirects keeps prefix', 'https://static-host-01.x.workers.dev/a.co.kr/journal', { status: 301, loc: 'https://static-host-01.x.workers.dev/a.co.kr/blog' });
await t('preview bad', 'https://static-host-01.x.workers.dev/', { status: 404 });
// unit
console.log(JSON.stringify(keyCandidates('/a/b')), defaultCacheControl('x.a1b2c3d4e5.css'), matchPattern('/images/*', '/images/a/b.jpg'), matchPattern('/:slug/', '/abc/'), !matchPattern('/:slug/', '/a/b/'));
console.log(fails ? `FAILS=${fails}` : 'ALL OK');
process.exit(fails ? 1 : 0);
