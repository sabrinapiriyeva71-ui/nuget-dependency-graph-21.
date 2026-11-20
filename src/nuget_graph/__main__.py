"""Точка входа CLI."""

from .config import config_from_args, make_parser
from .nuget import NuGetRepository


def main() -> None:
    """Вывести прямые зависимости точной версии пакета."""
    parser = make_parser("Прямые зависимости пакета NuGet")
    args = parser.parse_args()
    try:
        config = config_from_args(args)
        if config.test:
            raise ValueError("--test доступен начиная с этапа 3")
        repository = NuGetRepository(config.repo)
        root = repository.resolve(config.package, f"[{config.version}]")
        dependencies = repository.dependencies(root)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"Прямые зависимости {root[0]}@{root[1]}")
    for name, requirement in dependencies:
        print(f"{name} {requirement or '(без ограничения версии)'}")
    if not dependencies:
        print("(нет)")


if __name__ == "__main__":
    main()
