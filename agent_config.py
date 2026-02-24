# ========================================================================
# Elastic Dreamer — Agent Builder Configuration V2
# Knowledge Graph Agent with 5 tools for multi-step reasoning
# ========================================================================

AGENT_INSTRUCTIONS = """
You are the Elastic Dreamer — a secure, multi-step reasoning agent for enterprise knowledge retrieval and incident management.

## Your Purpose
You help users retrieve project-specific information from a knowledge graph stored in Elasticsearch, while enforcing **strict namespace isolation**. You can also WRITE new knowledge and log incidents.

## Available Tools (7 Total)
### Read Tools
1. **search_by_namespace** — Text search within a single namespace
2. **search_semantic** — Semantic vector search for fuzzy/conceptual queries
3. **find_entity_relations** — Graph traversal: find all connections for an entity
4. **list_namespaces** — List available contexts and document counts
5. **cross_reference** — Find entities shared across namespaces (only when asked)

### Write Tools (Workflows)
6. **ingest_memory** — Write a new knowledge triplet to the graph
7. **log_incident** — Log a security/operational incident with impact analysis

## Multi-Step Reasoning Rules
- For complex queries, use MULTIPLE tools in sequence:
  1. Use `list_namespaces` to discover contexts
  2. Use `find_entity_relations` to traverse the graph
  3. Use `search_by_namespace` for specific details
  4. Use `search_semantic` for conceptual queries
- For incident response, chain: find_entity_relations → search_by_namespace → log_incident
- When comparing projects, call `search_by_namespace` for EACH project separately, then synthesize

## Namespace Isolation (Critical)
- NEVER return data from a namespace the user hasn't requested
- The ONLY exception: user explicitly asks to compare or cross-reference
- Acknowledge namespace switches explicitly

## Response Format
- Present graph data as: "[Entity A] [relationship] [Entity B]"
- Cite the namespace for every piece of information
- For incidents, confirm what was logged and any affected shared infrastructure
"""


# ========================================================================
# ES|QL TOOLS (4 tools)
# ========================================================================

TOOL_1_SEARCH_BY_NAMESPACE = {
    "name": "search_by_namespace",
    "type": "esql",
    "description": "Search the knowledge graph within a specific namespace. Returns matching triplets and notes filtered by namespace. Use for direct text queries about a project's team, architecture, credentials, or notes.",
    "query": """FROM dreamer-memory
| WHERE namespace == ?namespace AND status == "dreamed"
| KEEP head, relation, tail, doc_type, content, namespace, timestamp
| SORT timestamp DESC
| LIMIT 10"""
}

TOOL_2_FIND_ENTITY_RELATIONS = {
    "name": "find_entity_relations",
    "type": "esql",
    "description": "Find all relationships for a specific entity in the knowledge graph. Works like graph traversal — given an entity name (person, project, service), returns all connected entities and their relationship types. Use for questions like 'what does Alice do?' or 'what services does Project_Alpha use?'",
    "query": """FROM dreamer-memory
| WHERE (head == ?entity OR tail == ?entity) AND status == "dreamed"
| KEEP head, relation, tail, namespace, doc_type
| LIMIT 15"""
}

TOOL_3_LIST_NAMESPACES = {
    "name": "list_namespaces",
    "type": "esql",
    "description": "List all available namespaces (project contexts) and their document counts. Use when the user wants to see what projects or contexts are available in the knowledge graph.",
    "query": """FROM dreamer-memory
| WHERE status == "dreamed"
| STATS doc_count = COUNT(*) BY namespace
| SORT doc_count DESC"""
}

TOOL_4_CROSS_REFERENCE = {
    "name": "cross_reference",
    "type": "esql",
    "description": "Find entities that are shared across multiple namespaces. Use ONLY when the user explicitly asks to compare projects or find shared resources. Returns entities that appear in more than one namespace.",
    "query": """FROM dreamer-memory
| WHERE status == "dreamed" AND doc_type == "triplet"
| STATS namespace_count = COUNT_DISTINCT(namespace), namespaces = VALUES(namespace) BY tail
| WHERE namespace_count > 1
| SORT namespace_count DESC
| LIMIT 10"""
}

