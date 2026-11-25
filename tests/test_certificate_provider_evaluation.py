"""Offline feasibility check for the crt.sh JSON response shape."""
import json
import unittest
from datetime import datetime
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / "examples/certificate-inventory/contract.json"


def read_rows(rows):
    if not isinstance(rows, list):
        raise ValueError("expected a JSON array")
    names = []
    for row in rows:
        if not isinstance(row, dict) or type(row.get("id")) is not int or not isinstance(row.get("name_value"), str):
            raise ValueError("invalid certificate row")
        names.extend(row["name_value"].splitlines())
    return names


class CertificateProviderEvaluation(unittest.TestCase):
    def test_invalid_refresh_preserves_populated_snapshot(self):
        rows = [{"id": 42, "name_value": "example.test"}]
        snapshot = read_rows(rows)
        with self.assertRaises(ValueError):
            snapshot = read_rows([{"id": 43, "name_value": "app.example.test"}, {}])
        self.assertEqual(snapshot, ["example.test"])

    def test_refresh_scenarios(self):
        fixture = json.loads(FIXTURE.read_text())
        expected_names = {case["input"]: case["expected_name"] for case in fixture["cases"]}
        # The contract fixtures supply the scope oracle. This experiment isolates
        # the provider's ability to distinguish rows, empty success and failures.
        for scenario in fixture["refresh_scenarios"]:
            snapshot = None
            for step in scenario["steps"]:
                with self.subTest(scenario=scenario["name"], at=step["at"]):
                    if step.get("error") == "timeout":
                        outcome = "provider_failure"
                    else:
                        rows = [{"id": cert.get("certificate_id", 123), "name_value": "\n".join(cert["names"])}
                                for cert in step["response"]["certificates"]]
                        try:
                            names = read_rows(rows)
                        except ValueError:
                            outcome = "invalid_response"
                        else:
                            outcome = "success"
                            snapshot = {"completed_at": step["at"], "names": [
                                expected_names[name] for name in names if expected_names[name] is not None
                            ]}
                    self.assertEqual(outcome, step["expected_outcome"])
                    self.assertEqual(snapshot, step["expected_snapshot"])
                    if "expected_age_seconds" in step:
                        attempted = datetime.fromisoformat(step["at"].replace("Z", "+00:00"))
                        completed = datetime.fromisoformat(snapshot["completed_at"].replace("Z", "+00:00"))
                        self.assertEqual((attempted - completed).total_seconds(), step["expected_age_seconds"])


if __name__ == "__main__":
    unittest.main()
