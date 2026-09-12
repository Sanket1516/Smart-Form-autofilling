import asyncio
import httpx

async def test_upload():
    # 1. Register a test user
    async with httpx.AsyncClient() as client:
        print("Registering user...")
        reg_res = await client.post("http://localhost:8000/api/v1/auth/register", json={
            "full_name": "Cloudinary Tester",
            "email": "cloud_test@example.com",
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!"
        })
        if reg_res.status_code != 201:
            print("Already registered or failed")

        print("Logging in...")
        login_res = await client.post("http://localhost:8000/api/v1/auth/login", json={
            "email": "cloud_test@example.com",
            "password": "StrongPassword123!"
        })
        token = login_res.json()["data"]["access_token"]
        print("Logged in!")

        # 2. Upload a test PDF
        print("Uploading document...")
        dummy_pdf = b"%PDF-1.4 dummy pdf for cloudinary testing"
        upload_res = await client.post(
            "http://localhost:8000/api/v1/documents",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("cloudinary_test.pdf", dummy_pdf, "application/pdf")}
        )
        print("Upload Response:", upload_res.status_code, upload_res.text)
        
        doc_id = upload_res.json()["data"]["document_id"]
        
        # 3. Process the document
        print("Triggering processing...")
        process_res = await client.post(
            f"http://localhost:8000/api/v1/documents/{doc_id}/process",
            headers={"Authorization": f"Bearer {token}"}
        )
        print("Process Response:", process_res.status_code, process_res.text)
        
        # Check processing status
        for _ in range(10):
            await asyncio.sleep(2)
            status_res = await client.get(
                f"http://localhost:8000/api/v1/documents",
                headers={"Authorization": f"Bearer {token}"}
            )
            docs = status_res.json()["data"]["documents"]
            doc = next(d for d in docs if d["document_id"] == doc_id)
            print("Status:", doc["status"], doc.get("processing_error"))
            if doc["status"] in ["processed", "requires_review", "failed"]:
                break

if __name__ == "__main__":
    asyncio.run(test_upload())
