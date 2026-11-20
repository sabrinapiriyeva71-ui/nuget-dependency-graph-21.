# Конфигурационное управление — практическая работа № 2

Вариант 21. Инструмент для анализа зависимостей пакетов .NET (NuGet).
Первый этап проверяет параметры командной строки и выводит их как
`ключ=значение`. Для запуска нужен Python 3.11 или новее.

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
