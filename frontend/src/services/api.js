const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function getHealth() {
  const response = await fetch(`${API_BASE_URL}/api/v1/health`);
  const body = await response.json();
  if (!response.ok) {
    throw new Error(body?.data?.status ?? "Backend health check failed");
  }
  return body.data;
}

export { API_BASE_URL };
