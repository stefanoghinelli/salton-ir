import os
import sys
import logging
import pdftotext
from nltk import word_tokenize, pos_tag
from nltk.corpus import wordnet
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from typing import List, Optional, Dict, Tuple, Protocol, runtime_checkable, Callable
from dataclasses import dataclass
from abc import ABC, abstractmethod

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@dataclass
class ProcessedDocument:
    """
    Data class to hold processed document information
    """
    title: str
    tokens: List[str]
    raw_text: str
    disambiguated_terms: Optional[List[Tuple[str, Optional[str]]]] = None

@runtime_checkable
class TextProcessor(Protocol):
    """
    Protocol defining the interface for text processors
    """
    
    def process_text(self, text: str) -> List[str]:
        ...

class BaseDocumentProcessor(ABC):
    """
    Abstract base class for document processors
    """
    
    @abstractmethod
    def process_documents(self, progress_callback: Optional[Callable[[int], None]] = None) -> List[ProcessedDocument]:
        pass
    
    @abstractmethod
    def process_single_document(self, filename: str) -> Optional[ProcessedDocument]:
        pass

class NLTKTextProcessor:
    """
    NLTK-based text processor implementation
    """
    
    def __init__(self):
        self.stops = set(stopwords.words("english"))
        self.lemmatizer = WordNetLemmatizer()
    
    def process_text(self, text: str) -> List[str]:
        """Process text using NLTK tokenization and lemmatization."""
        tokens = word_tokenize(text)
        return [
            self.lemmatizer.lemmatize(token.lower()) 
            for token in tokens 
            if token.isalpha() and token.lower() not in self.stops
        ]

class WordSenseDisambiguator:
    """
    Class responsible for word sense disambiguation
    """
    
    def __init__(self):
        self._pos_map = {
            "J": wordnet.ADJ,
            "V": wordnet.VERB,
            "N": wordnet.NOUN,
            "R": wordnet.ADV
        }
    
    def disambiguate(self, terms: List[str]) -> List[Tuple[str, Optional[str]]]:
        """
        Disambiguate a list of terms and return Synset names
        """
        tagged_terms = pos_tag(terms)
        results = []
        
        for idx, (term, tag) in enumerate(tagged_terms):
            best_sense = self._find_best_sense(term, tag, tagged_terms, idx)
            results.append((term, best_sense.name() if best_sense else None))
            self._log_disambiguation_result(term, best_sense)
        
        return results
    
    def _find_best_sense(self, term: str, tag: str, 
                         tagged_terms: List[Tuple[str, str]], 
                         idx: int) -> Optional[wordnet.synsets]:
        """
        Find the best sense for a term based on context
        """
        best_sense = None
        max_score = 0.0
        wordnet_pos = self._get_wordnet_pos(tag)
        
        start = max(0, idx - 5)
        end = min(len(tagged_terms), idx + 6)
        context_terms = [t for t, _ in tagged_terms[start:end] if t != term]
        
        for sense in wordnet.synsets(term, pos=wordnet_pos):
            context_score = self._compute_context_score(sense, context_terms)
            if context_score > max_score:
                best_sense = sense
                max_score = context_score
        
        return best_sense
    
    def _compute_context_score(self, sense, context_terms: List[str]) -> float:
        """
        Compute context similarity score
        """
        return sum(
            max(
                (similarity for context_sense in wordnet.synsets(context_term)
                 if (similarity := self._safe_similarity(sense, context_sense)) is not None),
                default=0.0
            )
            for context_term in context_terms
        )
    
    def _safe_similarity(self, sense1, sense2) -> Optional[float]:
        """
        Safely compute path similarity between two senses
        """
        try:
            similarity = sense1.path_similarity(sense2)
            return similarity if similarity is not None else 0.0
        except Exception:
            return None
    
    def _get_wordnet_pos(self, treebank_tag: str) -> str:
        """
        Convert Penn Treebank POS tags to WordNet POS tags
        """
        return self._pos_map.get(treebank_tag[0], wordnet.NOUN)
    
    def _log_disambiguation_result(self, term: str, sense) -> None:
        if sense:
            logger.debug(f"Disambiguated '{term}' → {sense.name()} ({sense.definition()})")
        else:
            logger.debug(f"Could not disambiguate '{term}'")

