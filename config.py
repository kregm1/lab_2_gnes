import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent


class Config:
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    YANDEX_API_KEY = os.getenv('YANDEX_API_KEY')
    YANDEX_FOLDER_ID = os.getenv('YANDEX_FOLDER_ID')

    ADMIN_IDS = [int(id_str) for id_str in os.getenv('ADMIN_IDS' , '').split(',') if id_str]

    KNOWLEDGE_BASE_FILE = BASE_DIR / "knowledge_base.json"
    SIMILARITY_THRESHOLD = 0.7
    MESSAGE_LIMIT_SECONDS = 10
    TOPIC_KEYWORDS = [
        "мониторинг" , "активность" , "безопасность" , "риск" , "сотрудник" ,
        "анализ" , "NLP" , "угроза" , "информация" , "конфиденциальность"
    ]
    SYSTEM_PROMPT = """Ты - эксперт по системам мониторинга онлайн-активности для оценки рисков безопасности. 
    Отвечай только на вопросы по этой теме. Отвечай кратко и точно на русском языке. 
    Если вопрос не по теме, вежливо сообщи, что не можешь помочь."""
    YANDEX_GPT_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"


    @classmethod
    def validate (cls):
        required = ['TELEGRAM_TOKEN' , 'YANDEX_API_KEY' , 'YANDEX_FOLDER_ID']
        for var in required:
            if not getattr(cls , var):
                raise ValueError(f"Не задана обязательная переменная: {var}")


config = Config()
Config.validate()
