import requests
import json
import sys

base_url = 'http://localhost:8000/api/v1'

# Try to register test user first
try:
    requests.post(f'{base_url}/auth/register', json={
        'full_name': 'Test User',
        'email': 'test@example.com',
        'password': 'TestPassword123!',
        'confirm_password': 'TestPassword123!'
    })
except Exception:
    pass

login_res = requests.post(f'{base_url}/auth/login', json={
    'email': 'test@example.com',
    'password': 'TestPassword123!'
})

if login_res.status_code != 200:
    print("Login failed:", login_res.text)
    sys.exit(1)

token = login_res.json()['data']['access_token']
headers = {'Authorization': f'Bearer {token}'}
docs_res = requests.get(f'{base_url}/documents', headers=headers)
print("User Documents:")
print(json.dumps(docs_res.json(), indent=2))
