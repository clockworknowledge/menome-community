from datetime import datetime
from langchain_community.adapters.openai import convert_openai_messages
from langchain_openai import ChatOpenAI
from backend.config import CurrentConfig
from neo4j import GraphDatabase
import uuid

class CritiqueAgent:
    def __init__(self, researchUuid: str):
        self.researchUuid = researchUuid
        self.driver = GraphDatabase.driver(CurrentConfig.NEO4J_URI, auth=(CurrentConfig.NEO4J_USER, CurrentConfig.NEO4J_PASSWORD))
        pass

    def critique(self, article: dict):
        prompt = [{
            "role": "system",
            "content": "You are an expert researcher of the subject of the article. Your sole purpose is to provide short feedback on an article "
                       "written by a student in the subject of the article so the student will know what to fix.\n "
        }, {
            "role": "user",
            "content": f"Today's date is {datetime.now().strftime('%d/%m/%Y')}\n."
                       f"{str(article)}\n"
                       f"Your task is to provide a really short feedback on the article if no feedback has been provided before or if the article has been revised. \n"
                       f"if you think the article is good, please return None.\n"
                       f"if you noticed the field 'message' in the article, it means the writer has revised the article"
                        f"based on your previous critique. You can provide feedback on the revised article or just "
                       f"return None if you think the article is good.\n"
                        f"Please return a string of your critique or None.\n"
        }]

        lc_messages = convert_openai_messages(prompt)
        response = ChatOpenAI(model=CurrentConfig.OPENAI_CHAT_MODEL, max_retries=1).invoke(lc_messages).content
        # store the response into the critque node in the graph
        self.store_feedback_in_graph(response, article)

        if response == 'None':
            return {'critique': None}
        else:
            # store the critique in the graph database
            print(f"For article: {article['title']}")
            print(f"Feedback: {response}\n")
            return {'critique': response, 'message': None}


    def store_feedback_in_graph(self, feedback, article):
        with self.driver.session() as session:
            session.write_transaction(self._create_feedback_node, feedback, article, self.researchUuid )

    @staticmethod
    def _create_feedback_node(tx, feedback, article, researchUuid):
        fuuid=str(uuid.uuid4())
        query = (
            """
            MATCH (d:Document {uuid: $researchUuid})-[:HAS_WORKFLOW]->(s1:Step)-[:NEXT*]-(s2:Step) where s2.name='critique' 
            with s2 
            CREATE (f:Feedback {uuid:$fuuid}) set f.text=$feedback, f.addeddate=datetime() 
            CREATE (s2)-[:RECEIVED_FEEDBACK]->(f) 
            WITH f 
            MATCH (d2:Document {uuid:$articleUuid}) set d2.text=$text, d2.name=$name, d2.summary=$summary
            CREATE (f)-[:FEEDBACK_ON]->(d2)"""
        )  

        tx.run(query, researchUuid=researchUuid, feedback=feedback, fuuid=fuuid, articleUuid=article.get('uuid'), text="\n\n".join(article.get('paragraphs')),name=article.get('title'), summary=article.get('summary'))

    def close(self):
        self.driver.close()

    def run(self, article: dict):
        article.update(self.critique(article))
        return article 