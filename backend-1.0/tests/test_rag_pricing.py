import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# 将 backend 目录添加到 Python 路径中
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.pipeline import generate_llm_response

class TestRAGPricingConstraints(unittest.IsolatedAsyncioTestCase):
    
    @patch("app.services.pipeline.OpenAI")
    @patch("app.services.pipeline.settings")
    @patch("app.services.pipeline.get_scene")
    async def test_generate_llm_response_rag_constraints(self, mock_get_scene, mock_settings, mock_openai_class):
        # Setup settings to simulate valid API key
        mock_settings.DEEPSEEK_API_KEY = "test-key"
        mock_settings.DEEPSEEK_BASE_URL = "https://api.deepseek.com"
        mock_settings.DEEPSEEK_MODEL = "deepseek-chat"
        mock_settings.XIAOMI_API_KEY = None
        mock_settings.OPENAI_API_KEY = None
        
        # Setup scene mocks
        mock_scene_ordering = MagicMock()
        mock_scene_ordering.category = "ordering"
        mock_scene_ordering.name = "繁忙咖啡厅点餐 (Cafe Ordering)"
        mock_scene_ordering.get_system_prompt.return_value = "Barista prompt"
        mock_scene_ordering.get_evaluation_rules.return_value = "Rules"
        
        mock_scene_meeting = MagicMock()
        mock_scene_meeting.category = "meeting"
        mock_scene_meeting.name = "产品发布会同步会议 (Business Meeting)"
        mock_scene_meeting.get_system_prompt.return_value = "Manager prompt"
        mock_scene_meeting.get_evaluation_rules.return_value = "Rules"

        mock_scene_interview = MagicMock()
        mock_scene_interview.category = "interview"
        mock_scene_interview.name = "软件工程师面试 (Job Interview)"
        mock_scene_interview.get_system_prompt.return_value = "Sarah prompt (Interviewer)"
        mock_scene_interview.get_evaluation_rules.return_value = "Rules"
        
        # Setup mock OpenAI client
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content='{"reply": "Hello", "grammar_correction": {"original": "hello", "corrected": "Hello", "explanation": "Ok"}}'))]
        mock_client.chat.completions.create.return_value = mock_response

        # Test Cafe Scene Pricing Constraints
        mock_get_scene.return_value = mock_scene_ordering
        await generate_llm_response(
            scene_id="ordering",
            user_text="I'd like a large latte",
            rag_context="Grande Latte: $3.75, Oat Milk: +$0.60",
            conversation_history=[]
        )
        
        # Verify the messages sent to the model
        args, kwargs = mock_client.chat.completions.create.call_args
        messages = kwargs["messages"]
        rag_message = [msg for msg in messages if msg["role"] == "system" and "[Scene Reference Knowledge Base" in msg["content"]][0]
        
        self.assertIn("CRITICAL PRICE CONSTRAINT", rag_message["content"])
        self.assertIn("calculate the total price mathematically", rag_message["content"])
        self.assertIn("As the barista/cashier", rag_message["content"])

        # Test Meeting Scene RAG prompt
        mock_get_scene.return_value = mock_scene_meeting
        await generate_llm_response(
            scene_id="meeting",
            user_text="status update",
            rag_context="Frontend delayed by 2 days",
            conversation_history=[]
        )
        args, kwargs = mock_client.chat.completions.create.call_args
        messages = kwargs["messages"]
        rag_message = [msg for msg in messages if msg["role"] == "system" and "[Scene Reference Knowledge Base" in msg["content"]][0]
        
        self.assertIn("As the chairperson or colleague", rag_message["content"])
        self.assertNotIn("CRITICAL PRICE CONSTRAINT", rag_message["content"])

        # Test Interview Scene RAG prompt
        mock_get_scene.return_value = mock_scene_interview
        await generate_llm_response(
            scene_id="interview",
            user_text="hello Sarah",
            rag_context="React Native experience",
            conversation_history=[]
        )
        args, kwargs = mock_client.chat.completions.create.call_args
        messages = kwargs["messages"]
        rag_message = [msg for msg in messages if msg["role"] == "system" and "[Scene Reference Knowledge Base" in msg["content"]][0]
        
        self.assertIn("As the interviewer", rag_message["content"])
        self.assertNotIn("CRITICAL PRICE CONSTRAINT", rag_message["content"])

if __name__ == "__main__":
    unittest.main()
