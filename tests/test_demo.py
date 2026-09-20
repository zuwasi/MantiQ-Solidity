from collections import Counter
import hashlib
import http.client
import json
import threading
import unittest
from unittest.mock import patch

import demo


class InventoryTests(unittest.TestCase):
    def test_no_findings_does_not_mean_coverage(self):
        result = demo.summarize_sbom(
            {
                "components": [{"name": "solc", "version": "0.8.37"}],
                "vulnerabilities": [],
            },
            {"devDependencies": {"solc": "0.8.37", "ethers": "6.17.0"}},
        )
        self.assertEqual(result["missing_direct_dependencies"], ["ethers"])
        self.assertEqual(result["cve_coverage"], {})
        self.assertIsNone(result["unresolved_inventory_fields"])
        self.assertEqual(result["vulnerabilities_reported"], 0)

    def test_coverage_and_findings_preserved(self):
        data = {
            "components": [{"name": "solc", "version": "0.8.37"}],
            "vulnerabilities": [{"id": "TEST-NOT-REAL"}],
            "metadata": {
                "properties": [
                    {
                        "name": "esl:metadata:vulnerability_analysis",
                        "value": json.dumps(
                            {
                                "cve_analysis_coverage": {
                                    "matched": 1,
                                    "not_analyzed": 7,
                                    "scanned_clean": 2,
                                }
                            }
                        ),
                    },
                    {
                        "name": "esl:quality_gate:result",
                        "value": '{"unresolved_blocker_count": 3}',
                    },
                ]
            },
        }
        result = demo.summarize_sbom(data, {"devDependencies": {"solc": "0.8.37"}})
        self.assertEqual(result["cve_coverage"]["not_analyzed"], 7)
        self.assertEqual(result["unresolved_inventory_fields"], 3)
        self.assertEqual(result["reported_vulnerability_ids"], ["TEST-NOT-REAL"])

    def test_published_license_evidence(self):
        sbom = demo.load(demo.WEB / "reports/sbomator.cdx.json")
        corrections = demo.load(demo.WEB / "evidence/license-evidence.json")
        audit = demo.load(demo.WEB / "evidence/license-enrichment.json")
        replay = demo.load(demo.WEB / "evidence/replay.json")
        components = {c["bom-ref"]: c for c in sbom["components"]}
        self.assertEqual(len(components), 368)
        self.assertTrue(all(c.get("licenses") for c in components.values()))
        self.assertEqual(len({c["component_ref"] for c in corrections}), 77)
        self.assertEqual(
            Counter(c["licenses"][0]["license"]["id"] for c in corrections),
            {"MIT": 70, "Apache-2.0": 3, "BSD-3-Clause": 3, "ISC": 1},
        )
        for correction in corrections:
            self.assertEqual(
                components[correction["component_ref"]]["licenses"],
                correction["licenses"],
            )
        self.assertEqual(len(sbom["vulnerabilities"]), 8)
        self.assertEqual(len({v["id"] for v in sbom["vulnerabilities"]}), 7)
        self.assertEqual(replay["sbomator"]["unresolved_inventory_fields"], 0)
        self.assertEqual(replay["license_enrichment"], audit)
        for path, key in (
            ("reports/sbomator.cdx.json", "corrected_sbom_sha256"),
            ("reports/sbomator-report.html", "corrected_report_sha256"),
            ("reports/sbomator-report-original.html", "original_report_sha256"),
            ("evidence/license-evidence.json", "license_evidence_sha256"),
        ):
            self.assertEqual(
                hashlib.sha256((demo.WEB / path).read_bytes()).hexdigest(), audit[key]
            )


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.server = demo.DemoServer(0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host = f"127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=5
        )
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        status, content = response.status, response.read()
        conn.close()
        return status, content

    def test_status_and_web_root_only(self):
        status, content = self.request("GET", "/api/status")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(content), {"running": False, "result": None})
        self.assertEqual(self.request("GET", "/../demo.py")[0], 403)
        self.assertEqual(self.request("GET", "/%2e%2e/demo.py")[0], 403)
        self.assertEqual(
            self.request("GET", "/api/status", headers={"Host": "evil.test"})[0], 403
        )

    def test_cross_origin_and_arbitrary_commands_rejected(self):
        self.assertEqual(
            self.request(
                "POST", "/api/run", "{}", {"Content-Type": "application/json"}
            )[0],
            403,
        )
        headers = {"Origin": f"http://{self.host}", "Content-Type": "application/json"}
        self.assertEqual(
            self.request("POST", "/api/run", '{"command":"anything"}', headers)[0], 400
        )
        headers["Origin"] = "https://evil.test"
        self.assertEqual(self.request("POST", "/api/run", "{}", headers)[0], 403)

    def test_start_and_duplicate_run_guard(self):
        released = threading.Event()
        entered = threading.Event()

        def fake_run(**kwargs):
            entered.set()
            released.wait(5)
            kwargs["progress"]({"stages": [{"status": "blocked"}]})

        headers = {"Origin": f"http://{self.host}", "Content-Type": "application/json"}
        with patch.object(demo, "run_demo", side_effect=fake_run):
            try:
                self.assertEqual(
                    self.request("POST", "/api/run", "{}", headers)[0], 202
                )
                self.assertTrue(entered.wait(2))
                self.assertEqual(
                    self.request("POST", "/api/run", "{}", headers)[0], 409
                )
                self.assertTrue(
                    json.loads(self.request("GET", "/api/status")[1])["running"]
                )
            finally:
                released.set()


if __name__ == "__main__":
    unittest.main()
