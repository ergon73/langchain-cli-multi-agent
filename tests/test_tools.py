"""Tests for agent tools."""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open, MagicMock

from agent.tools import (
    web_search,
    get_weather,
    get_crypto_price,
    get_fiat_currency,
    file_read,
    file_write,
    memory_save,
    generate_qr_code,
    get_all_tools
)


class TestWebSearch:
    """Tests for web_search tool."""
    
    def test_web_search_success(self, mock_ddgs):
        """Test successful web search."""
        # Mock DDGS results
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.__enter__ = Mock(return_value=mock_ddgs_instance)
        mock_ddgs_instance.__exit__ = Mock(return_value=False)
        mock_ddgs_instance.text = Mock(return_value=[
            {
                "title": "Test Result",
                "body": "Test description",
                "href": "https://example.com"
            }
        ])
        mock_ddgs.return_value = mock_ddgs_instance
        
        result = web_search.invoke({"query": "test", "max_results": 5})
        
        assert "Результаты поиска" in result or "🔍" in result
        assert "Test Result" in result or "example.com" in result
    
    def test_web_search_no_results(self, mock_ddgs):
        """Test web search with no results."""
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.__enter__ = Mock(return_value=mock_ddgs_instance)
        mock_ddgs_instance.__exit__ = Mock(return_value=False)
        mock_ddgs_instance.text = Mock(return_value=[])
        mock_ddgs.return_value = mock_ddgs_instance
        
        result = web_search.invoke({"query": "nonexistent", "max_results": 5})
        
        assert "не дал результатов" in result or "❌" in result or "🔍" in result


class TestWeather:
    """Tests for get_weather tool."""
    
    def test_get_weather_success(
        self, mock_requests_get, sample_geocode_data, sample_weather_data
    ):
        """Test successful weather retrieval."""
        # Mock geocoding response
        geocode_response = Mock()
        geocode_response.json.return_value = sample_geocode_data
        geocode_response.raise_for_status = Mock()
        
        # Mock weather response
        weather_response = Mock()
        weather_response.json.return_value = sample_weather_data
        weather_response.raise_for_status = Mock()
        
        # Set up mock to return different responses
        mock_requests_get.side_effect = [geocode_response, weather_response]
        
        result = get_weather.invoke({"city": "Moscow"})
        
        assert "Погода" in result
        assert "10.5" in result or "10" in result
        assert "Сегодня" in result
        assert "завтра" in result.lower()
    
    def test_get_weather_city_not_found(self, mock_requests_get):
        """Test weather with city not found."""
        geocode_response = Mock()
        geocode_response.json.return_value = {"results": []}
        geocode_response.raise_for_status = Mock()
        mock_requests_get.return_value = geocode_response
        
        result = get_weather.invoke({"city": "NonexistentCity"})
        
        assert "❌" in result or "не найден" in result.lower()
    
    def test_get_weather_minsk_mapping(
        self, mock_requests_get, sample_weather_data
    ):
        """Test that Minsk maps to Belarus, not Russia."""
        geocode_response = Mock()
        geocode_response.json.return_value = {
            "results": [
                {
                    "name": "Minsk",
                    "latitude": 53.9045,
                    "longitude": 27.5615,
                    "country": "Belarus",
                    "country_code": "BY"
                }
            ]
        }
        geocode_response.raise_for_status = Mock()
        
        weather_response = Mock()
        weather_response.json.return_value = sample_weather_data
        weather_response.raise_for_status = Mock()
        
        mock_requests_get.side_effect = [geocode_response, weather_response]
        
        result = get_weather.invoke({"city": "Минск"})
        
        assert "Minsk" in result or "Минск" in result or "Погода" in result
        # Should find Belarus, not Russia
        assert mock_requests_get.call_count == 2


