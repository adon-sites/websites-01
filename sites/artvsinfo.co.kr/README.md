# artvsinfo.co.kr — 부산 아트의원 정보 사이트

Sites(vinext/Next.js 16 SSR)로 운영되던 사이트를 2026-10-21 정적 저장소로 이전한 것. Cloudflare Pages 설정: 빌드 명령 없음, 출력 디렉터리 `dist`.

- `dist/` — 배포되는 정적 결과물 (홈·about·contact·시술 안내 6·블로그 목록/페이지/주제·글 전체·404·robots·sitemap·rss). 글·목록·시술 페이지는 이전 시점의 공개 HTML과 (클라이언트 런타임 제거 외) 동일하게 재생성됨 — 아래 "이전 시점과의 차이" 참고.
- `content/posts.json` — 이전 시점까지 발행된 글 1,216편 (수정하지 않음). `content/reserve.json` — 미승인 원고 14편(공개 대상 아님, 수정·발행 금지).
- `content/posts/*.md` — 이전 이후 추가되는 글. frontmatter(title, description, category, date, short_title 선택) + `## ` 소제목 4~7개(문단은 빈 줄 구분). 마지막에 `## 상담 전 확인할 내용` + `- ` 항목을 두면 체크리스트로 쓰이고, 없으면 기본 3항목이 들어간다.
  category는 `보톡스` / `필러` / `입술필러` / `이마필러` / `실리프팅` / `쥬베룩` 중 하나(블로그 주제·시술 페이지 연결에 그대로 쓰임).
- `content/site-data.json` — 시술 6종, 가이드 본문, 관련 글 규칙(readingPaths), 대표 글 6편, 이미지 정보. `homepage-original.json`·`homepage-cost-guide.json` — 홈 본문 데이터. `templates/*.css` — 라이브에서 가져온 컴파일 CSS(수정하지 않음). `public/` — 이미지·폰트·favicon·`_headers`·`_redirects`.
- `site-config.json` — origin, 색인 허용(`indexingEnabled`), 공개 시작 시각(`publicationStartAt`), 네이버 소유확인 값, 블로그 URL 형식.
- 생성: `python3 scripts/build.py` → dist 전체 재생성 (글 하단 자사 키워드 링크 `부산필러`(시술별 키워드) → `https://artvsinfo.co.kr/` 자동 삽입, 블로그 목록·주제·sitemap/rss 갱신, 미래 날짜 글 보류, KST 하루 30편 초과 시 중단). `ART_VERIFY=1 python3 scripts/build.py` 는 라이브 비교용(미색인·`?page=`·`?topic=` URL) 출력을 `dist-verify/`에 만든다.
- 원문·검수 도구는 `sources` 브랜치.

## URL
- 글: `/journal/<slug>` (파일 `dist/journal/<slug>.html`, Cloudflare Pages가 확장자 없는 주소로 제공). 시술: `/treatments/<slug>`, `/about`, `/contact`.
- 블로그: `/blog`, `/blog/page/N`, `/blog/topic/<treatment>`, `/blog/topic/<treatment>/page/N`. 이전의 `/blog?page=N&topic=…` 주소는 정적 호스팅에서 구분할 수 없으므로 `blog.html`의 작은 스크립트가 같은 내용의 경로형 주소로 보낸다. `/journal` → `/blog`, `/favicon.ico` → `/favicon.png` 는 `_redirects`.

## 이전 시점과의 차이 (의도된 것)
1. Next/vinext 클라이언트 런타임(`/_next/static/chunks/*.js`, modulepreload, RSC payload `<script>`, 스트리밍 placeholder)은 넣지 않는다. 사이트에 React로 동작하는 요소가 없어(메뉴는 `<details>`) 표시·동작은 같다.
2. 스트리밍으로 body 끝에 붙던 `<title>`·meta·icon·canonical 묶음을 `<head>`에 둔다(`data-vinext-streamed-icon` 속성 제거).
3. 이전 시점(2026-10-21) 라이브는 런타임 설정이 빠진 상태로 `noindex, nofollow`·`robots.txt Disallow: /`·날짜 없음으로 응답하고 있었다. 저장소는 운영 기록(OPERATIONS.md, 런타임 설정 revision 5: SEARCH_INDEXING=enabled, PUBLICATION_START_AT=2026-09-09T07:10:44.613Z)대로 **색인 허용 상태**로 생성한다: robots meta 없음, `robots.txt Allow: /`, 글·목록·홈 카드에 공개 날짜(`<time>`), sitemap `lastmod`, rss `pubDate`, Article JSON-LD `datePublished`, `naver-site-verification` meta. 글 순서(목록·이전/다음)는 공개 시각순. `indexingEnabled: false`로 바꾸면 라이브와 같은 미색인 출력이 된다.
4. 블로그 페이지 주소가 쿼리 문자열에서 경로로 바뀐다(위 URL 참고).
