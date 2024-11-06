import os
import re
from neo4j import GraphDatabase
from backend.config import CurrentConfig
import uuid
from backend.services.document_services import generate_shareable_link
from jinja2 import Template

class DesignerAgent:
    def __init__(self, researchUuid: str, userUuid: str):
        self.researchUuid = researchUuid
        self.userUuid = userUuid
        # Neo4j connection setup
        self.driver = GraphDatabase.driver(
            CurrentConfig.NEO4J_URI, 
            auth=(CurrentConfig.NEO4J_USER, CurrentConfig.NEO4J_PASSWORD)
        )
        self.markdown_template = """
# {{ title }}

![Article Image]({{ image }})

**{{ date }}**

{% for paragraph in paragraphs %}
{{ paragraph }}

{% endfor %}

---

© clockworKnowledge. All Rights Reserved.
        """

    def designer(self, article: dict, userUuid: str):
        template = Template(self.markdown_template)
        
        # Sanitize and prepare data
        context = {
            "title": self._sanitize_text(article.get("title", "")),
            "image": self._sanitize_url(article.get("image", "")),
            "date": self._sanitize_text(article.get("date", "")),
            "paragraphs": [self._sanitize_text(p) for p in article.get("paragraphs", [])]
        }
        
        # Render the markdown content
        markdown_content = template.render(context)
        
        article["markdown"] = markdown_content
        article = self.save_article_markdown(article, userUuid)
        return article

    def save_article_markdown(self, article, userUuid):
        article["uuid"] = str(uuid.uuid4())
        self.save_article_to_db(article, userUuid)
        return article

    def save_article_to_db(self, article, userUuid):
        with self.driver.session() as session:
            # Generate a shareable link for the article
            url = generate_shareable_link(article["uuid"], 'html', userUuid, self.driver)
            session.write_transaction(
                self._create_article_node, 
                self.researchUuid, 
                article, 
                url
            )

    @staticmethod
    def _create_article_node(tx, researchUuid, article, url):
        articleUuid = article["uuid"] 

        text = "\n\n".join(article.get('paragraphs', []))
        sources = article.get('sources', [])
        query = """
        MATCH (d:Document {uuid: $researchUuid})-[rel:HAS_WORKFLOW]->(s1:Step)-[:NEXT*]-(s2:Step {name: 'design'})
        WITH s2
        MERGE (a:Document {uuid: $uuid})
        SET 
            a.name = $title,
            a.publisheddate = $date,
            a.imagePath = $image,
            a.url = $url,
            a.text = $text,
            a.markdown = $markdown,
            a.addeddate = datetime(),
            a.type = "Generated Article"

        MERGE (s2)-[:DESIGNED]->(a)
        WITH a
        UNWIND $list_of_sources AS source
            MATCH (doc:Document {url: source.url})
            MERGE (a)-[:SOURCED_FROM]->(doc)
        """
        tx.run(query, {
            "researchUuid": researchUuid,
            "uuid": articleUuid,
            "title": article.get("title", ""),
            "date": article.get("date", ""),
            "image": article.get("image", ""),
            "url": url,
            "markdown": article.get("markdown", ""),
            "text": text,
            "list_of_sources": sources
        })

    def close(self):
        self.driver.close()

    def run(self, article: dict, userUuid: str):
        return self.designer(article, userUuid)
    
    def _sanitize_text(self, text: str) -> str:
        """
        Sanitize text to prevent Markdown injection or formatting issues.
        """
        if not isinstance(text, str):
            return ""
        # Remove any unwanted characters or escape Markdown-specific characters if necessary
        sanitized = re.sub(r'[{}]', '', text)
        return sanitized.strip()

    def _sanitize_url(self, url: str) -> str:
        """
        Sanitize URL to ensure it's safe and properly formatted.
        """
        if not isinstance(url, str):
            return ""
        # Basic URL validation can be added here
        sanitized = re.sub(r'[{}]', '', url)
        return sanitized.strip()
