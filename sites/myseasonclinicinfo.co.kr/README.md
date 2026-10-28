# myseasonclinicinfo.co.kr — 대구 나의계절의원 필러 정보 사이트

GPT/Sites에서 구축된 사이트를 2026-10-21 정적 저장소로 이전한 것. Cloudflare Pages 설정: 빌드 명령 없음, 출력 디렉터리 `dist`.

- `dist/` — 배포되는 정적 결과물 (홈·대표 글 6편·시술 안내 6·카테고리 6·블로그 22쪽·글 436편). 이전 시점의 공개본과 바이트 단위로 동일하게 재생성됨.
- `content.json` — 홈 대표 카드·대표 글 6편(`/journal/<slug>/`, `/treatments/<slug>/`, `/category/<slug>/`). 수정하지 않음.
- `publication/approved.json` + `publication/state.json` — 이전 시점까지 발행된 승인 원고 430편(`/journal/myseason-001/` … `myseason-430/`)과 발행 일시 장부. 수정하지 않음.
- `content/posts/*.md` — 이전 이후 추가되는 글. frontmatter(title, description, category, date, short_title 선택) + `## ` 소제목 4~7개, 문단은 빈 줄 구분.
  category는 홈 대표 6주제 `상담 기준` / `제품·시술 계획` / `시술 구분·주의사항` / `관자놀이` / `볼` / `턱` 중 하나(해당 `/category/…/` 목록에도 실림).
- `publication_renderer.py`, `home*.py`, `homepage-*.json/css`, `scripts/optimize_first_visit.py` — 글·홈 렌더링 단계. 수정하지 않음.
- 생성: `python3 build.py` → dist 전체 재생성 (글 하단 백링크 `나의계절의원 안내: 대구필러 → http://myseasonclinicinfo.co.kr` 자동 삽입, 블로그 목록 맨 앞에 새 글, sitemap/rss 갱신, 미래 날짜 글 보류). `<title>`은 short_title이 있으면 그것(접미사 없음), 없으면 `제목 | 나의계절의원`.
- 원문·검수 도구는 `sources` 브랜치.
