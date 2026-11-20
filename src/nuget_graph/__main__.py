"""Точка входа CLI."""

from .config import Config, config_from_args, make_parser
from .graph import Package, PackageRepository, build_graph
from .nuget import NuGetRepository
from .render import plantuml_text, save_svg
from .test_repository import TestRepository


def open_package(config: Config) -> tuple[PackageRepository, Package]:
    """Открыть источник данных и определить точную версию корня."""
    repository = (
        TestRepository(config.repo) if config.test
        else NuGetRepository(config.repo)
    )
    root = repository.resolve(config.package, f"[{config.version}]")
    return repository, root


def main() -> None:
    """Напечатать исходник PlantUML и сохранить SVG с графом."""
    parser = make_parser("Визуализация зависимостей NuGet, вариант 21")
    args = parser.parse_args()
    try:
        config = config_from_args(args)
        repository, root = open_package(config)
        graph = build_graph(repository, root, config.exclude)
        diagram = plantuml_text(graph)
        save_svg(diagram, config.output)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(diagram, end="")


if __name__ == "__main__":
    main()
