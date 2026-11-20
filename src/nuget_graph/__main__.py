"""Точка входа CLI."""

import argparse

from .config import (
    Config,
    config_from_args,
    make_parser,
    validate_package,
    validate_version,
)
from .graph import (
    Graph,
    Package,
    PackageRepository,
    build_all_graph,
    build_graph,
)
from .nuget import NuGetRepository
from .reverse import reverse_graph
from .test_repository import TestRepository


def open_package(config: Config) -> tuple[PackageRepository, Package]:
    """Открыть источник данных и определить точную версию корня."""
    repository = (
        TestRepository(config.repo) if config.test
        else NuGetRepository(config.repo)
    )
    root = repository.resolve(config.package, f"[{config.version}]")
    return repository, root


def print_graph(graph: Graph) -> None:
    """Вывести список смежности в порядке обхода."""
    if not graph:
        print("(граф пуст)")
    for (name, version), children in graph.items():
        labels = ", ".join(f"{item}@{rev}" for item, rev in children)
        print(f"{name}@{version} -> {labels or '(нет)'}")


def reverse_scope(value: str) -> Package:
    """Разобрать точную версию одного корня для обратного поиска."""
    name, separator, version = value.rpartition("@")
    if not separator:
        raise ValueError("--from-package: используйте формат ИМЯ@ВЕРСИЯ")
    return validate_package(name), validate_version(version)


def get_reverse(
    repository: PackageRepository,
    root: Package,
    args: argparse.Namespace,
) -> Graph:
    """Найти обратные зависимости во всём JSON или в заданных корнях."""
    if isinstance(repository, TestRepository):
        if args.from_package:
            raise ValueError("--from-package используется только с NuGet")
        roots = repository.all_packages()
    else:
        if not args.from_package:
            raise ValueError("--reverse для NuGet требует --from-package")
        roots = tuple(
            repository.resolve(name, f"[{version}]")
            for name, version in map(reverse_scope, args.from_package)
        )
    return reverse_graph(build_all_graph(repository, roots, args.exclude), root)


def print_reverse(graph: Graph, root: Package) -> None:
    """Вывести обратные зависимости в порядке DFS, пропустив корень."""
    print(f"Обратные зависимости {root[0]}@{root[1]}")
    dependents = tuple(graph)[1:]
    for name, version in dependents:
        print(f"{name}@{version}")
    if not dependents:
        print("(нет)")


def main() -> None:
    """Вывести прямой граф или список обратных зависимостей."""
    parser = make_parser("Граф зависимостей NuGet")
    parser.add_argument(
        "--reverse", action="store_true", help="найти обратные зависимости"
    )
    parser.add_argument(
        "--from-package", action="append", default=[], metavar="ИМЯ@ВЕРСИЯ",
        help="корень поиска в NuGet (опцию можно повторить)",
    )
    args = parser.parse_args()
    try:
        config = config_from_args(args)
        repository, root = open_package(config)
        if args.from_package and not args.reverse:
            raise ValueError("--from-package требует --reverse")
        if args.reverse:
            print_reverse(get_reverse(repository, root, args), root)
        else:
            print_graph(build_graph(repository, root, config.exclude))
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
