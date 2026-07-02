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


def test_override_unions_exclude_and_sets_secure(config_root, tmp_path):
    """A per-namespace tenant override with secure=True and extra excludes is merged
    with catalog defaults and consortia-member type defaults.  We inject a synthetic
    university.yaml into folio-edev/thunderjet (which carries university as an
    explicit tenant) to verify the overlay mechanics without touching the live tree."""
    import shutil
    import yaml as _yaml
    dst = tmp_path / "cfg"
    shutil.copytree(config_root / "platform", dst / "platform")
    shutil.copytree(config_root / "clusters", dst / "clusters")
    override_dir = dst / "clusters/folio-edev/namespaces/thunderjet/tenants"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "university.yaml").write_text(_yaml.safe_dump({
        "secure": True,
        "applications": {"exclude": ["app-fqm"]},
    }))
    tree = load_tree(dst)
    t = resolve_tenant(tree, "folio-edev", "thunderjet", "university",
                       namespace_exclude=[], app_index=None)
    assert t["secure"] is True
    assert "app-fqm" in t["applications"]["exclude"]           # overlay
    assert "app-consortia-manager" in t["applications"]["exclude"]  # type default
    assert "app-linked-data" in t["applications"]["exclude"]        # type default


def test_install_defaults_merge_with_override(config_root, tmp_path):
    """install overrides in a per-namespace tenant file deep-merge with the
    deployment-profile install defaults; injected into thunderjet/university."""
    import shutil
    import yaml as _yaml
    dst = tmp_path / "cfg"
    shutil.copytree(config_root / "platform", dst / "platform")
    shutil.copytree(config_root / "clusters", dst / "clusters")
    override_dir = dst / "clusters/folio-edev/namespaces/thunderjet/tenants"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "university.yaml").write_text(_yaml.safe_dump({
        "install": {"loadSample": False},
    }))
    tree = load_tree(dst)
    t = resolve_tenant(tree, "folio-edev", "thunderjet", "university",
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
    # thunderjet still uses an explicit tenants list; verify membership resolution
    tree = load_tree(config_root)
    m = tenant_membership(tree, "folio-edev", "thunderjet")
    assert m.tenant_ids == ["diku", "consortium", "university", "college"]
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


def test_catalog_ui_carried_for_ui_tenant(config_root):
    tree = load_tree(config_root)
    t = resolve_tenant(tree, "folio-edev", "eureka", "diku",
                       namespace_exclude=[], app_index=None)
    assert t["ui"] == {}


def test_catalog_ui_consortia_single_ux_for_central(config_root):
    tree = load_tree(config_root)
    t = resolve_tenant(tree, "folio-edev", "eureka", "consortium",
                       namespace_exclude=[], app_index=None)
    assert t["ui"] == {"consortiaSingleUx": True}


def test_no_ui_for_member_tenant(config_root):
    tree = load_tree(config_root)
    t = resolve_tenant(tree, "folio-edev", "eureka", "university",
                       namespace_exclude=[], app_index=None)
    assert "ui" not in t


def test_override_ui_deep_merges_with_catalog(config_root, tmp_path):
    """A per-namespace tenant override ui deep-merges onto the catalog ui rather
    than replacing it — injected into folio-edev/eureka/diku."""
    import shutil
    import yaml as _yaml
    dst = tmp_path / "cfg"
    shutil.copytree(config_root / "platform", dst / "platform")
    shutil.copytree(config_root / "clusters", dst / "clusters")
    override_dir = dst / "clusters/folio-edev/namespaces/eureka/tenants"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "diku.yaml").write_text(_yaml.safe_dump({
        "tenantId": "diku",
        "ui": {"enabled": True, "add": ["@folio/dev-app"]},
    }))
    tree = load_tree(dst)
    t = resolve_tenant(tree, "folio-edev", "eureka", "diku",
                       namespace_exclude=[], app_index=None)
    assert t["ui"] == {"enabled": True, "add": ["@folio/dev-app"]}
