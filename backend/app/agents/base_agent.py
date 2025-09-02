import google.generativeai as genai

class BaseAgent:
    """
    Base class for all agents. Handles LLM model initialization.
    """
    def __init__(self, api_key):
        if not api_key:
            raise ValueError("API key must be provided.")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash-latest')

    async def _call_llm(self, prompt):
        """
        Private method to call the Gemini LLM with a given prompt.
        """
        response = await self.model.generate_content_async(prompt)
        return response.text
