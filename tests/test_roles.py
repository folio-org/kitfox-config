from resolver.roles import mark_read_write_modules


def test_marks_modules_when_rwsplit_true():
    modules, marked = mark_read_write_modules(
        base_modules={"mod-users": {"replicaCount": 1}},
        read_write_modules=["mod-users", "mod-audit"],
        rw_split=True,
    )
    assert marked == ["mod-audit", "mod-users"]
    assert modules["mod-users"]["integrations"]["db"]["hostReader"] is True
    assert modules["mod-audit"]["integrations"]["db"]["hostReader"] is True
    # existing per-module config is preserved
    assert modules["mod-users"]["replicaCount"] == 1


def test_no_marking_when_rwsplit_false():
    modules, marked = mark_read_write_modules(
        base_modules={"mod-users": {}},
        read_write_modules=["mod-users"],
        rw_split=False,
    )
    assert marked == []
    assert "integrations" not in modules["mod-users"]


def test_marking_does_not_set_coordinate():
    modules, _ = mark_read_write_modules(
        base_modules={}, read_write_modules=["mod-audit"], rw_split=True,
    )
    db = modules["mod-audit"]["integrations"]["db"]
    assert db == {"hostReader": True}   # flag only; no host/port/url coordinate
