import os
import time
from concurrent.futures import ThreadPoolExecutor
from langgraph.graph import Graph
from neo4j import GraphDatabase
import uuid

from backend.config import CurrentConfig

# Import agent classes
from .agents import CuratorAgent, SearchAgent, WriterAgent, DesignerAgent, EditorAgent, PublisherAgent, CritiqueAgent


class MasterAgent:
    """
    MasterAgent class orchestrates the workflow of various agent tasks for research and content generation.

    Attributes:
        layout (str): The layout configuration for the generated content.

    Methods:
        run(userUuid: str, queries: list, researchUuid: str) -> str:
            Executes the entire workflow of research, content creation, and publishing.
    """

    def __init__(self):
        self.layout = "layout_1"

    def run(self, userUuid, queries: list, researchUuid: str):
        """
        Runs the complete workflow for research and content generation.

        Args:
            userUuid (str): Unique identifier for the user.
            queries (list): List of research queries to process.
            researchUuid (str): Unique identifier for the research project.

        Returns:
            str: Path to the published newspaper.
        """
        # Initialize agents
        # existing topic agent -   checking agent that takes the topics and checks to see if there are existing topics that are related
        
        search_agent = SearchAgent()
        curator_agent = CuratorAgent(researchUuid=researchUuid)
        writer_agent = WriterAgent(researchUuid=researchUuid)
        critique_agent = CritiqueAgent(researchUuid=researchUuid) 
        designer_agent = DesignerAgent(researchUuid=researchUuid, userUuid=userUuid)
        editor_agent = EditorAgent(self.layout, userUuid)
        publisher_agent = PublisherAgent(CurrentConfig.NEO4J_URI, CurrentConfig.NEO4J_USER, CurrentConfig.NEO4J_PASSWORD, CurrentConfig.SITE_URL, researchUuid=researchUuid)

        # Define a Langchain graph
        workflow = Graph()

        # Add nodes for each agent
        workflow.add_node("search", search_agent.run)
        workflow.add_node("curate", curator_agent.run)
        workflow.add_node("write", writer_agent.run)
        workflow.add_node("critique", critique_agent.run)
        workflow.add_node("design", lambda x: designer_agent.run(x, userUuid))

        # Set up edges
        workflow.add_edge('search', 'curate')
        workflow.add_edge('curate', 'write')
        workflow.add_edge('write', 'critique')
        workflow.add_conditional_edges('critique',
                                       lambda x: "accept" if x['critique'] is None else "revise",
                                       {"accept": "design", "revise": "write"})

        # set up start and end nodes
        workflow.set_entry_point("search")
        workflow.set_finish_point("design")
     
        # compile the graph
        chain = workflow.compile()

        # Store the workflow in the graph database
        neo4j_saver = Neo4jWorkflowSaver(CurrentConfig.NEO4J_URI, CurrentConfig.NEO4J_USER, CurrentConfig.NEO4J_PASSWORD)
        neo4j_saver.save_workflow(workflow, userUuid, researchUuid)
        neo4j_saver.close()

        # Execute the graph for each query in parallel
        with ThreadPoolExecutor() as executor:
            parallel_results = list(executor.map(lambda q: chain.invoke({"query": q}), queries))

        # Compile the final newspaper
        newspaper_html = editor_agent.run(parallel_results)
        newspaper_path = publisher_agent.run(userUuid,  newspaper_html)

        return newspaper_path


class Neo4jWorkflowSaver:
    """
    Neo4jWorkflowSaver class handles saving the workflow graph to a Neo4j database.

    Attributes:
        driver (neo4j.Driver): Neo4j database driver.

    Methods:
        save_workflow(workflow: Graph, userUuid: str, researchUuid: str):
            Saves the workflow graph to the Neo4j database.
        close():
            Closes the Neo4j database connection.
    """

    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def save_workflow(self, workflow, userUuid, researchUuid):
        """
        Saves the workflow graph to the Neo4j database.

        Args:
            workflow (Graph): The workflow graph to be saved.
            userUuid (str): Unique identifier for the user.
            researchUuid (str): Unique identifier for the research project.
        """
        with self.driver.session() as session:
            # First, create all the nodes
            # need a uuid for the run - 
            run_id = str(uuid.uuid4())
            for node in workflow.nodes:
                node_id = str(uuid.uuid4())
                session.write_transaction(self._create_step_node, node ,node_id, run_id)

            # Then, create all the edges
            for start, end in workflow.edges:
                session.write_transaction(self._create_relationship, start, end, run_id)
            
            # finally connect design to the start node
            session.write_transaction(self._create_relationship, "critique", "design", run_id)

            # and link to the document header node for the research run
            query = (
                "MATCH (d:Document {uuid: $uuid}), (s:Step {runuuid: $runuuid}) where s.name='search' "
                "CREATE (d)-[:HAS_WORKFLOW]->(s)"
            )
            session.run(query, uuid=researchUuid, runuuid=run_id)
            session.close()

    @staticmethod
    def _create_step_node(tx, step_name, node_id, run_id):
        """
        Creates a Step node in the Neo4j database.

        Args:
            tx (neo4j.Transaction): The database transaction.
            step_name (str): Name of the step.
            node_id (str): Unique identifier for the node.
            run_id (str): Unique identifier for the workflow run.
        """
        query = (
            "CREATE (s:Step {uuid: $uuid}) set s.runuuid=$runuuid, s.name=$name, s.text=$text, s.type=$type, s.process=True, s.addeddate= datetime()"
        )
        tx.run(query, name=step_name, uuid=node_id, text=step_name, type="Step", runuuid=run_id)

    @staticmethod
    def _create_relationship(tx, start_step, end_step, run_id):
        """
        Creates a relationship between two Step nodes in the Neo4j database.

        Args:
            tx (neo4j.Transaction): The database transaction.
            start_step (str): Name of the starting step.
            end_step (str): Name of the ending step.
            run_id (str): Unique identifier for the workflow run.
        """
        query = (
            "MATCH (a:Step {name: $start_name}), (b:Step {name: $end_name}) where a.runuuid=$runuuid and b.runuuid=$runuuid "
            "CREATE (a)-[:NEXT]->(b)"
        )
        tx.run(query, start_name=start_step, end_name=end_step, runuuid=run_id)

    def close(self):
        """
        Closes the Neo4j database connection.
        """
        self.driver.close()
