# brandnewclinicinfo.co.kr — 강남 브랜뉴의원 소프웨이브 정보 사이트

GPT/Sites에서 구축된 사이트를 2026-10-21 정적 저장소로 이전한 것. Cloudflare Pages 설정: 빌드 명령 없음, 출력 디렉터리 `dist`.

- `dist/` — 배포되는 정적 결과물 (홈·대표 글 6편·시술 안내 6·카테고리 6·블로그 23쪽·글 451편). 이전 시점의 공개본(라이브)과 동일하게 재생성됨: Sites 스냅샷 dist에 라이브 사이트의 키워드 치환(`applyBrandnewKeywords`: 홈 `<title>` "브랜뉴클리닉ㅣ강남온다리프팅ㅣ강남소프웨이브", h1 "강남온다리프팅 · 강남소프웨이브", 헤더 브랜드·og:site_name·rss 채널 제목)을 적용한 결과와 바이트 단위로 동일.
- `content.json` — 홈 대표 카드·대표 글 6편(`/journal/<slug>/`, `/treatments/<slug>/`, `/category/<slug>/`). 수정하지 않음.
- `publication/manuscripts/*.txt` + `publication/manifest.json` + `publication/released.json` — 이전 시점까지 발행된 승인 원고 445편(`/journal/brandnew-001-5fad78b3/` 형식, 원문 바이트 그대로)과 발행 일시 장부. 수정하지 않음.
- `content/posts/*.md` — 이전 이후 추가되는 글. frontmatter(title, description, category, date, short_title 선택) + `## ` 소제목 4~7개, 문단은 빈 줄 구분.
  category는 홈 대표 6주제 `시술 원리` / `상담 기준` / `통증·시술 과정` / `회복·경과` / `시술 선택` / `시술 전 확인` 중 하나(해당 `/category/…/` 목록에도 실림).
- `publication/render.py`, `home*.py`, `homepage-*.json/css`, `scripts/optimize_first_visit.py` — 글·홈 렌더링 단계. 수정하지 않음.
- 생성: `python3 build.py` → dist 전체 재생성 (글 하단 백링크 `소프웨이브 → https://brandnewclinicinfo.co.kr/` 자동 삽입, 블로그 목록 1쪽 대표 6편 다음에 새 글(최신순), sitemap/rss 갱신, 미래 날짜 글 보류, 마지막에 키워드 치환). `<title>`은 short_title이 있으면 그것(접미사 없음), 없으면 `제목 | 브랜뉴의원`.
- 원문·검수 도구는 `sources` 브랜치.
