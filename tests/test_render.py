"""Проверки описания PlantUML и записи SVG."""

import os
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

from nuget_graph.render import RenderError, plantuml_text, save_svg


ROOT = ("A", "1.0.0")
DEPENDENCY = ("B", "2.0.0")
ISOLATED = ("C", "3.0.0")
GRAPH = {
    ROOT: (DEPENDENCY, ROOT),
    DEPENDENCY: (ROOT,),
    ISOLATED: (),
}
SVG = "{http://www.w3.org/2000/svg}"
RENDERER_AVAILABLE = shutil.which("plantuml") or os.environ.get("PLANTUML_JAR")


class PlantUmlTests(unittest.TestCase):
    """Генерация исходника и интеграция с установленным PlantUML."""

    def test_cycle_self_loop_and_isolated_package(self):
        """Сохранить все вершины и направления рёбер."""
        source = plantuml_text(GRAPH)
        self.assertTrue(source.startswith("@startuml\n"))
        self.assertIn('rectangle "C 3.0.0" as p2\n', source)
        self.assertIn("p0 --> p1\n", source)
        self.assertIn("p1 --> p0\n", source)
        self.assertIn("p0 --> p0\n", source)
        self.assertTrue(source.endswith("@enduml\n"))

    def test_label_quotes_and_markup_are_escaped(self):
        """Передавать пользовательские символы как текст подписи."""
        source = plantuml_text({('A"__<B>', "1.0.0"): ()})
        escaped = "A<U+0022><U+005F><U+005F><U+003C>B<U+003E>"
        self.assertIn(f'rectangle "{escaped} 1.0.0" as p0', source)

    def test_missing_renderer_keeps_existing_file(self):
        """Сохранить прежний SVG при ошибке поиска PlantUML."""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.svg"
            output.write_text("previous", encoding="utf-8")
            command_lookup = "nuget_graph.render.shutil.which"
            with (
                patch.dict(os.environ, {"PLANTUML_JAR": ""}),
                patch(command_lookup, return_value=None),
                self.assertRaisesRegex(RenderError, "PLANTUML_JAR"),
            ):
                save_svg(plantuml_text(GRAPH), output)
            self.assertEqual("previous", output.read_text(encoding="utf-8"))

    @unittest.skipUnless(
        RENDERER_AVAILABLE, "для проверки SVG нужен PlantUML",
    )
    def test_svg_contains_package_labels(self):
        """Запустить PlantUML и прочитать подписи в созданном SVG."""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.svg"
            save_svg(plantuml_text(GRAPH), output)
            root = ET.parse(output).getroot()
        self.assertEqual(f"{SVG}svg", root.tag)
        labels = {text.text for text in root.iter(f"{SVG}text")}
        self.assertEqual({"A 1.0.0", "B 2.0.0", "C 3.0.0"}, labels)

    @unittest.skipUnless(
        RENDERER_AVAILABLE, "для проверки SVG нужен PlantUML",
    )
    def test_empty_graph_produces_svg(self):
        """Создать пустой SVG при отфильтрованном корневом узле."""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "empty.svg"
            save_svg(plantuml_text({}), output)
            root = ET.parse(output).getroot()
        self.assertEqual(f"{SVG}svg", root.tag)
        self.assertIsNone(root.find(f".//{SVG}text"))
