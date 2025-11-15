"""All 8 tools for the AI agent."""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import qrcode
import requests
try:
    from ddgs import DDGS
except ImportError:
    # Fallback for old package name
    from duckduckgo_search import DDGS
from langchain.tools import tool

# Configure logging
logger = logging.getLogger(__name__)

# Constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
PROJECT_ROOT = Path(__file__).parent.parent


@tool
def web_search(query: str, max_results: int = 5) -> str:
    """
    Search the web using DuckDuckGo.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return (default: 5)
    
    Returns:
        Formatted search results in Russian
    """
    try:
        logger.info(f"web_search: query={query}, max_results={max_results}")
        
        # Improve search query by adding context keywords if needed
        search_query = query.strip()
        
        # Use DuckDuckGo search with better parameters
        with DDGS() as ddgs:
            # Try to get more results and filter better ones
            results = list(
                ddgs.text(
                    search_query,
                    max_results=max_results * 2,  # Get more to filter
                    safesearch="moderate"
                )
            )
        
        if not results:
            logger.info("web_search: no results found")
            return "🔍 Поиск не дал результатов."
        
        # Filter results: check relevance and language
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        # Preferred domains for Russian/English content
        preferred_domains = [
            ".ru", ".com", ".org", ".net", ".edu", ".gov",
            "wikipedia.org", "github.com", "stackoverflow.com",
            "habr.com", "tproger.ru", "vc.ru"
        ]
        
        def is_relevant(result: dict) -> bool:
            """Check if result is relevant to query."""
            title = result.get("title", "").lower()
            snippet = result.get("body", "").lower()
            link = result.get("href", "").lower()
            combined = f"{title} {snippet}"
            
            # Count matching words
            matches = sum(1 for word in query_words if word in combined)
            # Result is relevant if at least 30% of query words match
            relevance_score = matches / max(1, len(query_words))
            
            # Language preference: prefer Russian/English domains
            language_score = 0
            if any(domain in link for domain in preferred_domains):
                language_score = 0.3
            
            # Strongly penalize Chinese/Japanese domains (unless query is about them)
            if any(domain in link for domain in [".cn", ".jp", "zhihu.com", "baidu.com"]):
                if not any(word in query_lower for word in ["китай", "япония", "chinese", "japanese", "china", "japan"]):
                    language_score = -0.8  # Strong penalty to exclude them
            
            # Total score
            total_score = relevance_score + language_score
            return total_score >= 0.3
        
        # Filter and sort by relevance
        filtered_results = [r for r in results if is_relevant(r)]
        
        # Sort by relevance (more matching words = better)
        def get_score(result: dict) -> float:
            title = result.get("title", "").lower()
            snippet = result.get("body", "").lower()
            link = result.get("href", "").lower()
            combined = f"{title} {snippet}"
            matches = sum(1 for word in query_words if word in combined)
            score = matches / max(1, len(query_words))
            # Bonus for preferred domains
            if any(domain in link for domain in preferred_domains):
                score += 0.2
            return score
        
        filtered_results.sort(key=get_score, reverse=True)
        filtered_results = filtered_results[:max_results]
        
        # If filtering removed all results, use original (sorted by score)
        if not filtered_results:
            all_results = sorted(results, key=get_score, reverse=True)
            filtered_results = all_results[:max_results]
        
        formatted_results = ["🔍 Результаты поиска:\n"]
        for i, result in enumerate(filtered_results, 1):
            title = result.get("title", "Без названия")
            snippet = result.get("body", "Нет описания")
            # Truncate long snippets
            if len(snippet) > 200:
                snippet = snippet[:197] + "..."
            link = result.get("href", "")
            formatted_results.append(
                f"{i}. {title}\n   {snippet}\n   {link}\n"
            )
        
        result_text = "\n".join(formatted_results)
        logger.info(
            f"web_search: success, found {len(filtered_results)} results"
        )
        return result_text
    
    except Exception as e:
        error_msg = f"Ошибка при поиске: {str(e)}"
        logger.error(f"web_search error: {error_msg}", exc_info=True)
        return f"❌ {error_msg}"


