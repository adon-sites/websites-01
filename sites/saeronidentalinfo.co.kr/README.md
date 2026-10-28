# saeronidentalinfo.co.kr — 김해 새론이치과 정보 사이트

GPT/Sites에서 구축된 사이트를 2026-10-21 정적 저장소로 이전한 것. Cloudflare Pages 설정: 빌드 명령 없음, 출력 디렉터리 `dist`.

- `dist/` — 배포되는 정적 결과물 (홈·대표 6페이지·예방진료·블로그 전체). 이전 시점의 공개본과 바이트 단위로 동일하게 재생성됨.
- `content/posts.json` — 이전 시점까지의 글 524편(발행 522편, `scheduled` 2편은 생성기가 내지 않음. 수정하지 않음).
- `content/posts/*.md` — 이전 이후 추가되는 글. frontmatter(title, description, category, date, short_title 선택) + `## ` 소제목 4~7개.
  category는 `임플란트` / `충치·신경치료` / `심미보철` / `턱관절·예방` / `사랑니발치` 중 하나(블로그 카테고리 탭 5개).
- `content/pages.json`, `content/site-sections.json`, `content/image-sources.json`, `site-config.json`, `home*.py/json/css` — 홈·대표 페이지 데이터. `content/route-manifest.json`은 생성기가 매번 다시 쓴다.
- 생성: `python3 scripts/build.py` → dist 전체 재생성 (글 본문 하단 백링크 `김해치과 → https://saeronidentalinfo.co.kr/` 자동 삽입, sitemap/rss 갱신, 미래 날짜 글 보류, 날짜 내림차순 정렬).
- 원문·검수 도구는 `sources` 브랜치.
