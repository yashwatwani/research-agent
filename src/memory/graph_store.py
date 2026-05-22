import json
import pickle
import os
import networkx as nx
from openai import OpenAI
from src.config import OPENAI_API_KEY, CHAT_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)

GRAPH_PATH = "data/graph/knowledge_graph.pkl"


def load_graph() -> nx.DiGraph:
    # loads the NetworkX graph from disk, creates empty one if none exists

    if os.path.exists(GRAPH_PATH):
        with open(GRAPH_PATH, "rb") as f:
            return pickle.load(f)
    return nx.DiGraph()


def save_graph(graph: nx.DiGraph):
    # persists the graph to disk as a pickle file

    os.makedirs(os.path.dirname(GRAPH_PATH), exist_ok=True)
    with open(GRAPH_PATH, "wb") as f:
        pickle.dump(graph, f)


def extract_entities_and_relations(text: str) -> list[dict]:
    #sends text to gpt-4o, gets back subject/relation/object triples

    prompt = f"""Extract entities and relationships from the text below.
Return ONLY a JSON array. No explanation, no markdown, no extra text.
Each item must have exactly these keys: "subject", "relation", "object"

Example output:
[
  {{"subject": "Anthropic", "relation": "created", "object": "MCP"}},
  {{"subject": "OpenAI", "relation": "adopted", "object": "MCP"}}
]

Text:
{text}

JSON array:"""

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    raw = response.choices[0].message.content.strip()

    try:
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except json.JSONDecodeError:
        print(f"Could not parse entities: {raw[:200]}")
        return []


def store_document_in_graph(text: str, source_url: str = "", source_title: str = ""):
    #extracts triples from text, adds nodes and edges to graph, saves

    graph = load_graph()
    triples = extract_entities_and_relations(text)

    added = 0
    for triple in triples:
        subject = triple.get("subject", "").strip()
        relation = triple.get("relation", "").strip()
        obj = triple.get("object", "").strip()

        if not all([subject, relation, obj]):
            continue

        graph.add_node(subject, type="entity")
        graph.add_node(obj, type="entity")
        graph.add_edge(subject, obj,
                       relation=relation,
                       source_url=source_url,
                       source_title=source_title)
        added += 1

    save_graph(graph)
    print(f"Added {added} relationships from {source_title or source_url}")
    return triples


def query_graph(question: str) -> list[dict]:
    #finds the entity in the graph matching the question, returns all connected edges

    graph = load_graph()

    if graph.number_of_nodes() == 0:
        return []

    prompt = f"""Extract the main entity being asked about from this question.
Return ONLY the entity name, nothing else.

Question: {question}
Entity:"""

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    entity = response.choices[0].message.content.strip()

    matched_node = None
    for node in graph.nodes():
        if entity.lower() in node.lower() or node.lower() in entity.lower():
            matched_node = node
            break

    if not matched_node:
        return []

    results = []

    for _, target, data in graph.out_edges(matched_node, data=True):
        results.append({
            "subject": matched_node,
            "relation": data.get("relation", ""),
            "object": target,
            "source_title": data.get("source_title", "")
        })

    for source, _, data in graph.in_edges(matched_node, data=True):
        results.append({
            "subject": source,
            "relation": data.get("relation", ""),
            "object": matched_node,
            "source_title": data.get("source_title", "")
        })

    return results


def get_graph_stats() -> dict:
    #returns node count, edge count, and entity list
    
    graph = load_graph()
    return {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "entities": list(graph.nodes())[:20]
    }