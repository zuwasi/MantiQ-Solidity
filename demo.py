"""Local-only evidence runner and dashboard. No third-party Python dependencies."""

from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
from urllib.parse import unquote, urlsplit
import uuid

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
STAGES = [
    ("evm", "Local EVM"),
    ("wolfram", "Wolfram"),
    ("lean", "Lean 4"),
    ("olympix", "Olympix"),
    ("sbomator", "ESL SBOMator"),
]


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_snapshot():
    paths = [ROOT / p for p in ("demo.py", "package.json", "package-lock.json")]
    for folder, pattern in (
        ("contracts", "*.sol"),
        ("scripts", "*.mjs"),
        ("lean", "*.lean"),
        ("lean", "*.toml"),
        ("wolfram", "*.wls"),
    ):
        paths.extend((ROOT / folder).glob(pattern))
    paths.append(ROOT / "lean" / "lean-toolchain")

    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
        )

    revision = git("rev-parse", "HEAD")
    status = git("status", "--porcelain")
    return {
        "revision": revision.stdout.strip()
        if revision.returncode == 0
        else "uncommitted",
        "dirty": bool(status.stdout.strip()),
        "files": {
            p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(paths) if p.exists()
        },
    }


def command(argv, cwd, log, timeout=300):
    env = {
        **os.environ,
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "NO_COLOR": "1",
    }
    with log.open("w", encoding="utf-8") as stream:
        try:
            p = subprocess.run(
                [str(x) for x in argv],
                cwd=cwd,
                env=env,
                stdout=stream,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"Tool timed out after {timeout}s; inspect the local log"
            ) from None
    if p.returncode:
        raise RuntimeError(
            f"Tool exited {p.returncode}; inspect {log.name} in the local run folder"
        )


def summarize_sbom(data, manifest):
    components = data.get("components", [])
    found = {c.get("name") for c in components}
    required = set(manifest.get("devDependencies", {})) | set(
        manifest.get("dependencies", {})
    )
    missing = sorted(required - found)
    properties = {
        p["name"]: p["value"] for p in data.get("metadata", {}).get("properties", [])
    }
    analysis = json.loads(properties.get("esl:metadata:vulnerability_analysis", "{}"))
    coverage = analysis.get("cve_analysis_coverage", {})
    vulns = data.get("vulnerabilities", [])
    quality = json.loads(properties.get("esl:quality_gate:result", "{}"))
    return {
        "components": len(components),
        "missing_direct_dependencies": missing,
        "direct_dependencies": [
            {"name": c.get("name"), "version": c.get("version")}
            for c in components
            if c.get("name") in required
        ],
        "unresolved_inventory_fields": quality.get("unresolved_blocker_count"),
        "vulnerabilities_reported": len(vulns),
        "cve_coverage": coverage,
        "database_sources": analysis.get("sources", []),
        "reported_vulnerability_ids": sorted({v.get("id", "unknown") for v in vulns}),
        "tools": data.get("metadata", {}).get("tools", {}),
        "limitations": [
            "Offline local database; no fresh online advisories.",
            "Grype re-scan disabled explicitly; no Solidity semantic or solc-advisory coverage promised.",
            "Missing or not-analyzed dependencies are not scanned-clean.",
            "Development tooling inventory, not an on-chain runtime dependency list.",
        ],
    }


