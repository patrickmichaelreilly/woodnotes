#!/usr/bin/env python3
"""Validate and canonically apply a player-exported transcription change set."""

import argparse
import json
from pathlib import Path

from parsecheck import parse


def normalize_encoding(value: str) -> str:
    """Normalize token spacing while retaining one newline per source system."""
    lines = [" ".join(line.split()) for line in value.splitlines() if line.strip()]
    if not lines:
        raise ValueError("encoding cannot be empty")
    encoding = "\n".join(lines)
    parse(encoding)
    return encoding


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("change_file", type=Path)
    parser.add_argument("--corpus", type=Path, default=Path("corpus.json"))
    args = parser.parse_args()

    export = json.loads(args.change_file.read_text(encoding="utf-8"))
    if export.get("format") != "woodnotes-transcription-changes" or export.get("version") != 1:
        raise ValueError("unsupported transcription-change format or version")
    changes = export.get("changes")
    if not isinstance(changes, list):
        raise ValueError("changes must be a list")

    corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
    figures = {figure["id"]: figure for figure in corpus["figures"]}
    seen: set[str] = set()
    applied: list[str] = []

    for change in changes:
        if not isinstance(change, dict) or not isinstance(change.get("id"), str):
            raise ValueError("every change must be an object with a string id")
        figure_id = change["id"]
        if figure_id in seen:
            raise ValueError(f"duplicate change id: {figure_id}")
        if figure_id not in figures:
            raise ValueError(f"unknown figure id: {figure_id}")
        unexpected = set(change) - {"id", "enc", "approved"}
        if unexpected:
            raise ValueError(f"{figure_id}: unsupported fields: {', '.join(sorted(unexpected))}")
        if "enc" not in change and "approved" not in change:
            raise ValueError(f"{figure_id}: change has no editable fields")

        figure = figures[figure_id]
        if "enc" in change:
            if not isinstance(change["enc"], str):
                raise ValueError(f"{figure_id}: enc must be a string")
            figure["enc"] = normalize_encoding(change["enc"])
        if "approved" in change:
            if not isinstance(change["approved"], bool):
                raise ValueError(f"{figure_id}: approved must be true or false")
            figure["approved"] = change["approved"]
        seen.add(figure_id)
        applied.append(figure_id)

    args.corpus.write_text(json.dumps(corpus, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Applied {len(applied)} changes: {', '.join(applied)}")


if __name__ == "__main__":
    main()
