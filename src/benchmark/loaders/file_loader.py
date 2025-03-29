"""File-based query loader for benchmarking."""

import re
from pathlib import Path
from typing import List, TextIO, Dict, Optional
from ..engines.base import BenchmarkQuery

class FileQueryLoader:
    """
    Loads benchmark queries from files
    """
    
    def __init__(self, 
                 natural_query_path: str = "./evaluation/queries/query_natural_lang.txt",
                 structured_query_path: str = "./evaluation/queries/query_benchmark.txt",
                 relevance_path: str = "./evaluation/queries/query_relevance.txt"):
        self.natural_query_path = Path(natural_query_path)
        self.structured_query_path = Path(structured_query_path)
        self.relevance_path = Path(relevance_path)
        
        self.query_pattern = re.compile(r'^query\s+([^#]+?)\s*(?:#.*)?$', re.IGNORECASE)
        self.entry_pattern = re.compile(r'^(\d+)\s+(\w+)\s+(\w+)\s*(?:#.*)?$')
    
    def _read_lines(self, filepath: Path) -> List[str]:
        with open(filepath, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f 
                   if line.strip() and not line.strip().startswith('#')]
    
    def _load_relevance_data(self) -> Dict[int, Dict[str, float]]:
        try:
            relevance_data = {}
            lines = self._read_lines(self.relevance_path)
            
            for i, line in enumerate(lines):
                try:
                    if '%' in line:
                        line = line.split('%')[0].strip()
                    
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) != 3:
                        print(f"Warning: Skipping invalid line {i+1}: expected 3 parts, got {len(parts)}")
                        continue
                    
                    relevance_data[i] = {
                        "precision": float(parts[0]),
                        "recall": float(parts[1]),
                        "relevant_docs": int(parts[2])
                    }
                except (ValueError, IndexError) as e:
                    print(f"Warning: Skipping invalid line {i+1}: {str(e)}")
                    continue
            
            return relevance_data
        except FileNotFoundError:
            print(f"Warning: Relevance file {self.relevance_path} not found. Using default values.")
            return {}
        except Exception as e:
            print(f"Error loading relevance data: {str(e)}")
            return {}
    
    def load_queries(self) -> List[BenchmarkQuery]:
        try:
            natural_queries = self._read_lines(self.natural_query_path)
            structured_queries = self._read_lines(self.structured_query_path)
            relevance_data = self._load_relevance_data()
            
            queries = []
            for i, (natural, structured) in enumerate(zip(natural_queries, structured_queries)):
                relevance = relevance_data.get(i, {
                    "precision": 0.0,
                    "recall": 0.0,
                    "relevant_docs": 0
                })
                
                queries.append(BenchmarkQuery(
                    natural_language=natural.strip(),
                    structured_query=structured.strip(),
                    expected_precision=relevance["precision"],
                    expected_recall=relevance["recall"],
                    expected_relevant_docs=relevance["relevant_docs"]
                ))
            
            return queries
            
        except Exception as e:
            print(f"Error loading queries: {str(e)}")
            return []
    
    def parse_benchmark_file(self, file: TextIO) -> List[BenchmarkQuery]:
        queries: List[BenchmarkQuery] = []
        current_query: Optional[str] = None
        current_relevance: List[Dict] = []
        
        for line_num, line in enumerate(file, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            if match := self.query_pattern.match(line):
                if current_query is not None:
                    queries.append(BenchmarkQuery(
                        natural_language=current_query,
                        structured_query=current_query,
                        expected_precision=1.0,
                        expected_recall=1.0,
                        expected_relevant_docs=len(current_relevance),
                        metadata={"relevance_data": current_relevance}
                    ))
                
                current_query = match.group(1).strip()
                current_relevance = []
                
            elif match := self.entry_pattern.match(line):
                if current_query is None:
                    raise ValueError(f"Found relevance entry before query at line {line_num}")
                
                relevance, source, doc_id = match.groups()
                current_relevance.append({
                    "relevance": int(relevance),
                    "source": source,
                    "doc_id": doc_id
                })
            else:
                raise ValueError(f"Invalid syntax at line {line_num}: {line}")
        
        if current_query is not None:
            queries.append(BenchmarkQuery(
                natural_language=current_query,
                structured_query=current_query,
                expected_precision=1.0,
                expected_recall=1.0,
                expected_relevant_docs=len(current_relevance),
                metadata={"relevance_data": current_relevance}
            ))
        
        return queries 