# Тесты для Personal AI Multitool Assistant

Этот каталог содержит автоматизированные тесты для всех инструментов агента.

## Структура

- `conftest.py` - Конфигурация pytest и фикстуры
- `test_tools.py` - Тесты для всех 8 инструментов
- `__init__.py` - Инициализация пакета тестов

## Запуск тестов

### Установка зависимостей для тестирования

```bash
pip install -r requirements.txt
```

### Запуск всех тестов

```bash
pytest
```

### Запуск с подробным выводом

```bash
pytest -v
```

### Запуск с покрытием кода

```bash
pytest --cov=agent --cov-report=html
```

Отчет о покрытии будет доступен в `htmlcov/index.html`.

### Запуск конкретного теста

```bash
pytest tests/test_tools.py::TestWebSearch::test_web_search_success
```

## Типы тестов

### Unit тесты

Тесты отдельных инструментов с моками внешних API:
- `TestWebSearch` - тесты веб-поиска
- `TestWeather` - тесты погоды
- `TestCryptoPrice` - тесты криптовалют
- `TestFiatCurrency` - тесты валютных курсов
- `TestFileOperations` - тесты файловых операций
- `TestMemory` - тесты сохранения памяти
- `TestQRCode` - тесты генерации QR-кодов
- `TestGetAllTools` - тесты функции получения всех инструментов

## Фикстуры

- `project_root` - корневая директория проекта
- `temp_dir` - временная директория для тестов
- `mock_requests_get` - мок для HTTP GET запросов
- `mock_requests_post` - мок для HTTP POST запросов
- `mock_ddgs` - мок для DuckDuckGo поиска
- `sample_weather_data` - пример данных погоды
- `sample_geocode_data` - пример данных геокодирования

## Маркеры

Тесты могут быть помечены маркерами для выборочного запуска:

- `@pytest.mark.unit` - unit тесты
- `@pytest.mark.integration` - интеграционные тесты
- `@pytest.mark.api` - тесты, требующие реальных API вызовов

Пример запуска только unit тестов:

```bash
pytest -m unit
```

## Примечания

- Все тесты используют моки для внешних API, чтобы не зависеть от сети
- Тесты не требуют реального OpenAI API ключа
- Временные файлы создаются в `tmp_path` и автоматически удаляются после тестов

