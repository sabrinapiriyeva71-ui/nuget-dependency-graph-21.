"""Проверки обратных зависимостей на всём тестовом репозитории."""

from pathlib import Path
from unittest import TestCase

from nuget_graph.graph import build_all_graph
from nuget_graph.reverse import reverse_graph
from nuget_graph.test_repository import TestRepository as LocalRepository

FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "repository.json"
VERSION = "1.0.0"
A = ("A", VERSION)
B = ("B", VERSION)
C = ("C", VERSION)
D = ("D", VERSION)
E = ("E", VERSION)
F = ("F", VERSION)
G = ("G", VERSION)


class ReverseGraphTests(TestCase):
    """Обратные рёбра, транзитивность, версии и циклы."""

    def setUp(self):
        """Загрузить тестовый репозиторий и граф всех версий."""
        self.repository = LocalRepository(FIXTURE)
        self.roots = self.repository.all_packages()
        self.graph = build_all_graph(self.repository, self.roots)

    def test_includes_package_outside_forward_scope(self):
        """Обратный обход проходит две ветви и находит внешний пакет E."""
        graph = reverse_graph(self.graph, D)
        self.assertEqual(list(graph), [D, B, A, C, E])
        self.assertEqual(
            graph, {D: (B, C), B: (A, D), A: (), C: (A, E), E: ()}
        )

    def test_cycle_and_different_package_versions(self):
        """Ребро образует петлю и идёт к конкретной версии B."""
        second_b = ("B", "2.0.0")
        graph = reverse_graph(self.graph, G)
        self.assertEqual(graph, {G: (second_b, G), second_b: ()})

    def test_isolated_package(self):
        """В обратном графе изолированного пакета остаётся сам пакет."""
        self.assertEqual(reverse_graph(self.graph, F), {F: ()})

    def test_filter_removes_branch(self):
        """Удаление C разрывает путь от D к E."""
        graph = build_all_graph(self.repository, self.roots, "c")
        self.assertEqual(reverse_graph(graph, D), {D: (B,), B: (A, D), A: ()})

    def test_missing_target(self):
        """Для цели за пределами анализируемой области граф пуст."""
        self.assertEqual(reverse_graph(self.graph, ("Z", VERSION)), {})
