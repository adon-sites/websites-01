# IndexNow (네이버)
- 키: `hosting/static-host/worker.js` 의 `INDEXNOW_KEY` (공개 값). Worker 가 모든 사이트의 `/<키>.txt` 에 키 한 줄을 응답한다.
- 전송 주소: `https://searchadvisor.naver.com/indexnow` (indexnow.org 참여 검색엔진 목록의 Naver 항목).
- 수동 전송: Actions `indexnow` 워크플로 (domains, dry_run). `indexnow_submit.py` 가 사이트맵의 주소를 500개씩 보낸다.
- 응답: 200/202 접수 · 400 형식 오류 · 403 키 불일치 · 422 주소·호스트 불일치 · 429 과다 요청.
- 자동 통보: deploy 워크플로가 사이트 배포 직전 사이트맵과 이번 빌드 사이트맵을 비교해 새 글·수정 글 주소만 보낸다(`notify_changed.py`). 한 번에 300건이 넘는 변경과 `exclude.txt` 의 사이트·묶음은 보내지 않는다. 발행 도구·예약 작업은 그대로.
