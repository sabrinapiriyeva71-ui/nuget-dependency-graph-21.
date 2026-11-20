"""Чтение версий и прямых зависимостей из метаданных репозитория NuGet."""

import json
import re
from urllib.error import HTTPError
from urllib.parse import quote, urljoin, urlsplit, urlunsplit
from urllib.request import urlopen
from xml.etree import ElementTree

from .nuget_versions import choose_version


REQUEST_TIMEOUT = 15
PACKAGE_NAME = re.compile(r"[A-Za-z0-9_]+(?:[.-][A-Za-z0-9_]+)*")
FLAT_CONTAINER_RESPONSES = frozenset({400, 403, 404, 405})


class NuGetError(ValueError):
    """Некорректные данные NuGet или ошибка обращения к репозиторию."""


def _get(url: str) -> bytes:
    """Загрузить содержимое одного HTTP-ресурса."""
    with urlopen(url, timeout=REQUEST_TIMEOUT) as response:
        return response.read()


def _json_object(data: bytes, url: str) -> dict:
    """Прочитать JSON-объект и указать его адрес в диагностике."""
    try:
        content = json.loads(data)
    except ValueError as error:
        raise NuGetError(f"Некорректный JSON по адресу {url}") from error
    if not isinstance(content, dict):
        raise NuGetError(f"Ожидался объект JSON по адресу {url}")
    return content


def _read(url: str) -> bytes:
    """Преобразовать ошибки HTTP и сети в сообщение репозитория."""
    try:
        return _get(url)
    except HTTPError as error:
        raise NuGetError(f"HTTP {error.code} при запросе {url}") from error
    except (OSError, ValueError) as error:
        raise NuGetError(f"Не удалось прочитать {url}: {error}") from error


def _resource_types(value: object) -> tuple[str, ...]:
    """Получить типы ресурса из поля @type индекса NuGet V3."""
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list):
        return tuple(item for item in value if isinstance(item, str))
    return ()


def _flat_container(content: dict, url: str) -> str:
    """Найти адрес совместимого ресурса PackageBaseAddress."""
    resources = content.get("resources")
    if not isinstance(resources, list):
        raise NuGetError(f"Ожидался индекс сервисов NuGet V3: {url}")
    for resource in resources:
        if not isinstance(resource, dict):
            continue
        types = _resource_types(resource.get("@type"))
        address = resource.get("@id")
        if "PackageBaseAddress/3.0.0" in types and isinstance(address, str):
            return urljoin(url, address)
    raise NuGetError(f"В индексе {url} отсутствует ресурс PackageBaseAddress")


def _discover_base(url: str) -> str:
    """Обнаружить адрес flat-container либо принять его напрямую."""
    requires_index = urlsplit(url).path.lower().endswith(".json")
    try:
        data = _get(url)
    except HTTPError as error:
        if not requires_index and error.code in FLAT_CONTAINER_RESPONSES:
            return url
        raise NuGetError(f"HTTP {error.code} при запросе {url}") from error
    except (OSError, ValueError) as error:
        raise NuGetError(f"Не удалось прочитать {url}: {error}") from error
    try:
        content = _json_object(data, url)
    except NuGetError:
        if requires_index:
            raise
        return url
    if requires_index or "resources" in content:
        return _flat_container(content, url)
    return url


def _path_url(base: str, *parts: str) -> str:
    """Построить адрес в flat-container с отдельным кодированием частей."""
    url = urlsplit(base)
    suffix = "/".join(quote(part.lower(), safe="") for part in parts)
    return urlunsplit(url._replace(path=f"{url.path.rstrip('/')}/{suffix}"))


def _declarations(data: bytes, url: str) -> tuple[tuple[str, str], ...]:
    """Прочитать объединение прямых зависимостей из групп файла .nuspec."""
    try:
        document = ElementTree.fromstring(data)
    except ElementTree.ParseError as error:
        raise NuGetError(f"Некорректный XML по адресу {url}") from error
    metadata = document.find("{*}metadata")
    if metadata is None:
        raise NuGetError(f"В .nuspec отсутствует элемент metadata: {url}")
    paths = (
        "{*}dependencies/{*}dependency",
        "{*}dependencies/{*}group/{*}dependency",
    )
    dependencies = {}
    for path in paths:
        for node in metadata.iterfind(path):
            name = node.get("id", "").strip()
            version = node.get("version", "").strip()
            if not PACKAGE_NAME.fullmatch(name):
                raise NuGetError(f"Некорректное имя в .nuspec: {name!r}, {url}")
            dependencies.setdefault((name.lower(), version), (name, version))
    return tuple(dependencies.values())


class NuGetRepository:
    """Репозиторий NuGet V3 с кэшем списков версий и файлов .nuspec."""

    def __init__(self, url: str) -> None:
        """Сохранить адрес индекса сервисов или самого flat-container."""
        self._url = url
        self._base: str | None = None
        self._versions: dict[str, tuple[str, ...]] = {}
        self._dependencies: dict[
            tuple[str, str], tuple[tuple[str, str], ...]
        ] = {}

    def _metadata_url(self, *parts: str) -> str:
        """Лениво обнаружить адрес flat-container при первом обращении."""
        if self._base is None:
            self._base = _discover_base(self._url)
        return _path_url(self._base, *parts)

    def _list_versions(self, name: str) -> tuple[str, ...]:
        """Получить доступные версии пакета из индекса версий."""
        key = name.lower()
        if key not in self._versions:
            url = self._metadata_url(key, "index.json")
            content = _json_object(_read(url), url)
            versions = content.get("versions")
            if not isinstance(versions, list) or not all(
                isinstance(item, str) for item in versions
            ):
                raise NuGetError(f"Некорректный список версий пакета {name}")
            self._versions[key] = tuple(versions)
        return self._versions[key]

    def resolve(self, name: str, requirement: str) -> tuple[str, str]:
        """Найти доступную версию с учётом ограничения из метаданных."""
        if not PACKAGE_NAME.fullmatch(name):
            raise NuGetError(f"Некорректное имя пакета NuGet: {name!r}")
        versions = self._list_versions(name)
        try:
            version = choose_version(versions, requirement)
        except ValueError as error:
            raise NuGetError(f"Пакет {name}: {error}") from error
        if version is None:
            message = f"У пакета {name} нет версии для условия {requirement!r}"
            raise NuGetError(message)
        return name, version

    def dependencies(
        self, package: tuple[str, str]
    ) -> tuple[tuple[str, str], ...]:
        """Вернуть идентификаторы и необработанные ограничения зависимостей."""
        name, version = package
        key = name.lower(), version.lower()
        if key not in self._dependencies:
            url = self._metadata_url(name, version, f"{name}.nuspec")
            self._dependencies[key] = _declarations(_read(url), url)
        return self._dependencies[key]
