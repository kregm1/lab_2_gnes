import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler

from config import config
from knowledge_base import KnowledgeBase
from yandex_gpt import yandex_gpt
from utils import check_message_limit, analyze_sentiment, is_on_topic

logger = logging.getLogger(__name__)

SELECTING_ACTION, GIVING_FEEDBACK, ADDING_QUESTION = range(3)


class BotHandlers:
    def __init__(self, knowledge_base: KnowledgeBase):
        self.knowledge_base = knowledge_base

    def start(self, update: Update) -> None:
        user = update.effective_user
        update.message.reply_text(
            f"Привет, {user.first_name}! Я бот для анализа систем мониторинга онлайн-активности.\n"
            "Я могу ответить на вопросы по темам:\n"
            "- Мониторинг онлайн-активности сотрудников\n"
            "- Оценка рисков безопасности\n"
            "- Анализ угроз с помощью NLP\n"
            "- Инструменты для разработки таких систем\n\n"
            "Задайте ваш вопрос или введите /help для списка команд."
        )

    def help_command(self, update: Update) -> None:
        help_text = """
Доступные команды:
/start - начать работу с ботом
/help - показать это сообщение
/feedback - оставить обратную связь
/add_question - добавить новый вопрос и ответ (только для администраторов)

Я отвечаю на вопросы по теме мониторинга онлайн-активности для оценки рисков безопасности.
"""
        update.message.reply_text(help_text)

    def handle_message(self, update: Update) -> None:
        user_id = update.effective_user.id

        if not check_message_limit(user_id):
            update.message.reply_text(
                f"Извините, вы можете отправлять сообщения не чаще 1 раза в {config.MESSAGE_LIMIT_SECONDS} секунд."
            )
            return

        user_question = update.message.text
        logger.info(f"User {user_id} asked: {user_question}")

        if not is_on_topic(user_question):
            update.message.reply_text(
                "Извините, я могу отвечать только на вопросы по теме мониторинга онлайн-активности "
                "и оценки рисков безопасности. Пожалуйста, задайте вопрос по этой теме."
            )
            return

        sentiment = analyze_sentiment(user_question)
        logger.info(f"Question sentiment: {sentiment}")

        answer, ratio = self.knowledge_base.find_answer(user_question)

        if answer and ratio > config.SIMILARITY_THRESHOLD:
            update.message.reply_text(answer)
            self._request_feedback(update, answer)
        else:
            update.message.reply_text("Ищу ответ...")
            yandex_response = yandex_gpt.ask(user_question)

            if yandex_response:
                update.message.reply_text(yandex_response)

                if user_id in config.ADMIN_IDS:
                    self._ask_to_save(update , user_question , yandex_response)

                self._request_feedback(update , yandex_response)
            else:
                update.message.reply_text("Извините, не удалось получить ответ. Попробуйте позже.")

    def _ask_to_save(self , update: Update , question: str , answer: str) -> None:
        keyboard = [
            [InlineKeyboardButton("Сохранить" , callback_data=f'save_{question}_{answer[:50]}')] ,
            [InlineKeyboardButton("Не сохранять" , callback_data='dont_save')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text("Сохранить этот вопрос и ответ в базу знаний?" , reply_markup=reply_markup)

    def feedback_handler(self, update: Update) -> None:
        query = update.callback_query
        query.answer()

        data_parts = query.data.split('_')
        feedback_type = data_parts[1]
        answer_snippet = data_parts[2] if len(data_parts) > 2 else ""
        user_id = query.from_user.id

        logger.info(f"Feedback from {user_id}: {feedback_type}")
        query.edit_message_text("Спасибо за оценку!")

    def save_question_handler(self, update: Update) -> None:
        query = update.callback_query
        query.answer()

        if query.data == 'dont_save':
            query.edit_message_text("Хорошо, не сохраняем.")
            return

        data_parts = query.data.split('_')
        if len(data_parts) < 3:
            query.edit_message_text("Ошибка обработки.")
            return

        question = '_'.join(data_parts[1:-1])
        full_answer = query.message.reply_to_message.text

        self.knowledge_base.add_question_answer(question, full_answer)
        query.edit_message_text("Вопрос и ответ сохранены!")

    def feedback_command(self, update: Update) -> int:
        user_id = update.effective_user.id

        if not check_message_limit(user_id):
            update.message.reply_text(f"Подождите {config.MESSAGE_LIMIT_SECONDS} секунд.")
            return ConversationHandler.END

        update.message.reply_text("Напишите ваши предложения по улучшению:")
        return GIVING_FEEDBACK

    def receive_feedback(self, update: Update) -> int:
        feedback = update.message.text
        user_id = update.effective_user.id

        logger.info(f"Feedback from {user_id}: {feedback}")
        update.message.reply_text("Спасибо за обратную связь!")
        return ConversationHandler.END

    def add_question_command(self, update: Update) -> int:
        user_id = update.effective_user.id

        if not check_message_limit(user_id):
            update.message.reply_text(f"Подождите {config.MESSAGE_LIMIT_SECONDS} секунд.")
            return ConversationHandler.END

        if user_id not in config.ADMIN_IDS:
            update.message.reply_text("Эта команда только для администраторов.")
            return ConversationHandler.END

        update.message.reply_text(
            "Введите вопрос и ответ через '|'.\n"
            "Пример: Как работает анализ? | Анализ использует NLP для обработки текста."
        )
        return ADDING_QUESTION

    def receive_question_answer(self, update: Update) -> int:
        user_id = update.effective_user.id
        text = update.message.text

        if not check_message_limit(user_id):
            update.message.reply_text(f"Подождите {config.MESSAGE_LIMIT_SECONDS} секунд.")
            return ADDING_QUESTION

        if '|' not in text:
            update.message.reply_text("Используйте '|' для разделения вопроса и ответа.")
            return ADDING_QUESTION

        question, answer = [part.strip() for part in text.split('|', 1)]
        self.knowledge_base.add_question_answer(question, answer)

        update.message.reply_text(
            f"Добавлено в базу знаний:\nВопрос: {question}\nОтвет: {answer}"
        )
        return ConversationHandler.END

    def cancel(self, update: Update) -> int:
        update.message.reply_text("Отменено.")
        return ConversationHandler.END

    def error(self, context: CallbackContext) -> None:
        logger.warning(f'Error: {context.error}')
