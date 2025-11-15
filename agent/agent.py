"""Main agent logic using LangChain."""

import logging
import os

from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from .tools import get_all_tools

# Configure logging
logger = logging.getLogger(__name__)


def create_agent() -> AgentExecutor:
    """
    Create and configure the LangChain agent.
    
    Returns:
        Configured AgentExecutor instance
    """
    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in .env")
    
    # Get model from environment or use default
    # gpt-4o-mini: faster, cheaper, good for most tasks
    # gpt-4o: smarter, more capable, but slower and more expensive
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    logger.info(f"Creating agent with model: {model_name}")
    
    # Initialize LLM
    llm = ChatOpenAI(
        model=model_name,
        temperature=0.7,
        api_key=api_key
    )
    
    # System prompt in Russian
    system_prompt = (
        "Ты — полезный AI-ассистент с доступом к различным инструментам.\n"
        "Ты можешь:\n"
        "- 🔍 Искать информацию в интернете\n"
        "- 🌤️ Узнавать погоду в любом городе\n"
        "- 💰 Проверять курсы криптовалют\n"
        "- 💱 Конвертировать валюты\n"
        "- 📁 Читать и записывать файлы (file_read, file_write)\n"
        "- 🎨 Создавать QR-коды\n"
        "- 💾 Сохранять важные разговоры в память (memory_save)\n\n"
        "ВАЖНО:\n"
        "- Если пользователь просит сохранить диалог или текст в ФАЙЛ, "
        "используй инструмент file_write, а НЕ memory_save\n"
        "- Если пользователь просит сохранить в память для запоминания, "
        "используй memory_save\n"
        "- Если пользователь просит сохранить 'этот разговор', 'наш диалог' "
        "или 'важные моменты разговора' в ПАМЯТЬ (не в файл), "
        "используй memory_save с последним сообщением пользователя и твоим ответом. "
        "Не проси уточнений - просто сохрани текущий обмен сообщениями.\n"
        "- При создании QR-кода для URL НЕ указывай filename - функция сама "
        "сгенерирует уникальное имя на основе домена\n\n"
        "Всегда отвечай на русском языке. "
        "Будь дружелюбным и полезным. "
        "Внимательно читай запросы пользователя и используй правильные инструменты."
    )
    
    # Create prompt template
    # chat_history is now included to support conversation context
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])
    
    # Get all tools
    tools = get_all_tools()
    logger.info(f"Loaded {len(tools)} tools")
    
    # Create agent
    agent = create_openai_functions_agent(llm, tools, prompt)
    
    # Create agent executor
    # Note: Memory is handled through MessagesPlaceholder in prompt
    # Chat history should be passed in invoke() call
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=10
    )
    
    logger.info("Agent created successfully")
    return agent_executor

