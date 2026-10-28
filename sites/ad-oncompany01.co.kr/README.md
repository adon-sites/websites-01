# ad-oncompany01.co.kr — 애드온 마케팅 사이트 (ad-oncompany01)

애드온 COMPANY01 사이트(아카이브 adon-company01 `migration/source.tar.gz.part*` = `adon-adviser-reference`)를 2026-10-21 독립 정적 저장소로 이전한 것. Cloudflare Pages 설정: 빌드 명령 없음, 출력 디렉터리 `dist`.

- `dist/` — 배포되는 정적 결과물(1510개 파일). 라이브(Cloudflare `build_cloudflare.mjs` 결과 = 원본 dist + 공용 헤더 로고 `/brand/ad-on-logo.svg`)와 바이트 단위로 동일하게 재생성됨. CMS Worker(`_worker.js`, `_routes.json`, `.admin-runtime`)는 포함하지 않음.
- `content/articles-adviser.txt`, `content/adviser-batch-*.txt` — 이전 시점까지의 원고 1,162편(`@@ ` 블록, 경로 `/2026/09/20/<slug>/`). `content/health-4452-articles.json` — 배정 글 165편(`/blog/<slug>/`). 수정하지 않음.
- `content/semantic-reviews.json`, `rewrite-audit.json`, `publication.json`, `publication-receipt.json`, `adviser-source-index.json` — 기존 글의 검수·공개 상태 근거(생성기가 읽음). 수정하지 않음.
- `content/posts/*.md` — 이전 이후 추가되는 글(`/blog/<slug>/`). frontmatter(title, short_title 선택, description, category, date `+09:00`) + `## ` 소제목 4~7개, 문단은 빈 줄로 구분.
  이 사이트에는 카테고리 페이지가 없다. category는 기존 글이 쓰는 카테고리명 중 하나여야 하며, 건강정보 글은 `치아·구강 건강` / `피부 건강`을 쓴다.
- `content/link-bundle.json` — 새 글 하단 "관련 사이트 안내"에 들어가는 46개 링크(병원 7 + 신규 12 + 마케팅 27, 순서 고정). 기존 글의 링크는 변경하지 않음.
- 생성: `python3 scripts/build.py` → dist 전체 재생성(마크다운 글은 /blog/ 목록 맨 앞·sitemap·rss에 포함, 미래 날짜 글 보류, 46개 링크 자동 삽입, 날짜 표시·정렬·디자인·홈 편집본·홈 글꼴 서브셋·이미지 최적화·헤더 로고 후처리 포함). Pillow 필요. 홈 글꼴 서브셋은 `content/home-fonts.json`과 `dist/fonts/`를 재사용하므로 네트워크가 필요 없다.
- 원문 카탈로그·검수 도구(`tools/check_md.py`, `tools/pick_source.py`)·지침(GUIDE.md, PROTECTED.md)은 `sources` 브랜치: `git worktree add ../ad-oncompany01-sources sources`.
- 원래 프로젝트의 AGENTS.md/docs는 `docs/`.
