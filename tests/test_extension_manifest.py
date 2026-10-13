"""Structural checks for the Chrome extension manifest and build configuration."""

import json
from pathlib import Path

EXTENSION = Path(__file__).resolve().parents[1] / "extension"


def test_manifest_is_mv3_with_minimal_permissions() -> None:
    manifest = json.loads((EXTENSION / "public" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["manifest_version"] == 3
    assert manifest["action"]["default_popup"] == "index.html"
    assert set(manifest["permissions"]) == {"activeTab", "scripting", "storage"}
    # Only the backend is a fixed host; content scripts are injected on demand.
    assert all(
        host.startswith(("http://localhost:", "http://127.0.0.1:"))
        for host in manifest["host_permissions"]
    )
    assert "content_scripts" not in manifest
    assert "background" not in manifest
    assert "<all_urls>" not in json.dumps(manifest)


def test_build_produces_a_classic_content_script() -> None:
    config = (EXTENSION / "vite.content.config.ts").read_text(encoding="utf-8")
    assert "formats: ['iife']" in config
    assert "content.js" in config
    for filename in ("index.html", "src/content/index.ts", "src/popup/index.tsx", "vite.config.ts"):
        assert (EXTENSION / filename).is_file()
    for legacy in ("manifest.json", "background.js", "popup.js", "backend-client.js"):
        assert not (EXTENSION / legacy).exists()
