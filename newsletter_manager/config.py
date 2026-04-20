import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    GMAIL_CREDENTIALS_FILE: str = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
    GMAIL_TOKEN_FILE: str = os.getenv("GMAIL_TOKEN_FILE", "token.json")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    DIGEST_RECIPIENT: str = os.getenv("DIGEST_RECIPIENT", "")
    DIGEST_TIME: str = os.getenv("DIGEST_TIME", "07:00")
    TIMEZONE: str = os.getenv("TIMEZONE", "America/New_York")
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "newsletters.db")
    SUBSCRIPTION_EMAIL: str = os.getenv("SUBSCRIPTION_EMAIL", "annejin2021+subs@gmail.com")
    GMAIL_LABEL_PREFIX: str = os.getenv("GMAIL_LABEL_PREFIX", "Newsletters")


config = Config()
