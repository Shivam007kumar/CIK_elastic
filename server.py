from mcp.server.fastmcp import FastMCP
from elasticsearch import Elasticsearch
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("Elastic-Dreamer")
es = Elasticsearch(
    cloud_id=os.getenv("ELASTIC_CLOUD_ID"),
    api_key=os.getenv("ELASTIC_API_KEY")
)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
INDEX_NAME = "dreamer-memory"

@mcp.tool()
def search_memory(query: str, project_context: str) -> str:
    """
    Search long-term memory with strict Namespace Isolation.
    Args:
        query: User question
        project_context: The active project (e.g., 'Project_Alpha')
    """
    # 1. Vectorize the query
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=query
    )
    q_emb = result['embedding']

    # 2. Hybrid Search (kNN + Exact Namespace Filter)
    # This proves the Elastic Dreamer concept of Context Isolation
    res = es.search(
        index=INDEX_NAME,
        body={
            "knn": {
                "field": "vector",
                "query_vector": q_emb,
                "k": 3,
                "num_candidates": 10,
                "filter": {
                    "term": {"namespace": project_context}
                }
            }
        }
    )

    hits = [hit['_source']['content'] for hit in res['hits']['hits']]
    return "\n".join(hits) if hits else f"No memory found for context: {project_context}."

if __name__ == "__main__":
    mcp.run()
