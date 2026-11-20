"""Разбор версий и диапазонов из метаданных NuGet."""

import re
from dataclasses import dataclass


RELEASE_COMPONENTS = 4
TOKEN = r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*"
VERSION = re.compile(
    rf"(?P<numbers>[0-9]+(?:\.[0-9]+){{0,3}})"
    rf"(?:-(?P<prerelease>{TOKEN}))?(?:\+{TOKEN})?"
)
FLOATING = re.compile(
    r"(?P<numbers>\*|(?:[0-9]+\.){1,3}\*|[0-9]+(?:\.[0-9]+){0,3})"
    r"(?:-(?P<prerelease>[A-Za-z0-9.-]*\*))?"
)


@dataclass(frozen=True, order=True)
class Version:
    """Версия в порядке сравнения NuGet, без метки сборки."""

    numbers: tuple[int, ...]
    stable: bool
    prerelease: tuple[tuple[bool, int | str], ...]

    @classmethod
    def parse(cls, value: str) -> "Version":
        """Разобрать числовую часть и идентификаторы предварительной версии."""
        match = VERSION.fullmatch(value)
        if match is None:
            raise ValueError(f"Некорректная версия NuGet: {value!r}")
        numbers = tuple(map(int, match["numbers"].split(".")))
        numbers += (0,) * (RELEASE_COMPONENTS - len(numbers))
        prerelease = match["prerelease"]
        tokens = tuple(
            (False, int(token)) if token.isdigit() else (True, token.lower())
            for token in prerelease.split(".")
        ) if prerelease else ()
        return cls(numbers, prerelease is None, tokens)


@dataclass(frozen=True)
class VersionRange:
    """Обычный диапазон с необязательными нижней и верхней границами."""

    lower: Version | None = None
    upper: Version | None = None
    include_lower: bool = False
    include_upper: bool = False

    def _allows_prerelease(self) -> bool:
        """Проверить наличие предварительной версии в границах диапазона."""
        return any(
            bound is not None and not bound.stable
            for bound in (self.lower, self.upper)
        )

    def accepts(self, version: Version) -> bool:
        """Проверить порядок версии и явный запрос нестабильных версий."""
        if not version.stable and not self._allows_prerelease():
            return False
        lower_ok = self.lower is None or version > self.lower
        upper_ok = self.upper is None or version < self.upper
        return (
            (lower_ok or self.include_lower and version == self.lower)
            and (upper_ok or self.include_upper and version == self.upper)
        )


@dataclass(frozen=True)
class FloatingVersion:
    """Плавающее выражение с префиксами чисел и предварительной версии."""

    numbers: tuple[int, ...]
    exact_numbers: bool
    prerelease_prefix: str | None

    @classmethod
    def parse(cls, value: str) -> "FloatingVersion":
        """Прочитать плавающее выражение с завершающими звёздочками."""
        match = FLOATING.fullmatch(value)
        if match is None:
            raise ValueError(f"Некорректный диапазон NuGet: {value!r}")
        numbers = match["numbers"]
        prerelease = match["prerelease"]
        if not numbers.endswith("*"):
            if prerelease is None:
                raise ValueError(f"Некорректный диапазон NuGet: {value!r}")
            return cls(Version.parse(numbers).numbers, True, prerelease[:-1])
        prefix = numbers.removesuffix("*").removesuffix(".")
        parts = tuple(map(int, prefix.split("."))) if prefix else ()
        return cls(parts, False, prerelease[:-1] if prerelease else None)

    def accepts(self, version: Version) -> bool:
        """Проверить соответствие префиксу и допуск prerelease-версий."""
        length = RELEASE_COMPONENTS if self.exact_numbers else len(self.numbers)
        if version.numbers[:length] != self.numbers:
            return False
        if version.stable:
            return True
        if self.prerelease_prefix is None:
            return False
        prefix = ".".join(str(token) for _, token in version.prerelease)
        return prefix.startswith(self.prerelease_prefix.lower())


def parse_range(value: str) -> VersionRange:
    """Прочитать точную версию, интервал или одиночную нижнюю границу."""
    if not value:
        return VersionRange()
    if value[0] not in "[(":
        return VersionRange(lower=Version.parse(value), include_lower=True)
    if value[-1] not in ")]":
        raise ValueError(f"Некорректный диапазон NuGet: {value!r}")
    lower_text, separator, upper_text = value[1:-1].partition(",")
    if not separator:
        if value[0] + value[-1] != "[]":
            raise ValueError(f"Некорректный диапазон NuGet: {value!r}")
        exact = Version.parse(lower_text.strip())
        return VersionRange(exact, exact, True, True)
    bounds = (lower_text.strip(), upper_text.strip())
    lower, upper = (Version.parse(item) if item else None for item in bounds)
    return VersionRange(lower, upper, value[0] == "[", value[-1] == "]")


def choose_version(versions: tuple[str, ...], requirement: str) -> str | None:
    """Выбрать версию из индекса NuGet согласно указанному требованию."""
    requirement = requirement.strip()
    if "*" in requirement:
        constraint = FloatingVersion.parse(requirement)
        select = max
    else:
        constraint = parse_range(requirement)
        select = min
    parsed = ((Version.parse(raw), raw) for raw in versions)
    matches = (pair for pair in parsed if constraint.accepts(pair[0]))
    result = select(matches, default=None)
    return result[1] if result is not None else None
