"""Each test copies the frozen reference tree, mutates exactly one thing, and
asserts exactly one cross-level rule trips with the expected message. Mirrors the
copytree+mutate pattern in tests/test_resolve_sprint.py."""

import shutil

import yaml

from validators.core import Violation


def test_violation_str_names_rule_file_entity():
    v = Violation("D.3", "clusters/folio-etesting/namespaces/sprint/namespace.yaml",
                  "ghost", "tenant id 'ghost' is not in platform/tenant-catalog.yaml")
    s = str(v)
    assert "D.3" in s
    assert "namespace.yaml" in s
    assert "ghost" in s


from validators.d5_dataset_tenants import check_dataset_xor_tenants


def test_d5_both_dataset_and_tenants_fails():
    ns_doc = {"name": "x", "dataset": {"profile": "bugfest"}, "tenants": ["fs09000000"]}
    vs = check_dataset_xor_tenants("c", "x", ns_doc)
    assert len(vs) == 1
    assert vs[0].rule == "D.5"
    assert "both" in vs[0].message
    assert "bugfest" in vs[0].message


def test_d5_only_dataset_ok():
    ns_doc = {"name": "x", "dataset": {"profile": "bugfest"}}
    assert check_dataset_xor_tenants("c", "x", ns_doc) == []


def test_d5_only_tenants_ok():
    ns_doc = {"name": "x", "tenants": ["diku"]}
    assert check_dataset_xor_tenants("c", "x", ns_doc) == []


def test_d5_neither_fails():
    ns_doc = {"name": "x"}
    vs = check_dataset_xor_tenants("c", "x", ns_doc)
    assert len(vs) == 1
    assert "neither" in vs[0].message


from resolver.tenants import Membership

from validators.d3_catalog import check_tenants_in_catalog


class _FakeTree:
    def __init__(self, catalog):
        self.catalog = catalog


def test_d3_unknown_tenant_id_fails():
    tree = _FakeTree({"diku": {"type": "standard"}})
    membership = Membership(tenant_ids=["diku", "ghost"], default_tenant="diku",
                            consortia=[], dataset=None)
    vs = check_tenants_in_catalog(tree, "c", "ns", membership)
    assert len(vs) == 1
    assert vs[0].rule == "D.3"
    assert vs[0].entity == "ghost"
    assert "tenant-catalog.yaml" in vs[0].message


def test_d3_consortia_member_checked_against_catalog():
    tree = _FakeTree({"consortium": {"type": "consortia-central"}})
    membership = Membership(tenant_ids=["consortium"], default_tenant="consortium",
                            consortia=[{"central": "consortium", "members": ["missing"]}],
                            dataset=None)
    vs = check_tenants_in_catalog(tree, "c", "ns", membership)
    assert [v.entity for v in vs] == ["missing"]


def test_d3_all_known_ok():
    tree = _FakeTree({"diku": {"type": "standard"}})
    membership = Membership(tenant_ids=["diku"], default_tenant="diku",
                            consortia=[], dataset=None)
    assert check_tenants_in_catalog(tree, "c", "ns", membership) == []


from validators.d2_default_tenant import check_default_tenant


def test_d2_default_not_in_tenants_fails():
    membership = Membership(tenant_ids=["diku", "university"], default_tenant="zzz",
                            consortia=[], dataset=None)
    vs = check_default_tenant("c", "ns", membership)
    assert len(vs) == 1
    assert vs[0].rule == "D.2"
    assert "zzz" in vs[0].message
    assert "diku" in vs[0].message  # message lists the valid set


def test_d2_default_in_tenants_ok():
    membership = Membership(tenant_ids=["diku"], default_tenant="diku",
                            consortia=[], dataset=None)
    assert check_default_tenant("c", "ns", membership) == []


def test_d2_no_default_tenant_skips():
    membership = Membership(tenant_ids=["diku"], default_tenant=None,
                            consortia=[], dataset=None)
    assert check_default_tenant("c", "ns", membership) == []


from validators.d4_consortia import check_consortia_block


def _tree_with_types(types):
    return _FakeTree({tid: {"type": t} for tid, t in types.items()})


