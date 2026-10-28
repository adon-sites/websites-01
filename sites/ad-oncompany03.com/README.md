# ad-oncompany03.com — 애드온 마케팅 사이트 (ad-oncompany03)

애드온 마케팅 사이트 `adon-hospital-10`(아카이브 adon-company01)를 2026-10-21 독립 정적 저장소로 이전한 것. Cloudflare Pages 설정: 빌드 명령 없음, 출력 디렉터리 `dist`.

- `dist/` — 배포되는 정적 결과물(481개 파일: 홈·블로그·카테고리·sitemap·rss·이미지). 이전 시점의 공개본과 바이트 단위로 동일하게 재생성됨.
- `content/reviewed-articles.json` — 이전 시점까지의 글 357편(published 165편, 나머지는 기존 공개 목록에 포함된 private_ready). 수정하지 않음.
- `content/posts/*.md` — 이전 이후 추가되는 글. frontmatter(title, short_title 선택, description, category, date `+09:00`) + `## ` 소제목 4~7개, 문단은 빈 줄로 구분.
  category는 `content/categories.json`의 이름 중 하나: `검색·SEO` / `관절·근골격 건강` / `귀·청력 건강` / `눈 성형·미용` / `눈·시력 건강` / `마케팅·협업 운영` / `매장·서비스 이용` / `방문 안내` / `법률·절차 안내` / `블로그 편집` / `블로그·콘텐츠 편집` / `사이트 검색` / `상담·예약 안내` / `생활·주거 서비스` / `성과 해석` / `성과·분석` / `여성 건강` / `치아·구강 건강` / `카페·커뮤니티 운영` / `커뮤니티 의견 해석` / `플레이스·지역 정보` / `피부 건강` / `협업 기준` / `홈페이지·사용성`.
- `content/link-bundle.json` — 새 글 하단 "관련 사이트 안내"에 들어가는 46개 링크(병원 7 + 신규 12 + 마케팅 27, 순서 고정). 기존 글의 링크는 변경하지 않음.
- `content/company.json`, `carousel.json`, `categories.json`, `design.json`, `homepage-editorial.json`, `publication*.json`, `keyword-site-mapping.json` 등 — 생성기가 읽는 설정.
- 생성: `python3 scripts/build.py` → dist 전체 재생성(마크다운 글은 목록 맨 앞·카테고리·sitemap·rss에 포함, 미래 날짜 글 보류, 46개 링크 자동 삽입, 날짜 표시·정렬·디자인·홈 편집본·이미지 최적화 후처리 포함). Pillow 필요.
- 원문 카탈로그·검수 도구(`tools/check_md.py`, `tools/pick_source.py`)·지침(GUIDE.md, PROTECTED.md)은 `sources` 브랜치: `git worktree add ../ad-oncompany03-sources sources`.
- 원래 사이트의 README는 `ORIGINAL_README.md`, 운영 문서는 `docs/`.
