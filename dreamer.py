import os
import time
from elasticsearch import Elasticsearch
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
es = Elasticsearch(
    cloud_id=os.getenv("ELASTIC_CLOUD_ID"),
    api_key=os.getenv("ELASTIC_API_KEY"),
    request_timeout=120
)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

INDEX_NAME = "dreamer-memory"
EMBEDDING_MODEL = "models/gemini-embedding-001"
EMBEDDING_DIMS = 3072


# ========================================================================
# SCHEMA: Knowledge Graph in Elasticsearch
# Knowledge Graph encoded as flat documents in Elasticsearch
# Each doc is either a "triplet" (head-relation-tail) or a "note" (rich text)
# ========================================================================

def setup_index():
    """Creates the enriched knowledge graph index."""
    if es.indices.exists(index=INDEX_NAME):
        print(f"ℹ️  Index '{INDEX_NAME}' already exists. Skipping creation.")
        return

    es.indices.create(
        index=INDEX_NAME,
        mappings={
            "properties": {
                "content":   {"type": "text"},          # Full text for search
                "head":      {"type": "keyword"},       # Entity: subject
                "relation":  {"type": "keyword"},       # Relationship type
                "tail":      {"type": "keyword"},       # Entity: object
                "doc_type":  {"type": "keyword"},       # "triplet" or "note"
                "namespace": {"type": "keyword"},       # Context isolation key
                "vector":    {
                    "type": "dense_vector",
                    "dims": EMBEDDING_DIMS,
                    "index": True,
                    "similarity": "cosine"
                },
                "status":    {"type": "keyword"},       # "raw" or "dreamed"
                "timestamp": {"type": "date"}
            }
        }
    )
    print(f"✅ Index '{INDEX_NAME}' created with knowledge graph schema.")


def reset_index():
    """Deletes and recreates the index."""
    if es.indices.exists(index=INDEX_NAME):
        es.indices.delete(index=INDEX_NAME)
        print(f"🗑️  Index '{INDEX_NAME}' deleted.")
    setup_index()


# ========================================================================
# INGESTION: Two document types — Triplets and Notes
# ========================================================================

def ingest_triplet(head, relation, tail, namespace, content=None):
    """
    Store a knowledge graph triplet.
    Like Neo4j's: (head)-[relation]->(tail) within a Context.
    """
    text = content or f"{head} {relation.replace('_', ' ').lower()} {tail}"
    doc = {
        "content": text,
        "head": head,
        "relation": relation,
        "tail": tail,
        "doc_type": "triplet",
        "namespace": namespace,
        "status": "raw",
        "timestamp": int(time.time() * 1000)
    }
    es.index(index=INDEX_NAME, document=doc)


def ingest_note(topic, text, namespace):
    """
    Store a rich note linked to a topic entity.
    Like Neo4j's: (Entity)-[:HAS_CONTEXT]->(Note)
    """
    doc = {
        "content": text,
        "head": topic,
        "relation": "HAS_NOTE",
        "tail": text[:100],
        "doc_type": "note",
        "namespace": namespace,
        "status": "raw",
        "timestamp": int(time.time() * 1000)
    }
    es.index(index=INDEX_NAME, document=doc)


# ========================================================================
# DREAM CYCLE: Background vectorization (the "Dreamer" agent)
# ========================================================================

def dream_cycle():
    """
    Background Consolidation Agent.
    Finds all raw documents, vectorizes them with Gemini, marks as 'dreamed'.
    Write-time consolidation: vectorize raw docs in the background.
    """
    response = es.search(
        index=INDEX_NAME,
        body={"query": {"term": {"status": "raw"}}, "size": 50}
    )

    hits = response['hits']['hits']
    if not hits:
        print("😴 No raw documents to process.")
        return

    print(f"💤 Found {len(hits)} raw document(s) to process...")

    # Batch embed for efficiency (like the embedding_cache in V3.5)
    texts = []
    for hit in hits:
        h = hit['_source']
        if h['doc_type'] == 'triplet':
            texts.append(f"{h['head']} {h['relation'].replace('_',' ').lower()} {h['tail']}")
        else:
            texts.append(h['content'][:500])

    # Batch vectorize
    print("  🔮 Vectorizing batch with Gemini...")
    embeddings = []
    for text in texts:
        result = genai.embed_content(model=EMBEDDING_MODEL, content=text)
        embeddings.append(result['embedding'])
        time.sleep(0.1)  # Rate limit courtesy

    # Update documents
    for hit, emb in zip(hits, embeddings):
        es.update(
            index=INDEX_NAME,
            id=hit['_id'],
            doc={"vector": emb, "status": "dreamed"}
        )

    print(f"🌙 Dream cycle complete. {len(hits)} documents consolidated.")


