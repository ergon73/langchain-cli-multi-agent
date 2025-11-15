"""Entry point for the Personal AI Multitool Assistant CLI.

Author: Георгий Белянин (Georgy Belyanin)
Email: georgy.belyanin@gmail.com
GitHub: https://github.com/ergon73/langchain-cli-multi-agent
"""

import logging
import os
import sys
from pathlib import Path

import colorama
from dotenv import load_dotenv

from agent.agent import create_agent

# Initialize colorama for Windows support
colorama.init(autoreset=True)

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("agent.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main CLI entry point."""
    # Load environment variables
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logger.info("Loaded .env file")
    else:
        logger.warning(
            ".env file not found. Please create it from .env.example"
        )
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print(
            colorama.Fore.RED +
            "❌ Ошибка: OPENAI_API_KEY не найден в .env файле!\n"
            "Создайте файл .env на основе .env.example и добавьте ваш API ключ."
        )
        sys.exit(1)
    
    # Print welcome message
    print(colorama.Fore.CYAN + "=" * 60)
    print(colorama.Fore.CYAN + "🤖 Personal AI Multitool Assistant")
    print(colorama.Fore.CYAN + "=" * 60)
    print(
        colorama.Fore.CYAN +
        "\nДоступные возможности:\n"
        "  🔍 Поиск в интернете\n"
        "  🌤️  Погода для любого города\n"
        "  💰 Курсы криптовалют\n"
        "  💱 Конвертация валют\n"
        "  📁 Работа с файлами\n"
        "  🎨 Генерация QR-кодов\n"
        "  💾 Сохранение в память\n"
    )
    print(colorama.Fore.CYAN + "Введите '/exit' или '/quit' для выхода\n")
    
    try:
        # Create agent
        logger.info("Initializing agent...")
        agent = create_agent()
        logger.info("Agent initialized successfully")
        
        # Main loop
        while True:
            try:
                # Get user input
                user_input = input(
                    colorama.Fore.YELLOW + "Вы: " + colorama.Fore.RESET
                ).strip()
                
                if not user_input:
                    continue
                
                # Check for exit commands
                if user_input.lower() in ["/exit", "/quit", "exit", "quit"]:
                    print(colorama.Fore.CYAN + "\n👋 До свидания!")
                    break
                
                # Check for help command
                if user_input.lower() in ["/help", "help", "помощь"]:
                    print(
                        colorama.Fore.CYAN +
                        "\n📖 Доступные команды:\n"
                        "  /exit, /quit - Выход из программы\n"
                        "  /help - Показать эту справку\n"
                        "\nПримеры запросов:\n"
                        "  - Какая погода в Москве?\n"
                        "  - Найди информацию о Python\n"
                        "  - Какой курс биткоина?\n"
                        "  - Сколько стоит 100 USD в RUB?\n"
                        "  - Прочитай файл README.md\n"
                        "  - Создай QR-код для https://example.com\n"
                    )
                    continue
                
                # Invoke agent
                logger.info(f"User query: {user_input}")
                print(colorama.Fore.CYAN + "\n🤖 Ассистент думает...\n")
                
                response = agent.invoke({"input": user_input})
                agent_response = response.get("output", "Нет ответа")
                
                print(colorama.Fore.GREEN + f"🤖 Ассистент: {agent_response}\n")
                logger.info("Agent response generated")
            
            except KeyboardInterrupt:
                print(colorama.Fore.CYAN + "\n\n👋 До свидания!")
                break
            
            except Exception as e:
                error_msg = f"Ошибка: {str(e)}"
                print(colorama.Fore.RED + f"❌ {error_msg}\n")
                logger.error(f"Error in main loop: {error_msg}", exc_info=True)
    
    except Exception as e:
        error_msg = f"Критическая ошибка: {str(e)}"
        print(colorama.Fore.RED + f"❌ {error_msg}")
        logger.critical(error_msg, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

