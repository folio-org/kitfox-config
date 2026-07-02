"""E2E: folio-etesting/bugfest (dataset path, §2.4b).
Asserts: tenant set + defaultTenant from the profile; no explicit tenants list in
the namespace; pgInstanceType/moduleReplicas surfaced; rwSplit marking only when true."""

import pytest

from resolver import resolve_namespace
from resolver.apps import AppIndex


@pytest.fixture
def bugfest(config_root, platform_descriptor, app_descriptors_dir):
    idx = AppIndex.load(platform_descriptor, app_descriptors_dir)
    return resolve_namespace(config_root, "folio-etesting", "bugfest", idx)


def test_tenants_and_default_from_profile(bugfest):
    assert [t.tenantId for t in bugfest.tenants] == [
        "fs09000000", "fs09000002", "fs09000003", "cs00000int", "cs00000int_0001"
    ]
    assert bugfest.defaultTenant == "fs09000000"
    assert bugfest.dataset["profile"] == "bugfest"
    assert bugfest.dataset["dbName"] == "folio"


def test_restore_sizing_surfaced(bugfest):
    assert bugfest.infra["pgInstanceType"] == "db.r6g.xlarge"
    assert bugfest.modules["mod-inventory-storage"]["replicaCount"] == 4
    assert bugfest.modules["mod-search"]["replicaCount"] == 4


def test_member_type_default_exclusions_applied(bugfest):
    member = next(t for t in bugfest.tenants if t.tenantId == "cs00000int_0001")
    assert "app-consortia-manager" in member.applications["exclude"]
    central = next(t for t in bugfest.tenants if t.tenantId == "cs00000int")
    assert central.applications["exclude"] == []   # consortia-central excludes nothing


def test_rwsplit_marks_when_enabled(config_root, platform_descriptor,
                                    app_descriptors_dir, tmp_path):
    """Flip features.rwSplit on a copied bugfest tree → readWriteModules marked."""
    import shutil
    import yaml
    dst = tmp_path / "cfg"
    shutil.copytree(config_root / "platform", dst / "platform")
    shutil.copytree(config_root / "clusters", dst / "clusters")
    ns = dst / "clusters/folio-etesting/namespaces/bugfest/namespace.yaml"
    doc = yaml.safe_load(ns.read_text())
    doc["features"]["rwSplit"] = True
    ns.write_text(yaml.safe_dump(doc))
    idx = AppIndex.load(platform_descriptor, app_descriptors_dir)
    resolved = resolve_namespace(dst, "folio-etesting", "bugfest", idx)
    assert "mod-users" in resolved.readWriteModules
    assert resolved.modules["mod-users"]["integrations"]["db"]["hostReader"] is True
