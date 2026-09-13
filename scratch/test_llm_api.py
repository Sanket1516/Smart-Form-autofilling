import json
import urllib.request
import urllib.error
import sys

base_url = 'http://localhost:8000/api/v1'

user_email = 'llm_test_user@example.com'
user_pass = 'TestPassword123!'

# 1. Login
login_payload = json.dumps({'email': user_email, 'password': user_pass}).encode('utf-8')
login_req = urllib.request.Request(
    f'{base_url}/auth/login',
    data=login_payload,
    headers={'Content-Type': 'application/json'}
)

with urllib.request.urlopen(login_req) as resp:
    res_data = json.loads(resp.read().decode('utf-8'))
    token = res_data['data']['access_token']

print('Logged in! Token:', token[:20] + '...')

# 2. Call classify-fields endpoint for multiple diverse concepts
batch_payload = json.dumps({
    'fields': [
        {
            'field_id': 'field_1',
            'name': 'applicant_dob',
            'label': 'Date of Birth',
            'placeholder': 'MM/DD/YYYY',
            'type': 'date'
        },
        {
            'field_id': 'field_2',
            'name': 'passport_no',
            'label': 'Passport Number',
            'placeholder': 'E.g. A12345678',
            'type': 'text'
        },
        {
            'field_id': 'field_3',
            'name': 'work_summary',
            'label': 'Brief Summary of Work Experience',
            'placeholder': 'Describe your previous responsibilities...',
            'type': 'textarea'
        }
    ]
}).encode('utf-8')

classify_req = urllib.request.Request(
    f'{base_url}/forms/classify-fields',
    data=batch_payload,
    headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }
)

with urllib.request.urlopen(classify_req) as resp:
    result = json.loads(resp.read().decode('utf-8'))
    print('\n--- BATCH CLASSIFICATION API RESPONSE FROM LIVE LLM ---')
    print(json.dumps(result, indent=2))
