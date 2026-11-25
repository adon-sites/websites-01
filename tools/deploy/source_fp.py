#!/usr/bin/env python3
"""source_fp.py — 사이트의 "배포 입력" 지문. sites/<도메인>/ 과 tools/deploy/ 의 git 트리(HEAD)가 같으면 같은 값.
usage: source_fp.py <도메인>   → 40자 지문 한 줄
r2_sync.py 가 배포 성공 뒤 R2 의 sites/<도메인>/.source 에 적어 두고, plan.py(--skip-deployed)가 push 배포 때 지문이 같은 사이트를 건너뛴다.
"""
import hashlib, subprocess, sys


def fp(domain):
    r = subprocess.run(['git', 'ls-tree', '-r', 'HEAD', '--', f'sites/{domain}', 'tools/deploy'], capture_output=True)
    if r.returncode or not r.stdout: return ''
    return hashlib.sha1(r.stdout).hexdigest()


if __name__ == '__main__':
    print(fp(sys.argv[1]))
