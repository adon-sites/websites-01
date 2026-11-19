#!/usr/bin/env python3
"""글 형식 보강(v4, 2026-11-18 17:09 사용자 결정 — 레퍼런스 obgynmarketing 글 구조와 동일):
  제목 H1 반복 + 이미지1, 리드 첫 문장 굵게, H2 번호, 2절 뒤 "{키워드} 실행/확인 순서" 표 + 이미지2, 4절 뒤 "{키워드} 작업/상담 요청" 표,
  마지막 절 뒤 마무리 문단, 자주 묻는 질문 6(키워드 포함), 해시태그 9(#키워드+주제), 관련 정보 링크 블록(병원 사이트). 본문 안 링크 없음.
  (v3 설명 — 대체됨:
  본문 각 H2 섹션 끝에 <h3>○○ 세부 비교</h3> + 3열 표(기존 문장 재배치 + 템플릿),
  2번 섹션 끝 자기 홈 키워드 링크, 4번·마지막 섹션 끝 같은 진료군 자매 사이트 링크,
  본문 뒤 "자주 확인하는 질문" Q&A 6개, 해시태그 9개(#키워드 + 섹션 주제 7 + #지역),
  요약문 뒤 안내 문단 1개. 본문 문장·URL·제목은 바꾸지 않는다. 멱등(이미 보강된 글은 건너뜀).

사용: python3 enrich_post.py <sites.json> <domain> <html 파일...>   (파일을 제자리에서 수정)
      python3 enrich_post.py <sites.json> <domain> --stdin < in.html > out.html
sites.json: {"<domain>": {"keyword","home","region","group","type"(sitegen|gen|wp), ...}, ...}
"""
import json, re, sys, html, hashlib
from pathlib import Path

MARK = '<!-- enrich:v4 -->'
OLD_MARKS = ['<!-- enrich:v3 -->']
IMG_BASE = '/images/enrich/'   # 글별 이미지 2장: {IMG_BASE}{slug}-1.webp(제목 아래), -2.webp(첫 표 아래) — 배포 때 make_images.py 가 생성
HEADER_SETS = [('진행 단계', '필요한 정보', '다음 행동'), ('선택 기준', '확인할 자료', '판단할 점'), ('비교 항목', '상황별 차이', '확인 시기'),
               ('관찰 포인트', '변화 여부', '문의 기준'), ('현재 상황', '구체적인 질문', '후속 점검'), ('우선 확인', '주의할 부분', '대안'), ('준비 항목', '적용 범위', '선택 전 확인')]
ACTIONS = [['상담 전에 정리해 두기', '진료에서 함께 확인', '변화가 있으면 다시 확인', '기록해서 가져가기', '설명을 들은 뒤 결정'],
           ['공식 안내와 비교', '상담에서 직접 질문', '서면으로 받아 두기', '개인 상황에 맞춰 판단', '급하게 정하지 않기'],
           ['첫 상담에서 확인', '검사 결과 뒤 확인', '증상이 바뀌면 확인', '정해진 재진 때 확인', '불편이 이어지면 바로 문의'],
           ['평소와 다르면 문의', '기준을 넘으면 연락', '기록으로 비교', '지정일 전에도 연락 가능', '사진·메모로 남기기'],
           ['지금 상태를 메모', '궁금한 점을 질문으로', '다음 방문 때 점검', '달라진 점을 비교', '경과를 기록'],
           ['먼저 확인', '무리하지 않기', '대안을 함께 상담', '기준을 미리 듣기', '의료진 안내를 따르기'],
           ['미리 준비', '해당되는지 확인', '선택 전에 질문', '조건을 비교', '적용 범위를 물어보기']]
Q_TPL = ['{t}{g} 관련해 변화가 생기면 어떻게 확인하나요?', '{t}{g} 관련해 결정 전에 비교할 정보는 무엇인가요?', '{t}{g} 관련해 언제 다시 확인하는 것이 좋나요?',
         '{t}{g} 관련해 현장 안내와 온라인 설명이 다르면 어떻게 하나요?', '{t}{g} 관련해 후속 일정은 무엇을 기준으로 정하나요?', '{t}{g} 관련해 무엇을 먼저 확인하나요?']
A_TPL = ['{t}에 대한 답은 현재 상태와 검사 결과를 함께 보고 정합니다. 증상이 달라지거나 불편이 이어지면 진료에서 다시 확인해 주세요.',
         '{t}은(는) 글의 기준을 참고하되 개인 상황에 따라 달라집니다. 상담에서 들은 설명과 다른 점이 있으면 그 자리에서 질문해 두세요.',
         '{t}은(는) 한 번에 정하기보다 기록을 모아 비교하는 것이 좋습니다. 기준을 넘는 변화가 있으면 지정된 날 전에도 연락할 수 있습니다.',
         '{t}에 대해서는 공식 안내와 상담 내용을 함께 확인하세요. 온라인 설명과 현장 안내가 다르면 현장 의료진의 설명을 기준으로 삼습니다.',
         '{t}은(는) 검사 결과가 나온 뒤 다음 일정을 정하는 것이 일반적입니다. 예상 기간과 비용 구성은 상담 때 서면으로 받아 두세요.',
         '{t}은(는) 먼저 지금 불편한 점과 시기를 정리하는 데서 시작합니다. 복용 중인 약과 이전 치료 기록이 있으면 함께 알려 주세요.']
PARTICLES = [' 은 ', ' 는 ', '은 ', '는 ', '이 ', '가 ', '을 ', '를 ', '에는 ', '에서 ', '도 ', '와 ', '과 ', '으로 ', '로 ', '의 ']

