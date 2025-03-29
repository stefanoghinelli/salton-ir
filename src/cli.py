import time
import click
from pathlib import Path
from typing import Callable
import importlib.util
import sys

from .config import DATA_DIR, BENCHMARK_DIR, INDEX_DIR

class OrderedGroup(click.Group):
    def __init__(self, name=None, commands=None, **attrs):
        super(OrderedGroup, self).__init__(name, commands, **attrs)
        self.commands = commands or {}
        self.command_order = [
            'fetch',
            'preprocess',
            'index',
            'search',
            'stats',
            'benchmark'
        ]

    def list_commands(self, ctx):
        return self.command_order

def is_module_available(module_name):
    """
    Check if a module is available
    """
    return importlib.util.find_spec(module_name) is not None

def import_or_none(module_name):
    if is_module_available(module_name):
        return importlib.import_module(module_name)
    return None

def print_header(text: str):
    click.echo("\n" + "=" * 50)
    click.echo(f"  {text}")
    click.echo("=" * 50 + "\n")

@click.group(cls=OrderedGroup)
def cli():
    """
    Salton: A thematic information retrieval system
    """
    pass

@cli.command()
@click.option('--limit', '-l', default=100, help='Number of papers to fetch')
def fetch(limit: int):
    """
    Fetch papers from CORE repository
    """
    try:
        from .scraping import scrape_papers
        
        print_header("Fetching Papers")
        
        with click.progressbar(length=limit, label='Fetching papers') as bar:
            def progress_callback(current):
                bar.update(current)
            
            scrape_papers(limit, progress_callback)
            
    except ImportError as e:
        click.echo(f"\nError: Missing dependencies for fetching papers. {str(e)}")
        click.echo("Please install the required dependencies: pip install requests lxml")
    except Exception as e:
        click.echo(f"\nError fetching papers: {str(e)}")

@cli.command()
def preprocess():
    """
    Preprocess fetched papers
    """
    try:
        from .preprocessing import preprocess_papers
        
        print_header("Preprocessing Papers")
        
        with click.progressbar(length=100, label='Preprocessing papers') as bar:
            def progress_callback(percent):
                bar.update(percent - bar.pos)
            
            preprocess_papers(progress_callback)
            
    except Exception as e:
        click.echo(f"\nError preprocessing papers: {str(e)}")

@cli.command()
def index():
    """
    Build the index
    """
    try:
        from .indexing import build_index
        
        print_header("Indexing Papers")
        
        with click.progressbar(length=100, label='Indexing papers') as bar:
            def progress_callback(percent):
                bar.update(percent - bar.pos)
            
            build_index(progress_callback)
            
    except Exception as e:
        click.echo(f"\nError indexing papers: {str(e)}")

@cli.command()
@click.option('--query', '-q', prompt='Enter your search query', help='Search query')
@click.option('--limit', '-l', default=10, help='Number of results to show')
def search(query: str, limit: int):
    """
    Search for papers
    """
    try:
        from .query_processing import process_query
        
        print_header(f"Results for: {query}")
        
        results = process_query(query, limit)
        
        if not results:
            click.echo("No results found.")
            return
            
        for i, result in enumerate(results, 1):
            click.echo(f"{i}. Title: {result['title']}")
            click.echo(f"   Score: {result['score']:.4f}")
            if 'abstract' in result:
                click.echo(f"   Abstract: {result['abstract'][:150]}...")
            click.echo("")
            
    except Exception as e:
        click.echo(f"\nError searching: {str(e)}")

