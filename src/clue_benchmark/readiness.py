"""Local metadata checks and honest public/research release gates."""

import json
from pathlib import Path

from .dataset import read_cases
from .review import presentation_hashes
from .study import sha256

RAI_FIELDS = (
    "rai:dataLimitations",
    "rai:dataBiases",
    "rai:personalSensitiveInformation",
    "rai:dataUseCases",
    "rai:dataSocialImpact",
    "rai:hasSyntheticData",
    "prov:wasDerivedFrom",
    "prov:wasGeneratedBy",
)


def metadata_checks(dataset):
    dataset = Path(dataset)
    meta = json.loads((dataset / "croissant.json").read_text())
    manifest = json.loads((dataset / "manifest.json").read_text())
    missing = [
        field
        for field in (
            "@context",
            "@type",
            "name",
            "url",
            "license",
            "conformsTo",
            "distribution",
            "recordSet",
            *RAI_FIELDS,
        )
        if field not in meta or meta[field] in (None, "", [], {})
    ]
    errors = []
    for file in meta.get("distribution", []):
        path = file.get("contentUrl", "")
        if path in manifest["files"] and (
            file.get("sha256") != manifest["files"][path]
            or sha256(dataset / path) != file.get("sha256")
        ):
            errors.append(path)
        elif path not in manifest["files"]:
            errors.append(path)
    return {
        "required_fields_present": not missing,
        "missing_fields": missing,
        "distribution_hashes_match": not errors,
        "hash_errors": errors,
        "license_decided": meta.get("license", "").startswith("https://"),
        "public_hosting_configured": bool(meta.get("distribution"))
        and all(
            file.get("contentUrl", "").startswith("https://")
            for file in meta.get("distribution", [])
        ),
        "validation_scope": "Local field/hash checks. Full Croissant validation and hosted loading must also succeed before publication.",
    }


def readiness_report(dataset, review_report=None, study_results=None):
    dataset = Path(dataset)
    checks = metadata_checks(dataset)
    ids = sorted(
        c["case_id"]
        for split in ("dev", "test")
        for c in read_cases(dataset / "public" / f"{split}.jsonl")
    )
    review_matches = bool(
        review_report
        and review_report.get("source_case_ids") == ids
        and review_report.get("presentation_hashes") == presentation_hashes()
    )
    gates = [
        {
            "gate": "ownership-and-licensing",
            "status": "pending",
            "reason": "Owner decision and imported-code ownership review remain pending.",
        },
        {
            "gate": "independent-wording-review",
            "status": "passed"
            if review_matches and review_report["status"] == "approved"
            else "pending",
            "reason": "Two independent human reviewers per packet item, no blocking issues, maintainer identity verification.",
        },
        {
            "gate": "dataset-hosting",
            "status": "configured"
            if checks["public_hosting_configured"]
            else "pending",
            "reason": "Final URLs must be accessible and loadable, with a decided license.",
        },
        {
            "gate": "hosted-croissant-validation",
            "status": "pending",
            "reason": "Run the official validator and verify record loading against the final host; local checks do not certify accessibility.",
        },
    ]
    empirical = bool(
        study_results
        and study_results["manifest"]["observed_samples"]
        == study_results["manifest"]["expected_episodes"]
        and study_results["manifest"]["observed_samples"] > 0
        and study_results["manifest"]["models"]
        and study_results["manifest"].get("test_sha256")
        == sha256(dataset / "private/test.jsonl")
        and all(
            not m.startswith("mockllm/") for m in study_results["manifest"]["models"]
        )
    )
    return {
        "dataset": str(dataset),
        "local_metadata": checks,
        "public_release_ready": False,
        "public_release_gates": gates,
        "model_evidence_available": empirical,
        "research_claim": "Formal case correctness is verified separately. Model reasoning and strategic-investigation claims need empirical validation and analysis; complete logs alone do not establish construct validity.",
        "paid_calls_in_readiness_check": 0,
    }
