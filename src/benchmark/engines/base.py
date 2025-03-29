from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class BenchmarkQuery:
    natural_language: str
    structured_query: str
    expected_precision: float
    expected_recall: float = 0.0
    expected_relevant_docs: int = 0
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class SearchResult:
    """
    A single search result with its relevance metrics
    """
    query: str
    result_id: str
    score: float
    position: int
    title: str = ""
    relevance: float = 0.0
    execution_time: float = 0.0

@dataclass
class BenchmarkResult:
    query: BenchmarkQuery
    results: List[SearchResult]
    total_time: float
    timestamp: datetime = datetime.now()

class BenchmarkEngine(ABC):
    """
    Abstract base class for benchmark engines
    """    
    
    @abstractmethod
    def prepare(self) -> None:
        """
        Prepare the engine for benchmarking
        """
        pass
    
    @abstractmethod
    def run_query(self, query: BenchmarkQuery) -> BenchmarkResult:
        """
        Run a single benchmark query
        """
        pass
    
    @abstractmethod
    def run_benchmark(self, queries: List[BenchmarkQuery]) -> List[BenchmarkResult]:
        """
        Run the complete benchmark suite
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """
        Clean up resources after benchmarking
        """
        pass 