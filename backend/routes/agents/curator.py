from datetime import datetime
from langchain_community.adapters.openai import convert_openai_messages

from langchain_openai import ChatOpenAI
from backend.config import CurrentConfig
from neo4j import GraphDatabase
import uuid

class CuratorAgent:
    def __init__(self, researchUuid: str):
        pass
        self.researchUuid = researchUuid
        self.driver = GraphDatabase.driver(CurrentConfig.NEO4J_URI, auth=(CurrentConfig.NEO4J_USER, CurrentConfig.NEO4J_PASSWORD))  

    def curate_sources(self, query: str, sources: list,  researchUuid: str):
        """
        Curate relevant sources for a query
        :param input:
        :return:
        """
        prompt = [{
            "role": "system",
            "content": "You are a world-class expert researcher in the domain of the given topic. Your task is to "
                       "critically evaluate and select the 5 most relevant and high-quality sources from a list of "
                       "articles. Use your expertise to assess the credibility, relevance, and scientific merit of "
                       "each source in relation to the topic at hand.\n "
        }, {
            "role": "user",
            "content": f"Today's date is {datetime.now().strftime('%d/%m/%Y')}\n."
                       f"Topic or Query: {query}\n"
                       f"Your task is to return the 5 most relevant articles for me to read for the provided topic or "
                       f"query\n "
                       f"Here is a list of articles:\n"
                       f"{sources}\n"
                       f"Please return nothing but a list of the strings of the URLs in this structure: ['url1',"
                       f"'url2','url3','url4','url5'].\n "
        }]

        lc_messages = convert_openai_messages(prompt)
        response = ChatOpenAI(model=CurrentConfig.OPENAI_CHAT_MODEL, max_retries=1).invoke(lc_messages).content
        chosen_sources = response
        for i in sources:
            if i["url"] not in chosen_sources:
                sources.remove(i)

        
        # Store curated sources in Neo4j
        with self.driver.session() as session:
            for src in sources:
                src['uuid']=str(uuid.uuid4())
                session.write_transaction(self._create_document_node, src, researchUuid)

        return sources

    def run(self, article: dict):
        article["sources"] = self.curate_sources(article["query"], article["sources"], self.researchUuid)

        return article
    

    @staticmethod
    def _create_document_node(tx, src, researchUuid):
        query = """
        MATCH (r:Document {uuid: $researchUuid})-[rel:HAS_WORKFLOW]->(s1:Step)-[:NEXT*]-(s2:Step {name: 'curate'})
        MERGE (d:Document {url: $url})
            ON CREATE SET
                d.uuid = randomUUID(),
                d.name = $title,
                d.imageurl = $image,
                d.type = 'Agent Contributed',
                d.researchuuid = $researchUuid,
                d.addeddate = datetime(),
                d.publisheddate = $publisheddate,
                d.process=true,
                d.text = $text,
                d.url = $url,
                d.createdNew = true  // Flag to indicate if the node was created
            ON MATCH SET
                d.lastUpdated = datetime(),  // Optional: track when matched nodes are updated
                d.createdNew = false  // Flag to indicate the node was matched not created
        WITH d, s2
        CALL {
            WITH d, s2
            MATCH  (dnew:Document) where dnew.uuid=d.uuid and d.createdNew = true 
            MERGE (s2)-[:CONTRIBUTED_NEW {score: $score}]->(d)
        }
        with d, s2
        CALL {
            WITH d, s2
            MATCH  (dnew:Document)-[:HAS_PAGE]-(p:Page) where p.uuid=$pageuuid
            MERGE (s2)-[:REFERENCED {score: $score}]->(p)
        }       
        """
        tx.run(query,url=src.get("url"), publisheddate=src.get("published date"), title=src.get("title"), image=src.get("image"),researchUuid=researchUuid,  text = src.get('content'), score = src.get('score', 1), pageuuid=src.get('pageuuid'))



    def close(self):
        self.driver.close()