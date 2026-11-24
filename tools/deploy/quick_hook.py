#!/usr/bin/env python3
"""quick_hook.py — 병원·정보 사이트 홈에서 오른쪽 퀵메뉴(#qm-side, .sideq, .contact-rail)를 대표 카드 6장 아래까지 스크롤했을 때 나타나게 한다.
usage: quick_hook.py <sites/<도메인> 경로>   빌드 출력의 index.html 에만 적용, 멱등. 퀵메뉴 자체(내용·모양)는 바꾸지 않는다.
  - PC 화면(오른쪽에 떠 있는 형태, 1101px 이상)에서만 적용. 모바일 하단 띠는 그대로.
  - 스크립트가 꺼진 브라우저에서는 처음부터 보인다.
  - 사용자 지시(2026-11-24): 27곳 홈, 캐러셀 6장 이미지 아래까지 스크롤하면 퀵메뉴 표시.
"""
import json, re, sys
from pathlib import Path

MARK = 'id="qm-reveal"'
SNIP = ('<style ' + MARK + '>@media(min-width:1101px){html.qm-js #qm-side,html.qm-js .sideq,html.qm-js .contact-rail{opacity:0;visibility:hidden;pointer-events:none;'
        'transition:opacity .25s ease,visibility .25s}html.qm-js.qm-on #qm-side,html.qm-js.qm-on .sideq,html.qm-js.qm-on .contact-rail{opacity:1;visibility:visible;pointer-events:auto}}</style>'
        '<script>(function(){var d=document,h=d.documentElement;if(!d.querySelector("#qm-side,.sideq,.contact-rail"))return;'
        'function pk(r){return [].slice.call(r.querySelectorAll("img")).filter(function(i){return !i.closest("header,footer,#qm-side,.sideq,.contact-rail")})}'
        'var c=d.querySelector(".homepage-carousel"),t=d.querySelector("#treatments");'
        'var im=c?[c]:(t&&pk(t).length>=6?pk(t):pk(d)).slice(0,6);if(!im.length)return;h.classList.add("qm-js");'
        'function f(){var b=-1e9;for(var i=0;i<im.length;i++){var r=im[i].getBoundingClientRect();if(r.height)b=Math.max(b,r.bottom)}'
        'if(b==-1e9)b=0;h.classList.toggle("qm-on",b<=window.innerHeight)}'
        'f();window.addEventListener("scroll",f,{passive:true});window.addEventListener("resize",f);window.addEventListener("load",f)})();</script>')


def main():
    site = Path(sys.argv[1]).resolve()
    sj = json.loads((site / 'site.json').read_text(encoding='utf-8')); domain = sj['domain']
    if sj.get('group') not in ('hospital', 'info', 'wp'):
        print(f'[{domain}] quick: 대상 아님'); return
    f = site / sj['dist'] / 'index.html'
    if not f.exists(): print(f'[{domain}] quick: 홈 없음'); return
    s = f.read_text(encoding='utf-8')
    if MARK in s: print(f'[{domain}] quick: 이미 있음'); return
    if not re.search(r'id="qm-side"|class="sideq"|class="contact-rail"', s): print(f'[{domain}] quick: 퀵메뉴 없음 → 건너뜀'); return
    if 'homepage-carousel' not in s and len(re.findall(r'<img\b', s)) < 6: print(f'[{domain}] quick: 대표 카드 6장을 못 찾음 → 건너뜀'); return
    i = s.rfind('</body>')
    if i < 0: print(f'[{domain}] quick: </body> 없음 → 건너뜀'); return
    f.write_text(s[:i] + SNIP + s[i:], encoding='utf-8'); print(f'[{domain}] quick: 퀵메뉴 스크롤 표시 적용')


if __name__ == '__main__':
    main()
