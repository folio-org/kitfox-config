from resolver import emit_json, resolve_namespace
from resolver.apps import AppIndex


def test_resolving_twice_is_byte_identical(config_root, platform_descriptor,
                                           app_descriptors_dir):
    idx = AppIndex.load(platform_descriptor, app_descriptors_dir)
    a = emit_json(resolve_namespace(config_root, "folio-etesting", "sprint", idx))
    b = emit_json(resolve_namespace(config_root, "folio-etesting", "sprint", idx))
    assert a == b


def test_top_level_import_works():
    # resolver/__init__.py re-exports must import cleanly now that model/resolve exist
    from resolver import ResolvedNamespace, ResolvedTenant  # noqa: F401
