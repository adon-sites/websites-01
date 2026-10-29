/**
 * static-host — R2 버킷 `sites` 의 `sites/<host>/…` 를 호스트명별로 서빙하는 Cloudflare Worker.
 * 규칙: site-ops/runbooks/SCALE_DESIGN.md §4
 *  - Host 헤더 → 접두어 `sites/<host>/` (www. 는 루트 호스트로 301)
 *  - 경로가 `/` 로 끝나면 index.html, 확장자 없는 경로는 `<path>.html` → `<path>/index.html`(있으면 끝 슬래시로 301)
 *  - 사이트별 `_headers`(Cloudflare Pages 형식)·`_redirects`(from to status) 를 R2 에서 읽어 그대로 적용
 *  - 기본 Cache-Control: html/xml/txt 300초, 해시 파일명(.<8+hex>.)은 1년 immutable, 그 외 이미지·css·js 86400초
 *  - `_headers` `_redirects` `manifest.json` 은 서빙하지 않음. 없는 경로는 `404.html`(status 404)
 * 바인딩: env.SITES (R2 bucket `sites`)
 */

const TYPES = {
  html: 'text/html; charset=utf-8', htm: 'text/html; charset=utf-8', xml: 'application/xml; charset=utf-8',
  txt: 'text/plain; charset=utf-8', css: 'text/css; charset=utf-8', js: 'text/javascript; charset=utf-8',
  mjs: 'text/javascript; charset=utf-8', json: 'application/json; charset=utf-8', webmanifest: 'application/manifest+json',
  svg: 'image/svg+xml', png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg', gif: 'image/gif', webp: 'image/webp',
  avif: 'image/avif', ico: 'image/x-icon', woff: 'font/woff', woff2: 'font/woff2', ttf: 'font/ttf', otf: 'font/otf',
  pdf: 'application/pdf', mp4: 'video/mp4', webm: 'video/webm', mp3: 'audio/mpeg', zip: 'application/zip',
};
const HIDDEN = new Set(['_headers', '_redirects', 'manifest.json']);
const HASHED = /\.[0-9a-f]{8,}[.-]/i;

export function ext(path) { const m = /\.([a-z0-9]+)$/i.exec(path); return m ? m[1].toLowerCase() : ''; }
export function contentType(path) { return TYPES[ext(path)] || 'application/octet-stream'; }

export function defaultCacheControl(path) {
  const e = ext(path);
  if (!e || ['html', 'htm', 'xml', 'txt', 'json', 'webmanifest'].includes(e)) return 'public, max-age=300';
  if (HASHED.test(path)) return 'public, max-age=31536000, immutable';
  return 'public, max-age=86400';
}

