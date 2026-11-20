"""Локальный источник зависимостей для тестового режима."""

import json
import re
from pathlib import Path

from .graph import Graph, Package

PACKAGE_NAME = re.compile(r"[A-Z]+")
VERSION = re.compile(r"[0-9]+(?:\.[0-9]+){0,3}(?:[-+][\w.+-]+)?", re.ASCII)


class TestRepositoryError(ValueError):
    """Ошибка чтения или обращения к тестовому репозиторию."""


def read_json(path: Path) -> object:
    """Прочитать JSON-файл с понятным сообщением при ошибке."""
    try:
        with path.open(encoding="utf-8") as stream:
            return json.load(stream, object_pairs_hook=unique_fields)
    except (OSError, UnicodeError, ValueError) as error:
        raise TestRepositoryError(f"Файл {path}: {error}") from error


def unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Проверить отсутствие повторяющихся ключей в JSON."""
    fields: dict[str, object] = {}
    for key, value in pairs:
        if key in fields:
            raise TestRepositoryError(f"повторяющийся ключ {key!r}")
        fields[key] = value
    return fields


def parse_dependencies(value: object, package: Package) -> tuple[Package, ...]:
    """Прочитать таблицу точных версий зависимостей узла."""
    if not isinstance(value, dict):
        raise TestRepositoryError(
            f"Для {package} ожидается объект зависимостей"
        )
    dependencies: list[Package] = []
    for name, version in value.items():
        if not isinstance(version, str) or not VERSION.fullmatch(version):
            raise TestRepositoryError(
                f"Для {package} неверная версия зависимости {name}"
            )
        dependencies.append((name, version))
    return tuple(dependencies)


def parse_package(name: str, versions: object) -> Graph:
    """Прочитать все версии одного пакета."""
    if not PACKAGE_NAME.fullmatch(name):
        raise TestRepositoryError(f"Недопустимое имя пакета {name!r}")
    if not isinstance(versions, dict) or not versions:
        raise TestRepositoryError(f"Нет списка версий для {name}")
    graph: Graph = {}
    for version, value in versions.items():
        if not VERSION.fullmatch(version):
            raise TestRepositoryError(f"Недопустимая версия {name}@{version}")
        package = (name, version)
        graph[package] = parse_dependencies(value, package)
    return graph


def parse_repository(data: object) -> Graph:
    """Проверить схему тестового репозитория и ссылки на другие пакеты."""
    if not isinstance(data, dict) or set(data) != {"packages"}:
        raise TestRepositoryError('Ожидается объект с ключом "packages"')
    packages = data["packages"]
    if not isinstance(packages, dict) or not packages:
        raise TestRepositoryError('Ожидается непустой объект "packages"')
    graph: Graph = {}
    for name, versions in packages.items():
        graph.update(parse_package(name, versions))
    for package, dependencies in graph.items():
        for name, version in dependencies:
            if (name, version) not in graph:
                raise TestRepositoryError(
                    f"{package} ссылается на неизвестный пакет {name}@{version}"
                )
    return graph


class TestRepository:
    """Предоставить доступ к версиям пакетов тестового графа."""

    def __init__(self, path: str | Path) -> None:
        """Загрузить описание пакетов и проверить целостность графа."""
        self._graph = parse_repository(read_json(Path(path)))

    def resolve(self, name: str, requirement: str) -> Package:
        """Найти пакет по имени и точной версии из тестового графа."""
        if requirement.startswith("[") and requirement.endswith("]"):
            requirement = requirement[1:-1]
        package = (name, requirement)
        if package not in self._graph:
            raise TestRepositoryError(f"Не найден пакет {name}@{requirement}")
        return package

    def dependencies(self, package: Package) -> tuple[Package, ...]:
        """Вернуть прямые зависимости выбранного пакета."""
        return self._graph[self.resolve(*package)]

    def all_packages(self) -> tuple[Package, ...]:
        """Перечислить версии всех пакетов в тестовом репозитории."""
        return tuple(self._graph)
