"""Export the structural schemas for the current dataset format."""

import json
import types
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Union, get_args, get_origin, get_type_hints

from clue_benchmark.community_config import CommunityConfig
from clue_benchmark.config import Config


def shape(annotation):
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin in (types.UnionType, Union):
        return {"anyOf": [shape(a) for a in args]}
    if is_dataclass(annotation):
        hints = get_type_hints(annotation)
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {f.name: shape(hints[f.name]) for f in fields(annotation)},
        }
    if origin is list or annotation is list:
        return {"type": "array", "items": shape(args[0]) if args else {}}
    if annotation is dict:
        return {"type": "object"}
    if annotation is tuple:
        return {"type": "array"}
    return {
        "type": {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            type(None): "null",
        }[annotation]
    }


def main():
    root = Path(__file__).resolve().parents[1] / "schemas"
    root.mkdir(parents=True, exist_ok=True)
    config = shape(CommunityConfig)
    config["properties"]["puzzle"]["properties"]["config"] = shape(Config)
    config["properties"]["schema_version"] = {"const": "clue-community-1"}
    outputs = {
        "configuration.schema.json": config,
        "public-record.schema.json": {
            "oneOf": [
                {
                    "type": "object",
                    "required": [
                        "kind",
                        "case_id",
                        "world_id",
                        "suspects",
                        "domains",
                        "assignment_mode",
                        "corruption_allowance",
                    ],
                    "properties": {"kind": {"const": "case"}},
                },
                {
                    "type": "object",
                    "required": ["kind", "case_id", "report_id", "constraint", "text"],
                    "properties": {
                        "kind": {"const": "report"},
                        "constraint": {"type": "object"},
                        "text": {"type": "string"},
                    },
                },
            ]
        },
        "partition-record.schema.json": {
            "type": "object",
            "required": ["case_id", "report_id", "partition_id", "owners"],
            "properties": {
                "owners": {
                    "type": "array",
                    "minItems": 1,
                    "uniqueItems": True,
                    "items": {"type": "integer", "minimum": 0, "maximum": 7},
                }
            },
        },
        "authorization.schema.json": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "schema_version",
                "plan_id",
                "approved_by",
                "approved_at",
                "spending_ceiling_microdollars",
                "max_requests",
            ],
            "properties": {
                "schema_version": {"const": "clue-community-authorization-1"},
                "plan_id": {"type": "string", "minLength": 64, "maxLength": 64},
                "approved_by": {"type": "string", "minLength": 1},
                "approved_at": {"type": "string", "minLength": 1},
                "spending_ceiling_microdollars": {"type": "integer", "minimum": 0},
                "max_requests": {"type": "integer", "minimum": 1},
            },
        },
    }
    header = {
        "kind": {"const": "case"},
        **{
            k: {"type": "string"}
            for k in (
                "case_id",
                "world_id",
                "presentation_id",
                "split",
                "assignment_mode",
                "padding",
                "rules",
            )
        },
        "suspects": {"type": "array", "items": {"type": "string"}},
        "domains": {"type": "object"},
        "display_names": {"type": "object"},
        **{
            k: {"type": "integer", "minimum": 0}
            for k in ("agent_count", "corruption_allowance", "total_reports")
        },
    }
    report = {
        "kind": {"const": "report"},
        **{k: {"type": "string"} for k in ("case_id", "report_id", "text")},
        "constraint": {"type": "object"},
    }
    outputs["public-record.schema.json"] = {
        "oneOf": [
            {
                "type": "object",
                "properties": props,
                "required": list(props),
                "additionalProperties": False,
            }
            for props in (header, report)
        ]
    }
    outputs.update(
        {
            "answer-record.schema.json": {
                "type": "object",
                "required": [
                    "case_id",
                    "world_id",
                    "solution",
                    "possible_culprits",
                    "false_report_ids",
                    "nuisance_count",
                    "core_report_ids",
                ],
                "properties": {
                    "solution": {"type": "object", "required": ["murderer", "world"]},
                    "possible_culprits": {"type": "array", "minItems": 1},
                },
            },
            "certificate-record.schema.json": {
                "type": "object",
                "required": ["case_id", "certificate", "partition"],
                "properties": {
                    "certificate": {
                        "type": "object",
                        "required": [
                            "status",
                            "candidates",
                            "minimum_subset",
                            "coalition",
                            "core_certificate",
                            "case_hash",
                        ],
                    },
                    "partition": {
                        "type": "object",
                        "required": [
                            "partition_id",
                            "core_allocation",
                            "nuisance_recipe",
                            "realized_overlap",
                        ],
                    },
                },
            },
            "manifest.schema.json": {
                "type": "object",
                "required": [
                    "schema_version",
                    "config",
                    "config_hash",
                    "files",
                    "worlds",
                    "metrics",
                    "complete",
                    "attempts",
                    "rejections",
                    "checkpoint_identity",
                ],
                "properties": {
                    "schema_version": {"const": "clue-community-1"},
                    "config": config,
                    "files": {
                        "type": "object",
                        "required": [
                            "cases.jsonl",
                            "partitions.jsonl",
                            "answers.jsonl",
                            "certificates.jsonl",
                        ],
                    },
                    "complete": {"type": "boolean"},
                },
            },
            "evaluation-plan.schema.json": {
                "type": "object",
                "required": [
                    "schema_version",
                    "plan_id",
                    "bundle_files",
                    "bundle_manifest_hash",
                    "source_hashes",
                    "models",
                    "conditions",
                    "prompt",
                    "tool_access",
                    "retries",
                    "spending_ceiling_microdollars",
                    "max_requests",
                ],
                "properties": {
                    "schema_version": {"const": "clue-community-evaluation-1"},
                    "retries": {"const": 0},
                    "models": {"type": "array", "minItems": 1},
                    "minimum_request_interval_seconds": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 60,
                    },
                },
            },
        }
    )
    for name, schema in outputs.items():
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["description"] = (
            "Structural contract; Python configuration/semantic validation additionally enforces cross-field guarantees."
        )
        (root / name).write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
