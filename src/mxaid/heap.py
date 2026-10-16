"""Indexed binary min-heap with update-key support.

A* needs a priority queue whose keys change when a better ``g`` value is
found.  A lazy heap would push duplicate entries and rely on stale-entry
checks; this implementation instead keeps one entry per node and a position
array, so ``update`` can sift up or down in O(log n).  The node id is always
the final component of the key, giving deterministic tie-breaking and making
tuple comparisons total.
"""

from __future__ import annotations

from typing import Any


class IndexedMinHeap:
    __slots__ = ("_heap", "_pos", "_keys")

    def __init__(self, n: int) -> None:
        self._heap: list[int] = []
        self._pos: list[int] = [-1] * n
        self._keys: list[tuple[Any, ...] | None] = [None] * n

    # -- basic queries ---------------------------------------------------
    def __len__(self) -> int:
        return len(self._heap)

    def __contains__(self, node: int) -> bool:
        return self._pos[node] != -1

    def contains(self, node: int) -> bool:
        return self._pos[node] != -1

    def min_key(self) -> tuple[Any, ...] | None:
        if not self._heap:
            return None
        return self._keys[self._heap[0]]

    def peek_min(self) -> int | None:
        return self._heap[0] if self._heap else None

    def items(self) -> list[int]:
        """A copy of the heap's node ids (used for demo traces)."""
        return list(self._heap)

    # -- mutations -------------------------------------------------------
    def insert(self, node: int, key: tuple[Any, ...]) -> None:
        if self._pos[node] != -1:
            self.update(node, key)
            return
        i = len(self._heap)
        self._heap.append(node)
        self._pos[node] = i
        self._keys[node] = key
        self._sift_up(i)

    def update(self, node: int, key: tuple[Any, ...]) -> None:
        i = self._pos[node]
        if i == -1:
            self.insert(node, key)
            return
        old = self._keys[node]
        self._keys[node] = key
        if old is None or key < old:
            self._sift_up(i)
        elif key > old:
            self._sift_down(i)

    def pop_min(self) -> int:
        if not self._heap:
            raise IndexError("pop from empty heap")
        heap = self._heap
        pos = self._pos
        keys = self._keys
        root = heap[0]
        last = heap.pop()
        pos[root] = -1
        keys[root] = None
        if heap:
            heap[0] = last
            pos[last] = 0
            self._sift_down(0)
        return root

    # -- sift ------------------------------------------------------------
    def _sift_up(self, i: int) -> None:
        heap = self._heap
        keys = self._keys
        pos = self._pos
        node = heap[i]
        key = keys[node]
        while i > 0:
            parent_i = (i - 1) >> 1
            parent = heap[parent_i]
            if keys[parent] <= key:
                break
            heap[i] = parent
            pos[parent] = i
            i = parent_i
        heap[i] = node
        pos[node] = i

    def _sift_down(self, i: int) -> None:
        heap = self._heap
        keys = self._keys
        pos = self._pos
        n = len(heap)
        node = heap[i]
        key = keys[node]
        while True:
            left = (i << 1) + 1
            if left >= n:
                break
            right = left + 1
            child = left
            if right < n and keys[heap[right]] < keys[heap[left]]:
                child = right
            child_node = heap[child]
            if key <= keys[child_node]:
                break
            heap[i] = child_node
            pos[child_node] = i
            i = child
        heap[i] = node
        pos[node] = i
