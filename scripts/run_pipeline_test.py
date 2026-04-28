from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.pipeline_service import process_document_image


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_pipeline_test.py <image_path> [lang]", file=sys.stderr)
        return 2

    image_path = Path(sys.argv[1])
    lang = sys.argv[2] if len(sys.argv) > 2 else "eng"

    if not image_path.exists():
        print(f"Image not found: {image_path}", file=sys.stderr)
        return 2

    result = process_document_image(image_path.read_bytes(), lang=lang)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
