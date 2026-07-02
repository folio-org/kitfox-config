"""E2E: folio-edev/eureka — per-tenant ui folds in the build-wide uiDefaults.

A UI-having tenant's resolved `ui` = the deployment-profile `uiDefaults` (build-wide
Stripes tunables) merged with its catalog `ui` (consortium adds consortiaSingleUx).
Members (university/college) have no bundle → ui is None. `uiDefaults` is NOT emitted
as a standalone namespace field — it is folded into each UI tenant."""

import pytest

from resolver import resolve_namespace

UI_DEFAULTS = {
    "idleSessionWarningSeconds": 60,
    "maxUnpagedResourceCount": 2000,
    "rtr": {"idleSessionTTL": "1h", "idleModalTTL": "30s"},
}


@pytest.fixture
def eureka(config_root):
    return resolve_namespace(config_root, "folio-edev", "eureka", app_index=None)


def _tenant(resolved, tid):
    return next(t for t in resolved.tenants if t.tenantId == tid)


def test_ui_tenant_folds_in_ui_defaults(eureka):
    # diku has an (empty) catalog ui → resolves to just the build-wide defaults.
    assert _tenant(eureka, "diku").ui == UI_DEFAULTS


def test_central_has_consortia_single_ux_plus_defaults(eureka):
    assert _tenant(eureka, "consortium").ui == {**UI_DEFAULTS, "consortiaSingleUx": True}


def test_member_tenants_have_no_ui(eureka):
    assert _tenant(eureka, "university").ui is None
    assert _tenant(eureka, "college").ui is None


def test_namespace_has_no_standalone_ui_or_ui_defaults(eureka):
    assert not hasattr(eureka, "ui")
    assert not hasattr(eureka, "uiDefaults")