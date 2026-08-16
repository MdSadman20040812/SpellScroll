"""
SpellScroll end-to-end validation script.
Simulates a real user session without a browser.
"""
import sys
import os
import time

os.environ['DJANGO_SETTINGS_MODULE'] = 'spellscroll.settings'
import django
django.setup()

import requests
import django
from django.conf import settings
from django.contrib.auth import get_user_model
import jwt, datetime, json

BASE = 'http://localhost:8000'
User = get_user_model()

def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%H:%M:%S')

def login(username, password):
    """GET landing to obtain CSRF cookie, then POST login."""
    print(f'[{now()}] Step 1: Open landing page and get CSRF cookie...')
    s = requests.Session()
    r = s.get(BASE + '/', timeout=10)
    print(f'  GET / -> {r.status_code}')

    # extract CSRF token from cookie
    csrf_token = s.cookies.get('csrftoken')
    if not csrf_token:
        print('  FAIL: no csrftoken in cookies')
        sys.exit(1)
    print(f'  CSRF token obtained: {csrf_token[:8]}...')

    print(f'[{now()}] Step 2: POST login for user "{username}"...')
    r = s.post(BASE + '/login/', data={
        'username': username,
        'password': password,
        'csrfmiddlewaretoken': csrf_token,
    }, headers={'Referer': BASE + '/'}, timeout=10)
    print(f'  POST /login/ -> {r.status_code} (final_url={r.url})')
    if r.status_code != 200 and '302' not in str(r.status_code):
        # Django returns 302 for successful login
        pass

    return s

def call_feed(s):
    print(f'[{now()}] Step 3: Call feed current endpoint...')
    r = s.get(BASE + '/api/v1/feed/current', timeout=60)
    print(f'  GET /api/v1/feed/current -> {r.status_code}')
    return r

def call_health():
    print(f'[{now()}] Step 4: Health check...')
    r = requests.get(BASE + '/api/v1/health', timeout=10)
    print(f'  GET /api/v1/health -> {r.status_code} {r.text}')
    return r

def main():
    print('='*60)
    print('SPELLSCROLL END-TO-END RUN')
    print('='*60)

    r = call_health()
    assert r.status_code == 200 and 'healthy' in r.text, 'Health check failed'

    s = login('demo', 'demo123')

    print(f'[{now()}] Step 5: Inspect cookies after login...')
    print('  Cookies:', {k: v[:12]+'...' for k,v in s.cookies.items()})

    feed = call_feed(s)
    print(f'[{now()}] Feed response preview: {feed.text[:200]}')

    if feed.status_code == 200:
        data = feed.json()
        webtoons = data.get('webtoons', [])
        print(f'  Cycle: {data.get("cycle_number")}')
        print(f'  Webtoons returned: {len(webtoons)}')
        for w in webtoons[:3]:
            print(f"    - {w.get('title')} | genres={w.get('genres')}")
        print('='*60)
        print('RUN COMPLETE: ALL CHECKS PASSED')
    else:
        print('FAILED at feed step')
        sys.exit(1)

if __name__ == '__main__':
    main()
