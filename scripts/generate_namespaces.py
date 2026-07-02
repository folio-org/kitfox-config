#!/usr/bin/env python3
"""Deterministic generator for all kitfox-config namespace.yaml files (Step 3/4).

Authoritative inputs are the namespace lists copied verbatim from
pipelines-shared-library/src/org/folio/Constants.groovy and the resolveMembers
logic from DependentParametersResolver.groovy. One rule, one place.

Usage:
    python scripts/generate_namespaces.py          # write files
    python scripts/generate_namespaces.py --check   # fail if any file is stale
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

# --- Constants.groovy (verbatim) ---------------------------------------------
TESTING_NAMESPACES = [
    "cypress", "data-migration", "data-anonymization", "release-validation",
    "ecs-snapshot", "karate", "snapshot", "snapshot2", "sprint", "sprint2",
    "pre-bugfest", "orchid-migration", "lsdi",
]
DEV_NAMESPACES = [
    "aggies", "bama", "bienenvolk", "big-fc", "citation", "corsair",
    "data-anonymization", "dreamliner", "dresden", "eureka", "eureka-2nd",
    "erm", "firebird", "folijet", "k-int", "leipzig", "spitfire",
    "spitfire-2nd", "thor", "thunderjet", "thunderjet-2nd", "vega", "vega-2nd",
    "volaris", "volaris-2nd",
]
RELEASE_NAMESPACES = ["sunflower", "trillium"]
TMP_NAMESPACES = ["test", "test-1", "test-2", "tdspora"]

# Cluster -> (namespace list, configType for the "ordinary" namespaces, lifecycle category)
CLUSTERS = {
    "folio-etesting": (TESTING_NAMESPACES, "testing", "testing"),
    "folio-edev": (DEV_NAMESPACES, "development", "dev"),
    "folio-eperf": (DEV_NAMESPACES + RELEASE_NAMESPACES, "performance", "dev"),
    "folio-tmp": (TMP_NAMESPACES, "development", "tmp"),
}

BUGFEST_SNAPSHOT_NAME = "folio-bugfest-trillium-16-06-2026-ga"

# resolveMembers
SHARED_NAMESPACES = ["sprint", "snapshot", "snapshot2"]
SHARED_ENV_MEMBERS = [
    "thunderjet", "folijet", "spitfire", "vega", "thor", "Eureka", "volaris",
    "corsair", "Bama", "Aggies", "Dreamliner", "Leipzig", "firebird", "dojo", "erm",
]
ENVS_MEMBERS_LIST = {
    "bama": "Bama", "big-fc": "Big FC", "citation": "Citation", "cypress": "AQA",
    "dresden": "Dresden", "dreamliner": "Dreamliner", "eureka": "Eureka",
    "eureka-2nd": "Eureka", "erm": "erm", "firebird": "firebird", "folijet": "folijet",
    "karate": "", "spitfire": "spitfire", "spitfire-2nd": "spitfire", "thor": "thor",
    "thunderjet": "thunderjet", "vega": "vega", "vega-2nd": "vega", "volaris": "volaris",
    "volaris-2nd": "volaris", "leipzig": "leipzig", "snapshot": "", "sprint": "",
}

QUAD_TENANTS = ["diku", "consortium", "university", "college"]
CONSORTIA_BLOCK = [
    {"central": "consortium", "name": "Consortium", "members": ["university", "college"]}
]
OPERATIONS = {
    "uiBuild": True, "runSanityCheck": False, "skipReindex": False,
    "entitlementApproach": "STATE", "setBaseUrl": True,
}


def resolve_members(namespace: str) -> list[str]:
    if namespace in SHARED_NAMESPACES:
        return list(SHARED_ENV_MEMBERS)
    val = ENVS_MEMBERS_LIST.get(namespace, "")
    return [val] if val else []


def build_namespace(cluster: str, namespace: str) -> dict:
    namespaces, ordinary_config, ordinary_category = CLUSTERS[cluster]

    is_release = namespace in RELEASE_NAMESPACES
    config_type = "release" if is_release else ordinary_config
    category = "release" if is_release else ordinary_category

    if namespace == "sunflower":
        platform_branch, release_type = "sunflower", "SUNFLOWER"
    elif namespace == "trillium":
        platform_branch, release_type = "trillium", "TRILLIUM"
    else:
        platform_branch, release_type = "snapshot", "SNAPSHOT"

    lifecycle: dict = {"category": category}
    if namespace in ("snapshot", "snapshot2", "sprint"):
        lifecycle["protected"] = True

    # infra: opensearch aws everywhere; pg/kafka/s3 aws on folio-eperf; sprint override.
    infra: dict = {}
    if cluster == "folio-eperf" or namespace == "sprint":
        infra = {"pgType": "aws", "kafkaType": "aws", "s3Type": "aws"}
    infra["opensearchType"] = "aws"

    config_extensions = ["consortia-single-ui"]
    if namespace == "sunflower" or namespace == "sprint":
        config_extensions = ["sunflower", "consortia-single-ui"]

    doc: dict = {
        "schemaVersion": 1,
        "name": namespace,
        "platform": "EUREKA",
        "configType": config_type,
        "platformBranch": platform_branch,
        "releaseType": release_type,
        "lifecycle": lifecycle,
        "members": resolve_members(namespace),
        "infra": infra,
        "configExtensions": config_extensions,
    }

    if cluster == "folio-etesting" and namespace == "sprint":
        # Dataset namespace: tenants + consortia come from the bugfest profile (D.5).
        doc["dataset"] = {"snapshot": BUGFEST_SNAPSHOT_NAME, "profile": "bugfest"}
    else:
        doc["consortia"] = CONSORTIA_BLOCK
        doc["tenants"] = list(QUAD_TENANTS)
        doc["defaultTenant"] = "diku"

    doc["operations"] = dict(OPERATIONS)
    return doc


def iter_namespaces():
    for cluster, (namespaces, _ct, _cat) in CLUSTERS.items():
        for namespace in namespaces:
            yield cluster, namespace, build_namespace(cluster, namespace)


def _render(cluster: str, namespace: str, doc: dict) -> str:
    header = (
        f"# clusters/{cluster}/namespaces/{namespace}/namespace.yaml"
        " — CreateNamespaceParameters surface (§2.6)\n"
    )
    return header + yaml.safe_dump(
        doc, sort_keys=False, default_flow_style=False, width=4096
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="generate kitfox-config namespaces")
    parser.add_argument("--check", action="store_true",
                        help="exit 1 if any file differs from generated content")
    args = parser.parse_args()

    stale: list[str] = []
    written = 0
    for cluster, namespace, doc in iter_namespaces():
        out = REPO_ROOT / "clusters" / cluster / "namespaces" / namespace / "namespace.yaml"
        content = _render(cluster, namespace, doc)
        if args.check:
            if not out.exists() or out.read_text() != content:
                stale.append(str(out.relative_to(REPO_ROOT)))
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content)
        written += 1

    if args.check:
        if stale:
            print("STALE:\n  " + "\n  ".join(stale))
            return 1
        print("OK: all 69 namespace.yaml up to date")
        return 0
    print(f"OK: wrote {written} namespace.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
