# websites-01 — adon-sites 정적 사이트 샤드 01

`sites/<도메인>/` 폴더 하나 = 사이트 하나. 규칙은 `exqq77-create/site-ops` 의 `runbooks/SCALE_DESIGN.md`, 등록부는 `site-ops/registry/sites.csv`.

각 `sites/<도메인>/site.json` 의 `builder` 로 빌드·배포 방식이 갈린다.

| builder | 뜻 | 커밋되는 것 | 배포 워크플로가 하는 일 |
|---|---|---|---|
| `python-generator` | 병원 7 · 마케팅 27 (content/posts/*.md → scripts/build.py 또는 build.py) | 소스 + `static/`(빌드가 만들지 않는 정적 파일: 이미지·CSS·favicon, jh04/05/06 보존 글) | `dist/` 비움 → `static/` 복사 → 빌드 → `dist/` 를 R2 `sites/<도메인>/` 로 |
| `static` | 정보 13 (정적 HTML, 생성기 없음) | `public/` 전체 | `public/` 을 그대로 R2 로 |
| `wpstatic` | 365raeon.co.kr(`public/`) · beomeorosee.co.kr(`docs/`) — `tools/wp_static_site.py publish` 로 글 생성, `scripts/build.py` 후처리 | 배포 폴더 전체(원본이자 출력) | `scripts/build.py` 를 제자리에서 실행(멱등) → 배포 폴더를 R2 로 |

- `dist/` 는 `.gitignore`. 원문·GUIDE·검수 도구는 비공개 저장소 `adon-sites/sources-01/<도메인>/`.
- 이 저장소는 **공개**다. 토큰·원문·내부 규칙을 넣지 않는다.
- 2026-10-28 이전 시 49곳 전부 기존 저장소 출력과 바이트 동일(verify.py 변경 0) 확인. 각 site.json 의 `repo_old_commit` 이 그 시점의 기존 저장소 커밋.
