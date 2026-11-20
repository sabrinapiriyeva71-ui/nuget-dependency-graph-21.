"""Обход обратных зависимостей пакета."""

from .graph import Graph, Package, dfs_graph, package_key


def reverse_graph(graph: Graph, root: Package) -> Graph:
    """Развернуть рёбра и найти пакеты, зависящие от заданного узла."""
    root_key = package_key(root)
    start = next(
        (package for package in graph if package_key(package) == root_key),
        None,
    )
    if start is None:
        return {}
    parents: dict[Package, list[Package]] = {
        package: [] for package in graph
    }
    for package, dependencies in graph.items():
        for dependency in dependencies:
            parents[dependency].append(package)
    return dfs_graph((start,), parents.__getitem__)
