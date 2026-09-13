import requests
import time
import sys

base_url = 'http://localhost:8000/api/v1'

def login():
    login_res = requests.post(f'{base_url}/auth/login', json={
        'email': 'test@example.com',
        'password': 'TestPassword123!'
    })
    return login_res.json()['data']['access_token']

def main():
    token = login()
    headers = {'Authorization': f'Bearer {token}'}
    
    docs_res = requests.get(f'{base_url}/documents', headers=headers)
    docs = docs_res.json().get('data', {}).get('documents', [])
    
    for doc in docs:
        doc_id = doc['document_id']
        name = doc['file_name']
        print(f"\n--- Checking {name} (ID: {doc_id}) ---")
        
        # wait for it to process
        for _ in range(30):
            res = requests.get(f'{base_url}/documents/{doc_id}', headers=headers)
            status = res.json()['data']['status']
            if status == 'processed':
                break
            elif status == 'failed':
                print(f"FAILED: {res.json()['data']}")
                break
            print(f"Status: {status} - waiting...")
            time.sleep(2)
            
        # get discovered facts
        facts_res = requests.get(f'{base_url}/profile/discovered-facts?document_id={doc_id}', headers=headers)
        facts = facts_res.json().get('data', [])
        
        print(f"Extracted {len(facts)} discovered facts:")
        for f in facts:
            print(f"  - {f['semantic_type']}: {f['value']} (Conf: {f['confidence']}, Entity: {f.get('entity_type', 'none')})")

if __name__ == '__main__':
    main()
