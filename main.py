import logging
import os

from telegram.ext import(
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters
)

from config import config
from knowledge_base import KnowledgeBase
from yandex_gpt import yandex_gpt
from utils import check_message_limit, is_on_topic

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s' ,
    level=logging.INFO
)
logger = logging.getLogger(__name__)

SELECTING_ACTION , GIVING_FEEDBACK , ADDING_QUESTION = range(3)


class BotHandlers:
    def __init__ (self , knowledge_base: KnowledgeBase):
        self.knowledge_base = knowledge_base

    async def start(self, update):
        user = update.effective_user
        await update.message.reply_text(
            f"Привет, {user.first_name}! Я бот для анализа систем мониторинга онлайн-активности.\n"
            "Я могу ответить на вопросы по темам:\n"
            "- Мониторинг онлайн-активности сотрудников\n"
            "- Оценка рисков безопасности\n"
            "- Анализ угроз с помощью NLP\n"
            "- Инструменты для разработки таких систем\n\n"
            "Задайте ваш вопрос или введите /help для списка команд."
        )

    async def help_command(self, update):
        help_text = """
Доступные команды:
/start - начать работу с ботом
/help - показать это сообщение
/feedback - оставить обратную связь
/add_question - добавить новый вопрос и ответ (только для администраторов)

Я отвечаю на вопросы по теме мониторинга онлайн-активности для оценки рисков безопасности.
"""
        await update.message.reply_text(help_text)

    async def handle_message(self, update):
        user_id = update.effective_user.id

        if not check_message_limit(user_id):
            await update.message.reply_text(f"Подождите {config.MESSAGE_LIMIT_SECONDS} секунд.")
            return

        user_question = update.message.text
        logger.info(f"User {user_id} asked: {user_question}")

        if not is_on_topic(user_question):
            await update.message.reply_text("Я отвечаю только на вопросы по мониторингу активности.")
            return

        answer, ratio = self.knowledge_base.find_answer(user_question)

        if answer and ratio > config.SIMILARITY_THRESHOLD:
            await update.message.reply_text(answer)
        else:
            await update.message.reply_text("Ищу ответ...")
            yandex_response = yandex_gpt.ask(user_question)

            if yandex_response:
                await update.message.reply_text(yandex_response)
                self.knowledge_base.add_question_answer(user_question, yandex_response)
            else:
                await update.message.reply_text("Не удалось получить ответ.")

    async def feedback_handler(self, update):
        query = update.callback_query
        await query.answer()

        data_parts = query.data.split('_')
        feedback_type = data_parts[1]
        # answer_snippet = data_parts[2] if len(data_parts) > 2 else ""
        user_id = query.from_user.id

        logger.info(f"Feedback from {user_id}: {feedback_type}")
        await query.edit_message_text("Спасибо за оценку!")

    async def save_question_handler(self, update, context):
        query = update.callback_query
        await query.answer()

        if query.data == 'dont_save':
            await query.edit_message_text("Хорошо, не сохраняем.")
            return

        data_parts = query.data.split('_')
        if len(data_parts) < 3:
            await query.edit_message_text("Ошибка обработки.")
            return

        question = '_'.join(data_parts[1:-1])
        full_answer = query.message.reply_to_message.text

        self.knowledge_base.add_question_answer(question , full_answer)
        await query.edit_message_text("Вопрос и ответ сохранены!")
        context.user_data.pop('last_question' , None)
        context.user_data.pop('last_answer' , None)

    async def feedback_command(self, update):
        user_id = update.effective_user.id

        if not check_message_limit(user_id):
            await update.message.reply_text(f"Подождите {config.MESSAGE_LIMIT_SECONDS} секунд.")
            return ConversationHandler.END

        await update.message.reply_text("Напишите ваши предложения по улучшению:")
        return GIVING_FEEDBACK

    async def receive_feedback(self, update):
        feedback = update.message.text
        user_id = update.effective_user.id

        logger.info(f"Feedback from {user_id}: {feedback}")
        await update.message.reply_text("Спасибо за обратную связь!")
        return ConversationHandler.END

    async def add_question_command(self, update):
        user_id = update.effective_user.id

        if not check_message_limit(user_id):
            await update.message.reply_text(f"Подождите {config.MESSAGE_LIMIT_SECONDS} секунд.")
            return ConversationHandler.END

        if user_id not in config.ADMIN_IDS:
            await update.message.reply_text("Эта команда только для администраторов.")
            return ConversationHandler.END

        await update.message.reply_text(
            "Введите вопрос и ответ через '|'.\n"
            "Пример: Как работает анализ? | Анализ использует NLP для обработки текста."
        )
        return ADDING_QUESTION

    async def receive_question_answer(self, update):
        user_id = update.effective_user.id
        text = update.message.text

        if not check_message_limit(user_id):
            await update.message.reply_text(f"Подождите {config.MESSAGE_LIMIT_SECONDS} секунд.")
            return ADDING_QUESTION

        if '|' not in text:
            await update.message.reply_text("Используйте '|' для разделения вопроса и ответа.")
            return ADDING_QUESTION

        question, answer = [part.strip() for part in text.split('|' , 1)]
        self.knowledge_base.add_question_answer(question, answer)

        await update.message.reply_text(
            f"Добавлено в базу знаний:\nВопрос: {question}\nОтвет: {answer}"
        )
        return ConversationHandler.END

    async def show_db(self, update):
        try:
            if not self.knowledge_base.base:
                await update.message.reply_text("📚 База знаний пуста")
                return

            message = ["Содержимое базы знаний:"]
            for answer , questions in self.knowledge_base.base.items():
                message.append(f"\nОтвет: {answer}")
                message.append(f"\nВопросы: {', '.join(questions)}")

            full_message = "\n".join(message)
            await update.message.reply_text(full_message[:4000])

        except Exception as e:
            logger.error(f"Ошибка показа базы знаний: {e}")
            await update.message.reply_text("Временные проблемы с доступом к базе знаний")

    async def cancel(self, update):
        await update.message.reply_text("Отменено.")
        return ConversationHandler.END

    async def error_handler(self, update, context):
        logger.warning(f'Update {update} caused error {context.error}')


