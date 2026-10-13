"""Structural validation for the source and build configuration of the extension."""

import json
from pathlib import Path


def test_extension_manifest_and_required_files() -> None:
    extension = Path(__file__).resolve().parents[1] / "extension"
    manifest = json.loads((extension / "public" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["manifest_version"] == 3
    assert manifest["background"]["service_worker"] == "background.js"
    assert manifest["action"]["default_popup"] == "index.html"
    assert manifest["content_scripts"][0]["js"] == ["content.js"]
    assert set(manifest["permissions"]) == {"storage", "activeTab", "scripting"}
    assert not (extension / "manifest.json").exists()
    for filename in (
        "index.html",
        "src/background/index.ts",
        "src/content/index.ts",
        "src/popup/index.tsx",
        "vite.config.ts",
    ):
        assert (extension / filename).is_file()
