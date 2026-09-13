import json
import time
import urllib.request
import urllib.error
import requests
import sys

base_url = 'http://localhost:8000/api/v1'

user_email = f'resume_live_{int(time.time())}@example.com'
user_pass = 'TestPassword123!'

# 1. Register or Login
print('1. Registering user...')
try:
    reg_res = requests.post(f'{base_url}/auth/register', json={
        'full_name': 'Resume Test User',
        'email': user_email,
        'password': user_pass,
        'confirm_password': user_pass
    })
except Exception:
    pass

login_res = requests.post(f'{base_url}/auth/login', json={
    'email': user_email,
    'password': user_pass
})
token = login_res.json()['data']['access_token']
headers = {'Authorization': f'Bearer {token}'}
print('User authenticated!')

# 2. Upload PDF resume
pdf_path = r'C:\Users\sanke\.gemini\antigravity-ide\brain\b1532920-1766-4cb2-827c-ee566b464646\.user_uploaded\media_1789279873084.pdf'
print(f'2. Uploading resume PDF: {pdf_path}')

with open(pdf_path, 'rb') as f:
    files = {'file': ('resume.pdf', f, 'application/pdf')}
    upload_res = requests.post(f'{base_url}/documents', headers=headers, files=files)

print('Upload response:', upload_res.status_code, upload_res.text)
doc_data = upload_res.json()['data']
doc_id = doc_data['document_id']
print(f'Uploaded document ID: {doc_id}')

# 3. Process document
print('3. Triggering document processing pipeline...')
proc_res = requests.post(f'{base_url}/documents/{doc_id}/process', headers=headers)
print('Process request triggered:', proc_res.status_code)

# 4. Poll status
print('4. Polling document status...')
for _ in range(30):
    status_res = requests.get(f'{base_url}/documents/{doc_id}/status', headers=headers)
    st = status_res.json()['data']
    print(f"Status: {st['status']}, Stage: {st['current_stage']}, Progress: {st['progress']}%")
    if st['status'] in ('processed', 'failed'):
        break
    time.sleep(1.5)

# 5. Fetch extracted facts from LLM
print('\n5. Fetching extracted facts from Knowledge Profile...')
facts_res = requests.get(f'{base_url}/profile/facts', headers=headers)
facts = facts_res.json()['data']['facts']

print(f'\n--- TOTAL EXTRACTED FACTS FROM LLM: {len(facts)} ---')
for f in facts:
    print(f"Concept: {f['concept']:<30} | Value: {f['value']:<35} | Confidence: {f['confidence']}")