@cli.command()
def stats():
    """
    Show statistics
    """
    try:
        from .indexing import get_index_stats
        
        print_header("Statistics")
        
        try:
            index_stats = get_index_stats()
            
            click.echo("Index Statistics:")
            click.echo(f"• Documents indexed: {index_stats['doc_count']}")
            click.echo(f"• Unique terms: {index_stats['unique_terms']}")
            click.echo(f"• Index size: {index_stats['index_size_mb']:.2f} MB")
        except Exception as e:
            click.echo("Index Statistics:")
            click.echo(f"• Error retrieving index statistics: {str(e)}")
        
        data_dir = Path(DATA_DIR)
        raw_count = len(list(data_dir.glob("raw/*.json"))) if data_dir.exists() else 0
        processed_count = len(list(data_dir.glob("processed/*.json"))) if data_dir.exists() else 0
        
        click.echo("\nData Statistics:")
        click.echo(f"• Raw papers: {raw_count}")
        click.echo(f"• Processed papers: {processed_count}")
        
        benchmark_dir = Path(BENCHMARK_DIR)
        query_sets = len(list(benchmark_dir.glob("*.json"))) if benchmark_dir.exists() else 0
        
        click.echo("\nBenchmark Statistics:")
        click.echo(f"• Available query sets: {query_sets}")
        
    except Exception as e:
        click.echo(f"\nError getting stats: {str(e)}")

@cli.command()
@click.option('--save/--no-save', default=True, help='Save benchmark results to file')
@click.option('--detailed/--simple', default=False, help='Show detailed results')
def benchmark(save: bool, detailed: bool):
    """
    Run benchmarks (experimental)
    """
    try:
        print_header("Running benchmarks (experimental)")
        
        try:
            from .benchmark.runner import BenchmarkRunner
            from .benchmark.engines.whoosh_engine import WhooshBenchmarkEngine
            from .benchmark.loaders.file_loader import FileQueryLoader
            from .benchmark.metrics.evaluator import MetricsEvaluator
            from whoosh import index
        except ImportError as e:
            click.echo(f"\nError: Missing dependencies for benchmarking. {str(e)}")
            return
        
        def progress_callback(percent):
            if hasattr(progress_callback, 'bar'):
                progress_callback.bar.update(percent - progress_callback.bar.pos)
        
        with click.progressbar(length=100, label='Running benchmarks') as bar:
            progress_callback.bar = bar
            
            try:
                query_loader = FileQueryLoader()
                queries = query_loader.load_queries()
                if not queries:
                    click.echo("\nNo benchmark queries found. Please create query files in the evaluation/queries directory.")
                    return
                
                ix = index.open_dir(INDEX_DIR)
                engine = WhooshBenchmarkEngine(index=ix)
                evaluator = MetricsEvaluator()
                
                runner = BenchmarkRunner(engine, query_loader, evaluator)
                results = runner.run(save_results=save, progress_callback=progress_callback)
            except Exception as e:
                click.echo(f"\nError during benchmark initialization: {str(e)}")
                return
            
        click.echo("\nBenchmark completed!")
        
        if not results:
            click.echo("No results to display.")
            return
            
        if detailed:
            click.echo("\nDetailed Results:\n")
            for query, metrics in results.items():
                click.echo(f"Query: {query}")
                click.echo(f"  Precision: {metrics.precision:.4f}")
                click.echo(f"  Recall: {metrics.recall:.4f}")
                click.echo(f"  NDCG: {metrics.ndcg:.4f}")
                click.echo(f"  Average Precision: {metrics.average_precision:.4f}")
                click.echo(f"  Execution Time: {metrics.execution_time:.4f}s")
                click.echo(f"  Result Count: {metrics.result_count}")
                click.echo("")
        else:
            click.echo("\nSummary Results:\n")
            avg_precision = sum(m.precision for m in results.values()) / len(results) if results else 0
            avg_recall = sum(m.recall for m in results.values()) / len(results) if results else 0
            avg_ndcg = sum(m.ndcg for m in results.values()) / len(results) if results else 0
            
            click.echo(f"Average Precision: {avg_precision:.4f}")
            click.echo(f"Average Recall: {avg_recall:.4f}")
            click.echo(f"Average NDCG: {avg_ndcg:.4f}")
            
    except Exception as e:
        click.echo(f"\nError running benchmark: {str(e)}")

def main():
    cli()

if __name__ == '__main__':
    main() 