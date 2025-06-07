import time
from typing import Dict
from textblob import TextBlob
from textblob.exceptions import NotTranslated

from config import config

user_last_message_time: Dict[int, float] = {}


def check_message_limit(user_id: int) -> bool:
    current_time = time.time()
    last_message_time = user_last_message_time.get(user_id, 0)

    if current_time - last_message_time < config.MESSAGE_LIMIT_SECONDS:
        return False

    user_last_message_time[user_id] = current_time
    return True


def analyze_sentiment(text: str) -> str:
    try:
        analysis = TextBlob(text)
        if analysis.sentiment.polarity > 0.1:
            return "positive"
        elif analysis.sentiment.polarity < -0.1:
            return "negative"
        return "neutral"
    except NotTranslated:
        return "neutral"
    except Exception as e:
        print(f"Error analyzing sentiment: {e}")
        return "neutral"


def is_on_topic(question: str) -> bool:
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in config.TOPIC_KEYWORDS)
