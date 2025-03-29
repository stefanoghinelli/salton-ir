import re
import logging
from typing import List, Dict, Optional, Protocol
from dataclasses import dataclass
from whoosh.qparser import MultifieldParser, OrGroup, AndGroup, QueryParser
from whoosh import scoring, index
from whoosh.fields import Schema
from whoosh.searching import Searcher, Results
from whoosh.query import Query
from abc import ABC, abstractmethod

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """
    Data class to hold search result information
    """
    title: str
    abstract: str
    score: float
    rank: int

class QueryStrategy(Protocol):
    """
    Protocol for query parsing strategies
    """
    
    def parse_query(self, query_string: str, schema: Schema) -> Query:
        """Parse a query string into a Whoosh Query object."""
        ...

class AndQueryStrategy:
    """
    Strategy for AND queries
    """
    
    def parse_query(self, query_string: str, schema: Schema) -> Query:
        parser = MultifieldParser(["title", "abstract", "content"], 
                                schema=schema, 
                                group=AndGroup)
        return parser.parse(query_string)

class OrQueryStrategy:
    """
    Strategy for OR queries
    """
    
    def parse_query(self, query_string: str, schema: Schema) -> Query:
        parser = MultifieldParser(["title", "abstract", "content"], 
                                schema=schema, 
                                group=OrGroup)
        return parser.parse(query_string)

class BaseSearchEngine(ABC):
    """
    Abstract base class for search engines
    """
    
    @abstractmethod
    def search(self, query: str, limit: int = 5) -> List[SearchResult]:
        """
        Perform a search and return results
        """
        pass
    
    @abstractmethod
    def suggest_correction(self, query: str) -> Optional[str]:
        """
        Suggest a correction for the query if needed
        """
        pass

class WhooshSearchEngine(BaseSearchEngine):
    """
    Whoosh-based implementation of search engine
    """
    
    def __init__(self, index_path: str = "./data/indexes"):

        self.index_path = index_path
        self.index = index.open_dir(index_path)
        self.searcher = self.index.searcher(
            weighting=scoring.BM25F(B=0.75, content_B=1.0, K1=1.2)
        )
        self.or_strategy = OrQueryStrategy()
        self.and_strategy = AndQueryStrategy()
    
    def __del__(self):
        """
        Clean up resources
        """
        if hasattr(self, 'searcher'):
            self.searcher.close()
    
    def search(self, query: str, limit: int = 5) -> List[SearchResult]:
        """
        Perform a search using the appropriate query strategy
        
        Args:
            query: Query string
            limit: Maximum number of results to return
            
        Returns:
            List of SearchResult objects
        """
        query = query.lower()
        strategy = self._select_query_strategy(query)
        
        try:
            whoosh_query = strategy.parse_query(query, self.searcher.schema)
            results = self.searcher.search(whoosh_query, limit=limit)
            return self._process_results(results)
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return []
    
    def suggest_correction(self, query: str) -> Optional[str]:
        """
        Suggest a correction for the query if needed
        
        Args:
            query: Original query string
            
        Returns:
            Corrected query string if available, None otherwise
        """
        try:
            strategy = self._select_query_strategy(query)
            whoosh_query = strategy.parse_query(query.lower(), self.searcher.schema)
            corrected = self.searcher.correct_query(whoosh_query, query.lower())
            
            if corrected.query != whoosh_query:
                return corrected.string
        except Exception as e:
            logger.error(f"Correction suggestion error: {str(e)}")
        
        return None
    
    def _select_query_strategy(self, query: str) -> QueryStrategy:
        """
        Select appropriate query strategy based on query content
        """
        return self.and_strategy if re.search(r'\bAND\b', query, re.IGNORECASE) else self.or_strategy
    
    def _process_results(self, results: Results) -> List[SearchResult]:
        """
        Convert Whoosh results to SearchResult objects
        """
        return [
            SearchResult(
                title=r["title"],
                abstract=r["abstract"],
                score=r.score,
                rank=r.rank
            )
            for r in results
        ]

def format_results(results: List[SearchResult]) -> None:
    print("\n---------------------")
    print("     Results     ")
    print("---------------------")
    
    for result in results:
        print(f"Paper: {result.title}")
        print(f"Abstract: {result.abstract}")
        print(f"Score: {result.score}")
        print("---------------------")

def interactive_search() -> None:
    """
    Run interactive search session
    """
    engine = WhooshSearchEngine()
    
    try:
        query = input("Insert your query: ")
        results = engine.search(query)
        
        if not results:
            correction = engine.suggest_correction(query)
            if correction:
                print(f"\nMaybe did you mean: {correction} ?")
        
        format_results(results)
        
    except Exception as e:
        logger.error(f"Search session error: {str(e)}")

def process_query(query: str, limit: int = 10) -> List[Dict]:
    """
    Process a search query and return results
    
    Args:
        query: Search query string
        limit: Maximum number of results to return
        
    Returns:
        List of dictionaries containing search results
    """
    try:
        engine = WhooshSearchEngine()
        results = engine.search(query, limit=limit)
        
        return [
            {
                "title": result.title,
                "abstract": result.abstract,
                "score": result.score
            }
            for result in results
        ]
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return []

if __name__ == '__main__':
    interactive_search()
