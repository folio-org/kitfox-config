from resolver.loader import load_tree


def test_load_tree_discovers_hierarchy(config_root):
    tree = load_tree(config_root)
    assert "folio-etesting" in tree.list_clusters()
    assert set(tree.list_namespaces("folio-etesting")) >= {"sprint", "bugfest"}
    # sprint is now dataset-based; no explicit tenants list, dataset profile instead
    ns = tree.namespace("folio-etesting", "sprint")
    assert ns.get("tenants") is None
    assert ns["dataset"]["profile"] == "bugfest"
    # catalog identity keyed by id
    assert tree.catalog["university"]["type"] == "consortia-member"
    # reference (non-merge) files loaded
    assert "readWriteModules" in tree.module_roles
    assert "rules" in tree.tenant_ruleset
    # type-defaults keyed by type
    assert "app-consortia" in tree.type_defaults["standard"]["applications"]["exclude"]
