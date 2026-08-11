#!/usr/bin/env python3
"""Validate the data-driven player corpus.

The player now loads corpus.json at runtime and renders one selected figure at a
time, so HTML section generation is intentionally no longer required.
"""
import json
import os
import sys

from parsecheck import parse

with open("corpus.json", encoding="utf-8") as source:
    corpus = json.load(source)

figures = corpus["figures"]
ids = [figure["id"] for figure in figures]
duplicates = sorted({figure_id for figure_id in ids if ids.count(figure_id) > 1})
errors = []

if duplicates:
    errors.append(f"duplicate ids: {', '.join(duplicates)}")

for figure in figures:
    if not isinstance(figure.get("approved"), bool):
        errors.append(f"{figure['id']}: approved must be true or false")

    encoding = figure.get("enc")
    if encoding:
        try:
            parse(encoding)
        except ValueError as error:
            errors.append(f"{figure['id']}: {error}")

    for crop in figure.get("crops") or []:
        if not os.path.isfile(crop):
            errors.append(f"{figure['id']}: missing crop {crop}")

if errors:
    print("\n".join(errors), file=sys.stderr)
    sys.exit(1)

playable = sum(bool(figure.get("enc")) for figure in figures)
active = len(figures)
print(
    f"OK: {playable} playable / {active} active catalogued; "
    "all crop paths present"
)
