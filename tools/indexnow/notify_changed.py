#!/usr/bin/env python3
"""notify_changed.py — 배포 직전 사이트맵(prev)과 이번 빌드 사이트맵을 비교해 새 글·수정 글 주소만 네이버 IndexNow 로 통보한다.
usage: notify_changed.py --host <도메인> [--group <site.json group>] --out <빌드 출력 폴더> --prev <배포 전 내려받은 sitemap.xml> --key <키> [--dry-run]
 - 새 글 = prev 에 없던 주소, 수정 글 = lastmod 가 달라진 주소. 목록 페이지(/blog/page/ 등)와 홈은 보내지 않는다.
 - prev 를 못 읽었거나(첫 배포·일시 오류) 변경이 MAX_AUTO(300)건을 넘으면 보내지 않는다(대량 변경은 Actions `indexnow` 로 수동 전송).
 - 통보 실패는 배포 실패가 아니다(항상 exit 0).
"""
import argparse, json, re, sys, urllib.request, urllib.error
from pathlib import Path

ENDPOINT = "https://searchadvisor.naver.com/indexnow"
SKIP = re.compile(r"/blog/page/|/blog/topic/|/blog/category/|/category/")
MAX_AUTO = 300
UA = {"User-Agent": "indexnow-submit/1.0"}

def entries(xml):
    out = {}
    for blk in re.findall(r"<url>.*?</url>", xml, re.S):
        loc = re.search(r"<loc>\s*([^<\s]+)\s*</loc>", blk)
        lm = re.search(r"<lastmod>\s*([^<\s]+)\s*</lastmod>", blk)
        if loc: out[loc.group(1).replace("&amp;", "&")] = lm.group(1) if lm else ""
    return out

def changed(prev_xml, cur_xml, host):
    prev, cur = entries(prev_xml), entries(cur_xml)
    home = {f"https://{host}/", f"https://{host}"}
    return [u for u, lm in cur.items() if u not in home and not SKIP.search(u) and (u not in prev or prev[u] != lm)]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--prev", required=True); ap.add_argument("--key", required=True)
    ap.add_argument("--group", default=""); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    ex = Path(__file__).resolve().parent / "exclude.txt"
    rules = [l.strip() for l in ex.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")] if ex.exists() else []
    if a.host in rules or (a.group and f"group:{a.group}" in rules):
        print(f"[{a.host}] indexnow: 제외 사이트 → 통보 안 함"); return
    try:
        prev = Path(a.prev).read_text(encoding="utf-8", errors="replace")
        cur = (Path(a.out) / "sitemap.xml").read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        print(f"[{a.host}] indexnow: 사이트맵을 읽지 못함({e}) → 건너뜀"); return
    if "<urlset" not in prev or not entries(prev):
        print(f"[{a.host}] indexnow: 배포 전 사이트맵 없음 → 건너뜀"); return
    urls = changed(prev, cur, a.host)
    if not urls:
        print(f"[{a.host}] indexnow: 새 글·수정 글 없음"); return
    if len(urls) > MAX_AUTO:
        print(f"::warning::[{a.host}] indexnow: 변경 {len(urls)}건 > {MAX_AUTO} → 자동 통보 안 함(Actions indexnow 로 수동 전송)"); return
    if a.dry_run:
        print(f"[{a.host}] indexnow(dry-run): {len(urls)}건"); [print("  " + u) for u in urls[:10]]; return
    body = json.dumps({"host": a.host, "key": a.key, "keyLocation": f"https://{a.host}/{a.key}.txt", "urlList": urls}).encode("utf-8")
    req = urllib.request.Request(ENDPOINT, data=body, method="POST", headers={"Content-Type": "application/json; charset=utf-8", **UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r: code = r.status
    except urllib.error.HTTPError as e: code = e.code
    except Exception as e: code = f"오류 {e}"
    msg = f"[{a.host}] indexnow: 새 글·수정 글 {len(urls)}건 통보 → HTTP {code}"
    print(msg if code in (200, 202) else "::warning::" + msg)

if __name__ == "__main__":
    try: main()
    except Exception as e: print(f"::warning::indexnow 통보 중 오류: {e}")
    sys.exit(0)
