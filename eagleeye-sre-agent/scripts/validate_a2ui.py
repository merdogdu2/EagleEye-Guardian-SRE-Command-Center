# Copyright 2026 EagleEye Guardian Contributors
# SPDX-License-Identifier: Apache-2.0

"""Standalone CLI validator checking all 10 mandatory A2UI v0.9 guardrails."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.core.a2ui.primitives import (
    A2UI_MIME_TYPE,
    A2UI_OPEN_TAG,
    extract_a2ui_messages_from_part,
    validate_a2ui_envelope,
    wrap_a2ui_part,
)
from app.core.a2ui.surfaces import build_all_reference_surfaces


def run_self_test() -> int:
    """Validate every generated A2UI v0.9 reference surface and verify negative rule traps."""
    surfaces = build_all_reference_surfaces()
    for name, messages in surfaces.items():
        errors = validate_a2ui_envelope(messages)
        if errors:
            print(f"[FAIL] Surface '{name}' failed validation:\n  - " + "\n  - ".join(errors))
            return 1
        part = wrap_a2ui_part(messages)
        if not part.part_metadata or part.part_metadata.get("mimeType") != A2UI_MIME_TYPE:
            print(f"[FAIL] Surface '{name}' Part missing mimeType={A2UI_MIME_TYPE}")
            return 1
        if not part.inline_data or A2UI_OPEN_TAG not in (part.inline_data.data or b""):
            print(f"[FAIL] Surface '{name}' Part missing <a2a_datapart_json> wrapper")
            return 1
        round_tripped = extract_a2ui_messages_from_part(part)
        if round_tripped != messages:
            print(f"[FAIL] Surface '{name}' round-trip mismatch")
            return 1
        print(f"[PASS] Surface '{name}' validated cleanly ({len(messages)} envelope verbs).")

    # Verify negative test cases are caught by the validator
    bad_h6 = [
        {
            "version": "v0.9",
            "updateComponents": {
                "surfaceId": "bad",
                "components": [
                    {
                        "id": "root",
                        "component": "MaterialText",
                        "text": "# Bad Heading",
                        "usageHint": "h6",
                    }
                ],
            },
        }
    ]
    detected = validate_a2ui_envelope(bad_h6)
    if len(detected) < 2:
        print("[FAIL] Validator did not catch forbidden usageHint='h6' and '#' heading.")
        return 1
    print(f"[PASS] Negative guardrail self-checks caught {len(detected)} expected violations.")
    print("All A2UI v0.9 surfaces and guardrails passed 100%.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate A2UI v0.9 JSON surfaces against the 10 mandatory guardrails."
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Validate all built-in EagleEye Guardian A2UI v0.9 surfaces and guardrail checks.",
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Optional JSON files containing A2UI v0.9 message arrays to validate.",
    )
    args = parser.parse_args(argv)

    if args.self_test or not args.files:
        rc = run_self_test()
        if rc != 0 or not args.files:
            return rc

    exit_code = 0
    for file_path in args.files:
        path = pathlib.Path(file_path)
        data = json.loads(path.read_text(encoding="utf-8"))
        errors = validate_a2ui_envelope(data)
        if errors:
            print(f"[FAIL] {path}: " + "; ".join(errors))
            exit_code = 1
        else:
            print(f"[PASS] {path}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
