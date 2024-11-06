import os
import uuid
from datetime import datetime
from neo4j import GraphDatabase
import logging
from backend.config import CurrentConfig
from backend.routes.agents.designer import generate_shareable_link

class PublisherAgent:
    def __init__(self, neo4j_uri, neo4j_user, neo4j_password, site_url, researchUuid):
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.site_url = site_url
        self.researchUuid = researchUuid

    def save_newspaper_html(self, userUuid, newspaper_html):
        # Generate a unique identifier for the document
        doc_id = self.researchUuid
       
        # Save the document in the Neo4j database
        url=self.save_document_in_neo4j(userUuid, doc_id, newspaper_html)
        return url

    def save_document_in_neo4j(self, userUuid, doc_id, text):
        name = "Research Article"  
        
        url = generate_shareable_link(doc_id, 'md', userUuid, self.driver)
        imageUrl = "default_image_url"  # If applicable, otherwise remove or set appropriately
        added_date = datetime.now().isoformat()
        
        with self.driver.session() as session:
            session.write_transaction(self._create_document_node, userUuid, doc_id, name, url, text, imageUrl, added_date)
        return url

    @staticmethod
    def _create_document_node(tx, userUuid, uuid, name, url, text, imageUrl, added_date):
        query = (
            """MERGE (d:Document {uuid: $uuid})
            set d.url = $url, d.text = $text, d.imageurl = $imageUrl, d.addeddate = $addedDate, d.type="Generated Research"
            with d
            MATCH (u:User {uuid: $useruuid})
            MERGE (ua:UserAction {useruuid: u.uuid}) 
            ON CREATE SET ua.name = u.username, ua.uuid=randomUUID()
            MERGE (u)-[r:HAS_ACTION]->(ua)
            MERGE (ua)-[:GENERATED]->(d) set r.dateadded= datetime()
            """ 
            
        )
        tx.run(query, useruuid=userUuid, uuid=uuid, name=name, url=url, text=text, imageUrl=imageUrl, addedDate=added_date)

    def run(self, userUuid, newspaper_html: str):
        newspaper_path = self.save_newspaper_html(userUuid, newspaper_html)
        return newspaper_path

    def close(self):
        self.driver.close()
