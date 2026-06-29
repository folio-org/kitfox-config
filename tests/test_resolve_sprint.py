"""E2E: folio-etesting/sprint (§3 resolution end-to-end).
Asserts: tenant set; university deployed apps exclude app-fqm + consortia-member
type-default exclusions; secure-tenant overlay applied iff a tenant is secure;
defaultTenant = diku."""

import pytest

from resolver import resolve_namespace
from resolver.apps import AppIndex


@pytest.fixture
def sprint(config_root, platform_descriptor, app_descriptors_dir):
    idx = AppIndex.load(platform_descriptor, app_descriptors_dir)
    return resolve_namespace(config_root, "folio-etesting", "sprint", idx)


def _tenant(resolved, tid):
    return next(t for t in resolved.tenants if t.tenantId == tid)


def test_tenant_set_and_default(sprint):
    assert [t.tenantId for t in sprint.tenants] == ["diku", "university", "college"]
    assert sprint.defaultTenant == "diku"


def test_university_excludes_fqm_and_type_defaults(sprint):
    uni = _tenant(sprint, "university")
    excl = uni.applications["exclude"]
    assert "app-fqm" in excl                       # tenant override
    assert "app-consortia-manager" in excl         # consortia-member type default
    assert "app-linked-data" in excl               # consortia-member type default
    assert "app-requests-mediated-ui" in excl      # consortia-member type default
    # deployed set excludes them
    assert "app-fqm" not in uni.deployedApps
    assert "app-consortia-manager" not in uni.deployedApps


def test_secure_tenant_overlay_applied_when_secure_present(sprint):
    # university is secure -> SECURE_TENANT_ID lands, substituted to 'university'
    env = sprint.modules["mod-patron"]["extraEnvVars"]
    val = next(e["value"] for e in env if e["name"] == "SECURE_TENANT_ID")
    assert val == "university"


def test_secure_tenant_overlay_absent_when_no_secure(config_root, platform_descriptor,
                                                     app_descriptors_dir, tmp_path):
    """Build a copy of the tree with university.secure removed → overlay must NOT apply."""
    import shutil
    import yaml
    dst = tmp_path / "cfg"
    shutil.copytree(config_root / "platform", dst / "platform")
    shutil.copytree(config_root / "clusters", dst / "clusters")
    uni = dst / "clusters/folio-etesting/namespaces/sprint/tenants/university.yaml"
    doc = yaml.safe_load(uni.read_text())
    doc["secure"] = False
    uni.write_text(yaml.safe_dump(doc))
    idx = AppIndex.load(platform_descriptor, app_descriptors_dir)
    resolved = resolve_namespace(dst, "folio-etesting", "sprint", idx)
    assert "mod-patron" not in resolved.modules


def test_rwsplit_false_marks_nothing(sprint):
    assert sprint.readWriteModules == []


def test_excluded_app_ui_modules_surfaced(sprint):
    uni = _tenant(sprint, "university")
    # cascade input present for each excluded app (value may be [] if no descriptor)
    assert set(uni.excludedAppsUiModules.keys()) == set(uni.applications["exclude"])
