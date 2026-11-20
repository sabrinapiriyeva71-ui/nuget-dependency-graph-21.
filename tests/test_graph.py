"""Проверки этапа построения графа и тестового репозитория."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from nuget_graph.graph import build_graph, dfs_graph
from nuget_graph.test_repository import TestRepository as LocalRepository
from nuget_graph.test_repository import TestRepositoryError

FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "repository.json"
VERSION = "1.0.0"
A = ("A", VERSION)
B = ("B", VERSION)
C = ("C", VERSION)
D = ("D", VERSION)
F = ("F", VERSION)
G = ("G", VERSION)


class GraphTests(TestCase):
    """Сценарии DFS на ветвлениях, циклах и разной глубине."""

    def setUp(self):
        """Загрузить граф с циклами и несколькими компонентами."""
        self.repository = LocalRepository(FIXTURE)

    def test_dfs_order_and_cycle(self):
        """DFS проходит ветвь до конца и сохраняет замыкающее ребро."""
        graph = build_graph(self.repository, A)
        self.assertEqual(list(graph), [A, B, D, C])
        self.assertEqual(graph, {A: (B, C), B: (D,), C: (D,), D: (B,)})

    def test_filter_removes_matching_nodes(self):
        """Фильтр удаляет узел и все входящие в него рёбра."""
        graph = build_graph(self.repository, A, exclude="b")
        self.assertEqual(list(graph), [A, C, D])
        self.assertEqual(graph, {A: (C,), C: (D,), D: ()})

    def test_filter_can_remove_root(self):
        """Граф пуст, если подстрока встречается в имени корня."""
        self.assertEqual(build_graph(self.repository, A, "a"), {})

    def test_isolated_package(self):
        """Граф сохраняет корневой пакет без зависимостей."""
        self.assertEqual(build_graph(self.repository, F), {F: ()})

    def test_exact_test_repository_version(self):
        """Выбор другой версии меняет зависимости и сохраняет петлю."""
        root = self.repository.resolve("B", "[2.0.0]")
        graph = build_graph(self.repository, root)
        self.assertEqual(graph, {root: (G,), G: (G,)})

    def test_duplicate_names_ignore_case(self):
        """Варианты регистра одного ID не создают второй узел."""
        root = ("First", VERSION)
        child = ("Second", VERSION)
        aliases = (child, ("SECOND", VERSION))
        graph = dfs_graph((root,), {root: aliases, child: ()}.__getitem__)
        self.assertEqual(graph, {root: (child,), child: ()})

    def test_dfs_uses_no_recursion(self):
        """Стек Python не ограничивает глубину цепочки зависимостей."""
        chain_size = 1_200
        chain = [(str(index), VERSION) for index in range(chain_size)]
        table = {
            package: tuple(chain[index + 1:index + 2])
            for index, package in enumerate(chain)
        }
        graph = dfs_graph((chain[0],), table.__getitem__)
        self.assertEqual(list(graph), chain)


class LocalRepositoryTests(TestCase):
    """Сценарии обработки ошибочных тестовых репозиториев."""

    def test_unknown_package_version(self):
        """Версия должна быть явно задана в тестовом репозитории."""
        repository = LocalRepository(FIXTURE)
        with self.assertRaisesRegex(TestRepositoryError, "Не найден пакет"):
            repository.resolve("B", "[3.0.0]")

    def test_unknown_dependency(self):
        """Некорректная ссылка выявляется при загрузке репозитория."""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "data.json"
            value = '{"packages": {"A": {"1.0.0": {"Z": "1.0.0"}}}}'
            path.write_text(value, encoding="utf-8")
            with self.assertRaisesRegex(TestRepositoryError, "неизвестный"):
                LocalRepository(path)

    def test_duplicate_json_key(self):
        """Исходный граф не теряет данные из-за одинаковых ключей."""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "data.json"
            value = '{"packages": {"A": {"1.0.0": {}, "1.0.0": {}}}}'
            path.write_text(value, encoding="utf-8")
            with self.assertRaisesRegex(TestRepositoryError, "ключ"):
                LocalRepository(path)
