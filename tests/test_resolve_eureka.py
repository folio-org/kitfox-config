"""E2E: folio-edev/eureka — per-tenant ui (catalog identity) + namespace uiDefaults.

diku & consortium carry catalog ui (consortium's has consortiaSingleUx:true);
university & college have no ui (not UI tenants); uiDefaults (build-wide Stripes
tunables) is present namespace-wide from the development deployment profile."""

import pytest

from resolver import resolve_namespace


@pytest.fixture
def eureka(config_root):
    return resolve_namespace(config_root, "folio-edev", "eureka", app_index=None)


def _tenant(resolved, tid):
    return next(t for t in resolved.tenants if t.tenantId == tid)


def test_ui_tenants_have_catalog_ui(eureka):
    assert _tenant(eureka, "diku").ui == {}


def test_central_has_consortia_single_ux(eureka):
    assert _tenant(eureka, "consortium").ui == {"consortiaSingleUx": True}


def test_member_tenants_have_no_ui(eureka):
    assert _tenant(eureka, "university").ui is None
    assert _tenant(eureka, "college").ui is None


def test_namespace_ui_defaults_present(eureka):
    assert eureka.uiDefaults["idleSessionWarningSeconds"] == 60
    assert eureka.uiDefaults["maxUnpagedResourceCount"] == 2000
    assert eureka.uiDefaults["rtr"] == {"idleSessionTTL": "1h", "idleModalTTL": "30s"}


def test_namespace_has_no_top_level_ui(eureka):
    assert not hasattr(eureka, "ui")
