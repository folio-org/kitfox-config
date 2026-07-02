from resolver.overlays import apply_overlays, substitute


def test_substitute_replaces_placeholders_only():
    data = {"modules": {"m": {"extraEnvVars": [{"name": "X", "value": "${secureTenantId}"}]}}}
    out = substitute(data, {"secureTenantId": "university"})
    assert out["modules"]["m"]["extraEnvVars"][0]["value"] == "university"


def test_substitute_leaves_unknown_text_untouched():
    assert substitute({"a": "plain"}, {"secureTenantId": "u"}) == {"a": "plain"}


def test_configextensions_merge_in_list_order():
    overlays = {
        "first":  {"name": "first",  "ui": {"flag": "a"}},
        "second": {"name": "second", "ui": {"flag": "b"}},
    }
    base = {"ui": {}}
    out = apply_overlays(
        base, config_extensions=["first", "second"], overlays=overlays,
        any_secure=False, secure_tenant_id=None, rtr=False,
    )
    assert out["ui"]["flag"] == "b"   # later wins


def test_presence_driven_secure_tenant_applied_and_substituted():
    overlays = {
        "secure-tenant": {
            "name": "secure-tenant",
            "modules": {
                "mod-patron": {"extraEnvVars": [{"name": "SECURE_TENANT_ID",
                                                 "value": "${secureTenantId}"}]}
            },
        }
    }
    out = apply_overlays(
        {}, config_extensions=[], overlays=overlays,
        any_secure=True, secure_tenant_id="university", rtr=False,
    )
    ev = out["modules"]["mod-patron"]["extraEnvVars"][0]
    assert ev["value"] == "university"


def test_secure_tenant_not_applied_when_no_secure_tenant():
    overlays = {"secure-tenant": {"name": "secure-tenant", "modules": {"m": {}}}}
    out = apply_overlays({}, config_extensions=[], overlays=overlays,
                         any_secure=False, secure_tenant_id=None, rtr=False)
    assert "modules" not in out or "m" not in out.get("modules", {})


def test_rtr_overlay_applied_by_flag():
    overlays = {"rtr": {"name": "rtr",
                        "modules": {"mod-authtoken": {"extraEnvVars": [
                            {"name": "LEGACY_TOKEN_TENANTS", "value": ""}]}}}}
    out = apply_overlays({}, config_extensions=[], overlays=overlays,
                         any_secure=False, secure_tenant_id=None, rtr=True)
    assert "mod-authtoken" in out["modules"]
