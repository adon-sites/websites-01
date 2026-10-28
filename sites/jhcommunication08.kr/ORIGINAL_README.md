# 애드온 독립 사이트

개별 소유자 전용 사이트입니다. 이 사이트의 원고·설정·이미지·도메인은 다른 사이트와 독립 관리합니다.

- 사이트별 신규 대표 원고 6편과 신규 이미지 6개, 첨부 원고 185편(이미지 없음)
- 대표 카드 → 해당 사이트 상세 글, 블로그 첫 페이지에 대표 6편
- 대표 6편 외 향후 일반 글은 이미지 없는 원고형
- 기준 디자인·색상·글꼴·모바일 메뉴·페이지 이동 방식 유지
- 사업자 정보·상담 이메일·카카오 오픈채팅·포스팅 하단 병원 링크 5개 유지
- 비공개 검토 상태, 검색 차단, 사이트맵·RSS에 글 항목 없음
- 실제 공개 전 발행일 미기입

content/company.json: 사이트 주소·회사·상담·병원 링크
content/reviewed-articles.json: 이 사이트 전용 원고
content/carousel.json: 대표 6편과 이미지 연결
content/publication.json: 검토 및 공개 단계
content/editorial-review.json: 최종 원고 해시와 독립 검수 기록

python scripts/build.py
python scripts/validate.py

공개 전 절차는 docs/publication.md를 참고하세요.

첨부 최종 원고 배포: content/import-manifest.json에 원본 파일명·해시·배정 내역을 기록했습니다. 이번 단계에서는 재작성이나 신규 의미 검수를 수행하지 않았습니다. 비공개 및 검색 차단은 유지합니다.