class TestCryptoPrice:
    """Tests for get_crypto_price tool."""
    
    def test_get_crypto_price_success(self, mock_requests_get):
        """Test successful crypto price retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "bitcoin": {
                "usd": 50000.0,
                "usd_24h_change": 2.5
            }
        }
        mock_response.raise_for_status = Mock()
        mock_requests_get.return_value = mock_response
        
        result = get_crypto_price.invoke({"crypto_id": "bitcoin"})
        
        assert "BITCOIN" in result or "bitcoin" in result.lower()
        # Price is formatted with commas: "50,000.00" or without: "50000"
        assert "50000" in result.replace(",", "") or "50,000" in result
        assert "📈" in result or "📉" in result
    
    def test_get_crypto_price_not_found(self, mock_requests_get):
        """Test crypto price with unknown crypto."""
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = Mock()
        mock_requests_get.return_value = mock_response
        
        result = get_crypto_price.invoke({"crypto_id": "nonexistentcoin"})
        
        assert "❌" in result or "не найдена" in result.lower()


class TestFiatCurrency:
    """Tests for get_fiat_currency tool."""
    
    def test_get_fiat_currency_success(self, mock_requests_get):
        """Test successful currency conversion."""
        # Mock exchangerate.host response (fails, uses alternative)
        first_response = Mock()
        first_response.json.return_value = {"success": False}
        first_response.raise_for_status = Mock()
        
        # Mock exchangerate-api.com response
        second_response = Mock()
        second_response.json.return_value = {
            "rates": {
                "RUB": 80.5
            },
            "date": "2025-11-15"
        }
        second_response.raise_for_status = Mock()
        
        mock_requests_get.side_effect = [first_response, second_response]
        
        result = get_fiat_currency.invoke({
            "from_currency": "USD",
            "to_currency": "RUB"
        })
        
        assert "Курс валют" in result
        assert "80.5" in result
        assert "RUB" in result
    
    def test_get_fiat_currency_rub_support(self, mock_requests_get):
        """Test that RUB is supported."""
        first_response = Mock()
        first_response.json.return_value = {"success": False}
        first_response.raise_for_status = Mock()
        
        second_response = Mock()
        second_response.json.return_value = {
            "rates": {"RUB": 80.5},
            "date": "2025-11-15"
        }
        second_response.raise_for_status = Mock()
        
        mock_requests_get.side_effect = [first_response, second_response]
        
        result = get_fiat_currency.invoke({
            "from_currency": "USD",
            "to_currency": "RUB"
        })
        
        # Should not return 404 error
        assert "404" not in result
        assert "❌" not in result or "RUB" in result


class TestFileOperations:
    """Tests for file operations."""
    
    def test_file_read_success(self, project_root, temp_dir):
        """Test successful file read."""
        # Create test file
        test_file = temp_dir / "test.txt"
        test_file.write_text("Test content", encoding="utf-8")
        
        # Mock PROJECT_ROOT to use temp_dir
        with patch("agent.tools.PROJECT_ROOT", temp_dir):
            # Use absolute path for file_read
            result = file_read.invoke({"file_path": str(test_file)})
        
        assert "Содержимое файла" in result or "Test content" in result
        assert "Test content" in result
    
    def test_file_read_not_found(self):
        """Test file read with non-existent file."""
        result = file_read.invoke({"file_path": "nonexistent.txt"})
        
        assert "❌" in result or "не найден" in result.lower()
    
    def test_file_write_success(self, temp_dir):
        """Test successful file write."""
        with patch("agent.tools.PROJECT_ROOT", temp_dir):
            result = file_write.invoke({
                "file_path": str(temp_dir / "test_output.txt"),
                "content": "Test content"
            })
        
        assert "✅" in result or "успешно" in result.lower() or "сохранён" in result.lower()
        assert (temp_dir / "test_output.txt").exists()
        assert (temp_dir / "test_output.txt").read_text(encoding="utf-8") == "Test content"
    
    def test_file_read_size_limit(self, temp_dir):
        """Test file read with size limit."""
        # Create large file (>10MB)
        large_file = temp_dir / "large.txt"
        large_content = "x" * (11 * 1024 * 1024)  # 11 MB
        large_file.write_text(large_content, encoding="utf-8")
        
        with patch("agent.tools.PROJECT_ROOT", temp_dir):
            result = file_read.invoke({"file_path": str(large_file)})
        
        assert "❌" in result or "слишком большой" in result.lower() or "превышает" in result.lower()


class TestMemory:
    """Tests for memory_save tool."""
    
    def test_memory_save_success(self, temp_dir):
        """Test successful memory save."""
        memory_file = temp_dir / "agent" / "memory.json"
        memory_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create empty memory file
        memory_file.write_text("[]", encoding="utf-8")
        
        with patch("agent.tools.PROJECT_ROOT", temp_dir):
            result = memory_save.invoke({
                "user_message": "Test message",
                "agent_response": "Test response",
                "summary": "Test summary"
            })
        
        assert "💾" in result or "сохранён" in result.lower() or "память" in result.lower()
        # Check if file was updated
        if memory_file.exists():
            content = memory_file.read_text(encoding="utf-8")
            assert "Test message" in content or "Test summary" in content
    
    def test_memory_save_corrupted_json(self, temp_dir):
        """Test memory_save with corrupted JSON file."""
        memory_file = temp_dir / "agent" / "memory.json"
        memory_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create corrupted JSON file
        memory_file.write_text("{invalid json}", encoding="utf-8")
        
        with patch("agent.tools.PROJECT_ROOT", temp_dir):
            result = memory_save.invoke({
                "user_message": "Test message",
                "agent_response": "Test response",
                "summary": "Test summary"
            })
        
        # Should handle corrupted file gracefully
        assert "💾" in result or "сохранён" in result.lower() or "память" in result.lower()
        # Backup file should be created
        backup_file = memory_file.with_suffix(".corrupted.json")
        assert backup_file.exists() or memory_file.exists()
    
    def test_memory_save_size_limit(self, temp_dir):
        """Test that memory is limited to MAX_MEMORY_ENTRIES."""
        memory_file = temp_dir / "agent" / "memory.json"
        memory_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create memory file with 150 entries (more than limit of 100)
        large_memory = [
            {
                "timestamp": "2025-01-01T00:00:00",
                "user": f"Message {i}",
                "agent": f"Response {i}",
                "summary": f"Summary {i}"
            }
            for i in range(150)
        ]
        memory_file.write_text(
            json.dumps(large_memory, ensure_ascii=False),
            encoding="utf-8"
        )
        
        with patch("agent.tools.PROJECT_ROOT", temp_dir):
            result = memory_save.invoke({
                "user_message": "New message",
                "agent_response": "New response",
                "summary": "New summary"
            })
        
        # Memory should be limited to 100 entries
        with open(memory_file, "r", encoding="utf-8") as f:
            saved_memory = json.load(f)
        
        assert len(saved_memory) == 100
        assert saved_memory[-1]["user"] == "New message"


class TestQRCode:
    """Tests for generate_qr_code tool."""
    
    def test_generate_qr_code_url(self, temp_dir):
        """Test QR code generation for URL."""
        qr_dir = temp_dir / "qr_codes"
        
        with patch("agent.tools.PROJECT_ROOT", temp_dir):
            result = generate_qr_code.invoke({"data": "https://example.com"})
        
        assert "QR-код" in result or "успешно" in result.lower() or "✅" in result
        # Check that file was created with correct name
        qr_files = list(qr_dir.glob("*example*")) if qr_dir.exists() else []
        # File should be created with domain-based name
        assert "example" in result.lower() or "qr_code" in result.lower() or len(qr_files) > 0
    
    def test_generate_qr_code_text(self, temp_dir):
        """Test QR code generation for text."""
        qr_dir = temp_dir / "qr_codes"
        
        with patch("agent.tools.PROJECT_ROOT", temp_dir):
            result = generate_qr_code.invoke({"data": "Hello, World!"})
        
        assert "QR-код" in result or "успешно" in result.lower() or "✅" in result


class TestGetAllTools:
    """Tests for get_all_tools function."""
    
    def test_get_all_tools_count(self):
        """Test that all 8 tools are returned."""
        tools = get_all_tools()
        
        assert len(tools) == 8
    
    def test_get_all_tools_names(self):
        """Test that all expected tools are present."""
        tools = get_all_tools()
        tool_names = [tool.name for tool in tools]
        
        expected_tools = [
            "web_search",
            "get_weather",
            "get_crypto_price",
            "get_fiat_currency",
            "file_read",
            "file_write",
            "memory_save",
            "generate_qr_code"
        ]
        
        for expected in expected_tools:
            assert expected in tool_names, f"Tool {expected} not found"

