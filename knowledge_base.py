import json
import logging
from typing import Dict, List
from pathlib import Path

logger = logging.getLogger(__name__)


class KnowledgeBase:
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.base = self._initialize_knowledge_base()

    def _initialize_knowledge_base(self) -> Dict[str, List[str]]:
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)

            if not self.file_path.exists():
                example_data = {
                    "Пример ответа": ["Пример вопроса 1", "Пример вопроса 2"]
                }
                with open(self.file_path, 'w', encoding='utf-8') as f:
                    json.dump(example_data, f, ensure_ascii=False, indent=2)
                return example_data

            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        except Exception as e:
            logger.error(f"Ошибка инициализации базы знаний: {e}")
            return {}

    def save(self):
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.base, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения базы знаний: {e}")

    def find_answer(self, user_question: str) -> tuple:
        try:
            for answer, questions in self.base.items():
                for question in questions:
                    if self._is_similar(question, user_question):
                        return answer, 1.0
            return None, 0.0
        except Exception as e:
            logger.error(f"Ошибка поиска ответа: {e}")
            return None, 0.0

    def add_question_answer(self, question: str, answer: str):
        try:
            question = question.strip()
            answer = answer.strip()

            if not question or not answer:
                return

            if answer in self.base:
                if question not in self.base[answer]:
                    self.base[answer].append(question)
            else:
                self.base[answer] = [question]

            self.save()
            logger.info(f"Автосохранение: Q: {question[:50]}... | A: {answer[:50]}...")
        except Exception as e:
            logger.error(f"Ошибка автосохранения: {e}")

    @staticmethod
    def _is_similar(a: str, b: str) -> bool:
        return a.lower().strip() == b.lower().strip()