# ---- 프로파일: clinic(기본) / marketing(애드온 27곳) — 표 머리·행동·FAQ·링크 문단·안내 문단 문구 세트 ----
PROFILES = {
 'clinic': dict(headers=HEADER_SETS, actions=ACTIONS, q=Q_TPL, a=A_TPL,
   intro='이 글에서는 {kw}{g} 관련해 제목에서 제기한 질문을 중심으로 확인할 사항을 구분합니다. 진단이나 치료의 최종 판단은 개인 상황에 대한 전문적인 평가를 바탕으로 해야 합니다.',
   link_self='이와 관련된 기본 정보를 더 살펴보려면 {a} 안내도 참고할 수 있습니다. 링크의 내용과 실제 이용 조건은 별도로 확인해 주세요.',
   link_hub='{a} 상담 전 확인사항은 안내 페이지에 주제별로 정리해 두었습니다. 글마다 다른 상황을 다루므로 현재 상태에 가까운 글을 함께 읽어 보세요.',
   link_sib='지역이 다르거나 비교가 필요하다면 {a} 안내에서 같은 기준으로 정리한 내용을 볼 수 있습니다. 병원마다 진료 방식과 조건이 다르므로 각 병원에서 직접 확인해 주세요.',
   link_client='{a} 안내처럼 주제별로 글을 나눠 정리한 구성을 참고할 수 있습니다. 병원마다 진료 방식과 조건이 다르므로 내용은 각 병원에서 직접 확인해 주세요.',
   faq_title='자주 묻는 질문',
   tblA=('{kw} 확인 순서', ('확인 순서', '살펴볼 대상', '확인할 내용')), tblB=('{kw} 상담 요청', ('진료에서 확인할 일', '판단 기준', '남길 기록')),
   tblB_last=['검사 결과·설명 메모', '복용약·이전 치료 기록', '질문 목록과 답변', '다음 방문 날짜', '달라진 점 기록'],
   q4=['{kw}의 {t} 항목을 비교할 때 조건은 어떻게 맞추나요?', '{kw}에서 {t} 기준을 먼저 정하는 이유는 무엇인가요?', '{kw}의 {t} 내용을 실제 상황에 적용하려면 무엇이 필요한가요?',
       '{kw}의 {t} 내용을 다시 검토할 시점은 언제인가요?', '{kw}에서 {t}{g} 다른 확인 사항을 함께 기록하나요?', '{kw}의 {t} 부분을 별도로 살펴보나요?'],
   a4=['{t}은(는) 현재 상태와 검사 결과를 같은 기준으로 놓고 비교합니다. 증상이 달라지거나 불편이 이어지면 진료에서 다시 확인해 주세요.',
       '{kw}에서 {t} 기준을 먼저 정해 두면 상담에서 들은 설명과 다른 점을 바로 질문할 수 있습니다. 개인 상황에 따라 적용은 달라집니다.',
       '{t}을(를) 적용하려면 지금 불편한 점과 시기, 복용 중인 약과 이전 치료 기록을 정리해 가져가야 합니다.',
       '{t}은(는) 검사 결과가 나온 뒤, 그리고 기준을 넘는 변화가 있을 때 다시 검토합니다. 지정된 날 전에도 연락할 수 있습니다.',
       '{kw}에서는 {t}{g} 함께 달라진 점을 기록으로 남겨 비교하는 것이 좋습니다. 사진·메모로 남기면 다음 진료에서 확인하기 쉽습니다.',
       '{kw}의 {t} 부분은 공식 안내와 상담 내용을 함께 확인하세요. 온라인 설명과 현장 안내가 다르면 현장 의료진의 설명을 기준으로 삼습니다.'],
   close='{kw} 관련 결정은 한 번에 정하기보다 지금까지 확인한 내용과 질문을 정리한 뒤 진료에서 함께 확인하는 것이 좋습니다. 결과와 회복은 개인에 따라 다릅니다.',
   fill_topics=['상담 준비', '검사 시점', '비용 구성', '회복 관리', '재방문 기준', '기록 정리', '주의 사항', '선택 기준', '후속 점검']),
 'marketing': dict(
   headers=[('진행 단계', '필요한 자료', '다음 작업'), ('판단 기준', '확인할 자료', '결정할 점'), ('비교 항목', '상황별 차이', '점검 시기'),
            ('관찰 포인트', '변화 여부', '조정 기준'), ('현재 상황', '구체적인 질문', '후속 점검'), ('우선 확인', '주의할 부분', '대안'), ('준비 항목', '적용 범위', '실행 전 확인')],
   actions=[['작업 전에 정리해 두기', '담당자와 함께 확인', '변화가 있으면 다시 확인', '기록으로 남기기', '검토 뒤 결정'],
            ['기존 자료와 비교', '담당자에게 직접 질문', '문서로 받아 두기', '운영 상황에 맞춰 판단', '급하게 정하지 않기'],
            ['첫 미팅에서 확인', '결과가 나온 뒤 확인', '지표가 바뀌면 확인', '정기 점검 때 확인', '문제가 이어지면 바로 문의'],
            ['평소와 다르면 확인', '기준을 넘으면 공유', '기록으로 비교', '정기 보고 전에도 공유 가능', '캡처·메모로 남기기'],
            ['지금 상태를 메모', '궁금한 점을 질문으로', '다음 점검 때 확인', '달라진 점을 비교', '경과를 기록'],
            ['먼저 확인', '무리하지 않기', '대안을 함께 검토', '기준을 미리 정하기', '가이드라인을 따르기'],
            ['미리 준비', '해당되는지 확인', '실행 전에 질문', '조건을 비교', '적용 범위를 확인하기']],
   q=['{t}{g} 관련해 지표가 달라지면 어떻게 확인하나요?', '{t}{g} 관련해 결정 전에 비교할 자료는 무엇인가요?', '{t}{g} 관련해 언제 다시 점검하는 것이 좋나요?',
      '{t}{g} 관련해 자료마다 설명이 다르면 어떻게 하나요?', '{t}{g} 관련해 후속 일정은 무엇을 기준으로 정하나요?', '{t}{g} 관련해 무엇을 먼저 확인하나요?'],
   a=['{t}에 대한 답은 현재 운영 상황과 확인된 자료를 함께 보고 정합니다. 지표가 달라지거나 문제가 이어지면 담당자와 다시 확인해 주세요.',
      '{t}은(는) 글의 기준을 참고하되 업체 상황에 따라 달라집니다. 미팅에서 들은 설명과 다른 점이 있으면 그 자리에서 질문해 두세요.',
      '{t}은(는) 한 번에 정하기보다 기록을 모아 비교하는 것이 좋습니다. 기준을 넘는 변화가 있으면 정기 보고 전에도 공유할 수 있습니다.',
      '{t}에 대해서는 공식 가이드라인과 실제 운영 자료를 함께 확인하세요. 자료마다 설명이 다르면 최신 공식 안내를 기준으로 삼습니다.',
      '{t}은(는) 결과 자료가 나온 뒤 다음 일정을 정하는 것이 일반적입니다. 예상 기간과 비용 구성은 계약 전에 문서로 받아 두세요.',
      '{t}은(는) 먼저 지금 필요한 작업과 시기를 정리하는 데서 시작합니다. 기존 채널 운영 기록이 있으면 함께 공유해 주세요.'],
   intro='이 글에서는 {kw}{g} 관련해 제목에서 제기한 질문을 중심으로 확인할 사항을 구분합니다. 실제 적용은 각 업체의 운영 상황과 자료를 바탕으로 판단해야 합니다.',
   link_self='이와 관련된 기본 정보를 더 살펴보려면 {a} 안내도 참고할 수 있습니다. 링크의 내용과 실제 서비스 조건은 별도로 확인해 주세요.',
   link_hub='{a} 안내 페이지에 관련 글을 주제별로 정리해 두었습니다. 글마다 다른 상황을 다루므로 현재 상황에 가까운 글을 함께 읽어 보세요.',
   link_sib='다른 채널이나 업종의 사례가 필요하다면 {a} 안내에서 같은 기준으로 정리한 내용을 볼 수 있습니다. 운영 조건은 업체마다 다르므로 각각 확인해 주세요.',
   link_client='정보 페이지 운영 사례로는 {a} 안내처럼 주제별로 글을 나눠 정리한 구성을 참고할 수 있습니다. 병원마다 진료 방식과 조건이 다르므로 내용은 각 병원에서 직접 확인해 주세요.',
   faq_title='자주 묻는 질문',
   tblA=('{kw} 실행 순서', ('검토 순서', '판단 대상', '확인할 내용')), tblB=('{kw} 작업 요청', ('담당자가 확인할 일', '실행 기준', '남길 자료')),
   tblB_last=['검토 메모와 캡처', '변경 이력', '질문 목록과 답변', '정기 점검 일정', '지표 비교표'],
   q4=['{kw}의 {t} 항목을 비교할 때 조건은 어떻게 맞추나요?', '{kw}에서 {t} 기준을 먼저 정하는 이유는 무엇인가요?', '{kw}의 {t} 내용을 실제 상황에 적용하려면 무엇이 필요한가요?',
       '{kw}의 {t} 내용을 다시 검토할 시점은 언제인가요?', '{kw}에서 {t}{g} 다른 확인 사항을 함께 기록하나요?', '{kw}의 {t} 부분을 별도로 살펴보나요?'],
   a4=['{t}은(는) 현재 운영 상황과 확인된 자료를 같은 기준으로 놓고 비교합니다. 지표가 달라지거나 문제가 이어지면 담당자와 다시 확인해 주세요.',
       '{kw}에서 {t} 기준을 먼저 정해 두면 미팅에서 들은 설명과 다른 점을 바로 질문할 수 있습니다. 업체 상황에 따라 적용은 달라집니다.',
       '{t}을(를) 적용하려면 지금 필요한 작업과 시기, 기존 채널 운영 기록을 정리해 공유해야 합니다.',
       '{t}은(는) 결과 자료가 나온 뒤, 그리고 기준을 넘는 변화가 있을 때 다시 검토합니다. 정기 보고 전에도 공유할 수 있습니다.',
       '{kw}에서는 {t}{g} 함께 달라진 점을 기록으로 남겨 비교하는 것이 좋습니다. 캡처·메모로 남기면 다음 점검에서 확인하기 쉽습니다.',
       '{kw}의 {t} 부분은 공식 가이드라인과 실제 운영 자료를 함께 확인하세요. 자료마다 설명이 다르면 최신 공식 안내를 기준으로 삼습니다.'],
   close='{kw} 관련 결정은 한 번에 정하기보다 지금까지 확인한 내용과 질문을 정리한 뒤 담당자와 함께 검토하는 것이 좋습니다. 운영 조건은 업체마다 다릅니다.',
   fill_topics=['자료 준비', '점검 시점', '비용 구성', '운영 기록', '보고 기준', '문구 검토', '주의 사항', '선택 기준', '후속 점검']),
}
_P = PROFILES['clinic']
def set_profile(name): 
    global _P; _P = PROFILES.get(name or 'clinic', PROFILES['clinic'])
H2_TPL = ['{kp}: {a}부터 확인', '{kp}{g} {a} 정리', '{kp} 기준으로 보는 {a}', '{kp}에서 살필 {a}', '{kp} 점검 포인트', '{kp}{g} 관련된 {a} 확인']

def has_jong(ch):
    o = ord(ch); return 0xAC00 <= o <= 0xD7A3 and (o - 0xAC00) % 28 != 0

def gwa(word):
    w = re.sub(r'[^가-힣A-Za-z0-9]+$', '', word); return '과' if (w and has_jong(w[-1])) else '와'

def strip_tags(s): return html.unescape(re.sub(r'<[^>]+>', '', s)).strip()