# ========================================================================
# DEMO DATA: Rich enterprise knowledge graph
# ========================================================================

def seed_demo_data():
    """
    Seeds a realistic enterprise knowledge graph across 4 namespaces.
    ~45 documents showing real multi-project complexity.
    """
    print("\n--- Seeding Knowledge Graph ---")

    # ============================================================
    # PROJECT ALPHA — AWS-based e-commerce platform
    # ============================================================
    ns = "Project_Alpha"
    print(f"\n📂 [{ns}]")

    # Team structure
    ingest_triplet("Alice Chen", "LEADS", "Project_Alpha", ns)
    ingest_triplet("Alice Chen", "ROLE", "Tech Lead", ns)
    ingest_triplet("Bob Kumar", "WORKS_ON", "Project_Alpha", ns)
    ingest_triplet("Bob Kumar", "ROLE", "Backend Engineer", ns)
    ingest_triplet("Carol Zhang", "WORKS_ON", "Project_Alpha", ns)
    ingest_triplet("Carol Zhang", "ROLE", "DevOps Engineer", ns)

    # Architecture
    ingest_triplet("Project_Alpha", "HOSTED_ON", "AWS", ns)
    ingest_triplet("Project_Alpha", "REGION", "us-east-1", ns)
    ingest_triplet("Project_Alpha", "USES_DB", "PostgreSQL RDS", ns)
    ingest_triplet("Project_Alpha", "USES_CACHE", "ElastiCache Redis", ns)
    ingest_triplet("Project_Alpha", "FRAMEWORK", "Django REST Framework", ns)

    # Credentials & Config
    ingest_triplet("PostgreSQL RDS", "PASSWORD", "alpha_pg_2024!secure", ns)
    ingest_triplet("PostgreSQL RDS", "HOST", "alpha-db.cluster-xyz.us-east-1.rds.amazonaws.com", ns)
    ingest_triplet("ElastiCache Redis", "ENDPOINT", "alpha-cache.abc123.use1.cache.amazonaws.com", ns)
    ingest_triplet("Project_Alpha", "API_KEY", "sk-alpha-prod-9f8e7d6c5b4a", ns)

    # Notes
    ingest_note("Sprint Planning", "Sprint 14 deadline: March 15. Feature freeze on March 10. Priority: checkout flow redesign and payment gateway migration from Stripe v2 to v3.", ns)
    ingest_note("Architecture Decision", "Decided to migrate from monolith to microservices. Phase 1: Extract user service and order service. Target completion: Q2 2026.", ns)
    ingest_note("Incident Report", "Production outage on Feb 10 lasting 45 minutes. Root cause: Redis connection pool exhaustion under peak load. Fix: increased max connections from 50 to 200.", ns)

    # ============================================================
    # PROJECT BETA — GCP-based healthcare analytics platform
    # ============================================================
    ns = "Project_Beta"
    print(f"📂 [{ns}]")

    # Team structure
    ingest_triplet("David Park", "LEADS", "Project_Beta", ns)
    ingest_triplet("David Park", "ROLE", "Engineering Manager", ns)
    ingest_triplet("Eve Martinez", "WORKS_ON", "Project_Beta", ns)
    ingest_triplet("Eve Martinez", "ROLE", "ML Engineer", ns)
    ingest_triplet("Frank Wilson", "WORKS_ON", "Project_Beta", ns)
    ingest_triplet("Frank Wilson", "ROLE", "Frontend Engineer", ns)

    # Architecture
    ingest_triplet("Project_Beta", "HOSTED_ON", "Google Cloud Platform", ns)
    ingest_triplet("Project_Beta", "REGION", "europe-west1", ns)
    ingest_triplet("Project_Beta", "USES_DB", "Cloud SQL MySQL", ns)
    ingest_triplet("Project_Beta", "USES_CACHE", "Memorystore Redis", ns)
    ingest_triplet("Project_Beta", "FRAMEWORK", "FastAPI", ns)
    ingest_triplet("Project_Beta", "COMPLIANCE", "HIPAA", ns)

    # Credentials & Config
    ingest_triplet("Cloud SQL MySQL", "PASSWORD", "beta_mysql_h1pp4!", ns)
    ingest_triplet("Cloud SQL MySQL", "HOST", "10.20.30.40", ns)
    ingest_triplet("Memorystore Redis", "ENDPOINT", "10.0.0.5:6379", ns)
    ingest_triplet("Project_Beta", "API_KEY", "sk-beta-prod-1a2b3c4d5e6f", ns)

    # Notes
    ingest_note("Client Meeting", "Client meeting scheduled Feb 28. Prepare Q4 analytics report and HIPAA compliance audit results. Key stakeholder: Dr. Smith, Chief Medical Officer.", ns)
    ingest_note("ML Pipeline", "Model retraining pipeline runs every Sunday at 2am UTC. Current model accuracy: 94.2% on validation set. Next improvement: add temporal features.", ns)
    ingest_note("Security Review", "Passed HIPAA compliance audit on Jan 15. Next audit scheduled for July. All PII data encrypted at rest using AES-256.", ns)

    # ============================================================
    # SHARED_INFRA — Internal tools & CI/CD shared across projects
    # ============================================================
    ns = "Shared_Infra"
    print(f"📂 [{ns}]")

    ingest_triplet("Jenkins", "SERVES", "Project_Alpha", ns)
    ingest_triplet("Jenkins", "SERVES", "Project_Beta", ns)
    ingest_triplet("Jenkins", "URL", "https://ci.internal.example.com", ns)
    ingest_triplet("Grafana", "MONITORS", "Project_Alpha", ns)
    ingest_triplet("Grafana", "MONITORS", "Project_Beta", ns)
    ingest_triplet("Grafana", "URL", "https://monitoring.internal.example.com", ns)
    ingest_triplet("SonarQube", "SCANS", "Project_Alpha", ns)
    ingest_triplet("SonarQube", "SCANS", "Project_Beta", ns)
    ingest_triplet("Vault", "MANAGES_SECRETS_FOR", "Project_Alpha", ns)
    ingest_triplet("Vault", "MANAGES_SECRETS_FOR", "Project_Beta", ns)

    # Dependencies between services
    ingest_triplet("Project_Alpha", "DEPENDS_ON", "Jenkins", ns)
    ingest_triplet("Project_Alpha", "DEPENDS_ON", "Grafana", ns)
    ingest_triplet("Project_Alpha", "DEPENDS_ON", "Vault", ns)
    ingest_triplet("Project_Beta", "DEPENDS_ON", "Jenkins", ns)
    ingest_triplet("Project_Beta", "DEPENDS_ON", "Grafana", ns)
    ingest_triplet("Project_Beta", "DEPENDS_ON", "Vault", ns)

    ingest_note("CI/CD Policy", "All deployments require two approvals. Staging must pass all integration tests before production deploy. Rollback SLA: 5 minutes.", ns)
    ingest_note("Monitoring Alert Rules", "Critical alert if p99 latency > 500ms. Warning if error rate > 1%. PagerDuty integration active for both projects.", ns)

    # ============================================================
    # GLOBAL — Company-wide information
    # ============================================================
    ns = "Global"
    print(f"📂 [{ns}]")

    ingest_triplet("Company VPN", "ENDPOINT", "vpn.example.com", ns)
    ingest_triplet("Company VPN", "PROTOCOL", "WireGuard", ns)
    ingest_triplet("All-Hands Meeting", "SCHEDULE", "Every Monday at 10am", ns)
    ingest_triplet("HR Portal", "URL", "https://hr.example.com", ns)
    ingest_triplet("IT Support", "EMAIL", "support@example.com", ns)
    ingest_triplet("IT Support", "SLACK_CHANNEL", "#it-help", ns)
    ingest_triplet("Alice Chen", "REPORTS_TO", "VP Engineering", ns)
    ingest_triplet("David Park", "REPORTS_TO", "VP Engineering", ns)

    ingest_note("Onboarding", "New engineer onboarding checklist: 1) Set up VPN 2) Request GitHub access 3) Join Slack channels 4) Complete security training 5) Schedule 1:1 with team lead.", ns)
    ingest_note("Security Policy", "All passwords must be rotated every 90 days. MFA required for all cloud consoles. SSH keys must use ED25519. No secrets in code repositories.", ns)

    print(f"\n✅ Seeded knowledge graph documents across 4 namespaces.")


# ========================================================================
# MAIN
# ========================================================================

if __name__ == "__main__":
    import sys

    print("🧠 Elastic Dreamer V2 — Knowledge Graph Engine")
    print("=" * 50)

    if "--reset" in sys.argv:
        reset_index()
    else:
        setup_index()

    seed_demo_data()

    print("\n⏳ Waiting for Elastic to index documents...")
    time.sleep(3)

    print("\n--- Starting Dream Cycle ---")
    dream_cycle()

    # Check if there are remaining raw docs (batch was >50)
    remaining = es.count(index=INDEX_NAME, body={"query": {"term": {"status": "raw"}}})
    if remaining['count'] > 0:
        print(f"\n💤 {remaining['count']} more documents to process...")
        dream_cycle()

    # Final stats
    total = es.count(index=INDEX_NAME)
    dreamed = es.count(index=INDEX_NAME, body={"query": {"term": {"status": "dreamed"}}})
    print(f"\n📊 Index Stats: {total['count']} total docs, {dreamed['count']} vectorized")
    print("🎉 Knowledge graph ready for Agent Builder!")
