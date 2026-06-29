import pytest

from resolver.apps import AppIndex
from resolver.loader import load_tree
from resolver.tenants import resolve_tenant, tenant_membership


def _idx(platform_descriptor, app_descriptors_dir):
    return AppIndex.load(platform_descriptor, app_descriptors_dir)


def test_identity_from_catalog(config_root):
    tree = load_tree(config_root)
    t = resolve_tenant(tree, "folio-etesting", "sprint", "diku",
                       namespace_exclude=[], app_index=None)
    assert t["type"] == "standard"
    assert t["name"] == "Datalogisk Institut"
    assert t["adminUser"]["username"] == "diku_admin"


def test_type_default_exclude_applied(config_root):
    tree = load_tree(config_root)
    t = resolve_tenant(tree, "folio-etesting", "sprint", "diku",
                       namespace_exclude=[], app_index=None)
    assert "app-consortia" in t["applications"]["exclude"]
    assert "app-requests-mediated-ui" in t["applications"]["exclude"]


def test_override_unions_exclude_and_sets_secure(config_root):
    tree = load_tree(config_root)
    t = resolve_tenant(tree, "folio-etesting", "sprint", "university",
                       namespace_exclude=[], app_index=None)
    assert t["secure"] is True
    assert "app-fqm" in t["applications"]["exclude"]
    assert "app-consortia-manager" in t["applications"]["exclude"]
    assert "app-linked-data" in t["applications"]["exclude"]


def test_install_defaults_merge_with_override(config_root):
    tree = load_tree(config_root)
    t = resolve_tenant(tree, "folio-etesting", "sprint", "university",
                       namespace_exclude=[], app_index=None)
    assert t["install"]["loadSample"] is False
    assert t["install"]["loadReference"] is True
    assert t["install"]["async"] is True


def test_code_present_for_member(config_root):
    tree = load_tree(config_root)
    t = resolve_tenant(tree, "folio-etesting", "sprint", "university",
                       namespace_exclude=[], app_index=None)
    assert t["code"] == "um"


def test_unknown_id_raises(config_root):
    tree = load_tree(config_root)
    with pytest.raises(KeyError):
        resolve_tenant(tree, "folio-etesting", "sprint", "ghost",
                       namespace_exclude=[], app_index=None)


def test_membership_explicit(config_root):
    tree = load_tree(config_root)
    m = tenant_membership(tree, "folio-etesting", "sprint")
    assert m.tenant_ids == ["diku", "university", "college"]
    assert m.default_tenant == "diku"
    assert m.dataset is None


def test_membership_from_dataset(config_root):
    tree = load_tree(config_root)
    m = tenant_membership(tree, "folio-etesting", "bugfest")
    assert m.tenant_ids == ["fs09000000", "fs09000002", "fs09000003",
                            "cs00000int", "cs00000int_0001"]
    assert m.default_tenant == "fs09000000"
    assert m.dataset["dbName"] == "folio"
    assert m.dataset["infra"]["pgInstanceType"] == "db.r6g.xlarge"
    assert m.dataset["moduleReplicas"]["mod-search"] == 4


def test_gap5_keeps_worldcat_drops_kb_for_sprint(config_root, platform_descriptor,
                                                 app_descriptors_dir):
    tree = load_tree(config_root)
    idx = _idx(platform_descriptor, app_descriptors_dir)
    t = resolve_tenant(tree, "folio-etesting", "sprint", "diku",
                       namespace_exclude=[], app_index=idx)
    # mod-copycat is in app-platform-complete (required) -> worldcat kept.
    assert "worldcat" in t["config"]
    # mod-kb-ebsco-java lives only in app-eholdings (not in the available set)
    # -> KB module never deployed for sprint -> config.kb dropped.
    assert "kb" not in t["config"]


def test_gap5_drops_config_when_module_absent(config_root, platform_descriptor,
                                              app_descriptors_dir):
    tree = load_tree(config_root)
    idx = _idx(platform_descriptor, app_descriptors_dir)
    # Exclude every available app that carries either module -> kb/worldcat drop.
    kb_apps = [a for a in idx.available if "mod-kb-ebsco-java" in idx.modules_of([a])]
    wc_apps = [a for a in idx.available if "mod-copycat" in idx.modules_of([a])]
    t = resolve_tenant(tree, "folio-etesting", "sprint", "diku",
                       namespace_exclude=sorted(set(kb_apps + wc_apps)), app_index=idx)
    assert "kb" not in t["config"]
    assert "worldcat" not in t["config"]
