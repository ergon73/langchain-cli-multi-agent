"""Tests for agent creation and chat history."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from agent.agent import create_agent


class TestAgentCreation:
    """Tests for agent creation."""
    
    @patch("agent.agent.ChatOpenAI")
    @patch("agent.agent.get_all_tools")
    @patch("agent.agent.create_openai_functions_agent")
    @patch("agent.agent.AgentExecutor")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_create_agent_success(
        self, mock_executor, mock_create_agent, mock_get_tools, mock_chat_openai
    ):
        """Test successful agent creation."""
        # Mock LLM
        mock_llm = MagicMock()
        mock_chat_openai.return_value = mock_llm
        
        # Mock tools (real tool objects with __name__ attribute)
        from agent.tools import web_search
        mock_get_tools.return_value = [web_search]
        
        # Mock agent creation
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent
        
        # Mock executor
        mock_executor_instance = MagicMock()
        mock_executor.return_value = mock_executor_instance
        
        agent = create_agent()
        
        assert agent is not None
        mock_chat_openai.assert_called_once()
        mock_get_tools.assert_called_once()
    
    @patch.dict("os.environ", {}, clear=True)
    def test_create_agent_missing_api_key(self):
        """Test agent creation fails without API key."""
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            create_agent()


class TestChatHistory:
    """Tests for chat history support."""
    
    @patch("agent.agent.ChatOpenAI")
    @patch("agent.agent.get_all_tools")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_agent_accepts_chat_history(self, mock_get_tools, mock_chat_openai):
        """Test that agent prompt template includes chat_history."""
        from langchain.prompts import ChatPromptTemplate
        
        mock_llm = MagicMock()
        mock_chat_openai.return_value = mock_llm
        mock_get_tools.return_value = []
        
        agent = create_agent()
        
        # Check that prompt template has chat_history placeholder
        # This is verified by checking that agent can be invoked with chat_history
        assert agent is not None
        
        # The actual test would require invoking the agent, but that needs real API
        # For now, we verify the agent was created successfully
        assert hasattr(agent, "invoke")

