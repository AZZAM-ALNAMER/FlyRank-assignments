import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import requests

CASES_PATH = Path(__file__).parent / "cases.json"
API_URL = "http://localhost:8000/enrich"

def run_evals():
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    results = []
    correct = 0

    for i, case in enumerate(cases, start=1):
        response = requests.post(API_URL, json={
            "title": case["title"],
            "description": case["description"]
        })

        if response.status_code != 200:
            print(f"Case {i} ({case['title']}): FAILED — status {response.status_code}")
            results.append({"case": i, "title": case["title"], "passed": False, "reason": f"status {response.status_code}"})
            continue

        actual = response.json()
        expected = case["expected_category"]
        passed = actual["category"] == expected

        if passed:
            correct += 1
            print(f"Case {i} ({case['title']}): PASS — got '{actual['category']}'")
        else:
            print(f"Case {i} ({case['title']}): FAIL — expected '{expected}', got '{actual['category']}'")

        results.append({
            "case": i,
            "title": case["title"],
            "expected": expected,
            "actual": actual["category"],
            "passed": passed
        })

    print(f"\n{correct}/{len(cases)} correct")

    failed = [r for r in results if not r["passed"]]
    if failed:
        print("\nFailed cases:")
        for r in failed:
            print(f"  - {r['title']}: expected {r.get('expected')}, got {r.get('actual')}")

    return correct, len(cases)


if __name__ == "__main__":
    run_evals()