def sentences(text):
    text = re.sub(r'\s+', ' ', text).strip()
    parts = re.split(r'(?<=[다요죠음됨임함])\.\s+|(?<=[\.\?!])\s+(?=[가-힣A-Z])', text)
    out = []
    for p in parts:
        p = p.strip().rstrip('.')
        if len(p) >= 12: out.append(p)
    return out

ADVERBS = {'반대로', '이런', '다만', '또한', '그래서', '그리고', '하지만', '먼저', '보통', '특히', '예를', '물론', '즉', '한편', '이때', '여기서', '그런', '그', '이', '저', '우선', '대개', '흔히', '실제로'}
PART_RE = re.compile(r'(에서는|에서도|에게는|으로는|에는|에서|으로|부터|까지|처럼|보다|이나|이라도|라도|은|는|이|가|을|를|도|로|의|와|과|에)$')
VERBISH = re.compile(r'(하는|되는|보는|않는|있는|없는|나누어|살펴|달리|함께|따로|먼저)$')
STOP_TOK = re.compile(r'(때|법|방법|하기|보기|챙기기|정하기)$')

def strip_particle(tok):
    t = PART_RE.sub('', tok) if len(tok) > 2 else tok
    return t if len(t) >= 2 else tok

def topic_of(h2):
    t = strip_tags(h2); t = re.sub(r'[\"“”\'‘’]', '', t)
    t = re.split(r'[,:·|—–?!]', t)[0].strip()
    toks = [x for x in t.split() if x]
    while toks and toks[0] in ADVERBS: toks.pop(0)
    out = []
    for tok in toks:
        if STOP_TOK.search(tok) and len(out) >= 1: break
        if VERBISH.search(tok): continue
        out.append(tok)
        if len(' '.join(out)) >= 16: break
    if not out: out = toks[:2]
    if out: out[-1] = strip_particle(out[-1])
    t = ' '.join(out).strip()
    t = re.sub(r'(하는|되는|보는)$', '', t).strip()
    return t or '진료 안내'


STOPN = {'받든', '잡기', '거울', '나누어', '본', '적어', '두어', '보아', '용기', '어떤', '갑자기', '보이', '하나', '가장', '조금', '자주', '다시', '미리', '바로', '거의', '아직', '이미', '매우', '특히', '오히려', '이렇게', '그렇게', '어디', '누구', '무엇', '언제', '경우', '사람', '정도', '때문', '이유', '부분', '내용', '상태', '정보', '방법', '기준', '순서', '설명', '안내', '진료', '상담', '확인', '병원', '의료진', '필요', '가능', '관련', '개인', '상황', '글', '점', '것', '수', '때', '전', '후', '뒤', '중', '분', '등', '및', '또', '더', '다른', '같은', '있는', '없는', '위한', '대한', '여러', '모든', '많은', '다음', '일반', '보통'}
def top_nouns(paras, k=2):
    cnt = {}
    for ptxt in paras:
        for tok in re.findall(r'[가-힣A-Za-z0-9·]+', strip_tags(ptxt)):
            if re.search(r'(다|요|죠|니다|습니다|세요|하고|하면|지만|으며|거나|해서|해도|이라|라서|려면|도록|듯)$', tok): continue
            core = PART_RE.sub('', tok)
            core = re.sub(r'(하|되|했|됐|보|적|들)$', '', core) if len(core) > 2 else core
            if len(core) < 2 or len(core) > 7 or core in STOPN or not re.match(r'^[가-힣A-Za-z0-9·]+$', core): continue
            cnt[core] = cnt.get(core, 0) + 1
    return [w for w, _ in sorted(cnt.items(), key=lambda x: (-x[1], len(x[0])))[:k]]

def noun_phrase(h2):
    t = strip_tags(h2); t = re.sub(r'[\"“”\'‘’]', '', t); t = re.split(r'[,:·|—–?!]', t)[0].strip()
    toks = [x for x in t.split() if x]
    while toks and (toks[0] in ADVERBS or toks[0] in MODIFIERS or VERBISH.search(toks[0])): toks.pop(0)
    out = []
    for tok in toks[:4]:
        if STOP_TOK.search(tok) or re.search(r'(다|요|죠|니다|세요|하면|지만|으며|거나|해서|려면|도록)$', tok): break
        core = PART_RE.sub('', tok) if len(tok) > 2 else tok
        if core != tok and len(core) >= 2:
            if re.search(r'(은|는|이|가|을|를)$', tok): out.append(core); return ' '.join(out)
            out.append(core); continue
        if VERBISH.search(tok): break
        out.append(tok)
    ph = ' '.join(out).strip()
    return ph if (ph and len(ph) <= 20 and not VERBISH.search(ph)) else ''

MODIFIERS = {'때', '본', '나누어', '다른', '위한', '대한', '같은', '있는', '없는', '해', '볼', '가져갈', '할', '될', '한', '든', '적어', '두는', '보는', '하는', '되는', '여러', '모든', '많은', '새', '첫', '이런', '그런', '어떤', '현실적인', '구체적인', '일반적인', '꼭', '더', '덜', '잘', '못'}
VERB_END = re.compile(r'(다|요|죠|니다|습니다|세요|하고|하면|지만|으며|거나|해서|해도|이라|라서|려면|도록|듯|기)$')
def trailing_phrase(h2):
    t = strip_tags(h2); t = re.sub(r'[\"“”\'‘’]', '', t); t = re.split(r'[,:·|—–?!]', t)[-1].strip()
    toks = [x for x in t.split() if x]
    if not toks or VERB_END.search(toks[-1]) or STOP_TOK.search(toks[-1]) or toks[-1] in ('것', '때', '점', '수', '중'): return ''
    out = []
    for tok in reversed(toks):
        if VERBISH.search(tok) or VERB_END.search(tok) or tok in ADVERBS or tok in MODIFIERS: break
        if out and re.search(r'의$', tok): out.insert(0, tok); continue
        core = PART_RE.sub('', tok) if len(tok) > 2 else tok
        if core != tok and len(core) >= 2 and out: break  # 앞 어절이 조사로 끝나면 거기서 끊음
        out.insert(0, tok if core == tok else core)
        if len(out) >= 3: break
    while out and out[0] in MODIFIERS: out.pop(0)
    ph = ' '.join(out).strip()
    return ph if (len(ph) >= 4 and len(ph) <= 18) else ''

def topic_for(h2, paras):
    ph = trailing_phrase(h2)
    if ph: return ph
    ph = noun_phrase(h2)
    if ph and len(ph) >= 4 and len(ph.split()) <= 3: return ph
    tn = top_nouns(paras)
    if tn: return '·'.join(tn)
    return topic_of(h2)
def key_phrase(sent):
    toks = [x for x in re.sub(r'[\"“”\'‘’()]', '', sent).split() if x]
    while toks and toks[0] in ADVERBS: toks.pop(0)
    out = []
    for tok in toks[:4]:
        core = PART_RE.sub('', tok) if len(tok) > 2 else tok
        ended = core != tok and len(core) >= 2
        out.append(core if ended else tok)
        if ended or len(' '.join(out)) >= 14: break
    k = re.sub(r'[,\.]+$', '', ' '.join(out)).strip()
    return k if len(k) >= 2 else sent[:10]

def short_clause(sent, limit=52):
    s = sent.strip()
    if len(s) <= limit: return s
    cut = s[:limit]; j = max(cut.rfind(', '), cut.rfind(' '))
    return (cut[:j] if j > 20 else cut).rstrip(',') + '…'

def build_table(idx, topic, paras):
    hs = _P['headers'][idx % len(_P['headers'])]; acts = _P['actions'][idx % len(_P['actions'])]
    sents = []
    for p in paras: sents += sentences(strip_tags(p))
    rows = []; seen = set()
    for k, s in enumerate(sents[:5]):
        kp = key_phrase(s)
        if kp in seen:
            toks = [x for x in s.split() if x not in ADVERBS][:3]; kp2 = PART_RE.sub('', ' '.join(toks)) if toks else kp
            kp = kp2 if kp2 not in seen else f'{kp} {k+1}'
        seen.add(kp); rows.append((kp, short_clause(s), acts[k % len(acts)]))
    if len(rows) < 3:
        rows += [(f'{topic} 확인', '상담 전에 현재 상태와 궁금한 점을 적어 둡니다', acts[(len(rows)) % len(acts)]), (f'{topic} 질문', '진료에서 들은 설명과 다른 점을 확인합니다', acts[(len(rows) + 1) % len(acts)])][:3 - len(rows)]
    th = ''.join(f'<th scope="col">{html.escape(h)}</th>' for h in hs)
    tr = ''.join('<tr>' + ''.join(f'<td>{html.escape(c)}</td>' for c in r) + '</tr>' for r in rows)
    cap = f'{topic} 세부 비교'
    return f'<h3 class="cmp-title">{html.escape(cap)}</h3><div class="cmp-wrap"><table class="cmp"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'

