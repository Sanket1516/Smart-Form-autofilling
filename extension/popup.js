const statusElement = document.querySelector("#status");
const refreshButton = document.querySelector("#refresh");

async function refreshHealth() {
  statusElement.textContent = "Checking backend…";
  refreshButton.disabled = true;
  const result = await chrome.runtime.sendMessage({ type: "GET_BACKEND_HEALTH" });
  statusElement.textContent = result.ok
    ? `Backend healthy (v${result.health.application_version})`
    : `Backend unavailable: ${result.error}`;
  refreshButton.disabled = false;
}

refreshButton.addEventListener("click", refreshHealth);
refreshHealth();

