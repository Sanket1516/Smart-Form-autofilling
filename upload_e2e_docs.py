import requests
import sys
import time

base_url = 'http://localhost:8000/api/v1'

def login():
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
        
    return login_res.json()['data']['access_token']

import os
def upload_document(token, file_path):
    print(f"Uploading {file_path}...")
    headers = {'Authorization': f'Bearer {token}'}
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'application/pdf')}
            res = requests.post(f'{base_url}/documents', headers=headers, files=files)
            if res.status_code == 200:
                doc_id = res.json()['data']['id']
                print(f"Uploaded successfully. Document ID: {doc_id}")
                return doc_id
            else:
                print(f"Upload failed: {res.text}")
                return None
    except Exception as e:
        print(f"Error uploading {file_path}: {e}")
        return None

def wait_for_document(token, doc_id):
    headers = {'Authorization': f'Bearer {token}'}
    print(f"Waiting for document {doc_id} to process...")
    for _ in range(30):
        res = requests.get(f'{base_url}/documents/{doc_id}', headers=headers)
        if res.status_code == 200:
            status = res.json()['data']['status']
            if status == 'processed':
                print(f"Document {doc_id} processed successfully.")
                return True
            elif status == 'failed':
                print(f"Document {doc_id} processing failed.")
                return False
        time.sleep(2)
    print(f"Document {doc_id} processing timed out.")
    return False

def check_discovered_facts(token, doc_id):
    headers = {'Authorization': f'Bearer {token}'}
    res = requests.get(f'{base_url}/profile/discovered-facts?document_id={doc_id}', headers=headers)
    if res.status_code == 200:
        facts = res.json().get('data', [])
        print(f"Document {doc_id} extracted {len(facts)} discovered facts.")
        for f in facts:
            print(f" - {f['semantic_type']}: {f['value']} (Conf: {f['confidence']})")
    else:
        print(f"Failed to fetch discovered facts for {doc_id}: {res.text}")

def main():
    token = login()
    print("Logged in successfully.")
    
    files = [
        'test-data/sample_resume.pdf',
        'backend/passbook.pdf',
        'test-data/academic_certificate.pdf',
        'test-data/employment_letter.pdf',
        'test-data/invoice.pdf',
        'test-data/prescription.pdf'
    ]
    
    for file_path in files:
        doc_id = upload_document(token, file_path)
        if doc_id:
            if wait_for_document(token, doc_id):
                check_discovered_facts(token, doc_id)
        print("-" * 40)

if __name__ == '__main__':
    main()
