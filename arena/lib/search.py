"""Graph search: BFS (grid + generic), Dijkstra, A*, components, toposort, union-find.
All iterative (no recursion limits). Grid cells are (x, y), grid[y][x]."""
import heapq
from collections import deque

from .grid import DIRS4


def grid_bfs(grid, sources, passable=lambda c: c != "#", dirs=DIRS4):
    """Multi-source BFS on a grid. sources: list of (x,y). Returns (dist dict, parent dict)."""
    h, w = len(grid), len(grid[0])
    dist, par = {}, {}
    q = deque()
    for s in sources:
        dist[s] = 0
        par[s] = None
        q.append(s)
    while q:
        x, y = q.popleft()
        d = dist[(x, y)] + 1
        for dx, dy in dirs:
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in dist and passable(grid[ny][nx]):
                dist[(nx, ny)] = d
                par[(nx, ny)] = (x, y)
                q.append((nx, ny))
    return dist, par


def bfs(start, neighbors, goal=None):
    """Generic BFS. neighbors(state) -> iterable. Stops early if goal(state). Returns (dist, parent, found)."""
    dist, par = {start: 0}, {start: None}
    q = deque([start])
    while q:
        u = q.popleft()
        if goal is not None and goal(u):
            return dist, par, u
        for v in neighbors(u):
            if v not in dist:
                dist[v] = dist[u] + 1
                par[v] = u
                q.append(v)
    return dist, par, None


def path_to(par, end):
    """Reconstruct [start..end] from parent dict."""
    out = []
    while end is not None:
        out.append(end)
        end = par[end]
    return out[::-1]


def dijkstra(start, neighbors, goal=None):
    """neighbors(u) -> iterable of (v, cost). Returns (dist, parent, found_goal_state)."""
    dist, par = {start: 0}, {start: None}
    pq = [(0, 0, start)]
    cnt = 1
    while pq:
        d, _, u = heapq.heappop(pq)
        if d > dist[u]:
            continue
        if goal is not None and goal(u):
            return dist, par, u
        for v, c in neighbors(u):
            nd = d + c
            if nd < dist.get(v, float("inf")):
                dist[v] = nd
                par[v] = u
                heapq.heappush(pq, (nd, cnt, v))
                cnt += 1
    return dist, par, None


def astar(start, neighbors, h, is_goal):
    """A*: neighbors(u) -> (v, cost); h(u) admissible heuristic. Returns (cost, path) or (None, None)."""
    g = {start: 0}
    par = {start: None}
    pq = [(h(start), 0, 0, start)]
    cnt = 1
    while pq:
        f, gu, _, u = heapq.heappop(pq)
        if gu > g[u]:
            continue
        if is_goal(u):
            return gu, path_to(par, u)
        for v, c in neighbors(u):
            ng = gu + c
            if ng < g.get(v, float("inf")):
                g[v] = ng
                par[v] = u
                heapq.heappush(pq, (ng + h(v), ng, cnt, v))
                cnt += 1
    return None, None


def grid_components(grid, passable=lambda c: c != "#", dirs=DIRS4):
    """Connected components: returns list of lists of cells."""
    h, w = len(grid), len(grid[0])
    seen = set()
    comps = []
    for y in range(h):
        for x in range(w):
            if (x, y) in seen or not passable(grid[y][x]):
                continue
            comp = [(x, y)]
            seen.add((x, y))
            st = [(x, y)]
            while st:
                cx, cy = st.pop()
                for dx, dy in dirs:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen and passable(grid[ny][nx]):
                        seen.add((nx, ny))
                        comp.append((nx, ny))
                        st.append((nx, ny))
            comps.append(comp)
    return comps


def toposort(nodes, edges):
    """Kahn. edges: iterable of (u, v) meaning u before v. Returns order or None if cycle."""
    nodes = list(nodes)
    indeg = {u: 0 for u in nodes}
    adj = {u: [] for u in nodes}
    for u, v in edges:
        adj[u].append(v)
        indeg[v] += 1
    q = deque(u for u in nodes if indeg[u] == 0)
    out = []
    while q:
        u = q.popleft()
        out.append(u)
        for v in adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    return out if len(out) == len(nodes) else None


class DSU:
    """Union-find with path halving + union by size. Works on any hashable keys."""

    def __init__(self, items=()):
        self.p = {}
        self.sz = {}
        for i in items:
            self.p[i] = i
            self.sz[i] = 1

    def find(self, x):
        p = self.p
        if x not in p:
            p[x] = x
            self.sz[x] = 1
            return x
        while p[x] != x:
            p[x] = p[p[x]]
            x = p[x]
        return x

    def union(self, a, b):
        a, b = self.find(a), self.find(b)
        if a == b:
            return False
        if self.sz[a] < self.sz[b]:
            a, b = b, a
        self.p[b] = a
        self.sz[a] += self.sz[b]
        return True

    def same(self, a, b):
        return self.find(a) == self.find(b)
