# Elastic Dreamer — Devpost Submission

## Project Name
Elastic Dreamer

## Elevator Pitch
A secure Knowledge Graph agent preventing data leakage via ES|QL namespace isolation. Combines graph traversal, semantic search, and workflows for safe, enterprise-grade automation.

## Description (~400 words)

### The Problem: Cross-Project Data Leakage
In enterprise environments, standard RAG pipelines create a critical security risk: **Data Flattening**. If an engineer working on *Project Alpha* asks an AI assistant "What's the database password?", a standard vector search often retrieves credentials from *Project Beta*. This cross-project leakage makes generic AI agents unsafe for internal work. Traditional knowledge graphs (like Neo4j) solve this but are complex to scale; flat vector stores scale but lack structure.

### The Solution: Knowledge Graph in Elasticsearch
Elastic Dreamer encodes enterprise knowledge as **graph triplets** `(head)-[relation]->(tail)` directly within Elasticsearch, enforcing strict namespace isolation through **ES|QL parameterized queries**. The architecture allows the agent to reason across project boundaries only when explicitly authorized.

**Key Innovations:**
1.  **Namespace-Isolated Retrieval:** The agent uses ES|QL to lock queries to a specific namespace (e.g., `WHERE namespace == ?`). This acts as a security firewall—Project Alpha’s secrets are physically unreachable from Project Beta’s context.
2.  **Tool-Driven Reasoning:** Instead of relying on prompts, the agent actively selects tools. It uses `find_entity_relations` to traverse team structures and `search_by_namespace` for precise data retrieval.
3.  **Reliable Action (Workflows):** The agent isn't just read-only. It uses the `ingest_memory` workflow to learn new facts in real-time and the `log_incident` workflow to write structured incident reports back to the system.

### Features Used
*   **Elastic Agent Builder:** Orchestrating a custom agent with 7 distinct tools.
*   **ES|QL Custom Tools (4):** For graph traversal, namespace isolation, and cross-reference analytics.
*   **Elastic Workflows (2):** `ingest_memory` (write-back) and `log_incident` (operational automation).
*   **Index Search Tool (1):** Semantic vector search using Gemini 3072-dim embeddings.
*   **Elasticsearch Serverless:** Storing 65+ triplet documents with dense vectors.

### Challenges & Highlights
*   **Highlight:** The **ES|QL guarded parameters** are a perfect security fit for LLMs. By hardcoding the query structure (`FROM index | WHERE...`), we prevent prompt injection attacks while allowing flexible entity search.
*   **Challenge:** Balancing real-time ingestion with vectorization latency. I solved this with a "Dreaming" pattern: data is ingested instantly as "raw" (fast write), then a background process vectorizes it to "dreamed" (slow AI) status asynchronously.