def test_d4_central_tenant_without_block_fails():
    tree = _tree_with_types({"cs00000int": "consortia-central"})
    membership = Membership(tenant_ids=["cs00000int"], default_tenant="cs00000int",
                            consortia=[], dataset=None)
    vs = check_consortia_block(tree, "c", "ns", membership)
    assert len(vs) == 1
    assert vs[0].rule == "D.4"
    assert "cs00000int" in vs[0].message
    assert "no consortia" in vs[0].message


def test_d4_member_not_in_tenant_set_fails():
    tree = _tree_with_types({"cs00000int": "consortia-central",
                             "m1": "consortia-member"})
    membership = Membership(tenant_ids=["cs00000int"], default_tenant="cs00000int",
                            consortia=[{"central": "cs00000int", "members": ["m1"]}],
                            dataset=None)
    vs = check_consortia_block(tree, "c", "ns", membership)
    assert len(vs) == 1
    assert "m1" in vs[0].message
    assert "not in the namespace" in vs[0].message


def test_d4_member_wrong_type_fails():
    tree = _tree_with_types({"cs00000int": "consortia-central",
                             "m1": "standard"})
    membership = Membership(tenant_ids=["cs00000int", "m1"], default_tenant="cs00000int",
                            consortia=[{"central": "cs00000int", "members": ["m1"]}],
                            dataset=None)
    vs = check_consortia_block(tree, "c", "ns", membership)
    assert len(vs) == 1
    assert "consortia-member" in vs[0].message


def test_d4_valid_central_and_members_ok():
    tree = _tree_with_types({"cs00000int": "consortia-central",
                             "m1": "consortia-member"})
    membership = Membership(tenant_ids=["cs00000int", "m1"], default_tenant="cs00000int",
                            consortia=[{"central": "cs00000int", "members": ["m1"]}],
                            dataset=None)
    assert check_consortia_block(tree, "c", "ns", membership) == []


def test_d4_no_central_tenant_skips():
    # sprint shape: members deployed, central named only in the block, not a tenant
    tree = _tree_with_types({"university": "consortia-member",
                             "consortium": "consortia-central"})
    membership = Membership(tenant_ids=["university"], default_tenant="university",
                            consortia=[{"central": "consortium", "members": ["university"]}],
                            dataset=None)
    assert check_consortia_block(tree, "c", "ns", membership) == []


from dataclasses import dataclass

from validators.d1_tenant_type import check_tenant_type_ruleset

RULESET = {
    "default": {"allowedTypes": ["standard", "consortia-member", "consortia-central"],
                "requireSecure": False},
    "rules": [
        {"applications": ["app-consortia", "app-dcb"],
         "allowedTypes": ["consortia-member", "consortia-central"], "requireSecure": False},
        {"applications": ["app-requests-mediated-ui"],
         "allowedTypes": ["consortia-central"], "requireSecure": True},
    ],
}


@dataclass
class _T:
    tenantId: str
    type: str
    secure: bool
    deployedApps: list


@dataclass
class _RN:
    namespaceName: str
    tenants: list


def test_d1_standard_deploying_consortia_app_fails():
    rn = _RN("ns", [_T("diku", "standard", False, ["app-consortia", "app-fqm"])])
    vs = check_tenant_type_ruleset(rn, RULESET, "c", "ns")
    assert len(vs) == 1
    assert vs[0].rule == "D.1"
    assert "diku" in vs[0].message
    assert "app-consortia" in vs[0].message
    assert "consortia-member" in vs[0].message  # message lists allowed types


def test_d1_member_with_consortia_app_ok():
    rn = _RN("ns", [_T("university", "consortia-member", True,
                       ["app-consortia", "app-fqm"])])
    assert check_tenant_type_ruleset(rn, RULESET, "c", "ns") == []


def test_d1_require_secure_violation():
    rn = _RN("ns", [_T("consortium", "consortia-central", False,
                       ["app-requests-mediated-ui"])])
    vs = check_tenant_type_ruleset(rn, RULESET, "c", "ns")
    assert len(vs) == 1
    assert "secure" in vs[0].message.lower()


def test_d1_default_rule_allows_unlisted_app():
    rn = _RN("ns", [_T("diku", "standard", False, ["app-acquisitions"])])
    assert check_tenant_type_ruleset(rn, RULESET, "c", "ns") == []


def test_d1_no_deployed_apps_skips():
    rn = _RN("ns", [_T("diku", "standard", False, None)])
    assert check_tenant_type_ruleset(rn, RULESET, "c", "ns") == []
