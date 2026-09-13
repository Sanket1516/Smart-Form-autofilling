import asyncio
import os
import sys
import time
import requests
from pymongo import MongoClient

# Configure this for your local setup
API_BASE_URL = "http://localhost:8000/api/v1"
FILE_PATH = "test-data/sanket_mali.pdf"
USER_ID = "test-user-123"

def main():
    if not os.path.exists(FILE_PATH):
        print(f"File not found: {FILE_PATH}")
        sys.exit(1)

    print(f"1. Uploading {FILE_PATH} to API...")
    with open(FILE_PATH, "rb") as f:
        # Mock auth via headers if not strictly enforced, or use test user
        headers = {"Authorization": f"Bearer temp-token"}
        # But wait, our API might not need auth in dev or we can bypass it.
        # Actually, let's just use the python pipeline directly instead of the API to avoid auth issues.
        pass

if __name__ == "__main__":
    main()
