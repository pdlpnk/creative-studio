#!/usr/bin/env python3
"""File-backed Creative Queue for reference images.

The queue is independent from OpenAI and the Concept Generator.  ``scan`` is
the only public action in v1: it discovers supported images and creates one
pending JSON record per new SHA-256 checksum.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
STATUSES = ("pending", "processing", "done", "failed")
QUEUE_ID_PATTERN = re.compile(r"^CQ-(\d{4,})$")
MODULE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODULE_DIR.parents[1]
DEFAULT_REFERENCES_DIR = PROJECT_ROOT / "assets" / "references"
DEFAULT_QUEUE_DIR = PROJECT_ROOT / "brain" / "queue"


def sha256_file(path: Path) -> str:
    """Calculate a SHA-256 checksum without loading the whole file at once."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def infer_context(image_path: Path) -> tuple[str, str]:
    """Infer GEO and funnel only when the library directory is unambiguous."""
    parts = {part.lower() for part in image_path.parts}
    geo = "TR" if "tr" in parts else "AZ" if "az" in parts else "unknown"
    funnel = (
        "registration"
        if "registration" in parts
        else "lead"
        if "lead" in parts
        else "unknown"
    )
    return geo, funnel


def image_files(references_dir: Path) -> Iterable[Path]:
    """Yield supported image files recursively in deterministic path order."""
    for path in sorted(references_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield path


def load_records(queue_dir: Path) -> list[dict[str, Any]]:
    """Read all valid queue records across every status directory."""
    records: list[dict[str, Any]] = []
    for status in STATUSES:
        status_dir = queue_dir / status
        if not status_dir.exists():
            continue
        for record_path in sorted(status_dir.glob("CQ-*.json")):
            try:
                record = json.loads(record_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid queue record: {record_path}") from error
            if not isinstance(record, dict):
                raise ValueError(f"Queue record must be an object: {record_path}")
            records.append(record)
    return records


def next_queue_id(records: Iterable[dict[str, Any]]) -> str:
    """Return the next monotonic queue ID without reusing existing IDs."""
    highest = 0
    for record in records:
        match = QUEUE_ID_PATTERN.match(str(record.get("id", "")))
        if match:
            highest = max(highest, int(match.group(1)))
    return f"CQ-{highest + 1:04d}"


def write_record(record: dict[str, Any], destination: Path) -> Path:
    """Write a new JSON record and refuse to overwrite an existing one."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"Queue record already exists: {destination}")
    destination.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return destination


def scan(
    references_dir: Path = DEFAULT_REFERENCES_DIR,
    queue_dir: Path = DEFAULT_QUEUE_DIR,
) -> list[dict[str, Any]]:
    """Create pending records for images whose SHA-256 is not already queued.

    Returns only the records created by this call. Existing records in any
    status folder prevent a duplicate queue entry for the same source bytes.
    """
    references_dir = references_dir.resolve()
    queue_dir = queue_dir.resolve()
    if not references_dir.is_dir():
        raise FileNotFoundError(f"References directory not found: {references_dir}")

    records = load_records(queue_dir)
    known_hashes = {str(record.get("sha256", "")) for record in records}
    created: list[dict[str, Any]] = []
    project_root = references_dir.parent.parent

    for image_path in image_files(references_dir):
        checksum = sha256_file(image_path)
        if checksum in known_hashes:
            continue

        geo, funnel = infer_context(image_path)
        record = {
            "id": next_queue_id([*records, *created]),
            "filename": image_path.name,
            "relative_path": image_path.relative_to(project_root).as_posix(),
            "sha256": checksum,
            "geo": geo,
            "funnel": funnel,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        write_record(record, queue_dir / "pending" / f"{record['id']}.json")
        known_hashes.add(checksum)
        created.append(record)

    return created


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create independent pending queue records for reference images."
    )
    parser.add_argument(
        "command", nargs="?", default="scan", choices=("scan",), help="Queue action."
    )
    parser.add_argument(
        "--references-dir",
        type=Path,
        default=DEFAULT_REFERENCES_DIR,
        help="Reference-library directory to scan.",
    )
    parser.add_argument(
        "--queue-dir",
        type=Path,
        default=DEFAULT_QUEUE_DIR,
        help="Queue directory holding status folders.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command != "scan":  # Defensive guard for future subcommands.
        raise ValueError(f"Unsupported command: {args.command}")

    created = scan(args.references_dir, args.queue_dir)
    print(f"Created {len(created)} pending queue record(s).")
    for record in created:
        print(f"{record['id']} {record['relative_path']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, FileExistsError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(2)
