import json,pathlib,re
R=pathlib.Path(__file__).resolve().parents[1]
refs=[p.name for p in (R/'content/reference').glob('*.txt')]
themes=[
('시흥 임플란트','임플란트','상실한 치아의 빈 공간과 주변 치아','시흥임플란트'),
('정왕동 임플란트','임플란트','잇몸뼈와 식립 위치','정왕동임플란트'),
('배곧 임플란트','임플란트','브릿지와 임플란트 선택','배곧임플란트'),
('오이도역 임플란트','임플란트','수술 전 검사와 일정','오이도역치과'),
('시흥 앞니 임플란트','임플란트','앞니의 심미와 맞물림','시흥임플란트'),
('시흥 어금니 임플란트','임플란트','어금니 저작 기능과 잇몸','시흥임플란트'),
('시흥 임플란트 뼈이식','임플란트','뼈이식 필요성 및 회복','시흥임플란트'),
('시흥 임플란트 관리','임플란트','보철물 주변 잇몸 위생','시흥임플란트'),
('시흥 사랑니','사랑니발치','발치 여부와 관찰 기준','시흥사랑니'),
('정왕동 매복사랑니','사랑니발치','매복 위치 및 주변 신경','정왕동사랑니'),
('배곧 사랑니','사랑니발치','부분 맹출과 음식물 끼임','배곧사랑니'),
('월곶 사랑니','사랑니발치','주변 어금니와 잇몸 염증','월곶 사랑니'),
('시흥 사랑니 발치 후','사랑니발치','지혈·식사와 회복 과정','시흥 사랑니 발치'),
('정왕역 사랑니','사랑니발치','반복되는 붓기와 청결 관리','정왕역치과'),
('시흥 충치치료','충치·신경치료','손상 범위와 자연치아 보존','시흥_충치치료'),
('정왕동 충치치료','충치·신경치료','기존 수복물과 이차 충치','정왕동충치치료'),
('시흥 큐레이 검사','충치·신경치료','형광 반응의 역할과 한계','시흥 충치치료 큐레이'),
('배곧 충치치료','충치·신경치료','치아 사이와 어금니의 초기 변화','시흥배곧충치치료'),
('시흥 신경치료','충치·신경치료','치아 내부 상태와 치료 순서','시흥충치치료'),
('안산 충치치료','충치·신경치료','레진·인레이·크라운 비교','안산충치치료'),
('시흥 치아 균열','충치·신경치료','씹을 때 통증과 균열 검사','시흥 큐레이'),
('시흥 구강검진','치아관리','증상이 없을 때 검진 주기','치과 정보 2'),
('정왕동 치과 첫 방문','치아관리','증상 기록과 약물 이력','정왕동치과'),
('시흥 잇몸 관리','치아관리','양치 시 출혈과 치태 관리','치과 정보글'),
('시흥 보철 관리','치아관리','수복물 맞물림과 사후검진','시흥치과')]
angles=[
('증상이 없을 때','증상이 없더라도 어떤 변화를 점검해야 하는가','육안으로 알기 어려운 부분과 검진이 필요한 조건','관찰을 선택했다면 다음 확인 시점'),
('상담을 시작할 때','상담 전에 준비할 증상과 치료 이력','검사 결과에서 담당자에게 물어볼 세부 내용','치료 목표를 본인의 생활과 연결하는 방법'),
('검사 결과를 볼 때','어떤 검사가 왜 필요한지','영상·진찰과 실제 증상 사이의 차이','검사의 한계를 설명받고 계획을 세우는 순서'),
('치료 방법을 비교할 때','현재 상태에서 가능한 선택지','방법마다 달라지는 방문 횟수와 관리 부담','비용과 위험을 같은 기준으로 비교하는 질문'),
('치료 시기를 정할 때','서두르거나 기다려야 하는 조건','건강 상태와 중요한 일정의 영향','계획이 바뀔 수 있는 검사 결과'),
('진료 후 회복할 때','집에서 지켜야 할 개별 관리 지침','예상 가능한 불편과 연락할 변화의 구분','일상 복귀와 다음 확인 시점'),
('문제가 반복될 때','반복 증상의 시점과 유발 상황 기록','기존 치료 부위와 주변 조직 재평가','다른 원인이나 추가 검사를 질문하는 방법'),
('장기 관리 계획','위생 관리 도구와 검진 간격','상태 변화가 생겼을 때의 연락 기준','다음 방문에서 비교할 기록')]
assert len(themes)==25 and len(angles)==8
existing={p['title'] for p in json.loads((R/'content/posts.json').read_text())}
queue=[]
for i,(keyword,category,focus,hint) in enumerate(themes):
 candidates=[name for name in refs if hint in name]
 if not candidates:
  candidates=[name for name in refs if keyword.split()[0] in name]
 assert candidates,(keyword,hint)
 for j,(angle,q1,q2,q3) in enumerate(angles):
  title=f'{keyword}, {angle} 확인할 {focus}'
  assert title not in existing
  queue.append({'id':f'nd-{i+1:02d}-{j+1:02d}','title':title,'category':category,'targetKeyword':keyword,'angle':angle,'focus':focus,'sourceReferences':candidates[:3],'outline':[q1+' — '+focus,q2+' — '+focus,q3+' — '+focus],'status':'planned-not-written','publication':'not-published','imagePolicy':'text-only'})
assert len(queue)==200 and len({x['title'] for x in queue})==200
(R/'content/editorial-queue-200.json').write_text(json.dumps(queue,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'editorial_slots':len(queue),'distinct_titles':len({x['title'] for x in queue}),'status':'planned-not-written','published_additions':0},ensure_ascii=False))
