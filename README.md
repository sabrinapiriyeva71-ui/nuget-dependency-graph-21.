# Конфигурационное управление — практическая работа № 2

Вариант 21. Инструмент для анализа зависимостей пакетов .NET (NuGet).
Текущий этап читает прямые зависимости из NuGet v3. Для запуска нужен Python 3.11 или новее.

## Параметры

| Параметр | Назначение | Значение по умолчанию |
| --- | --- | --- |
| `--package` | Идентификатор анализируемого пакета | Обязательный |
| `--repo` | URL NuGet v3 или путь к JSON с флагом `--test` | `https://api.nuget.org/v3/index.json` |
| `--test` | Использовать файл тестового репозитория | Выключен |
| `--version` | Точная версия анализируемого пакета | Обязательный |
| `--output` | Путь к файлу изображения SVG | `graph.svg` |
| `--exclude` | Подстрока для исключения пакетов из графа | Пустая |

## Команды

```sh
make build
make test
./run.sh --help
./run.sh --package Serilog --version 4.0.0
```

## Проверка ошибок

Каждая команда завершается с кодом 2 и печатает причину в stderr.

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

CLI читает индекс сервисов NuGet v3, находит `PackageBaseAddress/3.0.0`,
проверяет наличие заданной версии и загружает её `.nuspec`. Также можно
указать URL flat-container напрямую. Идентичные объявления из разных групп
целевых платформ печатаются один раз. Ограничения на версии показаны так,
как они указаны в метаданных. В этом коммите выводом служит список прямых
зависимостей. Тестовый JSON подключается на этапе 3.

```sh
./run.sh --package Serilog --version 4.0.0
./run.sh --package Microsoft.Extensions.Options --version 8.0.0 \
  --repo https://api.nuget.org/v3-flatcontainer/
```

## Этап 3. Итеративный DFS

Граф хранит ориентированные рёбра от пакета к его прямым зависимостям.
Узел определяется идентификатором пакета и конкретной версией. DFS обходит
граф с явным стеком. Уже посещённый узел повторно не раскрывается,
а ребро к нему сохраняется. Поэтому вывод сохраняет циклы и обе ветви,
которые приводят к одной зависимости.

`--exclude` отбрасывает пакеты, в чьём имени есть подстрока без учёта
регистра. Исключённый узел и его рёбра отсутствуют в графе. Если подстроке
соответствует корень, граф пустой.

В файле [examples/repository.json](examples/repository.json) ключи
`packages` — имена из заглавных латинских букв. Каждый пакет сопоставляет
версию и объект вида `{"ИМЯ": "ВЕРСИЯ"}` с прямыми зависимостями.
Пустой объект обозначает пакет без зависимостей. Каждая указанная версия
зависимости должна присутствовать в файле.

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
