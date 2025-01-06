import os
from dotenv import load_dotenv

load_dotenv()

#  OpenAI API key
API_KEY = os.getenv("OPENAI_API_KEY")
STATIC_TOKEN = os.getenv("STATIC_TOKEN")

MONGO_CLUSTER_URI = os.getenv("MONGO_CLUSTER_URI")
MONGO_DATABASE = os.getenv("MONGO_DATABASE", "AutoRFP")
