#!/usr/bin/env python3
"""사이트맵의 글 주소를 네이버 IndexNow로 통보한다.

사용법:
    python3 indexnow_submit.py <IndexNow키> <도메인> [<도메인> ...]
    python3 indexnow_submit.py <IndexNow키> --dry-run <도메인>

사전 조건:
    각 도메인 루트에 https://<도메인>/<키>.txt 파일이 있고, 내용이 키 문자열 한 줄이어야 한다.
"""
import json
import re
import sys
import urllib.request

ENDPOINT = "https://searchadvisor.naver.com/indexnow"
BATCH = 500  # 한 번에 보내는 주소 수 (규격상 최대 10,000)
# 통보에서 제외할 목록성 페이지
SKIP = re.compile(r"/blog/page/|/blog/topic/|/blog/category/|/category/")
UA = {"User-Agent": "indexnow-submit/1.0"}


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def sitemap_urls(domain):
    xml = fetch(f"https://{domain}/sitemap.xml")
    locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)
    # 사이트맵 인덱스면 하위 사이트맵을 펼친다
    if "<sitemapindex" in xml:
        urls = []
        for sub in locs:
            urls += re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", fetch(sub))
        locs = urls
    return [u for u in locs if not SKIP.search(u)]


def key_file_ok(domain, key):
    try:
        return fetch(f"https://{domain}/{key}.txt").strip() == key
    except Exception:
        return False


def submit(domain, key, urls):
    body = json.dumps({
        "host": domain,
        "key": key,
        "keyLocation": f"https://{domain}/{key}.txt",
        "urlList": urls,
    }).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT, data=body, method="POST",
        headers={"Content-Type": "application/json; charset=utf-8", **UA},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]
    if len(args) < 2:
        sys.exit(__doc__)
    key, domains = args[0], args[1:]

    for domain in domains:
        if not key_file_ok(domain, key):
            print(f"[{domain}] 키 파일 없음 또는 내용 불일치 → 건너뜀")
            continue
        urls = sitemap_urls(domain)
        print(f"[{domain}] 통보 대상 {len(urls)}건")
        if dry:
            continue
        for i in range(0, len(urls), BATCH):
            code = submit(domain, key, urls[i:i + BATCH])
            # 200/202 접수, 400 형식 오류, 403 키 불일치, 422 주소·호스트 불일치, 429 과다 요청
            print(f"  {i + 1}~{min(i + BATCH, len(urls))}: HTTP {code}")
            if code not in (200, 202):
                print("  접수 실패 → 이 도메인 중단")
                break


if __name__ == "__main__":
    main()
