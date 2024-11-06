from datetime import datetime

from langchain_openai import ChatOpenAI
import json5 as json
from backend.config import CurrentConfig
from langchain_community.adapters.openai import convert_openai_messages

sample_json = """
{
  "title": title of the article,
  "date": today's date,
  "paragraphs": [
    "paragraph 1",
    "paragraph 2",
    "paragraph 3",
    "paragraph 4",
    "paragraph 5",
    "paragraph 6",
    "paragraph 7",
    "paragraph 8",
    "paragraph 9",
    "paragraph 10"
    ],
    "summary": "2 sentences summary of the article"
}
"""

sample_revise_json = """
{
    "paragraphs": [
        "paragraph 1",
        "paragraph 2",
        "paragraph 3",
        "paragraph 4",
        "paragraph 5",
        "paragraph 6",
        "paragraph 7",
        "paragraph 8",
        "paragraph 9",
        "paragraph 10"
    ],
    "message": "message to the critique"
}
"""


class WriterAgent:
    def __init__(self, researchUuid: str):
        pass
        self.researchUuid = researchUuid

    def writer(self, query: str, sources: list):

        prompt = [{
            "role": "system",
            "content": "You are a highly respected and accomplished researcher in your field. Your task is to write a "
                       "high-quality, professional research paper on the provided topic, utilizing the given references. "
                       "Your paper should demonstrate deep understanding, critical analysis, and contribute meaningful "
                       "insights to the field. Ensure your writing is clear, thorough, and adheres to academic standards.\n"
        }, {
            "role": "user",
            "content": f"Today's date is {datetime.now().strftime('%d/%m/%Y')}\n."
                       f"Query or Topic: {query}"
                       f"{sources}\n"
                       f"Your task is to write a critically acclaimed article for me about the provided query or "
                       f"topic based on the sources.\n "
                       f"Please return nothing but a JSON in the following format:\n"
                       f"{sample_json}\n "

        }]

        lc_messages = convert_openai_messages(prompt)
        optional_params = {
            "response_format": {"type": "json_object"}
        }

        response = ChatOpenAI(model=CurrentConfig.OPENAI_CHAT_MODEL, max_retries=1, model_kwargs=optional_params).invoke(lc_messages).content
        return json.loads(response)

    def revise(self, article: dict):
        prompt = [{
            "role": "system",
            "content": "You are a highly qualified research editor and subject matter expert in the field of the provided topic. Your role is to critically review and enhance a research article, ensuring it meets the highest academic and professional standards. Your expertise allows you to provide insightful edits, suggest improvements in content and structure, and elevate the overall quality of the research. Please edit the article based on the given critique, focusing on accuracy, depth of analysis, and scholarly rigor.\n"
        }, {
            "role": "user",
            "content": f"{str(article)}\n"
                        f"Your task is to edit the article based on the critique given.\n "
                        f"Please return json format of the 'paragraphs' and a new 'message' field"
                        f"to the critique that explain your changes or why you didn't change anything.\n"
                        f"please return nothing but a JSON in the following format:\n"
                        f"{sample_revise_json}\n "

        }]

        lc_messages = convert_openai_messages(prompt)
        optional_params = {
            "response_format": {"type": "json_object"}
        }

        response = ChatOpenAI(model=CurrentConfig.OPENAI_CHAT_MODEL, max_retries=1, model_kwargs=optional_params).invoke(lc_messages).content
        response = json.loads(response)
        print(f"For article: {article['title']}")
        print(f"Writer Revision Message: {response['message']}\n")
        return response

    def run(self, article: dict):
        critique = article.get("critique")
        if critique is not None:
            article.update(self.revise(article))
        else:
            article.update(self.writer(article["query"], article["sources"]))
        return article