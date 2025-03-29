from dataclasses import dataclass
from typing import List, Dict
from ..engines.base import BenchmarkResult, SearchResult

@dataclass
class MetricResult:
    """
    Container for metric results
    """
    precision: float
    recall: float
    ndcg: float
    average_precision: float
    execution_time: float
    result_count: int

class MetricsEvaluator:
    """
    Evaluates search results using basic IR metrics
    """
    
    def compute_precision_recall(self, results: List[SearchResult], 
                               expected_relevant: int) -> tuple[float, float]:
        if not results or expected_relevant == 0:
            return 0.0, 0.0
        
        relevant_results = sum(1 for r in results if r.relevance == 1.0)
        
        precision = relevant_results / len(results) if results else 0.0
        recall = relevant_results / expected_relevant if expected_relevant > 0 else 0.0
        
        return precision, recall
    
    def compute_average_precision(self, results: List[SearchResult]) -> float:
        """
        Compute Average Precision
        """
        if not results:
            return 0.0
        
        relevant_count = sum(1 for r in results if r.relevance == 1.0)
        if relevant_count == 0:
            return 0.0
        
        running_sum = 0.0
        for i, result in enumerate(results, 1):
            if result.relevance == 1.0:
                relevant_so_far = sum(1 for r in results[:i] if r.relevance == 1.0)
                running_sum += relevant_so_far / i
        
        return running_sum / relevant_count
    
    def compute_ndcg(self, results: List[SearchResult]) -> float:
        """
        Compute Normalized Discounted Cumulative Gain
        """
        if not results:
            return 0.0
            
        scores = [r.relevance for r in results]
        
        dcg = scores[0]
        for i, score in enumerate(scores[1:], 1):
            dcg += score / (i + 1)
            
        ideal_scores = sorted(scores, reverse=True)
        idcg = ideal_scores[0]
        for i, score in enumerate(ideal_scores[1:], 1):
            idcg += score / (i + 1)
        
        return dcg / idcg if idcg > 0 else 0.0

    def evaluate(self, benchmark_result: BenchmarkResult) -> MetricResult:
        """
        Evaluate a benchmark result using multiple metrics
        """
        results = benchmark_result.results
        query = benchmark_result.query
        
        precision, recall = self.compute_precision_recall(
            results, 
            query.expected_relevant_docs
        )
        
        ndcg = self.compute_ndcg(results)
        ap = self.compute_average_precision(results)
        
        return MetricResult(
            precision=precision,
            recall=recall,
            ndcg=ndcg,
            average_precision=ap,
            execution_time=benchmark_result.total_time,
            result_count=len(results)
        )

    def evaluate_all(self, benchmark_results: List[BenchmarkResult]) -> Dict[str, MetricResult]:
        """
        Evaluate multiple benchmark results
        """
        return {
            result.query.natural_language: self.evaluate(result)
            for result in benchmark_results
        } 