def run_demo(*, olympix=False, progress=lambda result: None):
    run_id = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8]
    )
    folder = ROOT / "runs" / run_id
    folder.mkdir(parents=True)
    result = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": source_snapshot(),
        "stages": [
            {
                "id": key,
                "name": name,
                "status": "pending",
                "summary": "Waiting to execute",
            }
            for key, name in STAGES
        ],
    }

    def publish():
        dump(folder / "evidence.json", result)
        dump(ROOT / "runs" / "latest.json", result)
        progress(copy.deepcopy(result))

    def blocked(stage, reason):
        stage.update(status="blocked", summary=reason)

    publish()
    for stage in result["stages"]:
        key = stage["id"]
        stage.update(status="running", summary="Executing local tool")
        publish()
        log = folder / f"{key}.log"
        try:
            if key == "evm":
                if (
                    not shutil.which("node")
                    or not (ROOT / "node_modules" / "solc").exists()
                ):
                    blocked(
                        stage,
                        "Node.js / npm dependencies unavailable; run npm ci --ignore-scripts",
                    )
                else:
                    command(
                        ["node", ROOT / "scripts" / "evm.mjs", folder / "evm.json"],
                        ROOT,
                        log,
                    )
                    evidence = load(folder / "evm.json")
                    if not evidence.get("checks") or not all(
                        c["passed"] for c in evidence["checks"]
                    ):
                        raise RuntimeError("EVM checks incomplete or failed")
                    result.update(evm=evidence, scenario=evidence["scenario"])
                    stage.update(
                        status="passed",
                        summary=f"{len(evidence['checks'])} checks; defect reproduced, fixed call rejected",
                        details={
                            "compiler": evidence["compiler"],
                            "generated": evidence["generated"],
                            "checks": evidence["checks"],
                            "scope": "Compiled fixtures on an in-process EVM, test ETH only",
                        },
                    )
            elif key == "wolfram":
                if not shutil.which("wolframscript"):
                    blocked(
                        stage,
                        "WolframScript unavailable; licensed Wolfram installation required",
                    )
                else:
                    command(
                        [
                            "wolframscript",
                            "-file",
                            ROOT / "wolfram" / "check.wls",
                            folder / "wolfram.json",
                        ],
                        ROOT,
                        log,
                    )
                    evidence = load(folder / "wolfram.json")
                    if not evidence.get("AllPassed"):
                        raise RuntimeError("Wolfram validation failed")
                    result["wolfram"] = evidence
                    stage.update(
                        status="passed",
                        summary=f"{evidence['Search']['CaseCount']:,} finite model cases; boundary checks passed",
                        details=evidence,
                    )
            elif key == "lean":
                if not shutil.which("lake"):
                    blocked(
                        stage,
                        "Lean / Lake unavailable; install the pinned Lean toolchain",
                    )
                else:
                    command(["lake", "build"], ROOT / "lean", log)
                    proof = (ROOT / "lean" / "MantiQEscrowModel.lean").read_text(
                        encoding="utf-8"
                    )
                    import re

                    if re.search(r"\b(sorry|admit|axiom)\b", proof):
                        raise RuntimeError("Forbidden proof placeholder")
                    theorems = re.findall(r"^theorem (\w+)", proof, re.MULTILINE)
                    stage.update(
                        status="passed",
                        summary=f"{len(theorems)} model theorems built; no proof placeholders",
                        details={
                            "toolchain": (ROOT / "lean" / "lean-toolchain")
                            .read_text()
                            .strip(),
                            "theorems": theorems,
                            "scope": "Abstract transition model only; no bytecode correspondence proof",
                        },
                    )
            elif key == "olympix":
                cli = shutil.which("olympix")
                if not olympix or not cli:
                    blocked(
                        stage,
                        "CLI scan not run; VS Code installation does not establish CLI access",
                    )
                    stage["details"] = {
                        "next": "Install official CLI, authenticate yourself, then run python demo.py run --olympix",
                        "privacy": "Opt-in sends synthetic Solidity sources to Olympix. No VS Code tokens are read.",
                    }
                else:
                    out = folder / "olympix"
                    out.mkdir()
                    command(
                        [
                            cli,
                            "analyze",
                            "-w",
                            ROOT,
                            "-p",
                            ROOT / "contracts",
                            "-f",
                            "json",
                            "-o",
                            out,
                        ],
                        ROOT,
                        log,
                    )
                    reports = list(out.glob("*.json"))
                    if not reports:
                        raise RuntimeError("Olympix exited without a JSON report")
                    stage.update(
                        status="findings",
                        summary="Olympix report captured; manual finding triage required",
                        details={
                            "report_count": len(reports),
                            "scope": "Includes the intentionally defective fixture. Raw reports remain local.",
                        },
                    )
            elif key == "sbomator":
                home = Path(os.environ.get("SBOMATOR_HOME", r"C:\Sbomator_1.4.x"))
                cli = home / "cli-only" / "esl_sbomator_cli.py"
                if not cli.exists():
                    blocked(
                        stage, "Licensed local SBOMator unavailable; set SBOMATOR_HOME"
                    )
                else:
                    target = folder / "sbom.cdx.json"
                    command(
                        [
                            os.environ.get("SBOMATOR_PYTHON", sys.executable),
                            "-B",
                            cli,
                            ROOT,
                            "--skip-db-update",
                            "--include-dev",
                            "--no-lockfile",
                            "--cve-mode",
                            "local_osv",
                            "--no-grype",
                            "--no-model-analysis",
                            "--no-cpp-auto-seed",
                            "--product-version",
                            "0.1.0",
                            "--manufacturer",
                            "E.S.L SOFTWARE LAB LTD",
                            "-o",
                            target,
                        ],
                        home,
                        log,
                        600,
                    )
                    summary = summarize_sbom(load(target), load(ROOT / "package.json"))
                    result["sbomator"] = summary
                    incomplete = (
                        summary["missing_direct_dependencies"]
                        or not summary["cve_coverage"]
                        or summary["cve_coverage"].get("not_analyzed", 0)
                        or summary["unresolved_inventory_fields"] is None
                        or summary["unresolved_inventory_fields"] > 0
                    )
                    stage.update(
                        status="findings"
                        if incomplete or summary["vulnerabilities_reported"]
                        else "passed",
                        summary=f"{summary['components']} components; {summary['vulnerabilities_reported']} reported vulnerabilities; inspect coverage",
                        details=summary,
                    )
        except (OSError, RuntimeError, ValueError, KeyError) as error:
            stage.update(status="failed", summary=str(error))
        if log.exists():
            stage["log_sha256"] = sha(log)
        publish()
    if source_snapshot()["files"] != result["source"]["files"]:
        result["source_changed_during_run"] = True
        result["stages"].append(
            {
                "id": "provenance",
                "name": "Provenance",
                "status": "failed",
                "summary": "Source changed during execution; rerun before publishing",
            }
        )
    result["completed_at"] = datetime.now(timezone.utc).isoformat()
    publish()
    return result