def main():
    if not os.path.exists(config.KNOWLEDGE_BASE_FILE):
        logger.info("Создаем новую базу знаний...")
        kb = KnowledgeBase(config.KNOWLEDGE_BASE_FILE)
        kb.save()

    knowledge_base = KnowledgeBase(config.KNOWLEDGE_BASE_FILE)
    bot_handlers = BotHandlers(knowledge_base)

    application = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start" , bot_handlers.start))
    application.add_handler(CommandHandler("help" , bot_handlers.help_command))
    application.add_handler(CallbackQueryHandler(bot_handlers.feedback_handler , pattern='^feedback_'))
    application.add_handler(CallbackQueryHandler(bot_handlers.save_question_handler , pattern='^save_|dont_save'))

    feedback_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('feedback' , bot_handlers.feedback_command)] ,
        states={
            GIVING_FEEDBACK: [MessageHandler(filters.TEXT & ~filters.COMMAND , bot_handlers.receive_feedback)] ,
        } ,
        fallbacks=[CommandHandler('cancel' , bot_handlers.cancel)] ,
    )
    application.add_handler(feedback_conv_handler)

    add_question_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('add_question' , bot_handlers.add_question_command)] ,
        states={
            ADDING_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND , bot_handlers.receive_question_answer)] ,
        } ,
        fallbacks=[CommandHandler('cancel' , bot_handlers.cancel)] ,
    )
    application.add_handler(add_question_conv_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND , bot_handlers.handle_message))
    application.add_handler(CommandHandler("show_db" , bot_handlers.show_db))
    application.add_error_handler(bot_handlers.error_handler)

    application.run_polling()

if __name__ == '__main__':
    main()
