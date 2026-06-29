from resolver.merge import deep_merge


def test_scalars_and_maps_deep_merge_higher_wins():
    base = {"infra": {"pgType": "built-in", "pgVersion": "16.8"}}
    over = {"infra": {"pgType": "aws"}}
    assert deep_merge(base, over) == {"infra": {"pgType": "aws", "pgVersion": "16.8"}}


def test_named_lists_replace_wholesale_no_concat():
    base = {"members": ["a", "b", "c"]}
    over = {"members": ["x"]}
    assert deep_merge(base, over) == {"members": ["x"]}


def test_merge_does_not_mutate_inputs():
    base = {"a": {"b": 1}}
    over = {"a": {"c": 2}}
    deep_merge(base, over)
    assert base == {"a": {"b": 1}}
    assert over == {"a": {"c": 2}}


def test_new_keys_from_higher_layer_are_added():
    assert deep_merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}
