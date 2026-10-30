"""Rebuild draft-only evidence; reads contracts and the fixed diagnostic only."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import unittest

from .review import ROOT, audit_existing, digest

HERE = Path(__file__).resolve().parent


def write(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                      sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def inventory():
    names = ["RESEARCH_PROTOCOL", "RESEARCH_PROTOCOL_V2", "STRATEGY_SPEC",
             "DATA_DICTIONARY", "INTRATRADE_DATA_DICTIONARY", "DATASET_FREEZE",
             "INTRATRADE_RESEARCH_PROTOCOL", "INTRATRADE_R2_PROTOCOL",
             "INTRATRADE_R3_PROTOCOL", "INTRATRADE_R4_PROTOCOL",
             "FUTURE_VALIDATION_PROTOCOL", "FUTURE_VALIDATION_READINESS_RULE",
             "PROSPECTIVE_EVALUATION_PROTOCOL", "DRIFT_MONITOR_PROTOCOL",
             "SHADOW_MODE_PROTOCOL", "PC_A_NATIVE_TESTER_CAPABILITIES",
             "PROSPECTIVE_OPERATIONAL_ADDENDUM_20261023"]
    paths = [ROOT / "docs" / (n + ".md") for n in names]
    paths += [ROOT / "configs" / n for n in (
        "timestamp_clock_contract_v1.json", "drift_feature_whitelist.json",
        "drift_feature_whitelist_v1.archived.json", "prospective_candidate.template.json",
        "future_validation_cohort_manifest.template.json")]
    paths += sorted((ROOT / "research").rglob("*.json"))
    paths += sorted((ROOT / "docs/archive/pre_cloud_20261027").glob("*PROTOCOL.md"))
    result = []
    for path in paths:
        relative = path.relative_to(ROOT).as_posix()
        raw = path.read_bytes()
        content = raw.decode("utf-8-sig")  # require readable, valid source
        if path.suffix == ".json":
            json.loads(content)
        git = subprocess.check_output(["git", "show", "HEAD:" + relative], cwd=ROOT)
        if git.replace(b"\r\n", b"\n") != raw.replace(b"\r\n", b"\n"):
            raise ValueError("CONTRACT_CHANGED_" + relative)
        seal = Path(str(path) + ".sha256")
        seal_status = "NOT_PRESENT_NOT_INVENTED"
        if seal.exists():
            expected = seal.read_text().split()[0]
            seal_status = "VERIFIED" if expected == digest(path) else (
                "PARTIAL_LOCAL_CRLF_GIT_SEAL_VERIFIED" if
                expected == hashlib.sha256(git).hexdigest() and
                git.replace(b"\r\n", b"\n") == raw.replace(b"\r\n", b"\n")
                else "REJECTED")
            if seal_status == "REJECTED":
                raise ValueError("CONTRACT_SEAL_MISMATCH_" + relative)
        result.append(dict(path=relative, sha256=digest(path), bytes=len(raw),
                           git_content_sha256=hashlib.sha256(git).hexdigest(),
                           unchanged_from_reviewed_head=True, seal=seal_status,
                           status="VERIFIED_CONTENT_NOT_SCIENTIFIC_AUTHORIZATION",
                           authority="ARCHIVED" if "/archive/" in relative else
                           "PENDING_PROPOSAL" if "CAPABILITIES" in relative else
                           "REVIEWED_FROZEN_OR_OPERATIONAL_SOURCE"))
    return dict(base_head="ca7bab3d366d6a95575f54b57a923762fb234f5e", contracts=result,
                missing=["outputs/splits/split_manifest.json"] if not
                (ROOT / "outputs/splits/split_manifest.json").exists() else [],
                original_contracts_modified=False, new_contract_activated=False)


def main():
    write("contracts_inventory.json", inventory())
    write("arrival_review.json", audit_existing())
    patterns = ["test_native_methodology_proposal.py", "test_quote_replay.py"]
    suite = unittest.TestSuite()
    for pattern in patterns:
        suite.addTests(unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern=pattern))
    transcript = io.StringIO()
    result = unittest.TextTestRunner(stream=transcript, verbosity=2).run(suite)
    write("validation.json", dict(run=result.testsRun, failures=len(result.failures),
                                 errors=len(result.errors), skipped=len(result.skipped),
                                 patterns=patterns, transcript=transcript.getvalue()))
    if not result.wasSuccessful():
        raise SystemExit(1)
    write("evidence_hashes.json", {n: digest(HERE / n) for n in (
        "contracts_inventory.json", "arrival_review.json", "validation.json",
        "REVIEW_ES.md", "availability.py", "review.py", "build_evidence.py")})
    print(json.dumps(dict(contracts=len(inventory()["contracts"]), tests=result.testsRun,
                          failures=len(result.failures), errors=len(result.errors),
                          proposal="DRAFT_NOT_ACTIVE")))


if __name__ == "__main__":
    main()
