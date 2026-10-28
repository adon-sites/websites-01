"""Homepage-only editorial layout, preserving all manuscripts and release schedules."""
import html, re
from urllib.parse import quote

def apply(g):
    E, out, posts = html.escape, g['OUT'], g['posts']
    primary = posts[0]
    assert '소프웨이브' in primary['title']
    faq = [
        ('소프웨이브 상담 전에 무엇을 준비하면 되나요?', '현재 고민과 원하는 변화, 이전 시술 부위와 시기를 정리해 주세요. 복용 중인 약, 피부 질환, 알레르기 등도 의료진에게 알려 적용 가능 여부를 상담하세요. 약은 임의로 중단하지 마세요.'),
        ('피부가 얇거나 볼 꺼짐이 걱정돼도 받을 수 있나요?', '온라인 사진이나 후기만으로 적합성을 판단할 수 없습니다. 탄력 저하와 볼륨 부족은 다른 고민일 수 있으므로 현재 피부 상태와 치료 목표를 진료에서 확인해야 합니다.'),
        ('필러를 받은 부위도 시술할 수 있나요?', '제조사 안전 안내는 필러가 있는 부위 위에 직접 시술하는 것을 권장하지 않습니다. 이전 필러의 부위와 시기, 알고 있는 제품명을 의료진에게 알리고 가능한 범위를 확인하세요.'),
        ('통증이나 시술 후 불편이 있나요?', '시술 중 통증이나 열감을 느낄 수 있고, 이후 붉어짐·붓기·압통 등이 생길 수 있습니다. 통증과 회복 정도는 개인마다 다르며 심하거나 지속되는 증상은 병원에 알려 진료받으세요.'),
        ('시술 시간과 효과가 나타나는 시점은 모두 같은가요?', '시술 범위와 준비·회복 과정에 따라 방문 시간이 달라집니다. 효과의 정도와 시점도 개인차가 있으므로 중요한 일정을 미리 알리고 경과 확인 계획을 상담하세요.'),
        ('브랜뉴의원은 어디에 있나요?', '서울 강남구 압구정로 437 일신빌딩 4층에 있습니다. 아래 지도에서 위치를 확인하고 진료시간·휴진 일정·예약 가능 여부는 병원 공식 채널에 문의해 주세요.')
    ]
    sections=''.join(f'<section class="editorial-section"><span class="section-number">{i+1:02d}</span><h2>{E(h)}</h2><p>{E(t)}</p></section>' for i,(h,t) in enumerate(primary['sections']))
    topics=''.join(f'<div class="topic-detail"><h3>{E(p["topic"])}</h3><p>{E(p["excerpt"])}</p><p>{E(p["sections"][0][1])}</p></div>' for p in posts[1:])
    faq_html=''.join(f'<details class="faq-item"><summary>{E(q)}</summary><p>{E(a)}</p></details>' for q,a in faq)
    map_url='https://maps.google.com/maps?q='+quote('서울특별시 강남구 압구정로 437 브랜뉴의원')+'&output=embed'
    body=f'''<main class="home-shell editorial-home">
<section class="featured-section" aria-label="소프웨이브 대표 안내"><ul class="featured-list">{''.join(g['card'](i) for i in range(6))}</ul></section>
<article class="home-editorial" id="treatments" aria-labelledby="home-title">
<header class="editorial-heading"><p class="eyebrow">BRANDNEW CLINIC</p><h1 id="home-title">소프웨이브,<br>피부 탄력 상담에서 확인할 것</h1><p class="editorial-lead">{E(primary['excerpt'])}</p><p>피부의 변화를 고민할 때는 장비 이름뿐 아니라 현재 상태와 기대하는 변화를 함께 살펴보는 일이 중요합니다. 브랜뉴의원 소프웨이브 안내에서 시술 원리부터 상담, 회복과 주의사항까지 차근차근 읽어보세요.</p></header>
<figure class="home-clinic-photo"><img src="/images/interior-1.jpg" alt="브랜뉴의원 내부 공간" width="1000" height="667" loading="lazy"><figcaption>브랜뉴의원 제공 병원 공간 사진</figcaption></figure>
<div class="editorial-callout"><p>같은 시술 이름이라도,<br><strong>피부 상태와 원하는 변화에 따라 상담 내용은 달라집니다.</strong></p></div>
{sections}
<figure class="home-team-photo"><img src="/images/doctor.jpg" alt="브랜뉴의원 제공 의료진 사진" width="1000" height="667" loading="lazy"><figcaption>의료진의 자세한 소개는 <a href="https://brandnewclinic.com/Brandnew-02" target="_blank" rel="noopener noreferrer">공식 홈페이지</a>에서 확인하실 수 있습니다.</figcaption></figure>
<section class="editorial-section"><p class="eyebrow">SOFWAVE GUIDE</p><h2>상담부터 회복까지,<br>한 단계씩 확인하세요</h2><p>피부 상태와 시술 목표, 이전 시술 경험에 따라 확인할 내용이 달라집니다. 다음 안내는 진료 전에 질문을 정리하기 위한 일반적인 정보이며 개인에게 필요한 시술을 결정하지 않습니다.</p>{topics}</section>
<section class="editorial-section safety-section"><p class="eyebrow">SAFETY & CARE</p><h2>안전과 사후 관리도<br>상담의 중요한 부분입니다</h2><p>시술 부위에 상처나 피부 질환이 있거나, 삽입된 의료기기와 보형물, 이전 필러 시술이 있다면 의료진에게 알려주세요. 임신·수유 여부와 복용약도 상담이 필요하며 시술 가능 여부는 개별적으로 판단해야 합니다.</p><p>제조사 안내에는 통증, 압통, 색소 변화, 지속적인 붉어짐과 붓기, 피부 손상이나 멍 등의 가능성이 포함되어 있습니다. 증상이 심하거나 지속되면 시술받은 병원에 연락해 진료받고, 당일 안내받은 관리 방법을 따르세요.</p><p class="reference-note">참고: <a href="https://sofwave.com/safety-information" target="_blank" rel="noopener noreferrer">소프웨이브 제조사 안전 정보</a>. 국내 적용 범위와 개인별 주의사항은 진료 시 확인하세요.</p></section>
<section class="editorial-section home-faq" aria-labelledby="faq-title"><p class="eyebrow">FAQ</p><h2 id="faq-title">소프웨이브 자주 묻는 질문</h2>{faq_html}</section>
<section class="editorial-section home-location" aria-labelledby="location-title"><p class="eyebrow">LOCATION</p><h2 id="location-title">브랜뉴의원 오시는 길</h2><p class="location-address">서울 강남구 압구정로 437<br>일신빌딩 4층</p><iframe class="location-map" title="브랜뉴의원 위치 지도" src="{E(map_url)}" width="900" height="400" loading="lazy" referrerpolicy="no-referrer-when-downgrade" allowfullscreen></iframe><p class="map-note">지도는 위 주소를 기준으로 표시됩니다. 방문 전 아래 네이버 지도와 병원 안내에서 목적지를 확인해 주세요.</p>{g['actions']}<h3>진료시간</h3>{g['hours']}<p class="reference-note"><a href="https://brandnewclinic.com/Brandnew-03" target="_blank" rel="noopener noreferrer">공식 병원 진료·위치 안내</a></p></section>
<aside class="medical-disclaimer"><h2>의료정보 안내</h2><p>{g['notice']} 이 페이지는 일반적인 정보와 병원 위치를 안내하며 특정 시술의 효과나 결과를 보장하지 않습니다. 시술 가능 여부, 비용과 주의사항은 의료진과의 상담을 통해 확인하세요.</p></aside>
</article></main>'''
    path=out/'index.html'
    text=path.read_text()
    text=re.sub(r'<main class="home-shell">.*?</main>',body,text,flags=re.S)
    text=re.sub(r'<nav class="desktop-menu".*?</nav><details class="mobile-menu">.*?</details>', '<nav class="homepage-keyword" aria-label="공식 병원 안내"><a href="https://brandnewclinic.com/" target="_blank" rel="noopener noreferrer">소프웨이브</a></nav>',text,flags=re.S)
    text=text.replace('<link rel="stylesheet" href="/style.css">','<link rel="stylesheet" href="/style.css"><link rel="stylesheet" href="/home-layout.css">')
    path.write_text(text)
    print('Homepage: six primary-keyword cards, full editorial, FAQ and verified-address map')
