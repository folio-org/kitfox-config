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
