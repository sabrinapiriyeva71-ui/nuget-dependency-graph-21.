"""Точка входа CLI."""

from dataclasses import asdict

from .config import config_from_args, make_parser


def main() -> None:
    """Проверить и вывести пользовательскую конфигурацию."""
    parser = make_parser("Диаграмма зависимостей NuGet, вариант 21")
    args = parser.parse_args()
    try:
        config = config_from_args(args)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    for key, value in asdict(config).items():
        if isinstance(value, bool):
            value = str(value).lower()
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
