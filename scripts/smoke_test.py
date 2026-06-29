#!/usr/bin/env python3
"""Schema smoke test (Epic A, Story A.9 verification).

The Epic C reference repo does not exist yet, so this proves the gate bites
using the §2.x example blocks extracted under schemas/examples/:
  - every file in examples/valid/   MUST pass its schema
  - every file in examples/invalid/ MUST fail (removed flag, plaintext secret,
    cluster identity leak, pipeline selector, intra-file constraint, unknown schema)

Exit 0 only if every expectation holds.
"""

import sys

from validate_config import validate_paths


def _report(title, roots, expect_ok) -> bool:
    print(f"\n=== {title} ===")
    all_good = True
    _, results = validate_paths(roots)
    for r in results:
        good = r.ok == expect_ok
        all_good = all_good and good
        print(f"{'OK ' if good else 'BAD'}  {'PASS' if r.ok else 'FAIL'}  {r.file}")
        if not r.ok:
            for e in r.errors:
                print(f"        - {e}")
    return all_good


def main() -> int:
    ok_valid = _report("valid fixtures (expect PASS)", ["schemas/examples/valid"], True)
    ok_invalid = _report("invalid fixtures (expect FAIL)", ["schemas/examples/invalid"], False)

    print("\n=== result ===")
    if ok_valid and ok_invalid:
        print("Smoke test PASSED: all valid fixtures pass, all broken fixtures rejected.")
        return 0
    print("Smoke test FAILED: an expectation did not hold (see BAD lines above).")
    return 1


if __name__ == "__main__":
    sys.exit(main())