# ========================================================================
# INDEX SEARCH TOOL (1 tool — configured in Kibana UI)
# ========================================================================

TOOL_5_SEARCH_SEMANTIC = {
    "name": "search_semantic",
    "type": "index_search",
    "description": "Semantic vector search across the knowledge graph. Use for conceptual or fuzzy queries where exact keywords may not match.",
    "kibana_config": {
        "index": "dreamer-memory",
    }
}

# ========================================================================
# WORKFLOW TOOLS (2 tools — import YAML in Kibana → Management → Workflows)
# ========================================================================

TOOL_6_INGEST_MEMORY = {
    "name": "ingest_memory",
    "type": "workflow",
    "description": "Write a new knowledge triplet to the graph. The agent can learn new information from conversations.",
    "yaml_file": "workflows/ingest_memory.yml",
    "inputs": ["head (string)", "relation (string)", "tail (string)", "namespace (string)", "doc_type (string, optional)"]
}

TOOL_7_LOG_INCIDENT = {
    "name": "log_incident",
    "type": "workflow",
    "description": "Log a security or operational incident. Creates a structured incident record and checks for shared infrastructure impact.",
    "yaml_file": "workflows/log_incident.yml",
    "inputs": ["title (string)", "description (string)", "severity (string)", "affected_project (string)"]
}


# ========================================================================
# PRINT HELPER — Run this to get copy-paste configs for Kibana
# ========================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("  ELASTIC DREAMER — AGENT BUILDER CONFIGURATION V2")
    print("  7 Tools: 4 ES|QL + 1 Index Search + 2 Workflows")
    print("=" * 70)

    print("\n" + "─" * 70)
    print("📋 AGENT INSTRUCTIONS (copy into 'Custom Instructions' field)")
    print("─" * 70)
    print(AGENT_INSTRUCTIONS)

    tools = [
        TOOL_1_SEARCH_BY_NAMESPACE,
        TOOL_2_FIND_ENTITY_RELATIONS,
        TOOL_3_LIST_NAMESPACES,
        TOOL_4_CROSS_REFERENCE,
        TOOL_5_SEARCH_SEMANTIC,
        TOOL_6_INGEST_MEMORY,
        TOOL_7_LOG_INCIDENT
    ]

    for i, tool in enumerate(tools, 1):
        print(f"\n{'─' * 70}")
        print(f"🔧 TOOL {i}: {tool['name']} ({tool['type']})")
        print(f"{'─' * 70}")
        print(f"Description: {tool['description']}")
        if 'query' in tool:
            print(f"\nES|QL Query:\n{tool['query']}")
        if 'kibana_config' in tool:
            print(f"\nKibana Config: {tool['kibana_config']}")
        if 'yaml_file' in tool:
            print(f"\nYAML File: {tool['yaml_file']}")
            print(f"Inputs: {', '.join(tool['inputs'])}")

    print(f"\n{'=' * 70}")
    print("PARAMETERS TO ADD:")
    print("─" * 70)
    print("Tool 1 (search_by_namespace): ?namespace — String, Required")
    print("   Description: Project namespace (e.g. 'Project_Alpha', 'Project_Beta')")
    print()
    print("Tool 2 (find_entity_relations): ?entity — String, Required")
    print("   Description: Entity name to look up (e.g. 'Alice Chen', 'Jenkins', 'Project_Alpha')")
    print()
    print("Tool 5 (search_semantic): Configure as Index Search in Kibana")
    print("   Index: dreamer-memory")
    print()
    print("Tools 6-7 (Workflows): Import YAML files from workflows/ directory")
    print("   Kibana → Management → Workflows → Create Workflow → paste YAML")
    print(f"{'=' * 70}")
