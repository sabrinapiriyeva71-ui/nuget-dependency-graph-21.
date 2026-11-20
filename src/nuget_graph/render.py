"""Генерация описания PlantUML и сохранение диаграммы SVG."""

import os
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from string import ascii_letters, digits

from .graph import Graph, Package


RENDER_TIMEOUT = 60
SVG_TAG = "{http://www.w3.org/2000/svg}svg"
LABEL_CHARACTERS = frozenset(ascii_letters + digits + ".-+ ")


class RenderError(ValueError):
    """Ошибка преобразования диаграммы или записи файла."""


def _safe_label(package: Package) -> str:
    """Экранировать кавычки и разметку PlantUML в подписи узла."""
    label = " ".join(package)
    return "".join(
        char if char in LABEL_CHARACTERS else f"<U+{ord(char):04X}>"
        for char in label
    )


def plantuml_text(graph: Graph) -> str:
    """Представить ориентированный граф на языке PlantUML."""
    nodes = dict.fromkeys(graph)
    for dependencies in graph.values():
        nodes.update(dict.fromkeys(dependencies))
    aliases = {package: f"p{index}" for index, package in enumerate(nodes)}
    lines = [
        "@startuml",
        "!pragma layout smetana",
        "left to right direction",
        "skinparam shadowing false",
        "skinparam ArrowColor #536981",
        "skinparam rectangleBackgroundColor #F4F8FD",
        "skinparam rectangleBorderColor #58708A",
    ]
    for package, alias in aliases.items():
        color = " #DCEBFF" if alias == "p0" else ""
        lines.append(f'rectangle "{_safe_label(package)}" as {alias}{color}')
    for package, dependencies in graph.items():
        for dependency in dependencies:
            lines.append(f"{aliases[package]} --> {aliases[dependency]}")
    lines.append("@enduml")
    return "\n".join(lines) + "\n"


def _renderer_command() -> list[str]:
    """Найти установленный PlantUML или запустить его через Java."""
    jar = os.environ.get("PLANTUML_JAR")
    if jar:
        path = Path(jar).expanduser()
        if not path.is_file():
            raise RenderError(f"JAR PlantUML не найден: {path}")
        java = shutil.which("java")
        if not java:
            raise RenderError("Для запуска PlantUML JAR нужна Java в PATH.")
        return [java, "-Djava.awt.headless=true", "-jar", str(path)]
    executable = shutil.which("plantuml")
    if executable:
        return [executable]
    raise RenderError("Установите plantuml или укажите JAR в PLANTUML_JAR.")


def _render(source: str) -> bytes:
    """Преобразовать описание PlantUML в проверенный SVG."""
    flags = ["-pipe", "-tsvg", "-charset", "UTF-8", "-nometadata"]
    command = _renderer_command() + flags
    try:
        result = subprocess.run(
            command,
            input=source.encode("utf-8"),
            capture_output=True,
            timeout=RENDER_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise RenderError("PlantUML превысил время ожидания.") from error
    except OSError as error:
        raise RenderError(f"Не удалось запустить PlantUML: {error}") from error
    if result.returncode:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise RenderError(f"PlantUML завершился с ошибкой: {message}")
    try:
        root = ET.fromstring(result.stdout)
    except ET.ParseError as error:
        raise RenderError("PlantUML вернул некорректный SVG.") from error
    if root.tag != SVG_TAG:
        raise RenderError("Результат PlantUML не является SVG.")
    return result.stdout


def save_svg(source: str, output: Path) -> None:
    """Сохранить SVG в уже существующей директории."""
    svg = _render(source)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=output.parent, suffix=".tmp", delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(svg)
        temporary_path.replace(output)
    except OSError as error:
        message = f"Не удалось записать SVG в {output}: {error}"
        raise RenderError(message) from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
