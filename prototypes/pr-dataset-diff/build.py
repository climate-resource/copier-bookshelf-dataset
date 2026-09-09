#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["pyarrow>=23", "pyyaml>=6"]
# ///
"""Throwaway bundle reader. Run with uv run build.py --help."""

import argparse
import copy
import csv
import hashlib
import json
import math
import re
from pathlib import Path

import pyarrow.parquet as pq
import yaml


def json_safe(value):
    """Preserve nonfinite values and large integers in browser-readable JSON."""
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return {"nonfinite": str(value)}
    if isinstance(value, int) and abs(value) > 2**53 - 1:
        return {"integer": str(value)}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def read_bundle(path, keys):  # noqa: PLR0912 - Keep this throwaway reader in one place.
    """Read supported resource bytes and the metadata that frames them."""
    manifest = yaml.safe_load((path / "manifest.lock").read_text())
    if str(manifest.get("schema_version", "3.2")).split(".")[0] != "3":
        message = "Prototype supports bundle schema 3 only"
        raise ValueError(message)
    tables = {}
    for resource in manifest.get("resources", []):
        name = resource["name"]
        if resource.get("kind", "managed") == "pointer":
            tables[name] = {"unavailable": "External pointer: content was not fetched"}
            continue
        digest = resource["hash"]
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
            message = f"Invalid hash for {name}"
            raise ValueError(message)
        ext = "parquet" if resource["type"] in ("tabular", "timeseries") else "bin"
        file = path / "resources" / f"{digest[7:]}.{ext}"
        if hashlib.sha256(file.read_bytes()).hexdigest() != digest[7:]:
            message = f"Content hash mismatch: {name}"
            raise ValueError(message)
        if resource["type"] not in ("tabular", "timeseries"):
            tables[name] = {
                "unavailable": "Only bytes and metadata compared for this resource type"
            }
            continue
        if resource.get("format") == "csv":
            with file.open(newline="") as stream:
                reader = csv.DictReader(stream)
                rows = list(reader)
                columns = {c: "CSV text" for c in reader.fieldnames or []}
        elif file.read_bytes()[:4] == b"PAR1":
            table = pq.read_table(file)
            rows = table.to_pylist()
            columns = {field.name: str(field.type) for field in table.schema}
        else:
            tables[name] = {
                "unavailable": "Unsupported encoding: requires a format adapter"
            }
            continue
        if name in keys:
            identity = keys[name]
            source = "Explicit keys"
        elif resource["type"] == "timeseries" and any(
            re.fullmatch(r"\d{4}", c) for c in columns
        ):
            identity = [c for c in columns if not re.fullmatch(r"\d{4}", c)]
            source = (
                "Inferred wide annual timeseries: all non-year columns, including unit"
            )
        else:
            tables[name] = {
                "unavailable": "Row identity is unknown: supply --keys",
                "columns": columns,
                "row_count": len(rows),
            }
            continue
        if not set(identity) <= columns.keys():
            message = f"Missing key columns for {name}"
            raise ValueError(message)
        tables[name] = {
            "keys": identity,
            "key_source": source,
            "columns": columns,
            "rows": rows,
        }
    return json_safe({"manifest": manifest, "tables": tables})


