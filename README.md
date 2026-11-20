# Конфигурационное управление — практическая работа № 2

Вариант 21. Инструмент для анализа зависимостей пакетов .NET (NuGet).
Программа получает метаданные NuGet v3 через HTTP или читает тестовый JSON,
строит граф итеративным DFS, печатает PlantUML и сохраняет SVG.
Для чтения зависимостей используется стандартная библиотека Python.

## Параметры

| Параметр | Назначение | Значение по умолчанию |
| --- | --- | --- |
| `--package` | Идентификатор анализируемого пакета | Обязательный |
| `--repo` | URL NuGet v3 или путь к JSON с флагом `--test` | `https://api.nuget.org/v3/index.json` |
| `--test` | Использовать файл тестового репозитория | Выключен |
| `--version` | Точная версия анализируемого пакета | Обязательный |
| `--output` | Путь к SVG в существующем каталоге | `graph.svg` |
| `--exclude` | Подстрока для исключения пакетов из графа | Пустая |

## Установка и запуск

Нужен Python 3.11 или новее. Установите PlantUML для сохранения SVG.
Программа запускает команду `plantuml` из `PATH` или JAR, указанный
в переменной `PLANTUML_JAR`. Для JAR нужна Java. Работа проверена
с PlantUML 1.2025.10 и встроенной раскладкой Smetana. [PlantUML](https://plantuml.com/download)

```sh
make build                  # проверить компиляцию Python-модулей
make test                   # запустить unittest
./run.sh --help
```

Тесты записи SVG запускаются при наличии PlantUML. Если PlantUML скачан как JAR, перед запуском задайте путь к файлу.

```sh
export PLANTUML_JAR=/путь/к/plantuml-1.2025.10.jar
```

## Этапы в Git

| Тег | Поведение CLI |
| --- | --- |
| `stage-1` | Проверка и печать шести параметров |
| `stage-2` | Список прямых зависимостей точной версии |
| `stage-3` | Список смежности графа, построенного итеративным DFS |
| `stage-4` | Граф или список обратных зависимостей с `--reverse` |
| `stage-5` | Исходник PlantUML в stdout и изображение SVG |

Для демонстрации конкретного этапа откройте его тег в отдельном рабочем
каталоге. Замените `stage-4` тегом нужного этапа и выполняйте команды из
соответствующего раздела в созданном каталоге.

```sh
git worktree add --detach ../pr2-stage-4 stage-4
cd ../pr2-stage-4
make test
```

## Этап 1. Конфигурация и ошибки

```sh
./run.sh --package Serilog --version 4.0.0
```

```text
package=Serilog
repo=https://api.nuget.org/v3/index.json
test=false
version=4.0.0
output=graph.svg
exclude=
```

Ошибочные команды ниже завершаются с кодом 2 и печатают причину в stderr.

```sh
./run.sh --package 'bad/name' --version 4.0.0
./run.sh --package Serilog --version 4.0.0 --repo broken-url
./run.sh --package Serilog --version 4.0.0 --test=yes
./run.sh --package A --version 1.0.0 --test --repo missing.json
./run.sh --package Serilog --version '[4.0.0,5.0.0)'
./run.sh --package Serilog --version 4.0.0 --output graph.png
./run.sh --package Serilog --version 4.0.0 --exclude ' '
```

## Этап 2. Прямые зависимости

CLI на этом этапе читает индекс сервисов NuGet v3, находит `PackageBaseAddress/3.0.0`,
проверяет наличие заданной версии и загружает её `.nuspec`. Также можно
указать URL flat-container напрямую. Идентичные объявления из разных групп
целевых платформ печатаются один раз. Ограничения на версии показаны так,
как они указаны в метаданных. Для построения транзитивного графа
выбирается наименьшая подходящая версия для каждого обычного диапазона
и наибольшая для плавающего. Тестовый JSON подключается на этапе 3.

```sh
./run.sh --package Serilog --version 4.0.0
./run.sh --package Microsoft.Extensions.Options --version 8.0.0 \
  --repo https://api.nuget.org/v3-flatcontainer/
```

Для `Serilog@4.0.0` получены объявления `System.Diagnostics.DiagnosticSource 8.0.1`,
`System.Threading.Channels 8.0.0` и `System.ValueTuple 4.5.0`.

## Этап 3. Итеративный DFS

Граф хранит ориентированные рёбра от пакета к его прямым зависимостям.
Узел определяется идентификатором пакета и конкретной версией. DFS обходит
граф с явным стеком. Уже посещённый узел повторно не раскрывается,
а ребро к нему сохраняется. Поэтому вывод сохраняет циклы и обе ветви,
которые приводят к одной зависимости.

`--exclude` отбрасывает пакеты, в чьём имени есть подстрока без учёта
регистра. Исключённый узел и его рёбра отсутствуют в графе. Если подстроке
соответствует корень, граф пустой.

Ключи объекта `packages` — имена из заглавных латинских букв. Каждый пакет
сопоставляет версию и объект вида `{"A": "1.0.0"}` с прямыми зависимостями.
Пустой объект обозначает пакет без зависимостей. Каждая указанная версия
зависимости должна присутствовать в файле. [Пример JSON](examples/repository.json)

```sh
./run.sh --test --repo examples/repository.json --package A --version 1.0.0
./run.sh --test --repo examples/repository.json --package A --version 1.0.0 --exclude b
./run.sh --test --repo examples/repository.json --package B --version 2.0.0
./run.sh --test --repo examples/repository.json --package F --version 1.0.0
```

У `A@1.0.0` есть ветви `A → B → D` и `A → C → D`, а ребро
`D → B` замыкает цикл. При `--exclude b` остаётся цепочка
`A → C → D`. От `B@2.0.0` достижим пакет `G` с ребром к самому
себе. Пакет `F` изолирован.

## Этап 4. Обратные зависимости

На теге `stage-4` опция `--reverse` разворачивает рёбра и запускает
тот же итеративный DFS.
CLI выводит прямых и транзитивных потребителей выбранной версии.
В тестовом режиме рассматриваются все пакеты и версии из JSON, в том
числе пакеты за пределами прямого графа выбранного корня.

```sh
./run.sh --test --repo examples/repository.json --package D --version 1.0.0 --reverse
./run.sh --test --repo examples/repository.json --package D --version 1.0.0 --reverse --exclude c
./run.sh --test --repo examples/repository.json --package F --version 1.0.0 --reverse
./run.sh --test --repo examples/repository.json --package G --version 1.0.0 --reverse
```

- Для `D@1.0.0` результат — `B`, `A`, `C`, `E` версии 1.0.0.
  `E` найден через `C`, хотя его нет в графе зависимостей `A`.
- С `--exclude c` для `D@1.0.0` остаются `B` и `A`.
- У изолированного `F@1.0.0` результат пустой.
- У `G@1.0.0` результат — только `B@2.0.0`. Петля на `G` в
  графе сохраняется, а сам корень в список потребителей не входит.

В NuGet v3 поиск потребителей работает по графу указанных пакетов.
Для каждого корня требуется отдельная опция `--from-package ИМЯ@ВЕРСИЯ`.
Границы поиска заданы явно, потому что индекс `PackageBaseAddress`
предоставляет метаданные пакетов по известному идентификатору.

```sh
./run.sh --package Microsoft.Extensions.Primitives --version 8.0.0 --reverse \
  --from-package Microsoft.Extensions.Logging@8.0.0 --exclude System
```

## Этап 5. PlantUML и SVG

Стрелка направлена от пакета к зависимости. Подпись узла содержит
идентификатор пакета и версию. Корень выделен цветом. Команда сохраняет
SVG в файл `--output` и печатает описание PlantUML в stdout. Перенаправление
stdout позволяет сохранить описание для повторного рендеринга.

```sh
mkdir -p build/diagrams
./run.sh --package Serilog --version 4.0.0 \
  --output build/diagrams/serilog.svg > build/diagrams/serilog.puml
./run.sh --package Microsoft.Extensions.Options --version 8.0.0 \
  --output build/diagrams/options.svg > build/diagrams/options.puml
./run.sh --package Microsoft.Extensions.Logging --version 8.0.0 \
  --output build/diagrams/logging.svg > build/diagrams/logging.puml
```

Пример с небольшим тестовым графом и циклом.

```sh
./run.sh --test --repo examples/repository.json --package A --version 1.0.0 \
  --output build/diagrams/test-cycle.svg > build/diagrams/test-cycle.puml
```

## Сравнение с NuGet

Для проверки использован .NET SDK 8.0.419. Для каждого пакета создан отдельный
проект с `TargetFramework` равным `net8.0`, одним `PackageReference` и точной
версией, например `Version="[8.0.0]"`. После восстановления из NuGet.org
выполнены штатные команды .NET CLI.

```bash
dotnet restore Case.csproj --source https://api.nuget.org/v3/index.json
dotnet list Case.csproj package --include-transitive
dotnet nuget why Case.csproj Microsoft.Extensions.Primitives
```

Последняя команда показывает путь к указанной зависимости. Здесь
`Microsoft.Extensions.Primitives` подходит для проектов с
`Microsoft.Extensions.Options` и `Microsoft.Extensions.Logging`.
[dotnet list package](https://learn.microsoft.com/dotnet/core/tools/dotnet-package-list)
 · [dotnet nuget why](https://learn.microsoft.com/dotnet/core/tools/dotnet-nuget-why).

Количество узлов, включая корневой пакет, и рёбер сверено с данными
`obj/project.assets.json`, которые записал `dotnet restore`.

| Пакет | NuGet для `net8.0` | Программа без фильтра |
| --- | ---: | ---: |
| Serilog 4.0.0 | 1 узел, 0 рёбер | 86 узлов, 474 ребра |
| Microsoft.Extensions.Options 8.0.0 | 3 узла, 2 ребра | 89 узлов, 480 рёбер |
| Microsoft.Extensions.Logging 8.0.0 | 6 узлов, 7 рёбер | 93 узла, 494 ребра |

Все узлы и рёбра, выбранные NuGet для `net8.0`, присутствуют в каждом
соответствующем графе программы.

- **Serilog 4.0.0.** NuGet для `net8.0` вывел только корневой пакет. В графе
  программы есть ребро к `System.Threading.Channels 8.0.0`. Оно объявлено
  в группах для .NET Framework 4.6.2/4.7.1 и .NET Standard 2.0.
  [Манифест Serilog](https://api.nuget.org/v3-flatcontainer/serilog/4.0.0/serilog.nuspec).
- **Microsoft.Extensions.Options 8.0.0.** NuGet нашёл две зависимости
  версии 8.0.0 — `Microsoft.Extensions.DependencyInjection.Abstractions` и
  `Microsoft.Extensions.Primitives`. Эти два ребра есть и в графе программы.
  В нём также есть ребро к `System.ComponentModel.Annotations 5.0.0` из
  групп .NET Standard 2.0/2.1.
  [Манифест Options][options-nuspec].
- **Microsoft.Extensions.Logging 8.0.0.** NuGet нашёл пять зависимостей
  версии 8.0.0 — `Microsoft.Extensions.DependencyInjection`,
  `Microsoft.Extensions.DependencyInjection.Abstractions`,
  `Microsoft.Extensions.Logging.Abstractions`,
  `Microsoft.Extensions.Options` и `Microsoft.Extensions.Primitives`.
  Команда `dotnet nuget why` подтвердила три пути до
  `Microsoft.Extensions.DependencyInjection.Abstractions`, через
  `DependencyInjection`, `Logging.Abstractions` и `Options`. Эти пути есть
  и в графе программы. Дополнительное ребро к
  `System.Diagnostics.DiagnosticSource 8.0.0` объявлено в группах
  .NET Framework 4.6.2 и .NET Standard 2.0/2.1.
  [Манифест Logging][logging-nuspec].

Программа объединяет зависимости из всех групп `.nuspec`, поскольку анализирует
пакет и его версию без привязки к целевой платформе проекта. При восстановлении
NuGet выбирает ближайшую совместимую группу для `net8.0` и разрешает версии в
контексте всего проекта. Для приведённых примеров дополнительные рёбра возникают
из групп других целевых платформ.
[Разрешение зависимостей NuGet](https://learn.microsoft.com/nuget/concepts/dependency-resolution).

[options-nuspec]:
  <https://api.nuget.org/v3-flatcontainer/microsoft.extensions.options/8.0.0/microsoft.extensions.options.nuspec>
[logging-nuspec]:
  <https://api.nuget.org/v3-flatcontainer/microsoft.extensions.logging/8.0.0/microsoft.extensions.logging.nuspec>

Чтобы воспроизвести сравнение, установите .NET SDK 8.0.419 и запустите
`./examples/run-official.sh`. Скрипт создаёт три временных проекта и
удаляет их после завершения. Допускается путь к CLI в переменной
`DOTNET`. [Журнал проверки](examples/official-net8.txt)
