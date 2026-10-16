"""Demo command line.

    python -m demo.cli generate                 # profile -> 15 PDFs, 15 forms, answer key, scenario list
    python -m demo.cli load [--api URL]         # upload the documents to the demo account (idempotent)
    python -m demo.cli status
    python -m demo.cli evaluate [--browser]     # API suite (and the Chrome-extension suite)
    python -m demo.cli cleanup [--delete-account]

The answer key (demo/expected/manifest.json) is read only by `evaluate`.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from demo import evaluate, forms_gen, loader, manifest_gen
from demo.client import DEFAULT_API, DemoClient, InfrastructureError
from demo.documents_gen import generate as generate_documents

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT.parent / "frontend" / "public" / "demo"
RESULTS = ROOT / "results"


def cmd_generate(_: argparse.Namespace) -> int:
    docs = generate_documents(PUBLIC / "documents")
    forms = forms_gen.generate(PUBLIC / "forms")
    manifest_gen.write()
    print(f"documents: {len(docs)} -> {PUBLIC / 'documents'}")
    print(f"forms:     {len(forms)} (+index, css, js) -> {PUBLIC / 'forms'}")
    print(f"answer key: {ROOT / 'expected' / 'manifest.json'}")
    return 0


def _client(args: argparse.Namespace) -> DemoClient:
    client = DemoClient(api=args.api)
    client.sign_in()
    return client


def cmd_load(args: argparse.Namespace) -> int:
    client = _client(args)
    print(f"demo account: {client.email}")
    rows = loader.load(client)
    ok = sum(r["status"] == "processed" for r in rows)
    print(f"{ok}/{len(rows)} documents processed")
    return 0 if ok == len(rows) else 1


def cmd_status(args: argparse.Namespace) -> int:
    client = _client(args)
    demo_docs = [d for d in client.documents() if d["file_name"].startswith("DEMO_")]
    print(f"{len(demo_docs)} demo document(s) in {client.email}")
    for d in demo_docs:
        print(f"  {d['status']:<10} {d['file_name']} facts={d['fact_count']} chunks={d['chunk_count']} index={d['index_status']}")
    return 0


def cmd_cleanup(args: argparse.Namespace) -> int:
    client = _client(args)
    n = loader.cleanup(client)
    print(f"removed {n} demo document(s) and their extracted facts; other documents were not touched")
    if args.delete_account:
        client._call("DELETE", "/auth/me")
        print(f"deleted the dedicated demo account {client.email}")
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    manifest = json.loads((ROOT / "expected" / "manifest.json").read_text("utf-8"))
    RESULTS.mkdir(exist_ok=True)
    try:
        client = _client(args)
        print("loading documents (idempotent)…")
        loaded = loader.load(client)
        report = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "api": args.api, **evaluate.run_api_suite(client, manifest, loaded)}
    except InfrastructureError as exc:
        print(f"INFRASTRUCTURE FAILURE (not a model-quality result): {exc}")
        return 2
    if args.browser:
        report["autofill"] = run_browser_suite(args)
    out = RESULTS / f"evaluation_{time.strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), "utf-8")
    (RESULTS / "latest.json").write_text(out.read_text("utf-8"), "utf-8")
    from demo import report as report_md
    (RESULTS / "REPORT.md").write_text(report_md.render(report), "utf-8")
    (PUBLIC / "summary.json").write_text(json.dumps(report_md.public_summary(report), indent=1, ensure_ascii=False), "utf-8")
    print(report_md.console(report))
    print(f"\nfull report: {out}\nsummary:     {RESULTS / 'REPORT.md'}")
    return 0


def run_browser_suite(args: argparse.Namespace) -> dict:
    ext = ROOT.parent / "extension"
    result_file = RESULTS / "autofill_results.json"
    if result_file.exists():
        result_file.unlink()
    env = {**__import__("os").environ, "DEMO_API": args.api, "DEMO_RESULTS": str(result_file),
           "E2E_BACKEND_URL": args.api}
    npx = "npx.cmd" if sys.platform == "win32" else "npx"
    cmd = [npx, "playwright", "test", "-c", "playwright.demo.config.ts"]
    print("running the Chrome-extension autofill suite…")
    proc = subprocess.run(cmd, cwd=ext, env=env, capture_output=True, text=True)
    if not result_file.exists():
        return {"ran": False, "error": "browser suite produced no results", "stdout": proc.stdout[-1500:], "stderr": proc.stderr[-1500:]}
    return {"ran": True, "exit_code": proc.returncode, **json.loads(result_file.read_text("utf-8"))}


def main() -> int:
    parser = argparse.ArgumentParser(prog="demo")
    parser.add_argument("--api", default=DEFAULT_API)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, fn in (("generate", cmd_generate), ("load", cmd_load), ("status", cmd_status)):
        sub.add_parser(name).set_defaults(fn=fn)
    ev = sub.add_parser("evaluate")
    ev.add_argument("--browser", action="store_true", help="also run the Chrome-extension autofill suite")
    ev.set_defaults(fn=cmd_evaluate)
    cl = sub.add_parser("cleanup")
    cl.add_argument("--delete-account", action="store_true", help="also delete the dedicated demo account")
    cl.set_defaults(fn=cmd_cleanup)
    args = parser.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