def link_para(kind, kw, url, region=None):
    a = f'<a href="{html.escape(url, quote=True)}">{html.escape(kw)}</a>'
    key = {'self': 'link_self', 'hub': 'link_hub', 'client': 'link_client'}.get(kind, 'link_sib')
    return '<p class="ref-link">' + _P[key].format(a=a) + '</p>'

def build_faq(topics, seed):
    qs = []
    n = min(6, max(3, len(topics)))
    for i in range(n):
        t = topics[i % len(topics)]
        q = _P['q'][(i + seed) % len(_P['q'])].format(t=t, g=gwa(t)); a = _P['a'][(i + seed) % len(_P['a'])].format(t=t)
        a = a.replace('은(는)', '은' if has_jong(re.sub(r'[^가-힣]+$', '', t)[-1:] or '가') else '는')
        qs.append(f'<div class="faq-item"><h3>Q{i+1}. {html.escape(q)}</h3><p>{html.escape(a)}</p></div>')
    return '<section class="faq" id="faq"><h2>' + _P['faq_title'] + '</h2>' + ''.join(qs) + '</section>'

def hashtags(keyword, topics, region):
    tags = ['#' + re.sub(r'[^가-힣A-Za-z0-9]', '', keyword)]
    for t in topics:
        if '·' in t: t = max(t.split('·'), key=len)  # 빈도 명사 묶음이면 가장 긴 명사 하나만
        tg = re.sub(r'[^가-힣A-Za-z0-9]', '', t)[:12]
        if re.search(r'(고|며|면|서|어|아|요|다|죠|게|지|니|해|나|기|에|로|는|은|을|를|의|도|까|면서|라|실|피|듯|들)$', tg) or re.search(r'언제|얼마나|무엇|어떻게|어디|왜|번에|전에|뒤에|후에|동안|때문', tg): continue  # 용언 활용형·의문사·조사 포함 → 태그 제외
        if len(tg) >= 2 and '#' + tg not in tags: tags.append('#' + tg)
        if len(tags) >= 8: break
    tags.append('#' + re.sub(r'[^가-힣A-Za-z0-9]', '', region))
    return '<p class="tags enrich-tags">' + ' '.join(html.escape(x) for x in tags) + '</p>'

def intro_note(keyword):
    return '<p class="intro-note">' + html.escape(_P['intro'].format(kw=keyword, g=gwa(keyword))) + '</p>'

