import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
class AIChatbot:
    def __init__(self):
        api_key = os.getenv("OPENROUTER_API_KEY")

        # Create client with OpenRouter base URL
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        self.model = "meta-llama/llama-3.1-405b-instruct:free"

    def explain_term(self, term):
        prompt = f"Explain the term '{term}' in one concise paragraph. Do not include reasoning steps, lists, or meta-commentary — only give the final explanation."
        response = self.client.chat.completions.create(
        model=self.model,
        messages=[
            {"role": "system", "content": "You are a helpful tutor. Always respond with a single clear explanatory paragraph, without showing reasoning or internal thoughts."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=150,
        temperature=0.5,
        )
        explanation = response.choices[0].message.content.strip()
        
        return explanation
    
    def generate_test(self, prompt):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=1024,
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()