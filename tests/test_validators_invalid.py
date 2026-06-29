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
