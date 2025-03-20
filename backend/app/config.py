import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    API_PORT = int(os.getenv("API_PORT", 5001))
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    
settings = Settings()