def siblings_for(cfg, domain, slug):
    me = cfg[domain]; pool = sorted(me.get('siblings') or [])
    if not pool: return []
    h = int(hashlib.md5(slug.encode()).hexdigest(), 16)
    a = pool[h % len(pool)]; b = pool[(h // 7 + 1) % len(pool)] if len(pool) > 1 else a
    if b == a and len(pool) > 1: b = pool[(pool.index(a) + 1) % len(pool)]
    return [(cfg[a]['keyword'], cfg[a]['home']), (cfg[b]['keyword'], cfg[b]['home'])] if b != a else [(cfg[a]['keyword'], cfg[a]['home'])]


def eun(t):
    w = re.sub(r'[^가-힣A-Za-z0-9]+$', '', t); return '은' if (w and has_jong(w[-1])) else '는'
def eul(t):
    w = re.sub(r'[^가-힣A-Za-z0-9]+$', '', t); return '을' if (w and has_jong(w[-1])) else '를'
def fmt_tpl(tpl, kw, t):
    return tpl.format(kw=kw, t=t, g=gwa(t)).replace('은(는)', eun(t)).replace('을(를)', eul(t))

def row_phrases(paras, n=2):
    sents = []
    for p in paras: sents += sentences(strip_tags(p))
    rows = []; seen = set()
    for s in sents:
        kp = key_phrase(s)
        if kp in seen or len(kp) < 2: continue
        seen.add(kp); rows.append((kp, short_clause(s)))
        if len(rows) >= n: break
    return rows

def table_html(cap, hs, rows):
    th = ''.join(f'<th scope="col">{html.escape(h)}</th>' for h in hs)
    tr = ''.join('<tr>' + ''.join(f'<td>{html.escape(c)}</td>' for c in r) + '</tr>' for r in rows)
    return f'<p class="tbl-label"><em>{html.escape(cap)}</em></p><div class="cmp-wrap"><table class="cmp"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'

LEAD_BAD = re.compile(r'^(그래서|그리고|하지만|다만|또한|반대로|따라서|그러나|그런데|그럼에도|그러면|그렇다면|때문에|즉|한편|물론|이때|여기서|이런|그런|저런|이렇게|그렇게|이처럼|그처럼|이 |그 |이것|그것|이는|그는|이를|그를|이와|그와|이에|그에|이후|그 뒤|이 경우|예를|또 |혹은|또는|특히|오히려|결국|이러한|그러한|위와|앞서|아울러|더불어|반면|역시|마찬가지)')
SENT_END = re.compile(r'(니다|이다|한다|된다|있다|없다|좋다|많다|쉽다|어렵다|다르다|세요|어요|아요|해요|예요|에요|지요|죠|군요|네요|다)$')
ANAPH = re.compile(r'그렇|이렇|그런 |이런 |그것|이것|그 경우|이 경우|마찬가지|그때|이때|위의 |앞의 |앞서|그만큼|이만큼|그래야|그러면|그 뒤|이 뒤|그 밖|이 밖|이 중|그중|둘 다|두 가지 모두|해당합니다$|그렇지')
def full_sentence(paras, used=None, limit=78, hint=''):
    """표·FAQ 에 넣을 '끝맺음이 있는 한 문장'. 자르지 않는다(2026-11-19 사용자: "문장 끝맺음 확실하게 … 맥락 잘 이어줘").
    후보 = 종결어미로 끝나고, 접속어·지시어로 시작하지 않고, 앞 문장을 가리키는 말(그렇습니다·이런 등)이 없는 평서문.
    우선순위: ① 절의 첫 문장(주제문) ② 절 제목(hint)의 낱말을 담은 18~limit자 문장 ③ 18~limit자 문장 ④ 110자 이하 중 가장 짧은 것 ⑤ 종결된 문장 중 가장 짧은 것. 없으면 None."""
    used = used if used is not None else set()
    sents = []
    for p in paras: sents += sentences(strip_tags(p))
    ok = [x for x in sents if x not in used and SENT_END.search(x) and not re.search(r'[:;,]$', x) and x.count('(') == x.count(')') and '?' not in x]
    alone = [x for x in ok if not LEAD_BAD.match(x) and not ANAPH.search(x)]
    stems = [w for w in (strip_particle(t) for t in re.findall(r'[가-힣A-Za-z0-9]+', hint)) if len(w) >= 2 and w not in STOPN and not VERB_END.search(w)]
    mid = [x for x in alone if 18 <= len(x) <= limit]
    pick = sents[0] if (sents and sents[0] in alone and 18 <= len(sents[0]) <= limit + 20) else None
    pick = pick or next((x for x in mid if any(w in x for w in stems)), None) or (mid[0] if mid else None)
    if not pick:
        c = sorted([x for x in alone if len(x) <= 110], key=len) or sorted(ok, key=len)
        pick = c[0] if c else None
    if not pick: return None
    used.add(pick)
    return pick + '.'

def old_keys(paras, n):
    """v4 첫 판이 주제 목록(FAQ·해시태그)에 넣던 핵심어 — 이미 올라간 글의 FAQ·태그가 바뀌지 않게 그대로 계산한다."""
    return [kp for kp, _ in row_phrases(paras, n)]

def head_label(h2, kw, limit=34):
    """절 제목(사람이 쓴 문구)을 표·FAQ 에서 그대로 부르는 이름. 번호·따옴표·끝 문장부호만 떼고, 길면 첫 구절만."""
    t = re.sub(r'<span class="enrich-no">[^<]*</span>', '', h2); t = strip_tags(t)
    t = re.sub(r'^\s*\d+[\.\)]\s*', '', t); t = re.sub(r'[\"“”\'‘’]', '', t).strip()
    t = re.sub(r'[\s\.\?!:]+$', '', t)
    if len(t) > limit:
        c = re.split(r'\s*[,:—–|]\s*|\?\s+', t)[0].strip()
        t = c if 4 <= len(c) <= limit else ''
    return t or f'{kw} 확인'

def old_topics_a(kw, paras_a, paras_b):
    r1 = old_keys(paras_a, 1); out = list(r1)
    for kp in old_keys(paras_b, 2):
        if len(out) >= 2: break
        if r1 and kp == r1[0]: continue
        out.append(kp)
    while len(out) < 2: out.append(f'{kw} 확인')
    return out

def table_a(kw, sec_a, sec_b):
    """표 A: 1단계 = 첫 절, 2단계 = 표가 놓이는 절. sec = (절 제목, 문단들). 가운데 칸은 절 제목, 끝 칸은 그 절의 완결된 한 문장."""
    cap, hs = _P['tblA']; cap = cap.format(kw=kw)
    used = set(); rows = []; fb = '상담 전에 현재 상태와 궁금한 점을 적어 둡니다.' if _P is PROFILES['clinic'] else '작업 전에 현재 상황과 궁금한 점을 적어 둡니다.'
    secs = [sec_a] if sec_a[1] is sec_b[1] else [sec_a, sec_b]
    for lab, paras in secs:
        x = full_sentence(paras, used, hint=lab)
        if x: rows.append((f'{len(rows)+1}단계', lab, x))
    if len(rows) < 2:
        lab, paras = sec_b; x = full_sentence(paras, used)
        if x: rows.append((f'{len(rows)+1}단계', lab + ' (이어서)' if rows and rows[0][1] == lab else lab, x))
    while len(rows) < 2: rows.append((f'{len(rows)+1}단계', f'{kw} 확인', fb))
    return cap, rows, table_html(cap, hs, rows)

def table_b(kw, secs, seed):
    """표 B: secs = [(절 제목, 문단들)] 1~2개(표가 놓이는 절과, 표 A 에 안 쓴 바로 앞 절). 첫 칸은 절 제목, 가운데 칸은 완결된 한 문장."""
    cap, hs = _P['tblB']; cap = cap.format(kw=kw); last = _P['tblB_last']
    used = set(); rows = []
    for lab, paras in secs:
        x = full_sentence(paras, used, hint=lab)
        if x: rows.append((lab, x, last[(seed + len(rows)) % len(last)]))
    if len(rows) < 2 and secs:
        lab, paras = secs[-1]; x = full_sentence(paras, used)
        if x: rows.append((lab + ' (이어서)' if rows and rows[0][0] == lab else lab, x, last[(seed + len(rows)) % len(last)]))
    while len(rows) < 2: rows.append((f'{kw} 질문', '진료에서 들은 설명과 다른 점을 확인합니다.' if _P is PROFILES['clinic'] else '담당자에게 들은 설명과 다른 점을 확인합니다.', last[(seed + len(rows)) % len(last)]))
    return cap, rows, table_html(cap, hs, rows)

FAQ5 = {
 'clinic': [
  ('{kw} 글의 ‘{h}’ 부분에서 먼저 확인할 점은 무엇인가요?', '본문에서는 “{s}”라고 설명합니다. 이 내용을 기준으로 지금 상태와 궁금한 점을 먼저 적어 두시면 됩니다.', '지금 불편한 점과 시기를 먼저 정리해 두시면 됩니다. 복용 중인 약과 이전 치료 기록이 있으면 함께 알려 주세요.'),
  ('‘{h}’ 내용을 상담에서 어떻게 활용하면 좋은가요?', '본문에서는 “{s}”라고 설명합니다. 상담에서는 이 내용이 본인 상황에도 해당하는지 질문해 보세요.', '글의 내용이 본인 상황에도 해당하는지 상담에서 질문해 보세요. 들은 설명은 메모로 남겨 두면 좋습니다.'),
  ('‘{h}’ 부분은 누구에게나 똑같이 적용되나요?', '개인의 상태와 검사 결과에 따라 달라집니다. 본문에서는 “{s}”라고 설명하지만, 구체적인 적용은 진료에서 확인해 주세요.', '개인의 상태와 검사 결과에 따라 달라집니다. 구체적인 적용은 진료에서 확인해 주세요.'),
  ('‘{h}’ 내용을 다시 확인해야 하는 때는 언제인가요?', '증상이 달라지거나 불편이 이어질 때입니다. 본문에서는 “{s}”라고 설명하며, 정해진 날 전에도 다시 확인할 수 있습니다.', '증상이 달라지거나 불편이 이어질 때입니다. 정해진 날 전에도 다시 확인할 수 있습니다.'),
  ('‘{h}’{g} 관련해 기록해 두면 좋은 것은 무엇인가요?', '달라진 점을 날짜와 함께 메모나 사진으로 남겨 두세요. 본문에서는 “{s}”라고 설명하므로, 이 부분과 관련된 변화를 중심으로 적으면 다음 진료에서 확인하기 쉽습니다.', '달라진 점을 날짜와 함께 메모나 사진으로 남겨 두세요. 다음 진료에서 확인하기 쉽습니다.'),
  ('‘{h}’ 부분을 읽고도 궁금한 점이 남으면 어떻게 하나요?', '', '남은 질문은 목록으로 정리해 진료에서 직접 물어보세요. 온라인 설명과 현장 안내가 다르면 현장 의료진의 설명을 기준으로 삼습니다.')],
 'marketing': [
  ('{kw} 글의 ‘{h}’ 부분에서 먼저 확인할 점은 무엇인가요?', '본문에서는 “{s}”라고 설명합니다. 이 내용을 기준으로 지금 운영 상황과 궁금한 점을 먼저 적어 두시면 됩니다.', '지금 필요한 작업과 시기를 먼저 정리해 두시면 됩니다. 기존 채널 운영 기록이 있으면 함께 공유해 주세요.'),
  ('‘{h}’ 내용을 미팅에서 어떻게 활용하면 좋은가요?', '본문에서는 “{s}”라고 설명합니다. 미팅에서는 이 내용이 우리 업체 상황에도 해당하는지 질문해 보세요.', '글의 내용이 우리 업체 상황에도 해당하는지 미팅에서 질문해 보세요. 들은 설명은 문서로 남겨 두면 좋습니다.'),
  ('‘{h}’ 부분은 어느 업체에나 똑같이 적용되나요?', '운영 상황과 확인된 자료에 따라 달라집니다. 본문에서는 “{s}”라고 설명하지만, 구체적인 적용은 담당자와 확인해 주세요.', '운영 상황과 확인된 자료에 따라 달라집니다. 구체적인 적용은 담당자와 확인해 주세요.'),
  ('‘{h}’ 내용을 다시 점검해야 하는 때는 언제인가요?', '지표가 달라지거나 문제가 이어질 때입니다. 본문에서는 “{s}”라고 설명하며, 정기 보고 전에도 다시 점검할 수 있습니다.', '지표가 달라지거나 문제가 이어질 때입니다. 정기 보고 전에도 다시 점검할 수 있습니다.'),
  ('‘{h}’{g} 관련해 기록해 두면 좋은 것은 무엇인가요?', '달라진 점을 날짜와 함께 캡처나 메모로 남겨 두세요. 본문에서는 “{s}”라고 설명하므로, 이 부분과 관련된 변화를 중심으로 적으면 다음 점검에서 확인하기 쉽습니다.', '달라진 점을 날짜와 함께 캡처나 메모로 남겨 두세요. 다음 점검에서 확인하기 쉽습니다.'),
  ('‘{h}’ 부분을 읽고도 궁금한 점이 남으면 어떻게 하나요?', '', '남은 질문은 목록으로 정리해 담당자에게 직접 물어보세요. 자료마다 설명이 다르면 최신 공식 안내를 기준으로 삼습니다.')],
}
def build_faq5(kw, secs, seed):
    """FAQ 6문항, Q./A. 형태. 질문은 절 제목(사람이 쓴 문구)을 그대로 부르고, 답은 그 절의 완결된 한 문장을 인용한 뒤 안내 문장으로 맺는다.
    secs = [(절 제목, 문단들)]. (사용자 2026-11-19 09:35 "문장 끝맺음 확실하게 … 맥락 잘 이어줘", 09:37 "자주묻는질문에 Q A 형태로")"""
    tpl = FAQ5['clinic' if _P is PROFILES['clinic'] else 'marketing']
    used = set(); qs = []; n = len(secs)
    for i in range(6):
        h, paras = secs[(i + seed) % n]
        q, a_s, a_plain = tpl[i]
        x = full_sentence(paras, used, limit=70, hint=h) if a_s else None
        x = x[:-1] if x else None
        if x and ('“' in x or '”' in x or '"' in x or len(x) > 110): x = None
        q = q.format(kw=kw, h=h, g=gwa(h)); a = a_s.format(s=x) if x else a_plain
        qs.append(f'<div class="faq-item"><h3><span class="faq-q">Q.</span> {html.escape(q)}</h3><p><span class="faq-a">A.</span> {html.escape(a)}</p></div>')
    return '<section class="faq" id="faq"><h2>' + _P['faq_title'] + '</h2>' + ''.join(qs) + '</section>'

def img_fig(slug, n, alt):
    return f'<figure class="enrich-img"><img src="{IMG_BASE}{slug}-{n}.webp" alt="{html.escape(alt, quote=True)}" width="1200" height="675" loading="{"eager" if n == 1 else "lazy"}" decoding="async"></figure>'

def number_h2(block, n):
    m = re.match(r'(<h2\b[^>]*>)(.*?)(</h2>)', block, re.S)
    if not m: return block
    inner = m.group(2)
    if re.match(r'\s*(<[^>]+>)*\s*\d+\.\s', inner): return block
    return m.group(1) + f'<span class="enrich-no">{n}. </span>' + inner + m.group(3) + block[m.end():]

def build_faq4(kw, topics, seed):
    qs = []
    for i in range(6):
        t = topics[(i + seed) % len(topics)]
        q = fmt_tpl(_P['q4'][i], kw, t); a = fmt_tpl(_P['a4'][i], kw, t)
        qs.append(f'<div class="faq-item"><h3>Q{i+1}. {html.escape(q)}</h3><p>{html.escape(a)}</p></div>')
    return '<section class="faq" id="faq"><h2>' + _P['faq_title'] + '</h2>' + ''.join(qs) + '</section>'

TAG_BAD = re.compile(r'(고|며|면|서|어|아|요|다|죠|게|지|니|해|나|기|에|로|는|은|을|를|의|도|까|면서|라|실|피|듯|들)$')
TAG_BAD2 = re.compile(r'언제|얼마나|무엇|어떻게|어디|왜|번에|전에|뒤에|후에|동안|때문')
def hashtags4(kw, topics):
    """9개: #키워드(공백 제거)+주제어(4~8자, 공백 제거). 주제 부족하면 프로파일 기본 주제로 채움."""
    base = re.sub(r'[^가-힣A-Za-z0-9]', '', kw)
    tags = []
    def add(t):
        if '·' in t: t = max(t.split('·'), key=len)
        tg = re.sub(r'[^가-힣A-Za-z0-9]', '', t)
        if len(tg) < 3 or len(tg) > 10 or TAG_BAD.search(tg) or TAG_BAD2.search(tg) or tg == base or tg in base: return
        tag = '#' + base + tg
        if tag not in tags: tags.append(tag)
    for t in topics: add(t)
    for t in _P['fill_topics']:
        if len(tags) >= 9: break
        add(t)
    return '<p class="tags enrich-tags">' + ' '.join(html.escape(x) for x in tags[:9]) + '</p>'

def related_links(cfg, domain):
    """'관련 정보 링크': 병원 사이트는 자기 홈 1개(자기 키워드 앵커)만. 다른 병원·업체 홈 묶음(백링크)은 애드온 마케팅 27곳의 기존 '병원 홈페이지 안내' 블록에만 둔다
    (사용자 2026-11-19 01:07 "업체병원 사이트 도메인에는 있으면 안돼 … 자가링크는 괜찮아"). 마케팅 사이트는 빈 문자열(기존 묶음 블록과 중복 방지)."""
    me = cfg[domain]
    if me.get('group') == 'marketing': return ''
    items = [(me['keyword'], me['home'])]
    lis = ''.join(f'<li><a href="{html.escape(u, quote=True)}">{html.escape(k)}</a></li>' for k, u in items)
    return f'<section class="enrich-links" aria-label="관련 정보 링크"><h2>관련 정보 링크</h2><ul>{lis}</ul></section>'

def bold_lead(s, pat):
    """리드/요약 문단 첫 문장을 굵게(<strong class="enrich-lead">)."""
    m = re.search(pat, s, re.S)
    if not m or 'enrich-lead' in m.group(0): return s
    inner = m.group(2)
    if '<' in inner: return s
    mm = re.match(r'(.+?[\.!?。])(\s+.+)?$', inner.strip(), re.S)
    if not mm or not mm.group(2): return s
    new = m.group(1) + '<strong class="enrich-lead">' + mm.group(1) + '</strong>' + mm.group(2) + m.group(3)
    return s[:m.start()] + new + s[m.end():]

def head_block(s, slug, title):
    return f'<h1 class="enrich-title">{title}</h1>' + img_fig(slug, 1, strip_tags(title))

def page_title(s):
    m = re.search(r'<h1\b[^>]*>(.*?)</h1>', s, re.S)
    return m.group(1).strip() if m else ''

SKIP_H2_RE = re.compile(r'같은 주제|함께 읽|관련 글|이전 글|다음 글|자주 (확인|묻는)|전체 글|목차|확인할 내용$|주의사항$|참고 자료')

def enrich_blocks(body, cfg, domain, slug, hub=None, client=None):
    """v4: H2 번호(span) · 2절 뒤 표A+이미지2 · 4절 뒤 표B · 마지막 절 뒤 마무리 문단. 본문 안 링크 없음. returns (new_body, topics)"""
    me = cfg[domain]; kw = me['keyword']
    set_profile(me.get('profile'))
    seed = int(hashlib.md5(slug.encode()).hexdigest(), 16)
    parts = re.split(r'(?=<h2\b)', body)
    head, blocks = parts[0], parts[1:]
    topics = []; out = [head]
    content = []
    for b in blocks:
        m = re.match(r'<h2\b[^>]*>(.*?)</h2>', b, re.S); h2 = m.group(1) if m else ''
        paras = re.findall(r'<p(?![^>]*class=)[^>]*>(.*?)</p>', b, re.S)
        content.append((paras, h2) if (paras and not SKIP_H2_RE.search(strip_tags(h2))) else None)
    n = sum(1 for c in content if c)
    if n == 0: return body, []
    idxA = 1 if n >= 2 else 0
    idxB = 3 if n >= 4 else n - 1
    ci = -1; paras_all = []; sec_topics = []
    for b, c in zip(blocks, content):
        if not c: out.append(b); continue
        paras, h2 = c; ci += 1; paras_all.append(paras)
        topic = topic_for(h2, paras); topics.append(topic)
        b = number_h2(b, ci + 1)
        last = b.rfind('</p>'); tail = b[last + 4:] if last != -1 else ''; core = b[:last + 4] if last != -1 else b
        add = ''
        sec_topics.append(head_label(h2, kw))
        if ci == idxA:
            cap, rows, tbl = table_a(kw, (sec_topics[0], paras_all[0]), (sec_topics[ci], paras))
            topics += old_topics_a(kw, paras_all[0], paras)
            add += tbl + img_fig(slug, 2, cap)
        if ci == idxB:
            secs = ([(sec_topics[ci - 1], paras_all[ci - 1])] if ci - 1 > idxA else []) + [(sec_topics[ci], paras)]
            cap, rows, tbl = table_b(kw, secs, seed % 5)
            topics += (old_keys(paras, 2) + [f'{kw} 질문'] * 2)[:2]
            add += tbl
        if ci == n - 1:
            add += '<p class="enrich-close">' + html.escape(_P['close'].format(kw=kw)) + '</p>'
        out.append(core + add + tail)
    global _SECS; _SECS = list(zip(sec_topics, paras_all))
    return ''.join(out), topics

_SECS = []
def enrich_sitegen(s, cfg, domain, slug):
    if MARK in s: return s, False
    if any(m in s for m in OLD_MARKS): s = strip_enrich(s)
    i = s.find('<div class="body">')
    if i == -1: return s, False
    j = s.find('</div>', i)
    body = s[i + len('<div class="body">'):j]
    new_body, topics = enrich_blocks(body, cfg, domain, slug)
    if not topics: return s, False
    me = cfg[domain]; kw = me['keyword']
    seed = int(hashlib.md5(slug.encode()).hexdigest(), 16) % 6
    faq = build_faq5(kw, _SECS, seed)
    s = s[:i] + '<div class="body">' + new_body + '</div>' + MARK + faq + s[j + len('</div>'):]
    # 제목 반복 + 이미지1: 요약문 앞 / 요약문 첫 문장 굵게 / 요약 뒤 안내 문단
    title = page_title(s)
    s = re.sub(r'(<p class="summary">)', lambda m: head_block(s, slug, title) + m.group(1), s, count=1)
    s = bold_lead(s, r'(<p class="summary">)(.*?)(</p>)')
    s = re.sub(r'(<p class="summary">.*?</p>)', lambda m: m.group(1) + intro_note(kw), s, count=1, flags=re.S)
    s = re.sub(r'(<nav class="toc"[^>]*>.*?<ol>)(.*?)(</ol>)', lambda m: m.group(1) + m.group(2) + '<li><a href="#faq">자주 묻는 질문</a></li>' + m.group(3), s, count=1, flags=re.S)
    tags = hashtags4(kw, topics); links = related_links(cfg, domain)
    if '<p class="disclaimer">' in s:
        s = re.sub(r'(<p class="disclaimer">.*?</p>)', lambda m: m.group(1) + tags + links, s, count=1, flags=re.S)
    else:
        s = s.replace(MARK + faq, MARK + faq + tags + links, 1)
    return inject_css(s), True

STYLE_ID = 'enrich-css'
def inject_css(s):
    if f'id="{STYLE_ID}"' in s: return s
    return s.replace('</head>', f'<style id="{STYLE_ID}">{CSS}</style></head>', 1) if '</head>' in s else s

def strip_enrich(s):
    """보강 요소(v3·v4)를 모두 제거(템플릿 복제·재보강·검사용). 본문 문장은 그대로."""
    s = re.sub(r'<style id="' + STYLE_ID + r'">.*?</style>', '', s, flags=re.S)
    s = re.sub(r'<h1 class="enrich-title">.*?</h1>', '', s, flags=re.S)
    s = re.sub(r'<figure class="enrich-img">.*?</figure>', '', s, flags=re.S)
    s = re.sub(r'<strong class="enrich-lead">(.*?)</strong>', r'\1', s, flags=re.S)
    s = re.sub(r'<span class="enrich-no">[^<]*</span>', '', s)
    s = re.sub(r'<p class="intro-note">.*?</p>', '', s, flags=re.S)
    s = re.sub(r'<p class="enrich-close">.*?</p>', '', s, flags=re.S)
    s = re.sub(r'<h2 class="enrich-h2">.*?</h2>', '', s, flags=re.S)
    s = re.sub(r'<h3 class="cmp-title">.*?</h3><div class="cmp-wrap">.*?</div>', '', s, flags=re.S)
    s = re.sub(r'<p class="tbl-label">.*?</p><div class="cmp-wrap">.*?</div>', '', s, flags=re.S)
    s = re.sub(r'<p class="ref-link">.*?</p>', '', s, flags=re.S)
    s = re.sub(r'<section class="faq" id="faq">.*?</section>', '', s, flags=re.S)
    s = re.sub(r'<section class="enrich-links"[^>]*>.*?</section>', '', s, flags=re.S)
    s = re.sub(r'<p class="tags enrich-tags">.*?</p>', '', s, flags=re.S)
    s = s.replace('<li><a href="#faq">자주 확인하는 질문</a></li>', '').replace('<li><a href="#faq">자주 묻는 질문</a></li>', '').replace(MARK, '')
    for m in OLD_MARKS: s = s.replace(m, '')
    return s

def synth_sections(body, keyword):
    """소제목 없는 평문단 본문(<p>만) → 첫 1~2문단은 도입부로 두고 나머지를 2~6묶음으로 나눠 <h2 class="enrich-h2"> 소제목(본문 핵심어 + 템플릿)을 붙인다. 문장 불변."""
    parts = re.split(r'(?=<p(?![^>]*class=)[^>]*>)', body)
    head = parts[0]; ps = parts[1:]
    if len(ps) < 4: return None
    n = len(ps); k = min(6, max(2, n // 3)); intro = 1 if n < 8 else 2
    rest = ps[intro:]; size = -(-len(rest) // k)
    out = [head] + ps[:intro]; used = set()
    for c in range(k):
        chunk = rest[c * size:(c + 1) * size]
        if not chunk: continue
        paras = [re.sub(r'^<p[^>]*>|</p>\s*$', '', x.strip(), flags=re.S) for x in chunk]
        sents = sentences(strip_tags(paras[0])); kp = key_phrase(sents[0]) if sents else ''
        nouns = [w for w in top_nouns(paras, 4) if w not in kp and w not in used]
        a = nouns[0] if nouns else ''
        if len(kp) < 2 or kp in used: kp = a; a = nouns[1] if len(nouns) > 1 else ''
        if not kp: h = f'{keyword} 확인 사항 {c + 1}'
        elif not a: h = f'{kp} 점검 포인트'
        else: h = H2_TPL[c % len(H2_TPL)].format(kp=kp, a=a, g=gwa(kp))
        used.add(kp); used.add(a)
        out.append(f'<h2 class="enrich-h2">{html.escape(h)}</h2>' + ''.join(chunk))
    return ''.join(out)

def client_link(cfg, me, slug, page_html):
    """마케팅 글의 4번 절 링크: 그 글에 이미 들어간 거래처 백링크(관련 사이트 안내 첫 항목)를 우선, 없으면 병원 27곳 중 slug 해시로 1곳."""
    m = re.search(r'<section class="hospital-links publication-backlinks[^"]*"[^>]*>.*?<a href="([^"]+)">([^<]+)</a>', page_html, re.S)
    if m: return (html.unescape(m.group(2)), html.unescape(m.group(1)))
    pool = sorted(d for d, v in cfg.items() if v.get('group') != 'marketing')
    if not pool: return None
    d = pool[int(hashlib.md5(slug.encode()).hexdigest(), 16) % len(pool)]
    return (cfg[d]['keyword'], cfg[d]['home'])

def enrich_generic(s, cfg, domain, slug, spec):
    """생성기형·WP형·마케팅형: spec = {'start','end','head_at'(제목반복+이미지1 삽입 위치 regex; 기본 start 뒤),'lead'(리드 문단 regex, 기본 <p class="lead">),
    'intro_after','tags_at','merge_tags','synth_h2','client_links','links'(관련 정보 링크 블록 넣을지, 기본 True)}. start 매치의 끝 ~ end 매치의 시작 사이를 본문 영역으로 본다."""
    if MARK in s: return s, False
    if any(m in s for m in OLD_MARKS): s = strip_enrich(s)
    ms = re.search(spec['start'], s, re.S)
    if not ms: return s, False
    me_ = re.search(spec['end'], s[ms.end():], re.S)
    if not me_: return s, False
    i, j = ms.end(), ms.end() + me_.start()
    body = s[i:j]
    me = cfg[domain]; kw = me['keyword']; set_profile(me.get('profile'))
    content_h2 = [h for h in re.findall(r'<h2\b[^>]*>(.*?)</h2>', body, re.S) if not SKIP_H2_RE.search(strip_tags(h))]
    if not content_h2:
        if not spec.get('synth_h2'): return s, False
        body = synth_sections(body, kw)
        if body is None: return s, False
    new_body, topics = enrich_blocks(body, cfg, domain, slug)
    if not topics: return s, False
    seed = int(hashlib.md5(slug.encode()).hexdigest(), 16) % 6
    faq = build_faq5(kw, _SECS, seed)
    tags = hashtags4(kw, topics)
    links = related_links(cfg, domain) if spec.get('links', me.get('group') != 'marketing') else ''
    s = s[:i] + new_body + MARK + faq + s[j:]
    title = page_title(s)
    hb = head_block(s, slug, title)
    if spec.get('head_at'):
        s = re.sub('(' + spec['head_at'] + ')', lambda m: m.group(1) + hb, s, count=1, flags=re.S)
    elif re.match(r'<p class="lead"', spec['start']):
        s = re.sub('(' + spec['start'] + ')', lambda m: hb + m.group(1), s, count=1, flags=re.S)
    else:
        ms2 = re.search(spec['start'], s, re.S); s = s[:ms2.end()] + hb + s[ms2.end():]
    lead = spec.get('lead', r'(<p class="lead"[^>]*>)(.*?)(</p>)')
    s = bold_lead(s, lead)
    if spec.get('intro_after'):
        s = re.sub('(' + spec['intro_after'] + ')', lambda m: m.group(1) + intro_note(kw), s, count=1, flags=re.S)
    if spec.get('merge_tags') and re.search(r'<p class="tags">', s):
        s = re.sub(r'(<p class="tags">)(.*?)(</p>)', lambda m: m.group(1) + strip_tags(tags) + m.group(3), s, count=1, flags=re.S)
        s = s.replace(MARK + faq, MARK + faq + links, 1)
    elif spec.get('tags_at'):
        s = re.sub('(' + spec['tags_at'] + ')', lambda m: tags + links + m.group(1), s, count=1, flags=re.S)
    else:
        s = s.replace(MARK + faq, MARK + faq + tags + links, 1)
    return inject_css(s), True

def manuscript_to_html(txt):
    """pre-wrap 평문 원고 → <section><h2>/<p> 구조. 문장은 그대로, 빈 줄 단위 문단; 한 줄짜리 짧은 문단(문장 종결 없음)을 소제목으로 본다.
    소제목이 없으면 None(변환하지 않음)."""
    blocks = [b.strip() for b in re.split(r'\n\s*\n', txt) if b.strip()]
    is_h = lambda b: '\n' not in b and len(b) <= 45 and not re.search(r'[.!?다요죠)\]」”"]$', b)
    if sum(1 for b in blocks if is_h(b)) < 1 or not blocks: return None
    out, sec_open = [], False
    for b in blocks:
        if is_h(b):
            if sec_open: out.append('</section>')
            out.append('<section><h2>' + b + '</h2>'); sec_open = True
        else:
            out.append('<p>' + b.replace('\n', '<br>') + '</p>')
    if sec_open: out.append('</section>')
    return ''.join(out)

def enrich_manuscript(s, cfg, domain, slug, spec):
    """spec['manuscript'] = 평문 원고 div 여는 태그 regex. 변환 뒤 generic 보강."""
    if MARK in s: return s, False
    m = re.search(spec['manuscript'], s, re.S)
    if not m: return s, False
    j = s.find('</div>', m.end())
    if j == -1: return s, False
    conv = manuscript_to_html(s[m.end():j])
    if conv is None: return s, False
    cls = re.search(r'class="([^"]*)"', m.group(0)).group(1)
    s2 = s[:m.start()] + f'<div class="{cls} enrich-ms">' + conv + s[j:]
    sp = dict(spec); sp['start'] = r'<div class="[^"]*enrich-ms">'; sp['end'] = '</div>'
    return enrich_generic(s2, cfg, domain, slug, sp)

def enrich_any(s, cfg, domain, slug, spec):
    """spec 이 목록이면 먼저 맞는 것 하나를 적용(한 사이트에 글 마크업이 둘 이상일 때)."""
    for sp in (spec if isinstance(spec, list) else [spec]):
        if sp.get('manuscript'):
            out, ch = enrich_manuscript(s, cfg, domain, slug, sp)
            if ch: return out, True
            continue
        out, ch = enrich_generic(s, cfg, domain, slug, sp)
        if ch: return out, True
    return s, False

TBL_RE = re.compile(r'<p class="tbl-label">.*?</p><div class="cmp-wrap">.*?</div>', re.S)
def refresh_tables(s, cfg, domain, slug):
    """이미 v4 보강된 글의 표 A·B 만 새 규칙(완결 문장·절 주제)으로 다시 만든다. 본문·FAQ·태그·이미지 태그는 그대로. returns (html, 바뀜 여부, 사유)"""
    k = s.find(MARK)
    if k == -1: return s, False, 'no-mark'
    me = cfg[domain]; kw = me['keyword']; set_profile(me.get('profile'))
    seed = int(hashlib.md5(slug.encode()).hexdigest(), 16)
    region = s[:k]
    parts = re.split(r'(?=<h2\b)', region); head, blocks = parts[0], parts[1:]
    content = []
    for b in blocks:
        m = re.match(r'<h2\b[^>]*>(.*?)</h2>', b, re.S); h2 = re.sub(r'<span class="enrich-no">[^<]*</span>', '', m.group(1)) if m else ''
        paras = re.findall(r'<p(?![^>]*class=)[^>]*>(.*?)</p>', b, re.S)
        content.append((paras, h2) if (paras and not SKIP_H2_RE.search(strip_tags(h2))) else None)
    n = sum(1 for c in content if c)
    if n == 0: return s, False, 'no-content'
    idxA = 1 if n >= 2 else 0; idxB = 3 if n >= 4 else n - 1
    ci = -1; paras_all = []; sec_topics = []; out = [head]; hit = 0
    for b, c in zip(blocks, content):
        if not c:
            if TBL_RE.search(b): return s, False, 'table-in-skipped-block'
            out.append(b); continue
        paras, h2 = c; ci += 1; paras_all.append(paras); sec_topics.append(head_label(h2, kw))
        new_tbls = []
        if ci == idxA: new_tbls.append(table_a(kw, (sec_topics[0], paras_all[0]), (sec_topics[ci], paras))[2])
        if ci == idxB:
            secs = ([(sec_topics[ci - 1], paras_all[ci - 1])] if ci - 1 > idxA else []) + [(sec_topics[ci], paras)]
            new_tbls.append(table_b(kw, secs, seed % 5)[2])
        found = TBL_RE.findall(b)
        if len(found) != len(new_tbls): return s, False, f'table-count-mismatch(sec {ci+1}: {len(found)} vs {len(new_tbls)})'
        it = iter(new_tbls); b = TBL_RE.sub(lambda m: next(it), b); hit += len(new_tbls)
        out.append(b)
    tail = s[k:]
    faq = build_faq5(kw, list(zip(sec_topics, paras_all)), seed % 6)
    tail, nf = re.subn(r'<section class="faq" id="faq">.*?</section>', lambda m: faq, tail, count=1, flags=re.S)
    if nf != 1: return s, False, 'no-faq'
    new = ''.join(out) + tail
    new = re.sub(r'<style id="' + STYLE_ID + r'">.*?</style>', lambda m: f'<style id="{STYLE_ID}">{CSS}</style>', new, count=1, flags=re.S)
    return new, new != s, 'ok' if hit else 'no-table'

CSS = """
/* enrich v4 */
.enrich-title{font-size:1.45rem;line-height:1.4;margin:18px 0 12px;word-break:keep-all}
.enrich-img{margin:14px 0 18px}.enrich-img img{width:100%;height:auto;border-radius:10px;display:block}
.enrich-lead{font-weight:700}
.enrich-no{color:#2a5d8f}
.intro-note{color:#555;font-size:.95rem;margin:10px 0 0}
.tbl-label{margin:1.3em 0 .4em;color:#345;font-size:.98rem}.tbl-label em{font-style:italic}
.cmp-wrap{overflow-x:auto;margin:0 0 1.2em}
table.cmp{width:100%;border-collapse:collapse;font-size:.93rem;line-height:1.5;background:#fff}
table.cmp th,table.cmp td{border:1px solid #dfe6ee;padding:9px 10px;text-align:left;vertical-align:top}
table.cmp th{background:#f3f6fa;font-weight:600}
table.cmp td:first-child{white-space:nowrap;font-weight:600;color:#2a3b4d}
@media(max-width:640px){table.cmp td:first-child{white-space:normal}}
.enrich-close{margin:1.2em 0 0;color:#333}
.faq{margin:32px 0 8px}.faq h2{font-size:1.3rem}.faq-item{border-top:1px solid #e6ebf0;padding:14px 0}
.faq-item h3{font-size:1.02rem;margin:0 0 6px}.faq-item p{margin:0;font-size:.95rem;color:#333}
.faq-q{color:#2a5d8f;font-weight:700;margin-right:2px}.faq-a{color:#b4532a;font-weight:700;margin-right:2px}
.enrich-h2{margin:1.6em 0 .6em}
.enrich-ms{white-space:normal}.enrich-ms p{margin:0 0 1em}
.enrich-tags{margin:18px 0 0;font-size:.92rem;color:#4a6a8a;word-break:keep-all;line-height:1.9}
.enrich-links{margin:26px 0 8px;font-size:.92rem}.enrich-links h2{font-size:1.1rem;margin:0 0 8px}
.enrich-links ul{list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:6px 14px}.enrich-links li{margin:0}.enrich-links a{text-decoration:underline;color:#2a5d8f}
"""

def main():
    args = sys.argv[1:]
    cfg = json.load(open(args[0], encoding='utf-8')); domain = args[1]
    if args[2] == '--stdin':
        s = sys.stdin.read(); out, ch = enrich_sitegen(s, cfg, domain, 'stdin'); sys.stdout.write(out); return
    if args[2] == '--refresh-tables':
        import collections; st = collections.Counter()
        for f in args[3:]:
            p = Path(f); s = p.read_text(encoding='utf-8'); slug = p.parent.name if p.name == 'index.html' else p.stem
            out, ch, why = refresh_tables(s, cfg, domain, slug); st['changed' if ch else why if why != 'ok' else 'same'] += 1
            if ch: p.write_text(out, encoding='utf-8')
        print(json.dumps({'domain': domain, **st}, ensure_ascii=False)); return
    done = skipped = 0
    spec = cfg[domain].get('spec')
    for f in args[2:]:
        p = Path(f); s = p.read_text(encoding='utf-8')
        slug = p.parent.name if p.name == 'index.html' else p.stem
        out, ch = enrich_any(s, cfg, domain, slug, spec) if spec else enrich_sitegen(s, cfg, domain, slug)
        if ch: p.write_text(out, encoding='utf-8'); done += 1
        else: skipped += 1
    print(json.dumps({'domain': domain, 'enriched': done, 'skipped': skipped}, ensure_ascii=False))

if __name__ == '__main__': main()
