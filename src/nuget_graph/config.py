"""Опции командной строки и проверка конфигурации."""

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlsplit

DEFAULT_REPO = "https://api.nuget.org/v3/index.json"
MAX_PACKAGE_LENGTH = 100
RESERVED_TCP_PORT = 0
PACKAGE_ID = re.compile(r"[A-Za-z0-9_]+(?:[.-][A-Za-z0-9_]+)*")
VERSION = re.compile(
    r"[0-9]+(?:\.[0-9]+){0,3}"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)


@dataclass(frozen=True)
class Config:
    """Проверенные значения пользовательских параметров."""

    package: str
    repo: str
    test: bool
    version: str
    output: Path
    exclude: str


def make_parser(description: str) -> argparse.ArgumentParser:
    """Создать парсер с параметрами, общими для всех этапов."""
    parser = argparse.ArgumentParser(
        description=description, allow_abbrev=False
    )
    parser.add_argument("--package", required=True, help="идентификатор пакета")
    parser.add_argument(
        "--repo", default=DEFAULT_REPO, help="URL NuGet или путь к JSON"
    )
    parser.add_argument(
        "--test", action="store_true", help="читать локальный JSON"
    )
    parser.add_argument("--version", required=True, help="точная версия пакета")
    parser.add_argument(
        "--output", default="graph.svg", help="путь к выходному SVG"
    )
    parser.add_argument(
        "--exclude", default="", help="подстрока для исключения пакетов"
    )
    return parser


def validate_package(value: str) -> str:
    """Проверить идентификатор пакета NuGet."""
    if len(value) > MAX_PACKAGE_LENGTH or not PACKAGE_ID.fullmatch(value):
        raise ValueError("--package: недопустимый идентификатор пакета")
    return value


def validate_version(value: str) -> str:
    """Проверить синтаксис точной версии NuGet."""
    if not VERSION.fullmatch(value):
        raise ValueError("--version: укажите точную версию, например 8.0.0")
    return value


def validate_repo(value: str, test: bool) -> str:
    """Проверить путь к тестовому файлу или URL репозитория."""
    if test:
        try:
            if Path(value).is_file():
                return value
        except OSError:
            pass
        raise ValueError(f"--repo: тестовый файл не найден: {value!r}")
    message = "--repo: укажите корректный HTTP(S) URL или флаг --test"
    try:
        parts = urlsplit(value)
        checks = (
            parts.scheme in {"http", "https"},
            parts.hostname,
            parts.port != RESERVED_TCP_PORT,
            not parts.fragment,
            not any(char.isspace() for char in value),
        )
    except ValueError as error:
        raise ValueError(message) from error
    if not all(checks):
        raise ValueError(message)
    return value


def validate_output(value: str) -> Path:
    """Проверить расширение и родительский каталог файла SVG."""
    output = Path(value)
    if output.suffix.lower() != ".svg" or output.is_dir():
        raise ValueError("--output: укажите путь к файлу с расширением .svg")
    if not output.parent.is_dir():
        raise ValueError("--output: каталог для SVG не существует")
    return output


def validate_exclude(value: str) -> str:
    """Проверить, что непустой фильтр содержит видимые символы."""
    if value and (
        not value.strip()
        or any(unicodedata.category(char) == "Cc" for char in value)
    ):
        raise ValueError("--exclude: укажите подстроку без управляющих знаков")
    return value


def config_from_args(args: argparse.Namespace) -> Config:
    """Проверить все общие опции командной строки."""
    return Config(
        package=validate_package(args.package),
        repo=validate_repo(args.repo, args.test),
        test=args.test,
        version=validate_version(args.version),
        output=validate_output(args.output),
        exclude=validate_exclude(args.exclude),
    )
