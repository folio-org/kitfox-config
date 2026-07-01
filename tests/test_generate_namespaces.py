import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "generate_namespaces",
    Path(__file__).resolve().parent.parent / "scripts" / "generate_namespaces.py",
)
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


def test_namespace_count_is_69():
    docs = list(gen.iter_namespaces())
    assert len(docs) == 69
    by_cluster = {}
    for cluster, name, doc in docs:
        by_cluster.setdefault(cluster, set()).add(name)
    assert len(by_cluster["folio-etesting"]) == 13
    assert len(by_cluster["folio-edev"]) == 25
    assert len(by_cluster["folio-eperf"]) == 27
    assert len(by_cluster["folio-tmp"]) == 4


def test_quad_namespace_thunderjet():
    doc = gen.build_namespace("folio-edev", "thunderjet")
    assert doc["platform"] == "EUREKA"
    assert doc["configType"] == "development"
    assert doc["lifecycle"] == {"category": "dev"}
    assert doc["members"] == ["thunderjet"]
    assert doc["tenants"] == ["diku", "consortium", "university", "college"]
    assert doc["defaultTenant"] == "diku"
    assert doc["consortia"] == [
        {"central": "consortium", "name": "Consortium", "members": ["university", "college"]}
    ]
    assert doc["infra"] == {"opensearchType": "aws"}
    assert "dataset" not in doc


def test_eperf_quad_gets_aws_infra():
    doc = gen.build_namespace("folio-eperf", "spitfire")
    assert doc["configType"] == "performance"
    assert doc["lifecycle"]["category"] == "dev"
    assert doc["infra"] == {
        "pgType": "aws", "kafkaType": "aws", "s3Type": "aws", "opensearchType": "aws",
    }
    assert doc["members"] == ["spitfire"]


def test_release_namespace_sunflower():
    doc = gen.build_namespace("folio-eperf", "sunflower")
    assert doc["configType"] == "release"
    assert doc["lifecycle"] == {"category": "release"}
    assert doc["platformBranch"] == "sunflower"
    assert doc["releaseType"] == "SUNFLOWER"
    assert "sunflower" in doc["configExtensions"]
    assert doc["members"] == []


def test_release_namespace_trillium():
    doc = gen.build_namespace("folio-eperf", "trillium")
    assert doc["releaseType"] == "TRILLIUM"
    assert doc["platformBranch"] == "trillium"
    assert doc["configExtensions"] == ["consortia-single-ui"]


def test_sprint_is_dataset_not_tenants():
    doc = gen.build_namespace("folio-etesting", "sprint")
    assert "tenants" not in doc
    assert "consortia" not in doc
    assert doc["dataset"] == {
        "snapshot": "folio-bugfest-trillium-16-06-2026-ga", "profile": "bugfest",
    }
    assert doc["lifecycle"] == {"category": "testing", "protected": True}
    assert doc["infra"] == {
        "pgType": "aws", "kafkaType": "aws", "s3Type": "aws", "opensearchType": "aws",
    }
    # sprint is a shared namespace → SHARED member team
    assert doc["members"][0] == "thunderjet" and "erm" in doc["members"]


def test_shared_members_snapshot():
    doc = gen.build_namespace("folio-etesting", "snapshot")
    assert doc["lifecycle"]["protected"] is True
    assert len(doc["members"]) == 15
    assert doc["tenants"] == ["diku", "consortium", "university", "college"]


def test_empty_members_default():
    doc = gen.build_namespace("folio-tmp", "test")
    assert doc["configType"] == "development"
    assert doc["lifecycle"] == {"category": "tmp"}
    assert doc["members"] == []
