from cad_mcp.registry import EntityRegistry


def test_auto_naming_increments():
    r = EntityRegistry()
    assert r.register("body", object()) == "Body_001"
    assert r.register("body", object()) == "Body_002"


def test_hint_in_name():
    r = EntityRegistry()
    assert r.register("feature", object(), hint="Extrude") == "Feature_Extrude_001"


def test_requested_name_collision_preserves_intent():
    r = EntityRegistry()
    assert r.register("sketch", 1, "Profile") == "Profile"
    assert r.register("sketch", 2, "Profile") == "Profile_2"
    assert r.register("sketch", 3, "Profile") == "Profile_3"


def test_resolve_and_update():
    r = EntityRegistry()
    o1, o2 = object(), object()
    n = r.register("body", o1, descriptor={"inv_name": "Solid1"})
    assert r.resolve(n) is o1
    r.update_handle(n, o2)
    assert r.resolve(n) is o2
    assert r.get(n).descriptor["inv_name"] == "Solid1"


def test_names_filter_and_unknown():
    r = EntityRegistry()
    r.register("body", 1)
    r.register("sketch", 2)
    assert r.names("body") == ["Body_001"]
    assert "Body_001" in r
    try:
        r.resolve("nope")
    except KeyError:
        return
    raise AssertionError("expected KeyError")
