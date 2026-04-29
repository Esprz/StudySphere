"""CLI for standalone simulator DB bundle export/import."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .adapter import export_db_bundle
from .importer import import_db_bundle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export or import Prisma-compatible simulator DB bundles."
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=["export-bundle", "import-bundle"],
        default="export-bundle",
    )
    parser.add_argument("--input-dir", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--bundle-dir", type=Path, default=None)
    parser.add_argument("--database-url", type=str, default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "export-bundle":
        if args.input_dir is None:
            raise ValueError("--input-dir is required for export-bundle")
        result = export_db_bundle(input_dir=args.input_dir, output_dir=args.output_dir)
        print(
            json.dumps(
                {
                    "output_dir": str(result.output_dir),
                    "files": {name: str(path) for name, path in result.files.items()},
                    "record_counts": result.record_counts,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return

    if args.bundle_dir is None:
        raise ValueError("--bundle-dir is required for import-bundle")
    result = import_db_bundle(
        bundle_dir=args.bundle_dir,
        database_url=args.database_url,
        dry_run=args.dry_run,
    )
    print(
        json.dumps(
            {
                "bundle_dir": str(result.bundle_dir),
                "database_url": result.database_url,
                "available_counts": result.available_counts,
                "imported_counts": result.imported_counts,
                "dry_run": result.dry_run,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
