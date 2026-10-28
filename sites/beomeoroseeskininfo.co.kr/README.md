# beomeoroseeskininfo.co.kr — 대구 범어로제피부과 정보 사이트

GPT/Sites에서 구축된 사이트를 2026-10-21 정적 저장소로 이전한 것. Cloudflare Pages 설정: 빌드 명령 없음, 출력 디렉터리 `dist`.

- `dist/` — 배포되는 정적 결과물 (홈·소개·오시는 길·블로그·카테고리·글 전체). 이전 시점의 공개본과 바이트 단위로 동일하게 재생성됨.
- `content.json` — 이전 시점까지 발행된 글 709편 (수정하지 않음). 대표 글 6편(`featured`)은 홈 카드로 쓰인다.
- `content/posts/*.md` — 이전 이후 추가되는 글. frontmatter(title, description, category, date, short_title 선택) + `## ` 소제목 4~7개.
  category는 글이 실릴 `/category/<group>/` 페이지의 group 값: `skin-guide`(피부질환) / `acne`(여드름·모공·흉터) / `acne-scars`(여드름·모공·흉터) / `pigmentation`(기미·색소) / `thermage`(써마지·탄력) / `ultherapy`(울쎄라·초음파) / `lifting`(주름·탄력) / `hair-removal`(제모) / `skinboosters`(피부 시술) 중 하나.
- `site-config.json`, `home*.py/json/css` — 홈 레이아웃·상세·비용 안내 데이터 (수정하지 않음).
- 생성: `python3 build.py` → dist 전체 재생성 (글 하단 백링크 `대구피부과 → https://beomeoroseeskininfo.co.kr/` · `범어로제피부과 → https://beomeo.roseeskin.com/` 자동 삽입, sitemap/rss 갱신, 미래 날짜 글 보류, KST 하루 30편 초과 시 중단).
- 원문·검수 도구는 `sources` 브랜치.

## 키워드 재겨냥 (2026-10-23)
- 사이트 키워드: **대구써마지 · 대구울쎄라** (대구피부과는 beomeorosee.co.kr 담당). 허브: `/대구써마지/`(category thermage), `/대구울쎄라/`(category ultherapy) — build.py가 생성.
- 홈(dist/index.html)은 `content/home.json` → `tools/build_home.py`가 생성(build.py 끝에서 자동 실행). 홈 문구는 home.json에서만 수정. `home-assets/`, `content/site.json` 수정 금지.
- 새 글 제목은 "대구써마지" 또는 "대구울쎄라"로 시작, category는 thermage / ultherapy / lifting 중 하나.
