import time
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path

from .engines.base import BenchmarkEngine, BenchmarkQuery, BenchmarkResult
from .loaders.file_loader import FileQueryLoader
from .metrics.evaluator import MetricsEvaluator, MetricResult

class BenchmarkRunner:
    """
    Runs benchmarks and collects results
    """
    
    def __init__(self, 
                 engine: BenchmarkEngine,
                 loader: FileQueryLoader,
                 evaluator: MetricsEvaluator):
        self.engine = engine
        self.loader = loader
        self.evaluator = evaluator
        
    def _save_results(self, 
                     raw_results: List[BenchmarkResult],
                     metrics: Dict[str, MetricResult]) -> None:
        """Save benchmark results to file
        
        Args:
            raw_results: Raw benchmark results
            metrics: Computed metrics
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("./evaluation/results")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        raw_output = output_dir / f"raw_results_{timestamp}.json"
        with open(raw_output, "w") as f:
            json.dump(
                {
                    "timestamp": timestamp,
                    "results": [
                        {
                            "query": result.query.natural_language,
                            "structured_query": result.query.structured_query,
                            "total_time": result.total_time,
                            "results": [
                                {
                                    "title": r.title,
                                    "score": r.score,
                                    "position": r.position,
                                    "relevance": r.relevance
                                }
                                for r in result.results
                            ]
                        }
                        for result in raw_results
                    ]
                },
                f,
                indent=2
            )
        
        metrics_output = output_dir / f"metrics_{timestamp}.json"
        with open(metrics_output, "w") as f:
            json.dump(
                {
                    "timestamp": timestamp,
                    "metrics": {
                        query: {
                            "precision": result.precision,
                            "recall": result.recall,
                            "ndcg": result.ndcg,
                            "average_precision": result.average_precision,
                            "execution_time": result.execution_time,
                            "result_count": result.result_count
                        }
                        for query, result in metrics.items()
                    }
                },
                f,
                indent=2
            )
    
    def run(self, 
            save_results: bool = True,
            progress_callback: Optional[Any] = None) -> Dict[str, MetricResult]:
        """Run the complete benchmark suite
        
        Args:
            save_results: Whether to save results to file
            progress_callback: Optional callback for progress
            
        Returns:
            Dictionary mapping queries to their metrics
        """
        queries = self.loader.load_queries()
        if not queries:
            raise ValueError("No queries loaded")
        
        start_time = time.time()
        raw_results = []
        total_queries = len(queries)
        
        for i, query in enumerate(queries):
            try:
                result = self.engine.run_query(query)
                raw_results.append(result)
                
                if progress_callback:
                    progress = int((i + 1) / total_queries * 100)
                    progress_callback(progress)
            except Exception as e:
                print(f"Error running query '{query.natural_language}': {str(e)}")
                continue
        
        total_time = time.time() - start_time
        
        metrics = self.evaluator.evaluate_all(raw_results)
        
        if save_results:
            self._save_results(raw_results, metrics)
        
        return metrics 