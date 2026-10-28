# cjwelldentalinfo.co.kr — 청주웰치과 정보 사이트 (청주치과)

Sites(vinext/Next.js 16 SSR + Cloudflare Worker + D1)로 운영되던 사이트를 2026-10-21 정적 저장소로 이전한 것. Cloudflare Pages 설정: 빌드 명령 없음, 출력 디렉터리 `dist`.

- `dist/` — 배포되는 정적 결과물 (홈·about·visit·진료 안내 6·블로그 목록/페이지/주제·글 전체·404·robots·sitemap·rss). 2026-10-21 라이브 공개 HTML과 (클라이언트 런타임 제거 외) **byte 단위로 동일**하게 재생성됨 — 아래 "이전 시점과의 차이" 참고.
- `content/posts.json` — 이전 시점까지 발행된 글 736편 (수정하지 않음). 691편은 아카이브(`content/drafts.json`)에서, 마지막 45편(2026-10-20 11:09 KST ~ 10-21 16:07 KST 공개분)은 아카이브 이후 라이브에서만 발행된 글로 검수 재고(`editorial-reserve/20260929/reserve.json`)의 본문을 라이브 공개 시각과 함께 옮긴 뒤 라이브 HTML 해시와 대조해 확인한 것(`origin: live-crawl-2026-10-21`).
  `content/reserve.json` — 아직 발행되지 않은 검수 원고 136편(reviewed_reserve 134 + held 2). 공개 대상이 아님, 수정·발행 금지(동결).
- `content/posts/*.md` — 이전 이후 추가되는 글. frontmatter(title, description, category, date, short_title 선택, sources 선택) + `## ` 소제목 4~7개(문단은 빈 줄 구분).
  category는 `임플란트` / `치아교정` / `사랑니` / `치아미백` / `예방·잇몸관리` / `턱관절` 중 하나(블로그 주제·진료 안내 페이지 연결에 그대로 쓰임). `sources`는 쉼표로 구분한 https 주소(글 하단 "참고 자료"로 표시, 생략 가능).
- `content/treatments.json` — 진료 안내 6종(본문·FAQ·근거 링크). `homepage-original.json`·`homepage-cost-guide.json`·`homepage-image-variants.json` — 홈 본문·비용 안내·카드 이미지 srcset. `templates/*.css` — 라이브 번들에서 추출한 컴파일 CSS(라이브 inline `<style>`과 동일, 수정하지 않음). `public/` — 이미지·아이콘·favicon·`_headers`·`_redirects`.
- `site-config.json` — origin, 색인 허용(`indexingEnabled`), 발행 시작 시각(`publicationStartAt`), 네이버 소유확인 값(라이브 head의 값), 블로그 URL 형식.
- 생성: `python3 scripts/build.py` → dist 전체 재생성 (글 하단 자사 키워드 링크 `청주치과` → `https://cjwelldentalinfo.co.kr/` 자동 삽입(기존 글·진료 안내·about와 같은 마크업), 블로그 목록·주제·sitemap/rss 갱신, 같은 진료의 기존 글 "함께 읽는 치아 건강정보"(최신 3편)와 진료 안내의 "함께 읽으면 좋은 글" 갱신 — 라이브의 동적 동작과 같음, 미래 날짜 글 보류, KST 하루 30편 초과 시 중단). `WELL_VERIFY=1 python3 scripts/build.py` 는 라이브 비교용(`?page=`·`?topic=` 쿼리 주소, 리다이렉트 스크립트 없음) 출력을 `dist-verify/`에 만든다.
- 원문·검수 도구는 `sources` 브랜치.

## 이전 시점 상태 (2026-10-21 확인)
- 라이브는 색인 허용 상태였다: `robots` meta `index, follow, max-image-preview:large`, `robots.txt Allow: / · Disallow: /review`, sitemap 746건(정적 10 + 글 736), `naver-site-verification` meta 있음. 운영 설정(migration-config/runtime-settings.json revision 10): SEARCH_INDEXING=enabled, PUBLICATION_START_AT=2026-09-15T22:00:00+09:00, PUBLICATION_LIMIT=152, 간격 48분, NAVER_VERIFIED=true. 저장소도 같은 색인 허용 상태로 생성한다(`indexingEnabled: false`로 바꾸면 원본과 같이 noindex·robots Disallow·글 비공개가 된다).
- D1 데이터베이스(`analytics_daily`, `publication_schedule`)에는 글 본문이 없다. 글 본문은 `content/drafts.json`(TS/JSON)에, 발행 시각은 환경 변수(PUBLICATION_START_AT + 48분 슬롯 / 배치별 releaseAt)에 있었다. 방문 통계·리뷰어 인증(`/review`, ChatGPT 로그인)은 정적 사이트에 없다.
- 중앙 CMS 글(`/manual/`): "아직 발행된 글이 없습니다" (0편).
- 예약(미래) 글 0편. 발행되지 않은 검수 재고 136편은 `content/reserve.json`에 동결.

## URL
- 글: `/articles/<slug>` (파일 `dist/articles/<slug>.html`, Cloudflare Pages가 확장자 없는 주소로 제공). 진료 안내: `/treatments/<slug>`, `/about`, `/visit`. `/articles` → `/blog` 는 `_redirects`(301; 원본은 308).
- 블로그: `/blog`, `/blog/page/N`, `/blog/topic/<slug>`, `/blog/topic/<slug>/page/N` (주제 slug: `about`, `implants`, `orthodontics`, `wisdom-teeth`, `whitening`, `prevention`, `jaw-joint`). 이전의 `/blog?page=N&topic=…` 주소는 정적 호스팅에서 구분할 수 없으므로 `blog.html`의 작은 스크립트가 같은 내용의 경로형 주소로 보낸다. 주제·2페이지 이후는 원본과 같이 `noindex, follow`.
- 일부 이전 글의 treatmentSlug(`pediatric`, `implant`, `소아치과` 등 9종)는 진료 안내 6종에 없다. 원본은 이 글의 카테고리를 "치아 건강정보"로 표시하고 `/blog?topic=<그 값>`은 전체 목록을 보여줬다. 저장소는 그 링크 주소(`/blog/topic/<퍼센트 인코딩 값>`)에 `/blog` 1페이지 사본을 둔다. 값은 수정하지 않는다.

## 이전 시점과의 차이 (의도된 것)
1. Next/vinext 클라이언트 런타임(`/_next/static/chunks/*.js` script, modulepreload link, RSC payload·vinext navigation `<script>`)은 넣지 않는다. 사이트에 React로 동작하는 요소가 없어(메뉴·FAQ는 `<details>`) 표시·동작은 같다. 방문 통계 전송(`/api/metrics`)도 없다.
2. 블로그 페이지 주소가 쿼리 문자열에서 경로로 바뀐다(위 URL 참고).
3. 홈 응답 캐시 헤더(`X-Well-Home-Cache` 등)와 `Cache-Control: no-store`는 Worker 기능이라 없다. `_headers`는 원본 public의 것(이미지·아이콘 캐시)을 그대로 둔다.

검증 방법: 라이브 HTML에서 `<script>`(ld+json 제외)와 `<link rel="modulepreload">`(뒤따르는 줄바꿈 포함)만 제거한 결과와 `dist-verify/`의 파일을 SHA-256으로 비교. sitemap 746개 주소 전부 + 블로그 페이지 134개 + 404 + robots.txt + sitemap.xml + rss.xml 일치(2026-10-21 16:40 KST 기준).
