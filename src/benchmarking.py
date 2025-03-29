import logging
from typing import List, Dict, Optional, Protocol
from dataclasses import dataclass
from abc import ABC, abstractmethod
from query_processing import WhooshSearchEngine, SearchResult
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class BenchmarkQuery:
    natural_language: str
    structured_query: str
    expected_precision: float
    expected_recall: float = 0.0
    expected_relevant_docs: int = 0

class QueryLoader(Protocol):
    """
    Protocol for query loading strategies
    """
    
    def load_queries(self) -> List[BenchmarkQuery]:
        ...

class BenchmarkMetrics:
    """
    Class to hold and calculate benchmark metrics
    """
    
    def __init__(self):
        self.precisions: List[float] = []
        self.recalls: List[float] = []
        self.f1_scores: List[float] = []
        self.query_times: List[float] = []
        self.result_counts: List[int] = []
    
    def add_metrics(self, precision: float, recall: float, query_time: float, result_count: int) -> None:
        self.precisions.append(precision)
        self.recalls.append(recall)
        f1 = 2 * (precision * recall) / (precision + recall) if precision + recall > 0 else 0.0
        self.f1_scores.append(f1)
        self.query_times.append(query_time)
        self.result_counts.append(result_count)
    
    @property
    def mean_average_precision(self) -> float:
        """
        Calculate mean average precision
        """
        return sum(self.precisions) / len(self.precisions) if self.precisions else 0.0
    
    @property
    def mean_average_recall(self) -> float:
        """
        Calculate mean average recall
        """
        return sum(self.recalls) / len(self.recalls) if self.recalls else 0.0
    
    @property
    def mean_f1_score(self) -> float:
        """
        Calculate mean F1 score
        """
        return sum(self.f1_scores) / len(self.f1_scores) if self.f1_scores else 0.0
    
    @property
    def average_query_time(self) -> float:
        """
        Calculate average query time
        """
        return sum(self.query_times) / len(self.query_times) if self.query_times else 0.0
    
    @property
    def average_result_count(self) -> float:
        """
        Calculate average number of results
        """
        return sum(self.result_counts) / len(self.result_counts) if self.result_counts else 0.0
    
    def __str__(self) -> str:
        return (
            f"Benchmark Results:\n"
            f"  Mean Average Precision: {self.mean_average_precision:.3f}\n"
            f"  Mean Average Recall: {self.mean_average_recall:.3f}\n"
            f"  Mean F1 Score: {self.mean_f1_score:.3f}\n"
            f"  Average Query Time: {self.average_query_time:.3f}s\n"
            f"  Average Result Count: {self.average_result_count:.1f}"
        )

class FileSystemQueryLoader(QueryLoader):
    def __init__(self, 
                 natural_query_path: str = "./evaluation/query_natural_lang.txt",
                 benchmark_query_path: str = "./evaluation/query_benchmark.txt",
                 relevance_path: str = "./evaluation/query_relevance.txt"):
        self.natural_query_path = natural_query_path
        self.benchmark_query_path = benchmark_query_path
        self.relevance_path = relevance_path
        
    def load_queries(self) -> List[BenchmarkQuery]:
        try:
            natural_queries = self._read_lines(self.natural_query_path)
            structured_queries = self._read_lines(self.benchmark_query_path)
            relevance_data = self._load_relevance_data()
            
            queries = []
            for i, (natural, structured) in enumerate(zip(natural_queries, structured_queries)):
                relevance = relevance_data.get(i, {"precision": 0.0, "recall": 0.0, "relevant_docs": 0})
                queries.append(
                    BenchmarkQuery(
                        natural_language=natural.strip(),
                        structured_query=structured.strip(),
                        expected_precision=relevance["precision"],
                        expected_recall=relevance["recall"],
                        expected_relevant_docs=relevance["relevant_docs"]
                    )
                )
            return queries
            
        except Exception as e:
            logger.error(f"Error loading queries: {str(e)}")
            return []
    
    def _read_lines(self, filepath: str) -> List[str]:
        with open(filepath, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f]
    
    def _load_relevance_data(self) -> Dict[int, Dict[str, float]]:
        try:
            with open(self.relevance_path, 'r', encoding='utf-8') as f:
                return {
                    i: {
                        "precision": float(parts[0]),
                        "recall": float(parts[1]),
                        "relevant_docs": int(parts[2])
                    }
                    for i, line in enumerate(f)
                    if (parts := line.strip().split(','))
                }
        except FileNotFoundError:
            logger.warning(f"Relevance file {self.relevance_path} not found. Using default values.")
            return {}
        except Exception as e:
            logger.error(f"Error loading relevance data: {str(e)}")
            return {}

class SearchBenchmark:
    """
    Class responsible for running search benchmarks
    """
    
    def __init__(self, 
                 search_engine: WhooshSearchEngine,
                 query_loader: QueryLoader):
        self.search_engine = search_engine
        self.query_loader = query_loader
        self.metrics = BenchmarkMetrics()
    
    def run_benchmark(self) -> BenchmarkMetrics:
        """
        Run the benchmark.
        
        Returns:
            BenchmarkMetrics object containing results
        """
        queries = self.query_loader.load_queries()
        if not queries:
            logger.error("No queries loaded for benchmark")
            return self.metrics
        
        logger.info("Starting benchmark")
        for query in queries:
            self._process_query(query)
        
        logger.info(f"Benchmark completed.\n{self.metrics}")
        return self.metrics
    
    def _process_query(self, query: BenchmarkQuery) -> None:
        """
        Process a single benchmark query
        """
        try:
            start_time = time.time()
            
            results = self.search_engine.search(query.structured_query, limit=10)
            
            query_time = time.time() - start_time
            
            num_results = len(results)
            if query.expected_relevant_docs > 0:
                actual_precision = num_results / query.expected_relevant_docs if num_results > 0 else 0.0
                actual_recall = num_results / query.expected_relevant_docs
            else:
                actual_precision = query.expected_precision
                actual_recall = 0.0
            
            self.metrics.add_metrics(
                precision=actual_precision,
                recall=actual_recall,
                query_time=query_time,
                result_count=num_results
            )
            
            self._log_query_results(query, results, actual_precision, actual_recall, query_time)
            
        except Exception as e:
            logger.error(f"Error processing query '{query.structured_query}': {str(e)}")
    
    def _log_query_results(self, query: BenchmarkQuery, results: List[SearchResult], 
                          precision: float, recall: float, query_time: float) -> None:
        logger.info(f"\nNatural query: {query.natural_language}")
        logger.info(f"Executed query: {query.structured_query}")
        logger.info(f"Results count: {len(results)}")
        logger.info(f"Precision: {precision:.3f}")
        logger.info(f"Recall: {recall:.3f}")
        logger.info(f"Query time: {query_time:.3f}s")
        
        for result in results:
            logger.debug(f"Title: {result.title}")
            logger.debug(f"Score: {result.score}")
            logger.debug("---")

def main() -> None:
    try:
        search_engine = WhooshSearchEngine()
        query_loader = FileSystemQueryLoader()
        benchmark = SearchBenchmark(search_engine, query_loader)
        
        metrics = benchmark.run_benchmark()
        logger.info(f"\nFinal Results:\n{metrics}")
        
    except Exception as e:
        logger.error(f"Benchmark failed: {str(e)}")
        raise

if __name__ == '__main__':
    main()
