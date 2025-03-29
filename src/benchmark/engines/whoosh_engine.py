import time
from typing import List, Optional
from whoosh.index import Index
from whoosh.searching import Searcher
from whoosh.qparser import QueryParser, MultifieldParser, OrGroup
from whoosh.qparser.plugins import FuzzyTermPlugin

from .base import BenchmarkEngine, BenchmarkQuery, BenchmarkResult, SearchResult

class WhooshBenchmarkEngine(BenchmarkEngine):
    """
    Benchmark engine for Whoosh search engine
    """
    
    def __init__(self, index: Index, limit: int = 20):
        self.index = index
        self.searcher: Optional[Searcher] = None
        
        schema = self.index.schema
        fields = ["title", "content", "abstract"] if all(f in schema for f in ["title", "content", "abstract"]) else list(schema.names())
        
        self.parser = MultifieldParser(fields, schema, group=OrGroup)
        
        self.parser.add_plugin(FuzzyTermPlugin())
        
        self.field_boosts = {
            "title": 2.0,
            "abstract": 1.5,
            "content": 1.0
        }
        
        self.limit = limit
    
    def prepare(self) -> None:
        if self.searcher is None:
            self.searcher = self.index.searcher()
    
    def run_query(self, query: BenchmarkQuery) -> BenchmarkResult:
        """
        Run a single benchmark query
        """
        if self.searcher is None:
            self.prepare()
        
        whoosh_query = self.parser.parse(query.structured_query)
        start_time = time.time()
        
        results = self.searcher.search(
            whoosh_query, 
            limit=self.limit,
            terms=True
        )
        
        end_time = time.time()
        
        search_results = []
        max_score = max((hit.score for hit in results), default=1.0)
        
        expected_relevant = max(1, query.expected_relevant_docs)
        
        for pos, hit in enumerate(results, 1):
            normalized_score = hit.score / max_score
            
            position_factor = 1.0 / (1.0 + 0.1 * pos)
            
            adjusted_score = normalized_score * position_factor
            relevance = 1.0 if (adjusted_score > 0.2 or pos <= expected_relevant // 2) else 0.0
            
            search_results.append(SearchResult(
                query=query.structured_query,
                result_id=hit.get('id', ''),
                score=hit.score,
                position=pos,
                title=hit.get('title', ''),
                relevance=relevance,
                execution_time=end_time - start_time
            ))
        
        return BenchmarkResult(
            query=query,
            results=search_results,
            total_time=end_time - start_time
        )
    
    def run_benchmark(self, queries: List[BenchmarkQuery]) -> List[BenchmarkResult]:
        """
        Run the complete benchmark suite
        """
        self.prepare()
        return [self.run_query(query) for query in queries]
    
    def cleanup(self) -> None:
        """
        Clean up resources
        """
        if self.searcher is not None:
            self.searcher.close()
            self.searcher = None 