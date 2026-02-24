# 🧠 Elastic Dreamer V2

**Elastic Dreamer** — A multi-step AI agent that enforces strict namespace isolation for enterprise knowledge graph retrieval, built with Elastic Agent Builder.

> Built for the [Elasticsearch Agent Builder Hackathon](https://elasticsearch.devpost.com/) (Jan–Feb 2026)

---

## 🎯 Problem

In multi-project enterprises, AI agents with shared memory create a critical security risk: **cross-project data leakage**. When an engineer asks "What's the database password?" while working on Project Alpha, the agent must NEVER return Project Beta's credentials.

Traditional RAG systems lack this isolation. Knowledge graphs (like Neo4j) solve it but don't scale. Elastic Dreamer brings knowledge graph semantics to Elasticsearch's scale.

## 💡 Solution: Knowledge Graph in Elasticsearch

Elastic Dreamer stores knowledge as **graph triplets** `(head) -[relation]-> (tail)` within isolated namespaces:

```
┌─────────────────────────────────────────────────────────────┐
│              ELASTIC DREAMER KNOWLEDGE GRAPH                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Project_Alpha (isolated)           Project_Beta (isolated) │
│  ┌────────────────────────┐        ┌────────────────────┐   │
│  │ Alice ──LEADS──> Alpha │        │ David ──LEADS──> β │   │
│  │ Alpha ──USES_DB──> RDS │        │ Beta ──USES_DB──>  │   │
│  │ RDS ──PASSWORD──>      │        │   Cloud SQL        │   │
│  │   "alpha_pg_2024!"     │        │ SQL ──PASSWORD──>   │   │
│  │ Alpha ──HOSTED_ON──>   │        │   "beta_mysql_h1!" │   │
│  │   AWS                  │        │ Beta ──HOSTED_ON──> │   │
│  └────────────────────────┘        │   GCP              │   │
│              🔒                     └────────────────────┘   │
│          NAMESPACE WALL              🔒                      │
│         (Never crosses)           NAMESPACE WALL             │
│                                                             │
│  Shared_Infra (cross-cutting)     Global (company-wide)     │
│  ┌────────────────────────┐       ┌─────────────────────┐   │
│  │ Jenkins ──SERVES──>    │       │ VPN ──ENDPOINT──>   │   │
│  │   Alpha AND Beta       │       │   vpn.example.com   │   │
│  │ Grafana ──MONITORS──>  │       │ HR ──URL──>         │   │
│  │   Alpha AND Beta       │       │   hr.example.com    │   │
│  └────────────────────────┘       └─────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                USER (Kibana Agent Chat)                        │
│    "Who works on Alpha and what DB do they use?"              │
└──────────────────────┬────────────────────────────────────────┘
                       │
                       ▼
┌───────────────────────────────────────────────────────────────┐
│           ELASTIC DREAMER AGENT (Agent Builder)               │
│  Multi-step reasoning with 5 tools:                          │
│  1. find_entity_relations → discover team members             │
│  2. search_by_namespace  → get architecture details           │
│  3. search_semantic      → fuzzy conceptual queries           │
│  4. cross_reference      → find shared resources              │
│  5. list_namespaces      → overview of all contexts           │
└──────────────────────┬────────────────────────────────────────┘
                       │
                       ▼
┌───────────────────────────────────────────────────────────────┐
│              ELASTICSEARCH (dreamer-memory index)             │
│  65+ docs: triplets (head/relation/tail) + notes              │
│  Dense vectors (Gemini 3072-dim) for semantic search          │
│  Namespace field enforces context isolation                   │
└───────────────────────────────────────────────────────────────┘
                       ▲
                       │
┌───────────────────────────────────────────────────────────────┐
│              DREAMER (Background Processor)                    │
│  dreamer.py: ingest → extract triplets → vectorize → index   │
│  Write-time consolidation engine                              │
└───────────────────────────────────────────────────────────────┘
```

## 🛠️ Agent Builder Tools (All 3 Tool Types)

| # | Tool | Type | Purpose |
|---|---|---|---|
| 1 | `search_by_namespace` | ES\|QL | Text search within a namespace. Namespace parameter enforces isolation |
| 2 | `find_entity_relations` | ES\|QL | Graph traversal — find all connections for an entity |
| 3 | `list_namespaces` | ES\|QL | Overview of available contexts and document counts |
| 4 | `cross_reference` | ES\|QL | Find entities shared across namespaces |
| 5 | `search_semantic` | Index Search | Vector similarity using Gemini embeddings |
| 6 | `ingest_memory` | **Workflow** | Write new knowledge triplets — agent can LEARN |
| 7 | `log_incident` | **Workflow** | Log incidents + check shared infrastructure impact |

## 🎬 Demo Scenarios

```
User: "What namespaces are available?"
Agent: → Uses list_namespaces → Shows 4 contexts with doc counts

User: "I'm working on Project_Alpha. Who's on the team?"
Agent: → Uses find_entity_relations(Project_Alpha)
     → Returns: Alice (Tech Lead), Bob (Backend), Carol (DevOps)

User: "What's the database password?"
Agent: → Uses search_by_namespace(Project_Alpha)
     → Returns: "alpha_pg_2024!secure" (NEVER returns Beta's password)

User: "Switch to Project_Beta. Same question."
Agent: → Uses search_by_namespace(Project_Beta)
     → Returns: "beta_mysql_h1pp4!" (completely different!)

User: "Are there any shared resources between Alpha and Beta?"
Agent: → Uses cross_reference
     → Returns: Jenkins, Grafana, SonarQube, Vault serve both
```

## 🚀 Setup

### Prerequisites
- [Elastic Cloud Serverless](https://cloud.elastic.co/registration?cta=agentbuilderhackathon) (free trial)
- [Google AI Studio](https://aistudio.google.com/apikey) API key (Gemini embeddings)
- Python 3.10+

### 1. Clone & Install
```bash
git clone https://github.com/YOUR_USERNAME/elastic-dreamer.git
cd elastic-dreamer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure
```bash
cp .env.example .env
# Edit .env with your Elastic Cloud ID, API Key, and Gemini API Key
```

### 3. Seed Knowledge Graph
```bash
python dreamer.py          # Creates index + seeds 65 docs + vectorizes
python dreamer.py --reset  # Reset: deletes and re-seeds fresh data
```

### 4. Configure Agent Builder
```bash
python agent_config.py     # Prints all tool configs + agent instructions
```
Then in Kibana:
1. **Agents → Manage Tools** → Create 4 ES|QL tools + 1 Index Search tool
2. **Agents → Create Agent** → Paste instructions, assign all 5 tools
3. Test in the agent chat!

## 🔑 Features Used (All 3 Tool Types)
- **Elastic Agent Builder** — Custom agent with multi-step reasoning instructions and 7 tools
- **ES|QL Custom Tools (4)** — Parameterized queries with namespace guards + graph traversal
- **Index Search Tool (1)** — Vector similarity using Gemini 3072-dim embeddings
- **Elastic Workflows (2)** — `ingest_memory` for learning + `log_incident` for incident response
- **Elasticsearch** — Knowledge graph encoded as 65 triplets with dense vectors
- **Write-Time Consolidation** — Background processor vectorizes data asynchronously

## 📝 License
[MIT](LICENSE)
