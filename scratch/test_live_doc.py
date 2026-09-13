import requests
import json
import time

base_url = 'http://localhost:8000/api/v1'

# 1. Register/login user
user_email = f'live_user_{int(time.time())}@example.com'
user_pass = 'TestPassword123!'

requests.post(f'{base_url}/auth/register', json={
    'full_name': 'Live Test User',
    'email': user_email,
    'password': user_pass,
    'confirm_password': user_pass
})

login_res = requests.post(f'{base_url}/auth/login', json={
    'email': user_email,
    'password': user_pass
})
token = login_res.json()['data']['access_token']
headers = {'Authorization': f'Bearer {token}'}

# Create a sample ID card / document text file to test live processing
file_content = b"COLLEGE ID CARD\nName: Alex Smith\nStudent ID: CS-2026-8891\nDepartment: Computer Science\nUniversity: Stanford University\nDOB: 15/08/2002\nContact: alex.smith@stanford.edu\n"

upload_res = requests.post(
    f'{base_url}/documents',
    headers=headers,
    files={'file': ('College_ID_Card.txt', file_content, 'text/plain')}
)

print("Upload response:", upload_res.status_code, upload_res.json())
doc_id = upload_res.json()['data']['document_id']

# Trigger process explicitly
print("Triggering document process...")
proc_res = requests.post(f'{base_url}/documents/{doc_id}/process', headers=headers)
print("Process trigger response:", proc_res.status_code, proc_res.json())

# Poll processing status until done
print("Polling document status...")
for i in range(30):
    st_res = requests.get(f'{base_url}/documents/{doc_id}/status', headers=headers)
    st_data = st_res.json()['data']
    print(f"Sec {i*2}s -> Status: {st_data['status']}, Stage: {st_data.get('current_stage')}, Progress: {st_data.get('progress')}%")
    if st_data['status'] in ('processed', 'failed'):
        break
    time.sleep(2)

# Check extracted facts
facts_res = requests.get(f'{base_url}/profile/facts', headers=headers)
facts = facts_res.json()['data']['facts']
print(f"\nExtracted {len(facts)} facts from College ID Card:")
for f in facts:
    print(f" - Concept: {f['concept']:<30} | Value: {f['value']:<30} | Confidence: {f['confidence']}")