def demo():
    """Build synthetic walkthroughs for the comparison model."""
    rows = [
        {
            "region": "World",
            "scenario": "Reference",
            "unit": "Mt CO2/yr",
            "2020": 100.0,
            "2030": 90.0,
            "2050": 50.0,
        },
        {
            "region": "Europe",
            "scenario": "Reference",
            "unit": "Mt CO2/yr",
            "2020": 20.0,
            "2030": 15.0,
            "2050": 5.0,
        },
    ]
    before = {
        "manifest": {
            "schema_version": "3.2",
            "book": {
                "volume": "demo-emissions",
                "version": "v1.0.0",
                "description": "Illustrative data, not a published dataset",
                "license": "CC-BY-4.0",
                "entries": [{"name": "emissions"}],
            },
            "activity": {"code_ref": "demo-base"},
            "resources": [
                {
                    "name": "emissions",
                    "type": "timeseries",
                    "hash": "demo-before",
                    "visibility": "public",
                }
            ],
        },
        "tables": {
            "emissions": {
                "keys": ["region", "scenario", "unit"],
                "key_source": "Demo dimensions",
                "columns": {k: "double" if k.isdigit() else "string" for k in rows[0]},
                "rows": rows,
            }
        },
    }
    scenarios = {}

    def case(name, note, mutate):
        after = copy.deepcopy(before)
        mutate(after)
        if (
            after["tables"] != before["tables"]
            and after["manifest"]["resources"][0]["hash"] == "demo-before"
        ):
            after["manifest"]["resources"][0]["hash"] = "demo-changed"
        after["manifest"]["activity"]["code_ref"] = "demo-head"
        scenarios[name] = {
            "schema_version": "prototype-1",
            "baseline": "Synthetic PR base",
            "candidate": "Synthetic PR head",
            "note": note,
            "before": before,
            "after": after,
        }

    case(
        "No data change",
        "Provenance changes alone should not look like a data revision.",
        lambda x: None,
    )
    case(
        "Metadata only",
        "The license changed; the values are identical.",
        lambda x: x["manifest"]["book"].update(license="CC0-1.0"),
    )

    def revised(x):
        x["tables"]["emissions"]["rows"][0]["2030"] = 99.0
        x["tables"]["emissions"]["rows"][1]["2050"] = None
        x["tables"]["emissions"]["rows"].append(
            {
                "region": "Asia",
                "scenario": "Reference",
                "unit": "Mt CO2/yr",
                "2020": 40.0,
                "2030": 35.0,
                "2050": 25.0,
            }
        )
        x["manifest"]["resources"][0]["hash"] = "demo-revised"

    case(
        "Values and coverage",
        "One value rises 10%, one becomes null, and one region is added.",
        revised,
    )
    case(
        "Reordered rows",
        "Row order and byte hash change, but observations stay the same.",
        lambda x: (
            x["tables"]["emissions"]["rows"].reverse(),
            x["manifest"]["resources"][0].update(hash="demo-reordered"),
        ),
    )
    case(
        "Unit change",
        "Changing units removes and adds series; their values cannot be subtracted.",
        lambda x: x["tables"]["emissions"]["rows"][0].update(unit="Gt CO2/yr"),
    )
    case(
        "Duplicate identity",
        "Ambiguous row keys must stop the value comparison.",
        lambda x: x["tables"]["emissions"]["rows"].append(copy.deepcopy(rows[0])),
    )
    case(
        "Missing baseline",
        "No baseline means no comparison. It must not be reported as zero changes.",
        lambda x: None,
    )
    scenarios["Missing baseline"]["before"] = None
    return scenarios


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path)
    parser.add_argument("--after", type=Path)
    parser.add_argument(
        "--keys",
        default="{}",
        help='JSON resource-to-key mapping, e.g. {"raw":["region","year"]}',
    )
    parser.add_argument("--baseline", default="PR base bundle")
    parser.add_argument("--candidate", default="PR candidate bundle")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "demo.html")
    args = parser.parse_args()
    if args.before and not args.after:
        parser.error("--before requires --after")
    if args.after:
        keys = json.loads(args.keys)
        report = {
            "schema_version": "prototype-1",
            "baseline": args.baseline,
            "candidate": args.candidate,
            "note": (
                "Local bundle comparison. Baseline labels are supplied by the caller; "
                "code references are shown below."
            ),
            "before": read_bundle(args.before, keys) if args.before else None,
            "after": read_bundle(args.after, keys),
        }
        scenarios = {"Bundle comparison": report}
    else:
        scenarios = demo()
        report = scenarios["Values and coverage"]
    payload = json.dumps(scenarios, ensure_ascii=True, allow_nan=False).replace(
        "<", "\\u003c"
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    template = Path(__file__).with_name("viewer.html").read_text()
    args.out.write_text(template.replace("/* EMBEDDED_REPORTS */ {}", payload))
    args.out.with_suffix(".json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n"
    )
    print(
        f"Open {args.out}; "
        f"import {args.out.with_suffix('.json')} in any generated viewer"
    )
