"""Smoke test minimal E2E for Sistema SINAC NEXT

Checks:
 - Backend health at http://localhost:8000/health/
 - Frontend index at http://localhost:3000/ contains expected text
 - Frontend index at http://localhost:3000/ contains expected text ("SINAC NEXT")
 - (Optional) Camunda web on port 8081

Usage:
  python tests/smoke_test.py

Exit code: 0 on success, non-zero on failure.
"""
import sys
import requests

CHECKS = [
    {
        "name": "backend_health",
        "url": "http://localhost:8000/health/",
        "type": "json",
        "expect": {"status": "ok"}
    },
    {
        "name": "frontend_root",
        "url": "http://localhost:3000/",
        "type": "text",
        "expect_substr": "SINAC NEXT"
    },
    {
        "name": "camunda_home_optional",
        "url": "http://localhost:8081/",
        "type": "status",
        "optional": True
    }
]

TIMEOUT = 5


def fail(msg):
    print("[FAIL]", msg)


def ok(msg):
    print("[ OK ]", msg)


def run_check(check):
    name = check.get('name')
    url = check.get('url')
    optional = check.get('optional', False)
    try:
        r = requests.get(url, timeout=TIMEOUT)
    except Exception as e:
        if optional:
            print(f"[WARN] {name}: optional check failed ({e})")
            return True
        fail(f"{name}: request error: {e}")
        return False

    if check['type'] == 'status':
        if r.status_code == 200:
            ok(f"{name}: status 200")
            return True
        else:
            if optional:
                print(f"[WARN] {name}: unexpected status {r.status_code}")
                return True
            fail(f"{name}: unexpected status {r.status_code}")
            return False

    if check['type'] == 'json':
        try:
            j = r.json()
        except Exception as e:
            fail(f"{name}: invalid json: {e}")
            return False
        expected = check.get('expect', {})
        for k, v in expected.items():
            if j.get(k) != v:
                fail(f"{name}: json key '{k}' expected '{v}', got '{j.get(k)}'")
                return False
        ok(f"{name}: json OK")
        return True

    if check['type'] == 'text':
        text = r.text
        substr = check.get('expect_substr')
        if substr and substr in text:
            ok(f"{name}: found substring '{substr}'")
            return True
        else:
            fail(f"{name}: substring '{substr}' not found")
            return False

    fail(f"{name}: unknown check type '{check['type']}'")
    return False


def main():
    print("Running smoke test checks...\n")
    all_ok = True
    for c in CHECKS:
        ok_flag = run_check(c)
        all_ok = all_ok and ok_flag

    if all_ok:
        print("\nSmoke test passed.")
        return 0
    else:
        print("\nSmoke test failed.")
        return 2


if __name__ == '__main__':
    sys.exit(main())