@tool
def get_weather(city: str) -> str:
    """
    Get current weather and tomorrow forecast for a city using OpenMeteo API.
    
    Args:
        city: City name (e.g., "Moscow", "Москва", "London")
    
    Returns:
        Weather information in Russian with today and tomorrow forecast
    """
    try:
        logger.info(f"get_weather: city={city}")
        
        # Map Russian city names to English for better geocoding
        city_mapping = {
            # Russian cities
            "москва": "Moscow, Russia",
            "санкт-петербург": "Saint Petersburg, Russia",
            "спб": "Saint Petersburg, Russia",
            "новосибирск": "Novosibirsk, Russia",
            "екатеринбург": "Yekaterinburg, Russia",
            "казань": "Kazan, Russia",
            "нижний новгород": "Nizhny Novgorod, Russia",
            "челябинск": "Chelyabinsk, Russia",
            "самара": "Samara, Russia",
            "омск": "Omsk, Russia",
            # CIS capitals
            "минск": "Minsk, Belarus",
            "киев": "Kyiv, Ukraine",
            "київ": "Kyiv, Ukraine",
            "алматы": "Almaty, Kazakhstan",
            "астана": "Astana, Kazakhstan",
            "ташкент": "Tashkent, Uzbekistan",
            "бишкек": "Bishkek, Kyrgyzstan",
            "душанбе": "Dushanbe, Tajikistan",
            "ашхабад": "Ashgabat, Turkmenistan",
            # Popular foreign cities
            "лондон": "London, UK",
            "париж": "Paris, France",
            "берлин": "Berlin, Germany",
            "мадрид": "Madrid, Spain",
            "рим": "Rome, Italy",
            "амстердам": "Amsterdam, Netherlands",
            "варшава": "Warsaw, Poland",
            "прага": "Prague, Czech Republic",
            "вена": "Vienna, Austria",
            "токио": "Tokyo, Japan",
            "пекин": "Beijing, China",
            "шанхай": "Shanghai, China",
            "дубай": "Dubai, UAE",
            "нью-йорк": "New York, USA",
            "лос-анджелес": "Los Angeles, USA",
            "чикаго": "Chicago, USA",
            "торонто": "Toronto, Canada",
            "сидней": "Sydney, Australia",
            "мельбурн": "Melbourne, Australia"
        }
        
        # Normalize city name
        city_lower = city.lower().strip()
        
        # Check if city is in mapping
        if city_lower in city_mapping:
            search_query = city_mapping[city_lower]
            expected_country = None
            # Extract expected country from mapping
            if ", " in search_query:
                expected_country = search_query.split(", ")[1]
        elif city_lower == "москва" or "москва" in city_lower:
            search_query = "Moscow, Russia"
            expected_country = "Russia"
        else:
            search_query = city
            expected_country = None
        
        # Step 1: Geocode city to get coordinates
        geocode_url = "https://geocoding-api.open-meteo.com/v1/search"
        geocode_params = {
            "name": search_query,
            "count": 15,  # Get more results to find correct city
            "language": "en",
            "format": "json"
        }
        
        logger.info(f"get_weather: geocoding request to {geocode_url}")
        geocode_response = requests.get(
            geocode_url, params=geocode_params, timeout=10
        )
        geocode_response.raise_for_status()
        geocode_data = geocode_response.json()
        
        if not geocode_data.get("results"):
            logger.warning(f"get_weather: city '{city}' not found")
            return f"❌ Город '{city}' не найден. Проверьте название."
        
        # Find best match with improved logic
        results = geocode_data["results"]
        location = None
        
        # If we have expected country from mapping, prefer it
        if expected_country:
            for result in results:
                country = result.get("country", "").lower()
                country_code = result.get("country_code", "").upper()
                
                # Check if country matches
                if expected_country.lower() in country or \
                   (expected_country == "Russia" and country_code == "RU") or \
                   (expected_country == "Belarus" and country_code == "BY") or \
                   (expected_country == "Ukraine" and country_code == "UA") or \
                   (expected_country == "UK" and country_code == "GB"):
                    location = result
                    logger.info(
                        f"get_weather: found match by country: "
                        f"{location.get('name')}, {location.get('country')}"
                    )
                    break
        
        # If no match by country, try to find capital cities or major cities
        if not location:
            # For known capitals, prefer results with "capital" in admin level
            for result in results:
                admin_level = result.get("admin1", "").lower()
                if "capital" in admin_level or result.get("population", 0) > 1000000:
                    location = result
                    logger.info(
                        f"get_weather: found major city: "
                        f"{location.get('name')}, {location.get('country')}"
                    )
                    break
        
        # Fallback to first result
        if not location:
            location = results[0]
            logger.info(
                f"get_weather: using first result: "
                f"{location.get('name')}, {location.get('country')}"
            )
        
        latitude = location["latitude"]
        longitude = location["longitude"]
        city_name = location.get("name", city)
        country = location.get("country", "")
        country_code = location.get("country_code", "")
        
        logger.info(
            f"get_weather: found coordinates {latitude}, {longitude}, "
            f"country={country_code}"
        )
        
        # Step 2: Get weather data with forecast
        weather_url = "https://api.open-meteo.com/v1/forecast"
        weather_params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,wind_speed_10m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,weather_code",
            "timezone": "auto",
            "forecast_days": 2  # Today and tomorrow
        }
        
        logger.info(f"get_weather: weather request to {weather_url}")
        weather_response = requests.get(
            weather_url, params=weather_params, timeout=10
        )
        weather_response.raise_for_status()
        weather_data = weather_response.json()
        
        current = weather_data["current"]
        daily = weather_data["daily"]
        
        # Current weather
        temp_now = current["temperature_2m"]
        wind_now = current["wind_speed_10m"]
        code_now = current["weather_code"]
        
        # Tomorrow forecast (index 1 in daily arrays)
        if len(daily["time"]) > 1:
            temp_max_tomorrow = daily["temperature_2m_max"][1]
            temp_min_tomorrow = daily["temperature_2m_min"][1]
            code_tomorrow = daily["weather_code"][1]
            date_tomorrow = daily["time"][1]
        else:
            temp_max_tomorrow = None
            temp_min_tomorrow = None
            code_tomorrow = None
            date_tomorrow = None
        
        # Map weather codes to Russian descriptions
        weather_descriptions = {
            0: "Ясно",
            1: "Преимущественно ясно",
            2: "Переменная облачность",
            3: "Пасмурно",
            45: "Туман",
            48: "Иней",
            51: "Легкая морось",
            53: "Умеренная морось",
            55: "Сильная морось",
            56: "Легкая ледяная морось",
            57: "Сильная ледяная морось",
            61: "Небольшой дождь",
            63: "Умеренный дождь",
            65: "Сильный дождь",
            66: "Ледяной дождь",
            67: "Сильный ледяной дождь",
            71: "Небольшой снег",
            73: "Умеренный снег",
            75: "Сильный снег",
            77: "Снежные зерна",
            80: "Небольшой ливень",
            81: "Умеренный ливень",
            82: "Сильный ливень",
            85: "Небольшой снегопад",
            86: "Сильный снегопад",
            95: "Гроза",
            96: "Гроза с градом",
            99: "Сильная гроза с градом"
        }
        
        condition_now = weather_descriptions.get(code_now, "Неизвестно")
        
        location_str = f"{city_name}"
        if country and country_code != "RU":
            location_str += f", {country}"
        elif country_code == "RU":
            location_str += f", Россия"
        
        result = (
            f"🌤️ Погода в {location_str}:\n\n"
            f"📅 Сегодня:\n"
            f"Температура: {temp_now}°C\n"
            f"Скорость ветра: {wind_now} км/ч\n"
            f"Условия: {condition_now}"
        )
        
        # Add tomorrow forecast if available
        if temp_max_tomorrow is not None:
            condition_tomorrow = weather_descriptions.get(
                code_tomorrow, "Неизвестно"
            )
            # Format date
            from datetime import datetime
            try:
                date_obj = datetime.fromisoformat(date_tomorrow.replace("Z", "+00:00"))
                date_str = date_obj.strftime("%d.%m.%Y")
            except:
                date_str = "завтра"
            
            result += (
                f"\n\n📅 {date_str} (завтра):\n"
                f"Температура: {temp_min_tomorrow:.0f}°C / {temp_max_tomorrow:.0f}°C\n"
                f"Условия: {condition_tomorrow}"
            )
        
        logger.info("get_weather: success")
        return result
    
    except requests.Timeout:
        error_msg = "Превышено время ожидания при запросе погоды"
        logger.error(f"get_weather timeout: {error_msg}", exc_info=True)
        return f"❌ {error_msg}"
    except requests.RequestException as e:
        error_msg = f"Ошибка при запросе погоды: {str(e)}"
        logger.error(f"get_weather request error: {error_msg}", exc_info=True)
        return f"❌ {error_msg}"
    except Exception as e:
        error_msg = f"Ошибка: {str(e)}"
        logger.error(f"get_weather error: {error_msg}", exc_info=True)
        return f"❌ {error_msg}"


