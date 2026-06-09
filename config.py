import os
from dotenv import load_dotenv

# Cargar variables de entorno desde un archivo .env si existe
load_dotenv()

class Config:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    DATABASE_URL = os.getenv("DATABASE_URL")

    @staticmethod
    def validate():
        if not Config.TELEGRAM_TOKEN:
            raise ValueError("No se ha configurado TELEGRAM_TOKEN en las variables de entorno.")
        if not Config.DATABASE_URL:
            raise ValueError("No se ha configurado DATABASE_URL en las variables de entorno.")

config = Config()
