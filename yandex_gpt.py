import logging
import requests
from typing import Optional

from config import config

logger = logging.getLogger(__name__)


class YandexGPT:
    def __init__(self):
        self.api_key = config.YANDEX_API_KEY
        self.folder_id = config.YANDEX_FOLDER_ID
        self.url = config.YANDEX_GPT_URL
        self.system_prompt = config.SYSTEM_PROMPT

    def ask(self, question: str) -> Optional[str]:
        try:
            headers = {
                "Authorization": f"Api-Key {self.api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "modelUri": f"gpt://{self.folder_id}/yandexgpt-lite",
                "completionOptions": {
                    "stream": False,
                    "temperature": 0.5,
                    "maxTokens": 1000
                },
                "messages": [
                    {
                        "role": "system",
                        "text": self.system_prompt
                    },
                    {
                        "role": "user",
                        "text": question
                    }
                ]
            }

            response = requests.post(
                self.url,
                headers=headers,
                json=data,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                return result['result']['alternatives'][0]['message']['text']
            else:
                logger.error(f"Yandex GPT API error: {response.status_code} - {response.text}")
                print(response.text)
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Request to Yandex GPT failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in Yandex GPT: {e}")
            return None


yandex_gpt = YandexGPT()
