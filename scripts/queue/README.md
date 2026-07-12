# Creative Queue v1

Creative Queue is an independent, file-backed intake queue for reference images. It discovers supported images in `assets/references/` and creates one JSON record per new SHA-256 checksum.

It does not call OpenAI, does not inspect image pixels, does not invoke the Concept Generator and does not create Concept Cards. Its only responsibility is reliable image intake.

## Queue structure

```text
brain/queue/
├── pending/      # New images waiting for a future worker
├── processing/   # Reserved for a future worker
├── done/         # Reserved for successfully completed work
└── failed/       # Reserved for failed work with a recorded reason
```

Each queue item is an individual JSON file named `CQ-NNNN.json`. Its status is both stored in the JSON field and represented by its containing folder.

## Record contract

```json
{
  "id": "CQ-0001",
  "filename": "example.png",
  "relative_path": "assets/references/lead/tr/example.png",
  "sha256": "…",
  "geo": "TR",
  "funnel": "lead",
  "status": "pending",
  "created_at": "2026-07-12T00:00:00+00:00"
}
```

Required fields are `id`, `filename`, `relative_path`, `sha256`, `geo`, `funnel`, `status` and `created_at`.

## Scan behaviour

`scan()` recursively finds `.jpg`, `.jpeg`, `.png` and `.webp` files. For each file it:

1. calculates a SHA-256 checksum;
2. reads all queue records from `pending`, `processing`, `done` and `failed`;
3. skips the image when its SHA-256 is already present in any status;
4. infers `geo` and `funnel` only from unambiguous path components;
5. creates a new `pending/CQ-NNNN.json` record.

The source image is never changed, moved, renamed, copied or deleted. Because deduplication is checksum-based across all statuses, repeated scans are idempotent.

## Run

From the repository root:

```bash
python3 scripts/queue/queue.py
python3 scripts/queue/queue.py scan
```

Custom folders are available for isolated local checks:

```bash
python3 scripts/queue/queue.py scan \
  --references-dir /path/to/assets/references \
  --queue-dir /path/to/brain/queue
```

## Statuses

| Status | Meaning in v1 |
|---|---|
| `pending` | Image discovered and waiting for future processing. |
| `processing` | Reserved for a future worker that has claimed the item. |
| `done` | Reserved for a future worker that completed its task. |
| `failed` | Reserved for a future worker that recorded a failure. |

Creative Queue v1 only creates `pending` entries. Future consumers may move an item between status folders, but they must preserve the same `id` and `sha256` to retain deduplication.