class PDFDocumentProcessor(BaseDocumentProcessor):
    """
    Class responsible for processing PDF documents
    """
    
    def __init__(self, 
                 src_folder: str = "./data/pdf_downloads/", 
                 dst_folder: str = "./data/txt/",
                 text_processor: Optional[TextProcessor] = None,
                 use_disambiguation: bool = False):
        """
        Initialize the PDF document processor
        """
        self.src_folder = src_folder
        self.dst_folder = dst_folder
        self.text_processor = text_processor or NLTKTextProcessor()
        self.disambiguator = WordSenseDisambiguator() if use_disambiguation else None
        
        if not os.path.exists(dst_folder):
            os.makedirs(dst_folder)
            logger.info(f"Created destination directory: {dst_folder}")
    
    def process_documents(self, progress_callback: Optional[Callable[[int], None]] = None) -> List[ProcessedDocument]:
        """
        Process all PDF documents in the source folder with progress
        """
        files = [f for f in os.listdir(self.src_folder) if f.endswith('.pdf')]
        if not files:
            logger.error("Source directory is empty")
            raise ValueError("Source directory is empty")
        
        processed_docs = []
        total_files = len(files)
        
        for i, f_name in enumerate(files):
            if doc := self.process_single_document(f_name):
                processed_docs.append(doc)
                self._save_tokens(doc)
            
            if progress_callback:
                progress = int((i + 1) / total_files * 100)
                progress_callback(progress)
        
        return processed_docs
    
    def process_single_document(self, filename: str) -> Optional[ProcessedDocument]:
        """
        Process a single PDF document
        """
        raw_f_path = os.path.join(self.src_folder, filename)
        logger.info(f"Processing file: {filename}")
        
        try:
            raw_text = self._extract_pdf_text(raw_f_path)
            
            tokens = self.text_processor.process_text(raw_text)
            
            title = os.path.splitext(filename)[0]
            doc = ProcessedDocument(title=title, tokens=tokens, raw_text=raw_text)
            
            if self.disambiguator:
                doc.disambiguated_terms = self.disambiguator.disambiguate(tokens)
            
            return doc
            
        except Exception as e:
            logger.error(f"Error processing {filename}: {e}")
            return None
    
    def _extract_pdf_text(self, filepath: str) -> str:
        """
        Extract text from PDF file
        """
        with open(filepath, "rb") as f:
            pdf = pdftotext.PDF(f)
        return "\n\n".join(pdf)
    
    def _save_tokens(self, doc: ProcessedDocument) -> None:
        """
        Save processed tokens
        """
        tokens_file = os.path.join(self.dst_folder, f"{doc.title}_tokens.txt")
        
        try:
            with open(tokens_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(doc.tokens))
            logger.debug(f"Saved tokens to {tokens_file}")
        except Exception as e:
            logger.error(f"Error saving tokens for {doc.title}: {e}")

def preprocess_papers(progress_callback: Optional[Callable[[int], None]] = None) -> None:
    """
    Process all papers in the download directory
    
    Args:
        progress_callback: Optional callback for progress
    """
    try:
        processor = PDFDocumentProcessor(
            src_folder="./data/pdf_downloads",
            dst_folder="./data/txt",
            use_disambiguation=True
        )
        
        processed_docs = processor.process_documents(progress_callback=progress_callback)
        
        if not processed_docs:
            logger.warning("No documents were processed")
            return
            
        logger.info(f"Successfully processed {len(processed_docs)} documents")
        
    except Exception as e:
        logger.error(f"Error during preprocessing: {str(e)}")
        raise

if __name__ == "__main__":
    preprocess_papers()
