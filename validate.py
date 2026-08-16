"""SpellScroll end-to-end validation script."""
import os, sys, requests

os.environ['DJANGO_SETTINGS_MODULE'] = 'spellscroll.settings'
import django
django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model
import json

BASE = 'http://localhost:8000'
User = get_user_model()

def main():
    s = requests.Session()
    
    print('[1] GET landing page + CSRF')
    r = s.get(BASE + '/')
    assert r.status_code == 200, f'Landing failed: {r.status_code}'
    csrf = s.cookies.get('csrftoken')
    assert csrf, 'No CSRF token'
    print('    PASS')
    
    print('[2] POST login')
    r = s.post(BASE + '/login/', data={'username':'demo','password':'demo123','csrfmiddlewaretoken':csrf}, headers={'Referer': BASE + '/'})
    assert r.status_code in [200,302], f'Login failed: {r.status_code}'
    assert 'sessionid' in s.cookies, 'No session after login'
    print('    PASS')
    
    print('[3] GET feed HTML page')
    r = s.get(BASE + '/feed/')
    assert r.status_code == 200, f'Feed page failed: {r.status_code}'
    assert 'feed' in r.text.lower() or 'webtoon' in r.text.lower(), 'Feed page missing expected content'
    print('    PASS')
    
    print('[4] GET /api/v1/feed/current')
    r = s.get(BASE + '/api/v1/feed/current', timeout=120)
    assert r.status_code == 200, f'Feed API failed: {r.status_code} {r.text}'
    data = r.json()
    assert 'webtoons' in data, 'Missing webtoons key'
    assert len(data['webtoons']) > 0, 'Empty webtoons list'
    print(f'    PASS - {len(data["webtoons"])} webtoons, cycle {data.get("cycle_number")}')
    
    print('[5] POST feedback')
    first = data['webtoons'][0]
    r = s.post(BASE + '/api/v1/feed/feedback', json={'webtoon_id': first['id'], 'status': 'reading', 'rating': 4, 'feedback_note': 'Great art!'}, headers={'X-CSRFToken': csrf})
    assert r.status_code == 200, f'Feedback failed: {r.status_code} {r.text}'
    print('    PASS')
    
    print('[6] GET /api/v1/health')
    r = requests.get(BASE + '/api/v1/health')
    assert r.status_code == 200 and 'healthy' in r.text
    print('    PASS')
    
    print('\n=== ALL CHECKS PASSED ===')

if __name__ == '__main__':
    main()
