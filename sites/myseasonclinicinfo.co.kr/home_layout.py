"""Homepage-only editorial layout, preserving the publication renderer and manuscripts."""
import html, re
from urllib.parse import quote

def apply(g):
    E, out, posts = html.escape, g['OUT'], g['posts']
    primary = posts[0]
    assert '대구필러' in primary['title']
    faq = [
        ('필러 상담 전에 무엇을 준비하면 되나요?', '원하는 변화와 유지하고 싶은 특징, 이전 시술의 부위·시기·제품명을 정리해 주세요. 복용 중인 약, 알레르기, 시술 후 불편했던 경험도 의료진에게 알리고 상담하세요.'),
        ('다른 사람이 받은 용량을 기준으로 정해도 되나요?', '얼굴의 구조와 기존 시술 이력, 부위별 상태가 다르므로 같은 용량이 같은 결과를 뜻하지 않습니다. 적용 가능 여부와 필요한 범위는 진료를 통해 확인해야 합니다.'),
        ('상담 후 바로 시술을 결정해야 하나요?', '설명을 충분히 이해한 뒤 결정하는 것이 중요합니다. 기대할 수 있는 변화와 한계, 부작용, 비용과 사후 진료에 대해 질문하고 필요한 경우 생각할 시간을 가지세요.'),
        ('필러 효과와 회복 기간은 모두 같은가요?', '제품의 특성과 시술 부위, 개인의 상태에 따라 유지 기간과 회복 과정이 다릅니다. 중요한 일정이 있다면 미리 알리고 예상 경과와 주의사항을 확인하세요.'),
        ('시술 후 어떤 증상에 주의해야 하나요?', '멍·붓기·통증·붉어짐이 생길 수 있습니다. 평소와 다른 심한 통증, 피부색 변화, 시야 이상이 나타나면 기다리지 말고 즉시 의료진 또는 응급의료기관에서 진료받으세요.'),
        ('어디로 방문하면 되나요?', '나의계절의원은 대구 중구 명륜로23길 106, 클래시아 2차 5층에 있습니다. 아래 지도에서 위치를 확인하고 방문 전 병원에 진료 일정과 예약 여부를 문의해 주세요.')
    ]
    sections=''.join(f'<section class="editorial-section"><span class="section-number">{i+1:02d}</span><h2>{E(h)}</h2><p>{E(t)}</p></section>' for i,(h,t) in enumerate(primary['sections']))
    topics=''.join(f'<div class="topic-detail"><h3>{E(p["topic"])}</h3><p>{E(p["excerpt"])}</p><p>{E(p["sections"][0][1])}</p></div>' for p in posts[1:])
    faq_html=''.join(f'<details class="faq-item"><summary>{E(q)}</summary><p>{E(a)}</p></details>' for q,a in faq)
    address='대구광역시 중구 명륜로23길 106 나의계절의원'
    map_url='https://maps.google.com/maps?q='+quote(address)+'&output=embed'
    body=f'''<main class="home-shell editorial-home">
<section class="featured-section" aria-label="대구필러 대표 안내"><ul class="featured-list">{''.join(g['card'](i) for i in range(6))}</ul></section>
<article class="home-editorial" id="treatments" aria-labelledby="home-title">
<header class="editorial-heading"><p class="eyebrow">MY SEASON CLINIC</p><h1 id="home-title">대구필러,<br>상담에서 시작하는 얼굴의 균형</h1><p class="editorial-lead">{E(primary['excerpt'])}</p><p>필러를 알아보는 과정에서는 제품 이름이나 용량만큼 현재 상태와 기대하는 변화를 함께 살펴보는 일이 중요합니다. 나의계절의원 대구필러 안내에서 상담 전에 확인할 내용을 차근차근 읽어보세요.</p></header>
<figure class="home-clinic-photo"><img src="/images/interior-1.jpg" alt="나의계절의원 내부 공간" width="1000" height="667" loading="lazy"><figcaption>나의계절의원 제공 병원 공간 사진</figcaption></figure>
<div class="editorial-callout"><p>얼굴의 한 부분만 보기보다,<br><strong>내가 원하는 변화와 현재 상태를 함께 살펴보세요.</strong></p></div>
{sections}
<figure class="home-doctor-photo"><img src="/images/doctor.jpg" alt="나의계절의원 제공 의료진 사진" width="574" height="864" loading="lazy"><figcaption>의료진의 자세한 소개는 <a href="https://myseasonclinic.com/contents/01_company/sub02.html" target="_blank" rel="noopener noreferrer">공식 홈페이지</a>에서 확인하실 수 있습니다.</figcaption></figure>
<section class="editorial-section"><p class="eyebrow">FILLER GUIDE</p><h2>부위와 고민에 따라<br>확인할 내용이 달라집니다</h2><p>같은 필러 상담이라도 부위의 피부 상태, 얼굴 전체의 비율, 기존 시술 경험에 따라 질문이 달라집니다. 아래 내용은 진료 전에 고민을 정리하기 위한 일반적인 안내입니다.</p>{topics}</section>
<section class="editorial-section safety-section"><p class="eyebrow">BEFORE & AFTER</p><h2>결정하기 전에,<br>안전과 사후 관리까지 확인하세요</h2><p>시술의 기대 효과뿐 아니라 한계와 부작용, 제품별 허가 범위, 시술 후 연락할 방법을 확인하세요. 붓기·멍·통증·붉어짐 등이 나타날 수 있으며 드물게 혈관 관련 합병증처럼 심각한 문제가 발생할 수 있습니다.</p><p>시술 중이나 이후 평소와 다른 심한 통증, 피부색 변화 또는 시야 이상이 생기면 즉시 진료가 필요합니다. 온라인 안내만으로 증상을 판단하거나 기다리지 말고 의료진 또는 응급의료기관에 연락하세요.</p><p class="reference-note">참고: <a href="https://www.fda.gov/medical-devices/aesthetic-cosmetic-devices/dermal-fillers-soft-tissue-fillers" target="_blank" rel="noopener noreferrer">FDA 필러 안전 정보</a>. 미국의 허가 정보와 국내 제품별 허가 범위는 다를 수 있습니다.</p></section>
<section class="editorial-section home-faq" aria-labelledby="faq-title"><p class="eyebrow">FAQ</p><h2 id="faq-title">대구필러 자주 묻는 질문</h2>{faq_html}</section>
<section class="editorial-section home-location" aria-labelledby="location-title"><p class="eyebrow">LOCATION</p><h2 id="location-title">나의계절의원 오시는 길</h2><p class="location-address">대구 중구 명륜로23길 106<br>클래시아 2차 5층</p><iframe class="location-map" title="나의계절의원 위치 지도" src="{E(map_url)}" width="900" height="400" loading="lazy" referrerpolicy="no-referrer-when-downgrade" allowfullscreen></iframe><p class="map-note">지도는 위 주소를 기준으로 표시됩니다. 방문 전 아래 네이버 지도와 병원 안내에서 목적지를 확인해 주세요.</p>{g['actions']}<h3>진료시간 확인</h3><p>현재 진료·접수 시간과 휴진 일정은 대표전화 053-424-7575로 확인해 주세요.</p><p class="reference-note"><a href="https://myseasonclinic.com/contents/01_company/sub03.html" target="_blank" rel="noopener noreferrer">공식 병원 진료·위치 안내</a></p></section>
<aside class="medical-disclaimer"><h2>의료정보 안내</h2><p>{g['notice']} 이 페이지는 일반적인 정보와 병원 위치를 안내하며 특정 시술의 효과나 결과를 보장하지 않습니다. 제품별 허가 범위, 시술 가능 여부, 비용과 주의사항은 의료진과의 상담을 통해 확인하세요.</p></aside>
</article></main>'''
    path=out/'index.html'
    text=path.read_text()
    text=re.sub(r'<main class="home-shell">.*?</main>',body,text,flags=re.S)
    text=re.sub(r'<nav class="desktop-menu".*?</nav><details class="mobile-menu">.*?</details>', '<nav class="homepage-keyword" aria-label="공식 병원 안내"><a href="https://myseasonclinic.com/" target="_blank" rel="noopener noreferrer">대구필러</a></nav>',text,flags=re.S)
    text=text.replace('<link rel="stylesheet" href="/style.css">','<link rel="stylesheet" href="/style.css"><link rel="stylesheet" href="/home-layout.css">')
    path.write_text(text)
    print('Homepage: six primary-keyword cards, full editorial, FAQ and verified-address map')
