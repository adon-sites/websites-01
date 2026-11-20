#!/usr/bin/env python3
"""title_rules.py — 글 제목에 키워드를 넣는 규칙(사용자 2026-11-20 12:29 "병원글, 마케팅글 둘다 레퍼런스 각각 확인한 것처럼").
레퍼런스: 병원 사이트(orthocareplus·orthomedical·na-medi.kr)는 모든 글 제목에 사이트 키워드, 마케팅 사이트(orthomarketing·totalmarketing)는
글마다 주제 키워드를 제목 첫머리에 두고("AEO 콘텐츠 검수 기준, …") 본문에서 그 키워드를 반복.
- hosp_title(제목, 사이트 키워드) → 새 제목(사이트 키워드 포함). 글의 세부 키워드(구미치아교정…)에서 지역명 자리를 사이트 키워드로 바꾼다.
- mkt_title(제목, short_title, 사이트 키워드) → (새 제목, 글 키워드). 주제 키워드를 못 잡으면 사이트 키워드를 앞에 둔다.
URL·슬러그는 바꾸지 않는다."""
import re

REGIONS = sorted(['대구월성동', '대구동성로', '대구반월당', '대구중구', '수원시청역', '수원시청', '평택역', '동삭동', '고덕', '정왕동', '강서구', '양천구', '마곡', '고척동',
                  '범어동', '수성구', '압구정로데오', '압구정', '청담동', '청담', '신사역', '강남', '서면', '부산', '수영구', '남천동', '대연동', '경성대', '해운대', '마산', '진해',
                  '창원의창구', '창원', '반월당', '잠실', '송파구', '안양', '서울', '광주', '울산', '구미', '김해', '시흥', '청주', '수원', '평택', '대구', '서초', '송파', '동성로'], key=len, reverse=True)
PLACE_SUF = ('정형외과', '피부과', '치과', '안과', '병원')
PART = ('에서는', '에서도', '에서', '에는', '에도', '에', '의', '은', '는', '도')

def kw_split(kw):
    region = next((r for r in REGIONS if kw.startswith(r) and len(kw) > len(r)), '')
    return region, (kw[len(region):] if region else kw), kw.endswith(PLACE_SUF)

def hosp_title(t, kw):
    t = t.strip()
    if not t or kw in t: return t
    region, base, place = kw_split(kw)
    m = re.match(r'(\S+)(.*)$', t, re.S); lead, rest = m.group(1), m.group(2)
    punct = ''
    if lead and lead[-1] in ',?!': punct, lead = lead[-1], lead[:-1]
    r = next((x for x in REGIONS if lead.startswith(x)), None)
    if r is None:
        if not place and base and lead.startswith(base): return kw + lead[len(base):] + punct + rest       # 소프웨이브… → 강남소프웨이브…
        return f'{kw}, {t}'
    topic = lead[len(r):]
    # 지역명만 있는 첫 토큰(뒤에 다른 지역명이 이어지면 함께 걷어낸다): "강남 압구정 필러 상담에서"
    if not topic:
        rest2 = rest.lstrip()
        while True:
            mm = re.match(r'(\S+)\s+(.*)$', rest2, re.S)
            if mm and mm.group(1) in REGIONS: rest2 = mm.group(2)
            else: break
        if place: return f'{kw}{punct} {rest2}'
        return f'{kw}, {rest2}'
    if topic in PART:                                   # "김해에서 치아가 시릴 때"
        if place: return kw + topic + punct + rest
        return f'{kw}, {rest.lstrip()}'
    if place:
        if topic == base or (topic.startswith(base) and topic[len(base):] in PART + ('을', '를', '이', '가', '과', '와', '로', '으로')):   # 진해피부과 → 창원피부과
            return kw + topic[len(base):] + punct + rest
        if base in topic: return f'{kw}, {topic}{punct}{rest}'                 # 평택교정치과 → 평택치과, 교정치과 …
        return f'{kw} {topic}{punct}{rest}'                                    # 구미치아교정 → 구미치과 치아교정
    return f'{kw}, {topic}{punct}{rest}'                                       # 서면입술필러의 → 부산필러, 입술필러의

# ── 마케팅: 글 주제 키워드 ──
STOP_AFTER = ('전', '전에', '후', '후에', '뒤', '뒤에', '때', '시', '중', '속', '사이')
P_STOP = ('에서는', '에서', '에게', '으로', '은', '는', '이', '가', '을', '를', '에', '도', '로', '부터', '까지', '마다', '보다', '처럼', '만')
VERB_END = re.compile(r'(하기|보기|두기|짜기|되기|쓰기|읽기|나누기|정하기|맞추기|[가-힣]는|[가-힣]할|[가-힣]한|[가-힣]된|[가-힣]될|[가-힣]던|[가-힣]을|[가-힣]ㄹ|법|하는|있는|없는|않는|쓸지|할지|볼지|될지|인지|는지|은지)$')
GENERIC = {'글', '새 글', '정보', '내용', '기준', '방법', '순서', '질문', '독자', '방문자', '고객', '사람', '이유', '경우', '상황', '문제', '우리', '이것', '여러', '한 글', '첫 글'}
def _hangul_len(s): return len(re.sub(r'[^가-힣A-Za-z0-9]', '', s))
def _strip_tail(h):
    toks = h.split()
    while len(toks) > 1 and toks[-1] in STOP_AFTER: toks.pop()
    return ' '.join(toks)
def _ok_kw(k): return bool(k) and 4 <= _hangul_len(k) <= 16 and k not in GENERIC and len(k.split()) <= 4 and not re.search(r'[?!"“”‘’\'·,()\[\]<>&]', k) and not k.endswith('의')

def _head(st):
    """제목 첫머리의 명사구(조사·'전/후/때' 앞까지). 제목은 자르지 않는다. returns 명사구 | None"""
    toks = st.split(); head = []
    for tok in toks[:5]:
        if tok.endswith(','): return None
        if tok in STOP_AFTER: break
        p = next((x for x in P_STOP if tok.endswith(x) and len(tok) > len(x)), None)
        if VERB_END.search(tok) and not (p in ('을', '를', '이', '가', '에서', '에', '으로', '로') and not re.search(r'(하기|보기|는|던|할|한|된|될)$', tok[:-len(p)])): return ' '.join(head) if head else None
        if p:
            stem = tok[:-len(p)]
            if p in ('은', '는') and re.search(r'(놓|있|없|않|되|하|주|받|보|쓰|오|가|같|많|적|좋|크|작)$', stem): return ' '.join(head) if head else None   # 늘어놓은·있는: 동사
            head.append(stem); return ' '.join(head)
        head.append(tok)
    return ' '.join(head) if head and len(head) < 5 else None

def mkt_title(title, short, site_kw):
    """returns (새 제목, 글 키워드, 단계). short: 'A, B' 꼴 short_title 을 제목으로 / title: 제목이 이미 'A, B' / head: 제목 첫머리 명사구(제목 그대로) / site: 사이트 키워드를 앞에"""
    title = title.strip(); short = (short or '').strip()
    for src, tier in ((short, 'short'), (title, 'title')):
        if ', ' in src:
            h = src.split(', ')[0].strip(); k = _strip_tail(h)
            if _ok_kw(k) and _hangul_len(h) <= 20: return src, k, tier
    h = _head(title)
    if h:
        k = _strip_tail(h)
        if k.endswith('의'): k = k[:-1]
        if _ok_kw(k) and (len(k.split()) >= 2 or _hangul_len(k) >= 5) and title.startswith(k): return title, k, 'head'
    return f'{site_kw}, {title}', site_kw, 'site'
