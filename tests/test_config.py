"""Проверки конфигурации, доступной на всех этапах."""

from pathlib import Path
import tempfile
import unittest

from nuget_graph.config import config_from_args, make_parser


VALID_OPTIONS = ["--package", "Serilog", "--version", "4.0.0"]


class ConfigTests(unittest.TestCase):
    """Проверить валидацию и значения по умолчанию."""

    def setUp(self) -> None:
        self.parser = make_parser("Проверка конфигурации")

    def parse(self, *options: str):
        """Разобрать аргументы с заданными пакетом и версией."""
        return config_from_args(
            self.parser.parse_args([*VALID_OPTIONS, *options])
        )

    def test_default_options(self) -> None:
        config = self.parse()
        self.assertEqual(config.package, "Serilog")
        self.assertEqual(config.version, "4.0.0")
        self.assertEqual(config.repo, "https://api.nuget.org/v3/index.json")
        self.assertEqual(config.output, Path("graph.svg"))
        self.assertFalse(config.test)
        self.assertEqual(config.exclude, "")

    def test_accepts_a_local_file_when_test_mode_is_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "repo.json"
            path.write_text("{}", encoding="utf-8")
            config = self.parse("--repo", str(path), "--test")
        self.assertTrue(config.test)
        self.assertEqual(config.repo, str(path))

    def test_each_invalid_parameter(self) -> None:
        cases = (
            ("--package", ["--package", "bad/name"]),
            ("--repo", ["--repo", "repo.json"]),
            ("--repo", ["--test", "--repo", "missing-repo.json"]),
            ("--repo", ["--repo", "https://host:no"]),
            ("--version", ["--version", "[1.0,2.0)"]),
            ("--output", ["--output", "graph.png"]),
            ("--output", ["--output", "missing-folder/graph.svg"]),
            ("--exclude", ["--exclude", " "]),
        )
        for flag, options in cases:
            with self.subTest(options=options):
                with self.assertRaisesRegex(ValueError, flag):
                    self.parse(*options)

    def test_test_flag_does_not_accept_a_value(self) -> None:
        with self.assertRaises(SystemExit):
            self.parse("--test=yes")