class DemoServer(ThreadingHTTPServer):
    def __init__(self, port, olympix=False):
        super().__init__(("127.0.0.1", port), partial(Handler, directory=str(WEB)))
        self.lock = threading.Lock()
        self.running = False
        self.result = None
        self.olympix = olympix

    def update(self, result):
        with self.lock:
            self.result = result

    def run_checks(self):
        try:
            run_demo(olympix=self.olympix, progress=self.update)
        except Exception as error:
            self.update(
                {
                    "stages": [
                        {
                            "id": "evm",
                            "name": "Runner",
                            "status": "failed",
                            "summary": str(error),
                        }
                    ]
                }
            )
        finally:
            with self.lock:
                self.running = False


class Handler(SimpleHTTPRequestHandler):
    def json_response(self, code, value):
        body = json.dumps(value).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def local_host(self):
        return self.headers.get("Host") in {
            f"127.0.0.1:{self.server.server_port}",
            f"localhost:{self.server.server_port}",
        }

    def do_GET(self):
        if not self.local_host():
            return self.json_response(403, {"error": "Local host required"})
        if self.path == "/api/status":
            with self.server.lock:
                value = {
                    "running": self.server.running,
                    "result": copy.deepcopy(self.server.result),
                }
            return self.json_response(200, value)
        target = (WEB / unquote(urlsplit(self.path).path).lstrip("/")).resolve()
        if not target.is_relative_to(WEB.resolve()):
            return self.json_response(403, {"error": "Path outside web root"})
        if target.is_dir() and not (target / "index.html").is_file():
            return self.json_response(404, {"error": "No directory listings"})
        super().do_GET()

    def do_POST(self):
        origin = f"http://{self.headers.get('Host')}"
        if not self.local_host() or self.headers.get("Origin") != origin:
            return self.json_response(403, {"error": "Same-origin local requests only"})
        if (
            self.path != "/api/run"
            or self.headers.get_content_type() != "application/json"
        ):
            return self.json_response(400, {"error": "Expected /api/run with JSON"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 64 or json.loads(self.rfile.read(size)) != {}:
                raise ValueError()
        except (ValueError, json.JSONDecodeError):
            return self.json_response(400, {"error": "Expected empty JSON object"})
        with self.server.lock:
            if self.server.running:
                return self.json_response(409, {"error": "Run already active"})
            self.server.running = True
            self.server.result = None
        threading.Thread(target=self.server.run_checks, daemon=True).start()
        self.json_response(202, {"started": True})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["run", "serve", "export"])
    parser.add_argument(
        "--olympix",
        action="store_true",
        help="Explicitly enable remote Olympix scan of synthetic contracts",
    )
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if args.action == "run":
        result = run_demo(olympix=args.olympix)
        for stage in result["stages"]:
            print(f"{stage['status'].upper():8} {stage['name']}: {stage['summary']}")
        # 0 complete; 1 failed checks; 2 incomplete/needs triage. Never silently green.
        return (
            1
            if any(s["status"] == "failed" for s in result["stages"])
            else (
                2
                if any(s["status"] in {"blocked", "findings"} for s in result["stages"])
                else 0
            )
        )
    if args.action == "export":
        result = load(ROOT / "runs" / "latest.json")
        if not result.get("completed_at") or result.get("source_changed_during_run"):
            parser.error("Cannot export an incomplete or source-drifted run")
        if result["source"]["files"] != source_snapshot()["files"]:
            parser.error("Source changed since run; rerun before exporting evidence")
        dump(WEB / "evidence" / "replay.json", result)
        print("Exported summary only. Raw third-party reports and logs remain local.")
        return 0
    server = DemoServer(args.port, args.olympix)
    print(f"Dashboard: http://127.0.0.1:{args.port}/dashboard.html", flush=True)
    print(f"Presentation: http://127.0.0.1:{args.port}/", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
