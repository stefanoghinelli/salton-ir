import os
import sys
import logging
from datetime import datetime
from typing import List, Optional, Dict, Protocol, runtime_checkable, Callable
from whoosh.index import create_in, Index, exists_in, open_dir
from whoosh.fields import Schema, TEXT, DATETIME, analysis
from whoosh.writing import IndexWriter
from whoosh.searching import Searcher
from whoosh.qparser import QueryParser
from dataclasses import dataclass
from abc import ABC, abstractmethod

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class IndexableDocument:
    """
    Data class to hold document information for indexing
    """
    title: str
    content: str
    abstract: str
    date: datetime = datetime.now()

@runtime_checkable
class DocumentLoader(Protocol):
    """
    Protocol for document loading strategies
    """
    
    def load_document(self, filename: str) -> Optional[IndexableDocument]:
        ...

class BaseIndexer(ABC):
    """
    Abstract base class for document indexers
    """
    
    @abstractmethod
    def index_documents(self) -> int:
        pass
    
    @abstractmethod
    def search(self, query_string: str, field: str = "content") -> List[Dict]:
        pass

class FileSystemDocumentLoader(DocumentLoader):
    """
    Document loader that loads from the filesystem
    """
    
    def __init__(self, src_folder: str):
        self.src_folder = src_folder
    
    def load_document(self, filename: str) -> Optional[IndexableDocument]:
        """
        Load a document from the filesystem
        """
        try:
            title = filename[:-4] if filename.endswith('.txt') else filename
            file_path = os.path.join(self.src_folder, filename)

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            return IndexableDocument(
                title=title,
                content=content,
                abstract=content
            )

        except FileNotFoundError as e:
            logger.error(f"File not found: {e.filename}")
        except IOError as e:
            logger.error(f"IO error while loading document: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error while loading document: {str(e)}")
        
        return None

class IndexManager:
    """
    Class responsible for managing the Whoosh index
    """
    
    def __init__(self, index_dir: str, schema: Schema):
        self.index_dir = index_dir
        self.schema = schema
        self.index = self._create_or_open_index()
    
    def _create_or_open_index(self) -> Index:
        """
        Create a new index or open an existing one
        """
        if not os.path.exists(self.index_dir):
            os.makedirs(self.index_dir)
            logger.info(f"Created index directory: {self.index_dir}")
            return create_in(self.index_dir, self.schema)
        elif exists_in(self.index_dir):
            return open_dir(self.index_dir)
        else:
            return create_in(self.index_dir, self.schema)
    
    def get_writer(self) -> IndexWriter:
        """
        Get an index writer
        """
        return self.index.writer()
    
    def get_searcher(self) -> Searcher:
        """
        Get an index searcher
        """
        return self.index.searcher()

class WhooshIndexer(BaseIndexer):
    """
    Whoosh-based implementation of document indexer
    """

    def __init__(self, 
                 src_folder: str = './data/txt/',
                 dst_folder: str = './data/indexes/',
                 analyzer: Optional[analysis.Analyzer] = None,
                 document_loader: Optional[DocumentLoader] = None):
        """
        Initialize the Whoosh indexer
        """
        self.src_folder = src_folder
        self.dst_folder = dst_folder
        self.document_loader = document_loader or FileSystemDocumentLoader(src_folder)
        self.analyzer = analyzer or analysis.StemmingAnalyzer()
        
        self.schema = Schema(
            title=TEXT(stored=True, analyzer=self.analyzer, spelling=True),
            abstract=TEXT(stored=True, analyzer=self.analyzer, spelling=True),
            content=TEXT(stored=True, analyzer=self.analyzer, spelling=True),
            date=DATETIME(stored=True)
        )
        
        self.index_manager = IndexManager(dst_folder, self.schema)

    def index_documents(self, progress_callback: Optional[Callable[[int], None]] = None) -> int:
        """
        Index all documents in the source folder with progress
        """
        files = [f for f in os.listdir(self.src_folder) if f.endswith('.txt')]
        if not files:
            logger.error("Source directory is empty")
            raise ValueError("Source directory is empty")

        writer = self.index_manager.get_writer()
        try:
            return self._process_documents(files, writer, progress_callback)
        except Exception as e:
            logger.error(f"Error during indexing: {str(e)}")
            writer.cancel()
            raise

    def _process_documents(self, 
                         files: List[str], 
                         writer: IndexWriter,
                         progress_callback: Optional[Callable[[int], None]] = None) -> int:
        """
        Process and index documents with progress
        """
        indexed_count = 0
        total_files = len(files)
        
        for i, f_name in enumerate(files):
            try:
                doc = self.document_loader.load_document(f_name)
                if doc:
                    self._add_document_to_index(writer, doc)
                    indexed_count += 1
                    logger.debug(f"Indexed document: {doc.title}")
                
                if progress_callback:
                    progress = int((i + 1) / total_files * 100)
                    progress_callback(progress)
                    
            except Exception as e:
                logger.error(f"Failed to index document {f_name}: {str(e)}")
                continue

        writer.commit()
        logger.info(f"Successfully indexed {indexed_count} documents")
        return indexed_count

    def _add_document_to_index(self, writer: IndexWriter, doc: IndexableDocument) -> None:
        writer.add_document(
            title=doc.title,
            content=doc.content,
            abstract=doc.abstract,
            date=doc.date
        )

    def search(self, query_string: str, field: str = "content") -> List[Dict]:
        with self.index_manager.get_searcher() as searcher:
            query = QueryParser(field, self.schema).parse(query_string)
            results = searcher.search(query)
            return [dict(result) for result in results]

def get_index_stats() -> Dict[str, float]:
    """Get statistics about the Whoosh index
    Returns:
        Dict containing:
        - doc_count: Number of documents in the index
        - unique_terms: Number of unique terms
        - index_size_mb: Size of the index in megabytes
    """
    try:
        indexer = WhooshIndexer()
        index = indexer.index_manager.index
        
        doc_count = index.doc_count()
        
        unique_terms = 0
        with index.reader() as reader:
            for field in ['title', 'content', 'abstract']:
                if field in reader.schema:
                    field_terms = set()
                    for term in reader.lexicon(field):
                        field_terms.add(term)
                    unique_terms += len(field_terms)
        
        index_size = 0
        index_dir = indexer.dst_folder
        for dirpath, _, filenames in os.walk(index_dir):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                index_size += os.path.getsize(fp)
        
        index_size_mb = index_size / (1024 * 1024)
        
        return {
            "doc_count": doc_count,
            "unique_terms": unique_terms,
            "index_size_mb": index_size_mb
        }
        
    except Exception as e:
        logger.error(f"Error getting index statistics: {str(e)}")
        return {
            "doc_count": 0,
            "unique_terms": 0,
            "index_size_mb": 0.0
        }

def build_index(progress_callback: Optional[Callable[[int], None]] = None) -> None:
    """
    Build the search index from processed documents
    Args:
        progress_callback: Optional callback for progress
    """
    try:
        indexer = WhooshIndexer(
            src_folder='./data/txt',
            dst_folder='./data/indexes'
        )
        
        num_indexed = indexer.index_documents(progress_callback=progress_callback)
        logger.info(f"Indexing completed successfully. Indexed {num_indexed} documents.")
        
    except Exception as e:
        logger.error(f"Error building index: {str(e)}")
        raise

if __name__ == '__main__':
    try:
        build_index()
    except Exception as e:
        logger.error(f"Indexing failed: {str(e)}")
        sys.exit(1)
