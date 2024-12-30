import os
from dotenv import load_dotenv

load_dotenv()

#  OpenAI API key
API_KEY = os.getenv("OPENAI_API_KEY")
STATIC_TOKEN = os.getenv("STATIC_TOKEN")
