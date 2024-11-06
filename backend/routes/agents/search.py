from tavily import TavilyClient
import os
import uuid
from backend.services.search_services import search_thelink
from backend.config import CurrentConfig
import requests

tavily_client = TavilyClient(api_key=CurrentConfig.TAVILY_API_KEY)

# TODO : Augment the search agent to run against the Personal Knowledge Vault
class SearchAgent:
    def __init__(self):
        pass

    def search_tavily(self, query: str):
        try:
            results = tavily_client.search(query=query, topic="general", max_results=10, include_images=True)
            sources = results["results"]
            try:
                image = results["images"][0]
            except:
                image = "https://images.unsplash.com/photo-1542281286-9e0a16bb7366?ixid=MnwxMjA3fDB8MHxzZWFyY2h8Mnx8bmV3c3BhcGVyJTIwbmV3c3BhcGVyJTIwYXJ0aWNsZXxlbnwwfHwwfHw%3D&ixlib=rb-1.2.1&w=1000&q=80"
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print("Error: Unauthorized access. Please check your Tavily API key.")
                sources = []
                image = "https://images.unsplash.com/photo-1542281286-9e0a16bb7366?ixid=MnwxMjA3fDB8MHxzZWFyY2h8Mnx8bmV3c3BhcGVyJTIwbmV3c3BhcGVyJTIwYXJ0aWNsZXxlbnwwfHwwfHw%3D&ixlib=rb-1.2.1&w=1000&q=80"
            else:
                raise
        return sources, image


    def run(self, article: dict):
        res = self.search_tavily(article["query"])
        article["sources"] = res[0]
        article["image"] = res[1]
        article['uuid']=str(uuid.uuid4())
        query = article["query"]
        
        internal_results = search_thelink(query)
       
        article["sources"].extend(internal_results)
        return article
    