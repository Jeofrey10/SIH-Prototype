import urllib.request
import json

req = urllib.request.Request(
    'http://127.0.0.1:8000/api/v1/auth/login',
    data=json.dumps({'username': 'supervisor@aicte-demo.example', 'password': 'Demo@12345'}).encode(),
    headers={'Content-Type': 'application/json'}
)
res = urllib.request.urlopen(req)
token = json.loads(res.read().decode())['access_token']
headers = {'Authorization': f'Bearer {token}'}

# Limbo
req_limbo = urllib.request.Request('http://127.0.0.1:8000/api/v1/analytics/limbo-summary', headers=headers)
r_limbo = json.loads(urllib.request.urlopen(req_limbo).read().decode())
print('Limbo Summary:', r_limbo['total_stuck_count'], 'total stuck cases')

# Threads
req_threads = urllib.request.Request('http://127.0.0.1:8000/api/v1/threads', headers=headers)
r_threads = json.loads(urllib.request.urlopen(req_threads).read().decode())
print('Threads Count:', len(r_threads))

# Complaints
req_c = urllib.request.Request('http://127.0.0.1:8000/api/v1/complaints?page_size=2', headers=headers)
r_c = json.loads(urllib.request.urlopen(req_c).read().decode())
print('Sample delay explanation:', r_c['items'][0].get('delay_explanation', {}).get('sentence'))
print('Sample handover status:', r_c['items'][0].get('handover_status'))
print('All API tests passed!')