@tool
def get_crypto_price(crypto_id: str, currency: str = "usd") -> str:
    """
    Get current cryptocurrency price from CoinGecko API.
    
    Args:
        crypto_id: Cryptocurrency ID (e.g., "bitcoin", "ethereum")
        currency: Target currency (default: "usd")
    
    Returns:
        Cryptocurrency price information in Russian
    """
    try:
        logger.info(f"get_crypto_price: crypto_id={crypto_id}, currency={currency}")
        
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": crypto_id.lower(),
            "vs_currencies": currency.lower(),
            "include_24hr_change": "true"
        }
        
        logger.info(f"get_crypto_price: request to {url}")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if crypto_id.lower() not in data:
            logger.warning(f"get_crypto_price: crypto '{crypto_id}' not found")
            return (
                f"❌ Криптовалюта '{crypto_id}' не найдена. "
                f"Проверьте правильность названия (например: bitcoin, ethereum)"
            )
        
        crypto_data = data[crypto_id.lower()]
        price = crypto_data.get(currency.lower())
        change_24h = crypto_data.get(f"{currency.lower()}_24h_change", 0)
        
        if price is None:
            error_msg = f"Валюта '{currency}' не поддерживается"
            logger.error(f"get_crypto_price: {error_msg}")
            return f"❌ {error_msg}"
        
        change_symbol = "📈" if change_24h >= 0 else "📉"
        change_str = f"{change_24h:+.2f}%"
        
        result = (
            f"💰 {crypto_id.upper()}:\n"
            f"Цена: {price:,.2f} {currency.upper()}\n"
            f"Изменение за 24ч: {change_symbol} {change_str}"
        )
        
        logger.info("get_crypto_price: success")
        return result
    
    except requests.Timeout:
        error_msg = "Превышено время ожидания при запросе курса"
        logger.error(f"get_crypto_price timeout: {error_msg}", exc_info=True)
        return f"❌ {error_msg}"
    except requests.RequestException as e:
        error_msg = f"Ошибка при запросе курса: {str(e)}"
        logger.error(
            f"get_crypto_price request error: {error_msg}", exc_info=True
        )
        return f"❌ {error_msg}"
    except Exception as e:
        error_msg = f"Ошибка: {str(e)}"
        logger.error(f"get_crypto_price error: {error_msg}", exc_info=True)
        return f"❌ {error_msg}"


