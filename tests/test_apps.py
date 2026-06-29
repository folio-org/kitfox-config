from resolver.apps import AppIndex


def test_available_names_from_descriptor(platform_descriptor, app_descriptors_dir):
    idx = AppIndex.load(platform_descriptor, app_descriptors_dir)
    # required + optional names, versions ignored
    assert "app-platform-complete" in idx.available
    assert "app-fqm" in idx.available
    assert "app-consortia" in idx.available


def test_deployed_is_available_minus_excludes(platform_descriptor, app_descriptors_dir):
    idx = AppIndex.load(platform_descriptor, app_descriptors_dir)
    deployed = idx.deployed(exclude=["app-fqm", "app-consortia"])
    assert "app-fqm" not in deployed
    assert "app-consortia" not in deployed
    assert "app-platform-complete" in deployed
    assert deployed == sorted(deployed)  # deterministic order


def test_ui_modules_for_excluded_apps(platform_descriptor, app_descriptors_dir):
    idx = AppIndex.load(platform_descriptor, app_descriptors_dir)
    cascade = idx.excluded_ui_modules(["app-consortia"])
    # app-consortia is matched by name in appDescriptors; its uiModules surface
    assert "app-consortia" in cascade
    assert isinstance(cascade["app-consortia"], list)


def test_module_present_in_deployed_apps(platform_descriptor, app_descriptors_dir):
    idx = AppIndex.load(platform_descriptor, app_descriptors_dir)
    # mod-copycat lives in app-platform-complete (the descriptor's required set).
    complete = idx.modules_of(["app-platform-complete"])
    assert "mod-copycat" in complete
    assert "mod-kb-ebsco-java" not in complete
    # mod-kb-ebsco-java lives only in app-eholdings, which has a descriptor file
    # even though it is NOT in the platform-descriptor available set.
    assert "mod-kb-ebsco-java" in idx.modules_of(["app-eholdings"])


def test_missing_app_descriptor_is_tolerated(platform_descriptor, app_descriptors_dir):
    idx = AppIndex.load(platform_descriptor, app_descriptors_dir)
    # an app with no descriptor file contributes no modules/uiModules, no crash
    assert idx.excluded_ui_modules(["app-does-not-exist"]) == {"app-does-not-exist": []}
    assert idx.modules_of(["app-does-not-exist"]) == set()
