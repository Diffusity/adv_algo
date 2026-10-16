from mxaid.maps import MapSpec, generate_map


def test_generators_are_deterministic_and_connected():
    for topology in ("random", "maze", "rooms", "city"):
        spec = MapSpec(topology, 24, 24, density=0.2, seed=3)
        a = generate_map(spec)
        b = generate_map(spec)
        assert a.blocked == b.blocked
        assert (a.start, a.goal) == (b.start, b.goal)
        assert a.start not in a.blocked and a.goal not in a.blocked
        # A path must exist by construction.
        from mxaid.maps import _reachable

        assert _reachable(a.graph, a.start, a.goal, a.blocked)


def test_random_density_is_in_the_right_ballpark():
    spec = MapSpec("random", 40, 40, density=0.2, seed=11)
    m = generate_map(spec)
    assert 0.12 <= m.density <= 0.28


def test_maze_has_a_path_for_all_loop_levels():
    for density in (0.0, 0.1, 0.3):
        spec = MapSpec("maze", 25, 25, density=density, seed=4, random_endpoints=False)
        m = generate_map(spec)
        from mxaid.maps import _reachable

        assert _reachable(m.graph, m.start, m.goal, m.blocked)
