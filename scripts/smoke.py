"""Read-only smoke checks. No login, seeding, database reset or workflow mutation."""
import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    failed = False
    for path, expected in (("/api/health/live", 200), ("/api/health/ready", 200),
                           ("/api/applications", 401), ("/api/health/system", 401)):
        try:
            with urlopen(base + path, timeout=15) as response:
                status = response.status
                payload = json.load(response)
                valid = status == expected and (path != "/api/health/ready" or payload.get("ready") is True)
        except HTTPError as exc:
            status = exc.code
            valid = status == expected
        except (URLError, TimeoutError, ValueError) as exc:
            print(f"FAIL {path}: {type(exc).__name__}")
            failed = True
            continue
        print(f"{'PASS' if valid else 'FAIL'} {path}: HTTP {status} (expected {expected})")
        failed |= not valid
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
