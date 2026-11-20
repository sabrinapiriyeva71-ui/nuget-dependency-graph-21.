"""Точка входа CLI."""

from .config import Config, config_from_args, make_parser
from .graph import Graph, Package, PackageRepository, build_graph
from .nuget import NuGetRepository
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


def main() -> None:
    """Построить и вывести граф прямых и транзитивных зависимостей."""
    parser = make_parser("Граф зависимостей NuGet")
    args = parser.parse_args()
    try:
        config = config_from_args(args)
        repository, root = open_package(config)
        graph = build_graph(repository, root, config.exclude)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print_graph(graph)


if __name__ == "__main__":
    main()