@tool
def get_fiat_currency(from_currency: str, to_currency: str) -> str:
    """
    Get fiat currency exchange rate using exchangerate.host API.
    Supports RUB and other major currencies.
    
    Args:
        from_currency: Source currency code (e.g., "USD", "EUR")
        to_currency: Target currency code (e.g., "RUB", "JPY")
    
    Returns:
        Exchange rate information in Russian
    """
    try:
        logger.info(
            f"get_fiat_currency: {from_currency} -> {to_currency}"
        )
        
        from_curr = from_currency.upper()
        to_curr = to_currency.upper()
        
        # Use exchangerate.host API (free, no key required)
        url = f"https://api.exchangerate.host/latest"
        params = {
            "base": from_curr,
            "symbols": to_curr
        }
        
        logger.info(f"get_fiat_currency: request to {url}")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("success", False):
            # Try alternative API: exchangerate-api.com
            logger.info("Trying alternative API: exchangerate-api.com")
            alt_url = f"https://api.exchangerate-api.com/v4/latest/{from_curr}"
            alt_response = requests.get(alt_url, timeout=10)
            alt_response.raise_for_status()
            alt_data = alt_response.json()
            
            if to_curr not in alt_data.get("rates", {}):
                error_msg = (
                    f"Валюта '{to_currency}' не найдена или не поддерживается. "
                    f"Проверьте правильность кода валюты."
                )
                logger.error(f"get_fiat_currency: {error_msg}")
                return f"❌ {error_msg}"
            
            rate = alt_data["rates"][to_curr]
            date = alt_data.get("date", "неизвестно")
        else:
            rates = data.get("rates", {})
            if to_curr not in rates:
                error_msg = (
                    f"Валюта '{to_currency}' не найдена или не поддерживается. "
                    f"Проверьте правильность кода валюты."
                )
                logger.error(f"get_fiat_currency: {error_msg}")
                return f"❌ {error_msg}"
            
            rate = rates[to_curr]
            date = data.get("date", "неизвестно")
        
        # Calculate conversion for common amounts
        amount_100 = 100 * rate
        amount_1000 = 1000 * rate
        
        result = (
            f"💱 Курс валют:\n"
            f"1 {from_curr} = {rate:.4f} {to_curr}\n"
            f"100 {from_curr} = {amount_100:.2f} {to_curr}\n"
            f"1000 {from_curr} = {amount_1000:.2f} {to_curr}\n"
            f"Дата: {date}"
        )
        
        logger.info("get_fiat_currency: success")
        return result
    
    except requests.Timeout:
        error_msg = "Превышено время ожидания при запросе курса"
        logger.error(
            f"get_fiat_currency timeout: {error_msg}", exc_info=True
        )
        return f"❌ {error_msg}"
    except requests.RequestException as e:
        error_msg = f"Ошибка при запросе курса: {str(e)}"
        logger.error(
            f"get_fiat_currency request error: {error_msg}", exc_info=True
        )
        return f"❌ {error_msg}"
    except Exception as e:
        error_msg = f"Ошибка: {str(e)}"
        logger.error(
            f"get_fiat_currency error: {error_msg}", exc_info=True
        )
        return f"❌ {error_msg}"


