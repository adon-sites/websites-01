# 운영 사이트 상호 링크

2026-09-29 사용자 요청: 최초 대표 키워드로 27개 운영 사이트를 서로 연결한다.

`content/keyword-site-mapping.json`의 URL과 label을 그대로 사용한다. 각 사이트의 `content/company.json` marketingLinks에는 자기 도메인을 제외한 26개만 포함한다. 동일한 대표 키워드를 쓰는 사이트가 있어도 목적지 도메인이 다르면 유지한다.

`scripts/build.py`가 호출하는 `scripts/apply_keyword_settings.py`가 메인·블로그 목록·카테고리·개별 글·RSS에 링크를 재적용한다. 기존 마케팅 서비스 안내 영역을 교체하여 중복 영역을 만들지 않는다. 새 글 발행 시에도 이 경로를 유지한다. 병원 링크는 별도 설정과 사용자 승인 규칙을 따른다.

발행 전에 `python scripts/verify_network_links.py`로 모든 HTML과 RSS의 26개 목적지·대표 키워드·자기 도메인 제외·중복 영역 없음을 검증한다. 이 설정은 검색 수집·색인·노출의 확인을 의미하지 않는다.
