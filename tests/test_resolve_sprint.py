"""E2E: folio-etesting/sprint (§3 resolution end-to-end).
sprint uses the bugfest dataset profile; tenants are derived from that dataset
(fs09000000, fs09000002, fs09000003, cs00000int, cs00000int_0001).
Asserts: tenant set; consortia-member type-default exclusions on the dataset member
tenant; no SECURE_TENANT_ID injection (no secure tenant in dataset); defaultTenant."""

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
    # sprint resolves tenants from the bugfest dataset profile, not explicit list
    assert [t.tenantId for t in sprint.tenants] == [
        "fs09000000", "fs09000002", "fs09000003", "cs00000int", "cs00000int_0001"
    ]
    assert sprint.defaultTenant == "fs09000000"


def test_member_tenant_type_defaults(sprint):
    """cs00000int_0001 is the consortia-member from the bugfest dataset; verify
    that consortia-member type-default exclusions are applied."""
    member = _tenant(sprint, "cs00000int_0001")
    excl = member.applications["exclude"]
    assert "app-consortia-manager" in excl         # consortia-member type default
    assert "app-linked-data" in excl               # consortia-member type default
    assert "app-requests-mediated-ui" in excl      # consortia-member type default
    # deployed set excludes them
    assert "app-consortia-manager" not in member.deployedApps


def test_no_secure_tenant_in_dataset_sprint(sprint):
    """Sprint tenants come from the bugfest dataset; none are marked secure,
    so SECURE_TENANT_ID must not be injected into any module's extraEnvVars."""
    for mod_cfg in sprint.modules.values():
        env = mod_cfg.get("extraEnvVars", [])
        assert all(e.get("name") != "SECURE_TENANT_ID" for e in env)


def test_rwsplit_false_marks_nothing(sprint):
    assert sprint.readWriteModules == []


def test_excluded_app_ui_modules_surfaced(sprint):
    # cs00000int_0001 is the dataset consortia-member with type-default exclusions
    member = _tenant(sprint, "cs00000int_0001")
    # cascade input present for each excluded app (value may be [] if no descriptor)
    assert set(member.excludedAppsUiModules.keys()) == set(member.applications["exclude"])
