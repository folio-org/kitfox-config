"""The frozen Epic C reference tree must PASS all five validators + gap#8
(Story C.4 end-to-end green gate)."""

from validators import run_tree


def test_reference_tree_has_no_violations(config_root, app_index):
    results = run_tree(config_root, app_index)
    # both reference namespaces are discovered
    assert ("folio-etesting", "sprint") in results
    assert ("folio-etesting", "bugfest") in results
    all_violations = [v for vs in results.values() for v in vs]
    assert all_violations == [], "\n".join(str(v) for v in all_violations)


def test_run_tree_returns_entry_per_namespace(config_root, app_index):
    results = run_tree(config_root, app_index)
    assert all(isinstance(vs, list) for vs in results.values())