@tool
def file_read(file_path: str) -> str:
    """
    Read content from a file.
    
    Args:
        file_path: Relative path to file from project root
    
    Returns:
        File content with filename
    """
    try:
        logger.info(f"file_read: file_path={file_path}")
        
        # Resolve path relative to project root
        full_path = PROJECT_ROOT / file_path
        
        # Security: prevent directory traversal
        try:
            full_path.resolve().relative_to(PROJECT_ROOT.resolve())
        except ValueError:
            error_msg = "Недопустимый путь к файлу"
            logger.error(f"file_read: {error_msg}")
            return f"❌ {error_msg}"
        
        if not full_path.exists():
            error_msg = f"Файл '{file_path}' не найден"
            logger.error(f"file_read: {error_msg}")
            return f"❌ {error_msg}"
        
        if not full_path.is_file():
            error_msg = f"'{file_path}' не является файлом"
            logger.error(f"file_read: {error_msg}")
            return f"❌ {error_msg}"
        
        # Check file size
        file_size = full_path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            error_msg = (
                f"Файл слишком большой ({file_size / 1024 / 1024:.2f} MB). "
                f"Максимальный размер: {MAX_FILE_SIZE / 1024 / 1024} MB"
            )
            logger.error(f"file_read: {error_msg}")
            return f"❌ {error_msg}"
        
        # Read file
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        result = (
            f"📁 Содержимое файла '{file_path}':\n\n{content}"
        )
        
        logger.info(f"file_read: success, size={file_size} bytes")
        return result
    
    except UnicodeDecodeError:
        error_msg = "Файл содержит не текстовые данные"
        logger.error(f"file_read: {error_msg}", exc_info=True)
        return f"❌ {error_msg}"
    except Exception as e:
        error_msg = f"Ошибка при чтении файла: {str(e)}"
        logger.error(f"file_read error: {error_msg}", exc_info=True)
        return f"❌ {error_msg}"


