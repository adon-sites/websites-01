#!/usr/bin/env python3
"""글 형식 보강(v3, 2026-11-18 사용자 결정 — 레퍼런스 orthomedical 구조):
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

MARK = '<!-- enrich:v3 -->'
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
   faq_title='자주 확인하는 질문'),
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
   faq_title='자주 확인하는 질문'),
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

SKIP_H2_RE = re.compile(r'같은 주제|함께 읽|관련 글|이전 글|다음 글|자주 (확인|묻는)|전체 글|목차|확인할 내용$|주의사항$|참고 자료')

def enrich_blocks(body, cfg, domain, slug, hub=None, client=None):
    """body: HTML of the article body containing <h2>…</h2> + <p> (sitegen). returns (new_body, topics)"""
    me = cfg[domain]; kw, home, region = me['keyword'], me['home'], me['region']
    set_profile(me.get('profile'))
    parts = re.split(r'(?=<h2\b)', body)
    head, blocks = parts[0], parts[1:]
    topics = []
    out = [head]
    sibs = siblings_for(cfg, domain, slug)
    n = sum(1 for b in blocks if re.search(r'<p(?![^>]*class=)[^>]*>', b) and not re.search(r'같은 주제|함께 읽|관련 글|이전 글|다음 글|자주 (확인|묻는)|전체 글|목차|확인할 내용$|주의사항$|참고 자료', strip_tags(re.match(r'<h2\b[^>]*>(.*?)</h2>', b, re.S).group(1) if re.match(r'<h2\b[^>]*>(.*?)</h2>', b, re.S) else '')))
    SKIP_H2 = SKIP_H2_RE
    content_idx = -1
    for i, b in enumerate(blocks):
        m = re.match(r'<h2\b[^>]*>(.*?)</h2>', b, re.S); h2 = m.group(1) if m else ''
        paras = re.findall(r'<p(?![^>]*class=)[^>]*>(.*?)</p>', b, re.S)
        if not paras or SKIP_H2.search(strip_tags(h2)):
            out.append(b); continue
        content_idx += 1; i = content_idx
        topic = topic_for(h2, paras); topics.append(topic)
        # 섹션 꼬리(닫는 태그들)와 본문을 분리: 마지막 </p> 뒤를 꼬리로 본다
        last = b.rfind('</p>'); tail = b[last + 4:] if last != -1 else ''; core = b[:last + 4] if last != -1 else b
        add = build_table(i, topic, paras)
        if i == 1: add += link_para('self', kw, home)
        elif i == 3:
            if client: add += link_para('client', *client)
            elif sibs: add += link_para('sib', *sibs[0])
            elif hub: add += link_para('hub', kw, hub)
        elif i == n - 1 and n >= 5 and sibs and (len(sibs) > 1 or client): add += link_para('sib', *(sibs[1] if len(sibs) > 1 else sibs[0]))
        out.append(core + add + tail)
    return ''.join(out), topics

def enrich_sitegen(s, cfg, domain, slug):
    if MARK in s: return s, False
    i = s.find('<div class="body">')
    if i == -1: return s, False
    j = s.find('</div>', i)
    body = s[i + len('<div class="body">'):j]
    mh = re.search(r'<a class="hub-link" href="([^"]+)"', s); hub = mh.group(1) if mh else None
    new_body, topics = enrich_blocks(body, cfg, domain, slug, hub)
    me = cfg[domain]
    faq = build_faq(topics, int(hashlib.md5(slug.encode()).hexdigest(), 16) % 6)
    s = s[:i] + '<div class="body">' + new_body + '</div>' + MARK + faq + s[j + len('</div>'):]
    # 요약문 뒤 안내 문단
    s = re.sub(r'(<p class="summary">.*?</p>)', lambda m: m.group(1) + intro_note(me['keyword']), s, count=1, flags=re.S)
    # 목차에 FAQ 항목
    s = re.sub(r'(<nav class="toc"[^>]*>.*?<ol>)(.*?)(</ol>)', lambda m: m.group(1) + m.group(2) + '<li><a href="#faq">자주 확인하는 질문</a></li>' + m.group(3), s, count=1, flags=re.S)
    # 해시태그: 면책 문단 뒤
    tags = hashtags(me['keyword'], topics, me['region'])
    if '<p class="disclaimer">' in s:
        s = re.sub(r'(<p class="disclaimer">.*?</p>)', lambda m: m.group(1) + tags, s, count=1, flags=re.S)
    else:
        s = s.replace(MARK + faq, MARK + faq + tags, 1)
    return inject_css(s), True

STYLE_ID = 'enrich-css'
def inject_css(s):
    if f'id="{STYLE_ID}"' in s: return s
    return s.replace('</head>', f'<style id="{STYLE_ID}">{CSS}</style></head>', 1) if '</head>' in s else s

def strip_enrich(s):
    """보강 요소를 모두 제거(템플릿 복제·재보강용). 본문 문장은 그대로."""
    s = re.sub(r'<style id="' + STYLE_ID + r'">.*?</style>', '', s, flags=re.S)
    s = re.sub(r'<p class="intro-note">.*?</p>', '', s, flags=re.S)
    s = re.sub(r'<h2 class="enrich-h2">.*?</h2>', '', s, flags=re.S)
    s = re.sub(r'<h3 class="cmp-title">.*?</h3><div class="cmp-wrap">.*?</div>', '', s, flags=re.S)
    s = re.sub(r'<p class="ref-link">.*?</p>', '', s, flags=re.S)
    s = re.sub(r'<section class="faq" id="faq">.*?</section>', '', s, flags=re.S)
    s = re.sub(r'<p class="tags enrich-tags">.*?</p>', '', s, flags=re.S)
    s = s.replace('<li><a href="#faq">자주 확인하는 질문</a></li>', '').replace(MARK, '')
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
    """생성기형·WP형: spec = {'start': regex, 'end': regex, 'intro_after': regex|None, 'faq_at': 'end'|regex, 'tags_at': regex|None, 'merge_tags': bool}
    start 매치의 끝 ~ end 매치의 시작 사이를 본문 영역으로 본다."""
    if MARK in s: return s, False
    ms = re.search(spec['start'], s, re.S)
    if not ms: return s, False
    me_ = re.search(spec['end'], s[ms.end():], re.S)
    if not me_: return s, False
    i, j = ms.end(), ms.end() + me_.start()
    body = s[i:j]
    me = cfg[domain]; set_profile(me.get('profile'))
    content_h2 = [h for h in re.findall(r'<h2\b[^>]*>(.*?)</h2>', body, re.S) if not SKIP_H2_RE.search(strip_tags(h))]
    if not content_h2:
        if not spec.get('synth_h2'): return s, False
        body = synth_sections(body, me['keyword'])
        if body is None: return s, False
    hub = None
    mh = re.search(spec['hub'], s) if spec.get('hub') else None
    if mh: hub = mh.group(1)
    client = client_link(cfg, me, slug, s) if spec.get('client_links') else None
    new_body, topics = enrich_blocks(body, cfg, domain, slug, hub, client)
    if not topics: return s, False
    faq = build_faq(topics, int(hashlib.md5(slug.encode()).hexdigest(), 16) % 6)
    tags = hashtags(me['keyword'], topics, me['region'])
    s = s[:i] + new_body + MARK + faq + s[j:]
    if spec.get('intro_after'):
        s = re.sub('(' + spec['intro_after'] + ')', lambda m: m.group(1) + intro_note(me['keyword']), s, count=1, flags=re.S)
    if spec.get('merge_tags') and re.search(r'<p class="tags">', s):
        s = re.sub(r'(<p class="tags">)(.*?)(</p>)', lambda m: m.group(1) + m.group(2).rstrip() + ' ' + strip_tags(tags).replace(strip_tags(tags).split()[0] + ' ', '', 1) + m.group(3), s, count=1, flags=re.S)
        # 기존 태그줄에 우리 태그(키워드 제외)를 이어 붙임
    elif spec.get('tags_at'):
        s = re.sub('(' + spec['tags_at'] + ')', lambda m: tags + m.group(1), s, count=1, flags=re.S)
    else:
        s = s.replace(MARK + faq, MARK + faq + tags, 1)
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

CSS = """
/* enrich v3 */
.intro-note{color:#555;font-size:.95rem;margin:10px 0 0}
.cmp-title{font-size:1.02rem;margin:1.4em 0 .5em;color:#345}
.cmp-wrap{overflow-x:auto;margin:0 0 1.2em}
table.cmp{width:100%;border-collapse:collapse;font-size:.93rem;line-height:1.5;background:#fff}
table.cmp th,table.cmp td{border:1px solid #dfe6ee;padding:9px 10px;text-align:left;vertical-align:top}
table.cmp th{background:#f3f6fa;font-weight:600}
table.cmp td:first-child{white-space:nowrap;font-weight:600;color:#2a3b4d}
@media(max-width:640px){table.cmp td:first-child{white-space:normal}}
.ref-link{background:#f7f9fb;border-left:3px solid #c9d6e2;padding:10px 14px;margin:14px 0;font-size:.95rem}
.faq{margin:32px 0 8px}.faq h2{font-size:1.3rem}.faq-item{border-top:1px solid #e6ebf0;padding:14px 0}
.faq-item h3{font-size:1.02rem;margin:0 0 6px}.faq-item p{margin:0;font-size:.95rem;color:#333}
.enrich-h2{margin:1.6em 0 .6em}
.enrich-ms{white-space:normal}.enrich-ms p{margin:0 0 1em}
.enrich-tags{margin:18px 0 0;font-size:.92rem;color:#4a6a8a;word-break:keep-all;line-height:1.9}
"""

def main():
    args = sys.argv[1:]
    cfg = json.load(open(args[0], encoding='utf-8')); domain = args[1]
    if args[2] == '--stdin':
        s = sys.stdin.read(); out, ch = enrich_sitegen(s, cfg, domain, 'stdin'); sys.stdout.write(out); return
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
