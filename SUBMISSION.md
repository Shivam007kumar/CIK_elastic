# Elastic Dreamer — Devpost Submission Description (~300 words)

## Problem Solved

In multi-project enterprises, AI assistants with shared memory create a critical security
risk: cross-project data leakage. When an engineer working on Project Alpha asks
"What's the database password?", a standard RAG pipeline might return Project Beta's
credentials — a catastrophic security failure. Traditional knowledge graphs (like Neo4j)
solve context isolation but don't scale. Flat vector stores scale but lack structure.

## Solution: Elastic Dreamer — Knowledge Graph in Elasticsearch

Elastic Dreamer encodes enterprise knowledge as **graph triplets**
`(head)-[relation]->(tail)` within Elasticsearch, with strict namespace isolation
enforced through ES|QL parameterized queries. The architecture has three layers:

**Write-Time Consolidation:** Raw data is ingested instantly with a namespace tag, then a
background "Dreamer" agent vectorizes it using Gemini embeddings — separating fast writes
from slow AI processing.

**Knowledge Graph Schema:** Instead of flat documents, data is structured as typed
relationships (LEADS, USES_DB, PASSWORD, HOSTED_ON) across entities (people, services,
projects). This enables graph-like traversal queries using ES|QL.

**Namespace-Isolated Retrieval:** Five Agent Builder tools (4 ES|QL + 1 Index Search)
provide multi-step reasoning. The agent traverses entity relationships, performs semantic
vector search, cross-references shared infrastructure — all while enforcing strict
namespace boundaries. Project Alpha's credentials are physically unreachable from Project
Beta's context.

## Features Used

- **Elastic Agent Builder:** Custom agent with multi-step reasoning instructions and 5 tools
- **ES|QL Custom Tools (4):** Parameterized namespace guards, entity relationship traversal,
  cross-namespace reference detection, and namespace listing
- **Index Search Tool (1):** Semantic vector search using Gemini 3072-dim embeddings on the
  knowledge graph
- **Elasticsearch:** Triplet-based knowledge graph schema with dense vectors

## What I Liked / Challenges

1. **ES|QL guarded parameters** are perfect for security — the query structure is locked down
   while the LLM fills in entity names. This maps beautifully to graph traversal queries.
2. **Multi-tool agent reasoning** impressed me — the agent consistently chains
   find_entity_relations → search_by_namespace for complex questions.
3. **Challenge:** Encoding graph relationships as flat Elasticsearch documents required
   careful schema design — a pattern worth documenting for the community.