@tool
def file_write(file_path: str, content: str) -> str:
    """
    Write content to a file.
    
    Args:
        file_path: Relative path to file from project root
        content: Content to write
    
    Returns:
        Confirmation message with file path and size
    """
    try:
        logger.info(f"file_write: file_path={file_path}")
        
        # Resolve path relative to project root
        full_path = PROJECT_ROOT / file_path
        
        # Security: prevent directory traversal
        try:
            full_path.resolve().relative_to(PROJECT_ROOT.resolve())
        except ValueError:
            error_msg = "Недопустимый путь к файлу"
            logger.error(f"file_write: {error_msg}")
            return f"❌ {error_msg}"
        
        # Create directory if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        file_size = full_path.stat().st_size
        
        result = (
            f"✅ Файл '{file_path}' успешно создан.\n"
            f"Размер: {file_size} байт"
        )
        
        logger.info(f"file_write: success, size={file_size} bytes")
        return result
    
    except Exception as e:
        error_msg = f"Ошибка при записи файла: {str(e)}"
        logger.error(f"file_write error: {error_msg}", exc_info=True)
        return f"❌ {error_msg}"


@tool
def memory_save(user_message: str, agent_response: str, summary: str) -> str:
    """
    Save conversation to long-term memory.
    
    Args:
        user_message: User's message
        agent_response: Agent's response
        summary: Brief summary of the exchange
    
    Returns:
        Confirmation message
    """
    try:
        logger.info("memory_save: saving conversation")
        
        memory_file = PROJECT_ROOT / "agent" / "memory.json"
        
        # Load existing memory or create new
        if memory_file.exists():
            with open(memory_file, "r", encoding="utf-8") as f:
                memory = json.load(f)
        else:
            memory = []
        
        # Add new entry
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user": user_message,
            "agent": agent_response,
            "summary": summary
        }
        memory.append(entry)
        
        # Save memory
        with open(memory_file, "w", encoding="utf-8") as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)
        
        result = (
            f"💾 Разговор сохранён в память.\n"
            f"Всего записей: {len(memory)}"
        )
        
        logger.info(f"memory_save: success, total entries={len(memory)}")
        return result
    
    except Exception as e:
        error_msg = f"Ошибка при сохранении в память: {str(e)}"
        logger.error(f"memory_save error: {error_msg}", exc_info=True)
        return f"❌ {error_msg}"


@tool
def generate_qr_code(data: str, filename: Optional[str] = None) -> str:
    """
    Generate QR code from text/data.
    
    Args:
        data: Data to encode in QR code
        filename: Optional filename (if not provided, generates from data)
    
    Returns:
        Confirmation message with file path
    """
    try:
        logger.info(f"generate_qr_code: data_length={len(data)}")
        
        # Generate filename from data if not provided
        if filename is None:
            # Extract domain from URL if it's a URL
            if data.startswith(("http://", "https://")):
                from urllib.parse import urlparse
                try:
                    parsed = urlparse(data)
                    domain = parsed.netloc.replace("www.", "")
                    # Clean domain for filename
                    domain = "".join(
                        c if c.isalnum() or c in "-_" else "_"
                        for c in domain
                    )
                    filename = f"{domain}_qr_code.png"
                except:
                    filename = "qr_code.png"
            else:
                # Generate filename from first 20 chars of data
                safe_name = "".join(
                    c if c.isalnum() or c in "-_" else "_"
                    for c in data[:20]
                )
                filename = f"{safe_name}_qr_code.png"
        
        # Ensure filename ends with .png
        if not filename.endswith(".png"):
            filename += ".png"
        
        # Sanitize filename
        filename = "".join(
            c if c.isalnum() or c in "-_." else "_"
            for c in filename
        )
        
        # Create output directory
        output_dir = PROJECT_ROOT / "qr_codes"
        output_dir.mkdir(exist_ok=True)
        
        output_path = output_dir / filename
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(output_path)
        
        result = (
            f"🎨 QR-код успешно создан.\n"
            f"Файл: qr_codes/{filename}"
        )
        
        logger.info(f"generate_qr_code: success, file={output_path}")
        return result
    
    except Exception as e:
        error_msg = f"Ошибка при создании QR-кода: {str(e)}"
        logger.error(f"generate_qr_code error: {error_msg}", exc_info=True)
        return f"❌ {error_msg}"


def get_all_tools():
    """Get list of all available tools."""
    return [
        web_search,
        get_weather,
        get_crypto_price,
        get_fiat_currency,
        file_read,
        file_write,
        memory_save,
        generate_qr_code
    ]

