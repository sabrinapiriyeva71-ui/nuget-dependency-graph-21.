"""Проверки разбора метаданных и версий NuGet без доступа к сети."""

import json
import unittest
from urllib.error import HTTPError
from unittest.mock import patch

from nuget_graph.nuget import NuGetError, NuGetRepository
from nuget_graph.nuget_versions import choose_version


INDEX = "https://packages.example/v3/index.json"
BASE = "https://packages.example/flat"
VERSIONS_URL = f"{BASE}/example/index.json"
NUSPEC_URL = f"{BASE}/example/2.0.0/example.nuspec"
NUSPEC = b"""<package
  xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd">
  <metadata>
    <id>Example</id><version>2.0.0</version>
    <dependencies>
      <dependency id="AnyRelease" />
      <group targetFramework="net7.0">
        <dependency id="Dependency" version="[1.0,2.0)" />
      </group>
      <group targetFramework="net8.0">
        <dependency id="dependency" version="[1.0,2.0)" />
        <dependency id="Dependency" version="[2.0]" />
      </group>
    </dependencies>
  </metadata>
</package>"""


def read_fixture(url: str) -> bytes:
    """Имитировать HTTP-ответы индекса и flat-container."""
    if url == INDEX:
        return json.dumps({"resources": [{
            "@type": ["PackageBaseAddress/3.0.0"], "@id": "../flat",
        }]}).encode()
    if url == VERSIONS_URL:
        return b'{"versions": ["1.0.0", "2.0.0", "2.1.0-beta"]}'
    if url == NUSPEC_URL:
        return NUSPEC
    raise HTTPError(url, 404, "Not Found", None, None)


class NuGetRepositoryTests(unittest.TestCase):
    """Проверки использования индекса пакетов и чтения .nuspec."""

    @patch("nuget_graph.nuget._get", side_effect=read_fixture)
    def test_service_index_exact_and_declarations(self, fetch):
        """Разрешить точную версию, объединить группы и переиспользовать кэш."""
        repository = NuGetRepository(INDEX)
        package = repository.resolve("Example", "[2.0]")
        self.assertEqual(package, ("Example", "2.0.0"))
        expected = (
            ("AnyRelease", ""),
            ("Dependency", "[1.0,2.0)"),
            ("Dependency", "[2.0]"),
        )
        self.assertEqual(repository.dependencies(package), expected)
        self.assertEqual(repository.resolve("example", "2.0"), (
            "example", "2.0.0",
        ))
        self.assertEqual(repository.dependencies(package), expected)
        self.assertEqual([call.args[0] for call in fetch.call_args_list], [
            INDEX, VERSIONS_URL, NUSPEC_URL,
        ])

    @patch("nuget_graph.nuget._get", side_effect=read_fixture)
    def test_flat_container(self, fetch):
        """Воспользоваться прямым адресом, если корень сервера вернул 404."""
        repository = NuGetRepository(BASE)
        self.assertEqual(repository.resolve("Example", "[2.1.0-beta]"), (
            "Example", "2.1.0-beta",
        ))
        fetch.assert_any_call(VERSIONS_URL)

    @patch("nuget_graph.nuget._get", side_effect=read_fixture)
    def test_missing_version(self, _fetch):
        """Сообщить об отсутствии версии, удовлетворяющей диапазону."""
        with self.assertRaisesRegex(NuGetError, "нет версии"):
            NuGetRepository(INDEX).resolve("Example", "[3.0.0]")

    @patch("nuget_graph.nuget._get", side_effect=read_fixture)
    def test_missing_package(self, _fetch):
        """Выдать диагностическое сообщение для пакета с ответом HTTP 404."""
        with self.assertRaisesRegex(NuGetError, "HTTP 404"):
            NuGetRepository(INDEX).resolve("Unknown", "[1.0.0]")


class NuGetVersionTests(unittest.TestCase):
    """Проверки сравнения версий и разрешения ограничений."""

    def test_range_endpoints(self):
        """Проверить открытые и закрытые границы и минимальную версию."""
        versions = ("1.1.0", "1.2.0", "2.0.0")
        self.assertEqual(choose_version(versions, "(1.1,2.0)"), "1.2.0")
        self.assertEqual(choose_version(versions, "[1.1,2.0)"), "1.1.0")
        self.assertEqual(choose_version(versions, "(1.2,2.0]"), "2.0.0")
        self.assertIsNone(choose_version(versions, "(1.2,2.0)"))
        self.assertEqual(choose_version(versions, "(,1.2]"), "1.1.0")
        self.assertEqual(choose_version(versions, "[1.2,)"), "1.2.0")
        self.assertEqual(choose_version(versions, "1.2"), "1.2.0")
        self.assertEqual(choose_version(versions, ""), "1.1.0")

    def test_prerelease_and_revision(self):
        """Проверить порядок prerelease, метку сборки и четвёртый компонент."""
        versions = ("1.0.0-rc.10", "1.0.0-rc.2", "1.0.0", "1.0.0.4")
        self.assertEqual(choose_version(versions, "1.0.0"), "1.0.0")
        self.assertEqual(choose_version(versions, "1.0.0-RC.2"), "1.0.0-rc.2")
        self.assertEqual(choose_version(versions, "[1.0.0+tag]"), "1.0.0")
        self.assertEqual(choose_version(versions, "(1.0.0,)"), "1.0.0.4")
        self.assertEqual(choose_version(versions, "[1.0.0.4]"), "1.0.0.4")

    def test_floating_versions(self):
        """Проверить выбор самой новой версии для плавающего требования."""
        versions = ("1.0.0", "1.1.0", "1.2.0-rc.2", "1.2.0-rc.10", "2.0.0")
        self.assertEqual(choose_version(versions, "1.*"), "1.1.0")
        self.assertEqual(
            choose_version(versions, "1.*-*"), "1.2.0-rc.10",
        )
        self.assertEqual(
            choose_version(versions, "1.2.0-rc.*"), "1.2.0-rc.10",
        )
        self.assertEqual(
            choose_version((*versions, "1.2.0"), "1.2.0-rc.*"), "1.2.0",
        )
