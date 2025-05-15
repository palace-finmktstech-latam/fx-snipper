import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    API_PORT = int(os.getenv("API_PORT", 5008))
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

    # Logging Configuration
    LOGGING_API_URL = os.getenv("LOGGING_API_URL", "http://localhost:8001/api/")
    
settings = Settings()