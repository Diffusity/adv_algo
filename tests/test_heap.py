import heapq
import random

import pytest

from mxaid.heap import IndexedMinHeap


def test_empty_heap():
    h = IndexedMinHeap(4)
    assert len(h) == 0
    assert h.min_key() is None
    with pytest.raises(IndexError):
        h.pop_min()


def test_insert_pop_order_and_ties():
    h = IndexedMinHeap(5)
    h.insert(3, (2.0, 3))
    h.insert(1, (1.0, 1))
    h.insert(4, (2.0, 4))
    h.insert(0, (2.0, 0))
    h.insert(2, (1.0, 2))
    order = [h.pop_min() for _ in range(5)]
    assert order == [1, 2, 0, 3, 4]


def test_update_decrease_and_increase():
    h = IndexedMinHeap(4)
    for v in range(4):
        h.insert(v, (10.0 + v, v))
    h.update(3, (1.0, 3))
    assert h.pop_min() == 3
    h.update(2, (99.0, 2))
    assert h.pop_min() == 0
    assert h.pop_min() == 1
    assert h.pop_min() == 2
    assert len(h) == 0


def test_random_against_dict():
    rng = random.Random(1234)
    n = 32
    h = IndexedMinHeap(n)
    active: dict[int, tuple] = {}
    for _ in range(3000):
        if not active or rng.random() < 0.6:
            v = rng.randrange(n)
            key = (rng.randrange(20), rng.randrange(20), v)
            if v in active:
                h.update(v, key)
            else:
                h.insert(v, key)
            active[v] = key
        else:
            expected_node = min(active, key=lambda v: active[v])
            got = h.pop_min()
            assert got == expected_node
            del active[got]
        assert len(h) == len(active)
        if active:
            assert h.min_key() == min(active.values())
    while active:
        expected_node = min(active, key=lambda v: active[v])
        assert h.pop_min() == expected_node
        del active[expected_node]


def test_insert_existing_updates():
    h = IndexedMinHeap(2)
    h.insert(0, (5.0, 0))
    h.insert(0, (1.0, 0))
    assert len(h) == 1
    assert h.pop_min() == 0
