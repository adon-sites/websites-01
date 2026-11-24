# IndexNow (네이버)
- 키: `hosting/static-host/worker.js` 의 `INDEXNOW_KEY` (공개 값). Worker 가 모든 사이트의 `/<키>.txt` 에 키 한 줄을 응답한다.
- 전송 주소: `https://searchadvisor.naver.com/indexnow` (indexnow.org 참여 검색엔진 목록의 Naver 항목).
- 수동 전송: Actions `indexnow` 워크플로 (domains, dry_run). `indexnow_submit.py` 가 사이트맵의 주소를 500개씩 보낸다.
- 응답: 200/202 접수 · 400 형식 오류 · 403 키 불일치 · 422 주소·호스트 불일치 · 429 과다 요청.
