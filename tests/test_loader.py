from resolver.loader import load_tree


def test_load_tree_discovers_hierarchy(config_root):
    tree = load_tree(config_root)
    assert "folio-etesting" in tree.list_clusters()
    assert set(tree.list_namespaces("folio-etesting")) >= {"sprint", "bugfest"}
    # tenant membership comes from namespace.tenants, not readdir
    ns = tree.namespace("folio-etesting", "sprint")
    assert ns["tenants"] == ["diku", "university", "college"]
    # catalog identity keyed by id
    assert tree.catalog["university"]["type"] == "consortia-member"
    # reference (non-merge) files loaded
    assert "readWriteModules" in tree.module_roles
    assert "rules" in tree.tenant_ruleset
    # type-defaults keyed by type
    assert "app-consortia" in tree.type_defaults["standard"]["applications"]["exclude"]
