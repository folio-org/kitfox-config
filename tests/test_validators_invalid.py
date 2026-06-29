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
