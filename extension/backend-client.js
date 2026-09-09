const DEFAULT_BACKEND_URL = "http://localhost:8000";

export async function getBackendUrl() {
  const { backendUrl = DEFAULT_BACKEND_URL } = await chrome.storage.local.get("backendUrl");
  return backendUrl.replace(/\/$/, "");
}

export async function getBackendHealth() {
  const backendUrl = await getBackendUrl();
  const response = await fetch(`${backendUrl}/health`);
  const body = await response.json();
  if (!response.ok) throw new Error(body?.data?.status ?? "Backend unavailable");
  return body.data;
}

