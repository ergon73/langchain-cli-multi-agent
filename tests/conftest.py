"""Pytest configuration and fixtures."""

import os
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

# Set test environment variables
os.environ["OPENAI_API_KEY"] = "test-api-key"
os.environ["OPENAI_MODEL"] = "gpt-4o-mini"
os.environ["LOG_LEVEL"] = "DEBUG"


@pytest.fixture
def project_root():
    """Return project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def temp_dir(tmp_path):
    """Create temporary directory for tests."""
    return tmp_path


@pytest.fixture
def mock_requests_get():
    """Mock requests.get for API calls."""
    with patch("requests.get") as mock_get:
        yield mock_get


@pytest.fixture
def mock_requests_post():
    """Mock requests.post for API calls."""
    with patch("requests.post") as mock_post:
        yield mock_post


@pytest.fixture
def mock_ddgs():
    """Mock DuckDuckGo search."""
    # Try to patch DDGS from ddgs, fallback to duckduckgo_search
    try:
        with patch("agent.tools.DDGS") as mock_ddgs:
            yield mock_ddgs
    except AttributeError:
        with patch("ddgs.DDGS") as mock_ddgs:
            yield mock_ddgs


@pytest.fixture
def sample_weather_data():
    """Sample weather API response."""
    return {
        "current": {
            "temperature_2m": 10.5,
            "wind_speed_10m": 5.2,
            "weather_code": 61
        },
        "daily": {
            "time": ["2025-11-15", "2025-11-16"],
            "temperature_2m_max": [12.0, 8.0],
            "temperature_2m_min": [5.0, 2.0],
            "weather_code": [61, 3]
        }
    }


@pytest.fixture
def sample_geocode_data():
    """Sample geocoding API response."""
    return {
        "results": [
            {
                "name": "Moscow",
                "latitude": 55.7558,
                "longitude": 37.6173,
                "country": "Russia",
                "country_code": "RU"
            }
        ]
    }

