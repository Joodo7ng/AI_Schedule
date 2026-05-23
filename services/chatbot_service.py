
import os
from openai import OpenAI
from dotenv import load_dotenv
from rag_functions import get_rag_answer


load_dotenv()

def get_chatbot_answer(user_message):
    return get_rag_answer(user_message)

#실제 ai호출은 ragFuction.py에서 하는중