/** Pages 형식 `_headers` 파싱 → [{pattern, headers:{}}] */
export function parseHeaders(text) {
  const rules = []; let cur = null;
  for (const raw of (text || '').split('\n')) {
    const line = raw.replace(/\r$/, '');
    if (!line.trim() || line.trim().startsWith('#')) continue;
    if (!/^\s/.test(line)) { cur = { pattern: line.trim(), headers: {} }; rules.push(cur); continue; }
    const i = line.indexOf(':'); if (i < 0 || !cur) continue;
    cur.headers[line.slice(0, i).trim()] = line.slice(i + 1).trim();
  }
  return rules;
}
export function matchPattern(pattern, path) {
  // Pages: `*` 는 아무 문자열, `:name` 플레이스홀더는 세그먼트 하나
  const re = new RegExp('^' + pattern.replace(/[.+?^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*').replace(/:[A-Za-z0-9_]+/g, '[^/]+') + '$');
  return re.test(path);
}
/** `_redirects` 파싱 → [{from, to, status}] (정확히 일치하는 from 만 지원) */
export function parseRedirects(text) {
  const out = [];
  for (const raw of (text || '').split('\n')) {
    const line = raw.replace(/\r$/, '').trim();
    if (!line || line.startsWith('#')) continue;
    const [from, to, status] = line.split(/\s+/);
    if (from && to) out.push({ from: safeDecode(from), to, status: Number(status) || 301 });
  }
  return out;
}
export function safeDecode(s) { try { return decodeURIComponent(s); } catch { return s; } }

/** 요청 경로 → 시도할 R2 키 후보 (접두어 제외) */
export function keyCandidates(path) {
  const p = safeDecode(path);
  if (p.endsWith('/')) return [{ key: p.slice(1) + 'index.html' }];
  const e = ext(p);
  if (e) return [{ key: p.slice(1) }];
  return [{ key: p.slice(1) + '.html' }, { key: p.slice(1) + '/index.html', redirectTo: p + '/' }, { key: p.slice(1) }];
}

const siteMetaCache = new Map(); // host → {headers, redirects, at}
async function siteMeta(env, host) {
  const c = siteMetaCache.get(host);
  if (c && Date.now() - c.at < 60_000) return c;
  const [h, r] = await Promise.all([env.SITES.get(`sites/${host}/_headers`), env.SITES.get(`sites/${host}/_redirects`)]);
  const meta = { headers: parseHeaders(h ? await h.text() : ''), redirects: parseRedirects(r ? await r.text() : ''), at: Date.now() };
  siteMetaCache.set(host, meta);
  return meta;
}

export function applyHeaderRules(rules, path, headers) {
  for (const rule of rules) if (matchPattern(rule.pattern, path)) for (const [k, v] of Object.entries(rule.headers)) headers.set(k, v);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    let host = url.hostname.toLowerCase();
    let path = url.pathname;
    let previewBase = '';
    if (host.endsWith('.workers.dev')) {
      // 라우트 전 확인용 preview: https://static-host-01.<sub>.workers.dev/<사이트 호스트>/<경로>
      const m = /^\/([a-z0-9.-]+\.[a-z]{2,})(\/.*)?$/i.exec(path);
      if (!m) return new Response('preview: /<host>/<path>', { status: 404, headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
      host = m[1].toLowerCase(); path = m[2] || '/'; previewBase = '/' + host;
      if (host.startsWith('www.')) host = host.slice(4);
    } else if (host.startsWith('www.')) {
      host = host.slice(4);
      return Response.redirect(`https://${host}${url.pathname}${url.search}`, 301);
    }
    if (!['GET', 'HEAD'].includes(request.method)) return new Response('Method Not Allowed', { status: 405 });
    const prefix = `sites/${host}/`;
    const redirectHost = previewBase ? `${url.hostname}${previewBase}` : host;
    const meta = await siteMeta(env, host);

    const decoded = safeDecode(path);
    for (const rd of meta.redirects) if (rd.from === decoded || rd.from === path) return Response.redirect(new URL(previewBase + rd.to, url).toString(), rd.status);

    const base = decoded.slice(1).split('/').pop();
    if (HIDDEN.has(base)) return notFound(env, prefix, meta, request);

    for (const cand of keyCandidates(path)) {
      if (cand.redirectTo) {
        const head = await env.SITES.head(prefix + cand.key);
        if (head) return Response.redirect(`https://${redirectHost}${encodeURI(cand.redirectTo)}${url.search}`, 301);
        continue;
      }
      const obj = await env.SITES.get(prefix + cand.key, { onlyIf: request.headers });
      if (!obj) continue;
      const headers = new Headers();
      headers.set('Content-Type', contentType(cand.key));
      headers.set('Cache-Control', defaultCacheControl(cand.key));
      if (obj.httpEtag && /^[\x20-\x7e]+$/.test(obj.httpEtag)) headers.set('ETag', obj.httpEtag);
      headers.set('X-Content-Type-Options', 'nosniff');
      applyHeaderRules(meta.headers, decoded, headers);
      if (obj.body === undefined || obj.body === null) return new Response(null, { status: 304, headers }); // onlyIf 조건 일치
      return new Response(request.method === 'HEAD' ? null : obj.body, { status: 200, headers });
    }
    return notFound(env, prefix, meta, request);
  },
};

async function notFound(env, prefix, meta, request) {
  const obj = await env.SITES.get(prefix + '404.html');
  const headers = new Headers({ 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'public, max-age=60', 'X-Content-Type-Options': 'nosniff' });
  if (!obj) return new Response('Not Found', { status: 404, headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
  return new Response(request.method === 'HEAD' ? null : obj.body, { status: 404, headers });
}
