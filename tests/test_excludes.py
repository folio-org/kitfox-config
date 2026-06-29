from resolver.excludes import union_excludes


def test_union_accumulates_across_layers():
    type_default = ["app-consortia", "app-dcb"]
    namespace = ["app-reading-room"]
    tenant = ["app-fqm"]
    assert union_excludes(type_default, namespace, tenant) == sorted(
        {"app-consortia", "app-dcb", "app-reading-room", "app-fqm"}
    )


def test_union_is_deduplicated_and_sorted():
    assert union_excludes(["b", "a"], ["a"], ["b"]) == ["a", "b"]


def test_tenant_omission_cannot_unexclude_type_default():
    # tenant override does not list app-consortia; the union still excludes it.
    resolved = union_excludes(["app-consortia"], [], [])
    assert "app-consortia" in resolved


def test_none_layers_treated_as_empty():
    assert union_excludes(None, ["a"], None) == ["a"]
