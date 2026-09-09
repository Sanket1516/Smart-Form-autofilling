"""Structural validation for the Phase 1 Chrome extension."""
import json
from pathlib import Path


def test_extension_manifest_and_required_files() -> None:
    extension = Path(__file__).resolve().parents[1] / "extension"
    manifest = json.loads((extension / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["manifest_version"] == 3
    assert manifest["background"]["service_worker"] == "background.js"
    assert set(manifest["permissions"]) == {"storage", "activeTab", "scripting"}
    for filename in ("background.js", "content.js", "popup.html", "popup.js", "backend-client.js"):
        assert (extension / filename).is_file()

