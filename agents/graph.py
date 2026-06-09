import os
from .state import AgentState
from .nodes.preference_cleaner import clean_onboarding_preferences
from .nodes.webtoon_scraper import webtoon_scraper_node
from .nodes.rag_retriever import retrieve_nearest_webtoons
from .nodes.feed_ranker import rank_webtoons_node

try:
    from langgraph.graph import StateGraph, END
    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False

class FallbackStateGraph:
    """
    A lightweight, pure-Python fallback execution engine mimicking LangGraph's StateGraph.
    Guarantees execution safety if langgraph dependency lacks C-compilers on the host OS.
    """
    def __init__(self, state_schema):
        self.state_schema = state_schema
        self.nodes = {}
        self.entry_point = None
        self.edges = {}
        self.conditional_edges = {}

    def add_node(self, name, func):
        self.nodes[name] = func

    def set_entry_point(self, name):
        self.entry_point = name

    def add_edge(self, start, end):
        self.edges[start] = end

    def add_conditional_edges(self, source, path_func, path_map=None):
        self.conditional_edges[source] = (path_func, path_map)

    def compile(self):
        return CompiledFallbackGraph(self)


class CompiledFallbackGraph:
    def __init__(self, graph):
        self.graph = graph

    def invoke(self, inputs: dict) -> dict:
        state = dict(inputs)
        # Default state values
        state.setdefault("webtoon_universe_loaded", False)
        state.setdefault("top_20_ids", [])
        state.setdefault("feed_cycle_number", 1)
        state.setdefault("all_skipped", False)
        state.setdefault("expansion_count", 0)
        state.setdefault("scrape_triggered", False)
        
        current_node = self.graph.entry_point
        print(f"[Graph Execution Start] Entry node: {current_node}")
        
        steps = 0
        max_steps = 100
        while current_node and current_node not in ["END", "__end__"] and steps < max_steps:
            node_func = self.graph.nodes.get(current_node)
            if not node_func:
                print(f"[Graph Error] Node '{current_node}' function not found.")
                break
                
            print(f"[Executing Node] -> {current_node}")
            output = node_func(state)
            if output:
                state.update(output)
                
            # Compute next transition
            next_node = None
            if current_node in self.graph.conditional_edges:
                path_func, path_map = self.graph.conditional_edges[current_node]
                decision = path_func(state)
                next_node = path_map[decision] if path_map and decision in path_map else decision
            elif current_node in self.graph.edges:
                next_node = self.graph.edges[current_node]
                
            print(f"[Transition] Node '{current_node}' finished. Next node: {next_node}")
            current_node = next_node
            steps += 1
            
        print("[Graph Execution End] Completed successfully.")
        return state


def get_agent_graph():
    """
    Builds and returns the master system StateGraph.
    Falls back to FallbackStateGraph if native LangGraph is not loadable.
    """
    if HAS_LANGGRAPH:
        try:
            workflow = StateGraph(AgentState)
            
            workflow.add_node("clean_preferences", clean_onboarding_preferences)
            workflow.add_node("scrape_universe", webtoon_scraper_node)
            workflow.add_node("rag_retrieve", retrieve_nearest_webtoons)
            workflow.add_node("feed_rank", rank_webtoons_node)
            
            workflow.set_entry_point("clean_preferences")
            workflow.add_edge("clean_preferences", "scrape_universe")
            workflow.add_edge("scrape_universe", "rag_retrieve")
            workflow.add_edge("rag_retrieve", "feed_rank")
            workflow.add_edge("feed_rank", END)
            
            return workflow.compile()
        except Exception as e:
            print(f"Error compiling LangGraph: {e}. Defaulting to fallback.")
            
    # Assemble fallback graph flow
    workflow = FallbackStateGraph(AgentState)
    
    workflow.add_node("clean_preferences", clean_onboarding_preferences)
    workflow.add_node("scrape_universe", webtoon_scraper_node)
    workflow.add_node("rag_retrieve", retrieve_nearest_webtoons)
    workflow.add_node("feed_rank", rank_webtoons_node)
    
    workflow.set_entry_point("clean_preferences")
    workflow.add_edge("clean_preferences", "scrape_universe")
    workflow.add_edge("scrape_universe", "rag_retrieve")
    workflow.add_edge("rag_retrieve", "feed_rank")
    workflow.add_edge("feed_rank", "END")
    
    return workflow.compile()
