"""Построение графа зависимостей итеративным обходом в глубину."""

from collections.abc import Callable, Iterable
from typing import Protocol

Package = tuple[str, str]
Graph = dict[Package, tuple[Package, ...]]


class PackageRepository(Protocol):
    """Операции источника данных, необходимые построителю графа."""

    def resolve(self, name: str, requirement: str) -> Package:
        """Определить конкретную версию пакета по ограничению."""

    def dependencies(self, package: Package) -> tuple[Package, ...]:
        """Вернуть имена и ограничения версий прямых зависимостей."""


def package_key(package: Package) -> Package:
    """Вернуть идентификатор узла, независимый от регистра."""
    name, version = package
    return name.casefold(), version.casefold()


def dfs_graph(
    roots: Iterable[Package],
    neighbors: Callable[[Package], Iterable[Package]],
) -> Graph:
    """Обойти узлы стеком, сохраняя все рёбра и порядок посещения."""
    graph: Graph = {}
    canonical: dict[Package, Package] = {}
    pending = list(reversed(list(roots)))
    while pending:
        package = pending.pop()
        node = canonical.setdefault(package_key(package), package)
        if node in graph:
            continue
        children = (
            canonical.setdefault(package_key(child), child)
            for child in neighbors(node)
        )
        graph[node] = tuple(dict.fromkeys(children))
        pending.extend(reversed(graph[node]))
    return graph


def build_all_graph(
    repository: PackageRepository,
    roots: Iterable[Package],
    exclude: str = "",
) -> Graph:
    """Построить граф от заданных корней с фильтром имён пакетов."""
    needle = exclude.casefold()

    def included(name: str) -> bool:
        """Проверить имя узла с учётом подстроки фильтра."""
        return not needle or needle not in name.casefold()

    def resolve_neighbors(package: Package) -> Iterable[Package]:
        """Разрешить версии прямых зависимостей, прошедших фильтр."""
        for name, requirement in repository.dependencies(package):
            if included(name):
                yield repository.resolve(name, requirement)

    included_roots = (package for package in roots if included(package[0]))
    return dfs_graph(included_roots, resolve_neighbors)


def build_graph(
    repository: PackageRepository,
    root: Package,
    exclude: str = "",
) -> Graph:
    """Построить граф прямых и транзитивных зависимостей пакета."""
    return build_all_graph(repository, (root,), exclude)
