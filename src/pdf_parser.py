#!/usr/bin/env python3
"""
PDF Parser Core - Professional PDF Processing Engine
Adapted from FSS-RAG with enhancements for CLI operations

This module provides comprehensive PDF parsing with multiple backend support,
text extraction, and metadata handling optimized for CLI agent workflows.
"""

import logging
from pathlib import Path
from typing import Iterator, List, Dict, Any, Optional, Tuple, Union
import time
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)

# PDF Backend Imports with graceful fallbacks
try:
    import fitz  # PyMuPDF - preferred for quality and speed
    _has_pymupdf = True
except ImportError:
    _has_pymupdf = False
    logger.debug("PyMuPDF not available")

try:
    import pdfplumber  # Good for tables and layout
    _has_pdfplumber = True
except ImportError:
    _has_pdfplumber = False
    logger.debug("pdfplumber not available")

try:
    import PyPDF2  # Fallback option
    _has_pypdf2 = True
except ImportError:
    _has_pypdf2 = False
    logger.debug("PyPDF2 not available")


class ExtractionMode(Enum):
    """Text extraction modes with different quality/speed tradeoffs."""
    FAST = "fast"                    # Quick extraction, basic formatting
    NORMAL = "normal"                # Standard extraction with layout awareness
    HIGH_QUALITY = "high_quality"    # Best quality extraction
    LAYOUT_AWARE = "layout_aware"    # Preserve complex layouts
    

class ChunkStrategy(Enum):
    """Chunking strategies for PDF content."""
    PAGE = "page"                    # One chunk per page
    PARAGRAPH = "paragraph"          # Chunk by paragraphs
    SECTION = "section"              # By document sections
    FIXED_SIZE = "fixed_size"        # Fixed character count
    SMART = "smart"                  # Adaptive based on content


@dataclass
class PDFMetadata:
    """Comprehensive PDF metadata structure."""
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    keywords: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[datetime] = None
    modification_date: Optional[datetime] = None
    page_count: int = 0
    file_size: int = 0
    is_encrypted: bool = False
    is_linearized: bool = False
    pdf_version: Optional[str] = None


@dataclass
class PageData:
    """Data structure for individual page content."""
    page_number: int
    text: str
    word_count: int
    char_count: int
    has_images: bool = False
    has_tables: bool = False
    extraction_quality: float = 1.0


@dataclass
class ExtractionResult:
    """Complete PDF extraction result."""
    success: bool
    text: str
    pages: List[PageData]
    metadata: PDFMetadata
    backend_used: str
    extraction_time: float
    quality_score: float = 1.0
    error_message: Optional[str] = None


class PDFParser:
    """
    Professional PDF parser with multiple backend support.
    
    Features:
    - Multiple PDF library support (PyMuPDF, pdfplumber, PyPDF2)
    - Smart backend selection and fallback
    - Quality-aware text extraction
    - Comprehensive metadata extraction
    - Performance optimized for CLI operations
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize PDF parser with configuration.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.extraction_mode = ExtractionMode(
            self.config.get('extraction_mode', 'normal')
        )
        self.chunk_strategy = ChunkStrategy(
            self.config.get('chunk_strategy', 'page')
        )
        self.max_chunk_size = self.config.get('max_chunk_size', 4000)
        self.min_chunk_size = self.config.get('min_chunk_size', 100)
        self.quality_threshold = self.config.get('quality_threshold', 0.7)
        
        # Backend selection
        self.preferred_backend = self.config.get('backend', 'auto')
        self.backend = self._select_pdf_backend()
        
        logger.info(f"PDF Parser initialized with backend: {self.backend}")
    
    def _select_pdf_backend(self) -> str:
        """Select the best available PDF library."""
        if self.preferred_backend != 'auto':
            # User specified a backend
            if self.preferred_backend == 'pymupdf' and _has_pymupdf:
                return 'pymupdf'
            elif self.preferred_backend == 'pdfplumber' and _has_pdfplumber:
                return 'pdfplumber'
            elif self.preferred_backend == 'pypdf2' and _has_pypdf2:
                return 'pypdf2'
            else:
                logger.warning(f"Requested backend {self.preferred_backend} not available, falling back to auto")
        
        # Auto-selection based on availability and quality
        if _has_pymupdf:
            return 'pymupdf'  # Best overall performance and quality
        elif _has_pdfplumber:
            return 'pdfplumber'  # Good for complex layouts
        elif _has_pypdf2:
            return 'pypdf2'  # Basic fallback
        else:
            raise ImportError("No PDF parsing libraries available. Install PyMuPDF, pdfplumber, or PyPDF2")
    
    def can_parse(self, file_path: Union[str, Path]) -> bool:
        """Check if file can be parsed."""
        file_path = Path(file_path)
        return file_path.suffix.lower() == '.pdf' and file_path.exists()
    
    def extract_text(self, file_path: Union[str, Path], 
                    pages: Optional[List[int]] = None) -> ExtractionResult:
        """
        Extract text from PDF with comprehensive metadata.
        
        Args:
            file_path: Path to PDF file
            pages: Optional list of specific pages to extract (1-indexed)
            
        Returns:
            ExtractionResult with text, metadata, and quality metrics
        """
        file_path = Path(file_path)
        start_time = time.time()
        
        if not self.can_parse(file_path):
            return ExtractionResult(
                success=False,
                text="",
                pages=[],
                metadata=PDFMetadata(),
                backend_used=self.backend,
                extraction_time=0.0,
                error_message=f"Cannot parse file: {file_path}"
            )
        
        try:
            # Extract metadata first
            metadata = self._extract_metadata(file_path)
            
            # Validate page selection
            if pages:
                pages = [p for p in pages if 1 <= p <= metadata.page_count]
                if not pages:
                    return ExtractionResult(
                        success=False,
                        text="",
                        pages=[],
                        metadata=metadata,
                        backend_used=self.backend,
                        extraction_time=time.time() - start_time,
                        error_message="No valid pages specified"
                    )
            
            # Extract text content
            pages_data = self._extract_pages_content(file_path, metadata, pages)
            
            # Combine all text
            full_text = "\n\n".join(page.text for page in pages_data if page.text.strip())
            
            # Calculate quality score
            quality_score = self._assess_extraction_quality(pages_data, full_text)
            
            extraction_time = time.time() - start_time
            
            result = ExtractionResult(
                success=True,
                text=full_text,
                pages=pages_data,
                metadata=metadata,
                backend_used=self.backend,
                extraction_time=extraction_time,
                quality_score=quality_score
            )
            
            # Retry with different backend if quality is low
            if quality_score < self.quality_threshold and self._has_fallback_backend():
                logger.info(f"Quality {quality_score:.2f} below threshold, trying fallback backend")
                fallback_result = self._try_fallback_extraction(file_path, pages)
                if fallback_result.success and fallback_result.quality_score > quality_score:
                    logger.info(f"Fallback improved quality: {fallback_result.quality_score:.2f}")
                    return fallback_result
            
            logger.info(f"PDF extracted: {file_path.name} - {len(pages_data)} pages in {extraction_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Error extracting PDF {file_path}: {e}")
            return ExtractionResult(
                success=False,
                text="",
                pages=[],
                metadata=PDFMetadata(),
                backend_used=self.backend,
                extraction_time=time.time() - start_time,
                error_message=str(e)
            )
    
    def _extract_metadata(self, file_path: Path) -> PDFMetadata:
        """Extract comprehensive metadata from PDF."""
        metadata = PDFMetadata()
        metadata.file_size = file_path.stat().st_size
        
        try:
            if self.backend == 'pymupdf':
                doc = fitz.open(file_path)
                meta = doc.metadata
                metadata.title = meta.get('title')
                metadata.author = meta.get('author')
                metadata.subject = meta.get('subject')
                metadata.keywords = meta.get('keywords')
                metadata.creator = meta.get('creator')
                metadata.producer = meta.get('producer')
                metadata.page_count = doc.page_count
                metadata.is_encrypted = doc.needs_pass
                metadata.is_linearized = doc.is_pdf
                doc.close()
                
            elif self.backend == 'pdfplumber':
                with pdfplumber.open(file_path) as pdf:
                    metadata.page_count = len(pdf.pages)
                    if hasattr(pdf, 'metadata') and pdf.metadata:
                        metadata.title = pdf.metadata.get('Title')
                        metadata.author = pdf.metadata.get('Author')
                        metadata.subject = pdf.metadata.get('Subject')
                        metadata.keywords = pdf.metadata.get('Keywords')
                        metadata.creator = pdf.metadata.get('Creator')
                        metadata.producer = pdf.metadata.get('Producer')
                        
            elif self.backend == 'pypdf2':
                with open(file_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    metadata.page_count = len(reader.pages)
                    metadata.is_encrypted = reader.is_encrypted
                    if reader.metadata:
                        metadata.title = reader.metadata.get('/Title')
                        metadata.author = reader.metadata.get('/Author')
                        metadata.subject = reader.metadata.get('/Subject')
                        metadata.keywords = reader.metadata.get('/Keywords')
                        metadata.creator = reader.metadata.get('/Creator')
                        metadata.producer = reader.metadata.get('/Producer')
                        
        except Exception as e:
            logger.warning(f"Could not extract metadata from {file_path}: {e}")
            
        return metadata
    
    def _extract_pages_content(self, file_path: Path, metadata: PDFMetadata, 
                             target_pages: Optional[List[int]] = None) -> List[PageData]:
        """Extract content from all or specified pages."""
        pages_data = []
        
        try:
            if self.backend == 'pymupdf':
                doc = fitz.open(file_path)
                for page_num in range(doc.page_count):
                    if target_pages and (page_num + 1) not in target_pages:
                        continue
                        
                    page = doc[page_num]
                    text = page.get_text()
                    
                    # Analyze page content
                    page_data = PageData(
                        page_number=page_num + 1,
                        text=text,
                        word_count=len(text.split()) if text else 0,
                        char_count=len(text),
                        has_images=len(page.get_images()) > 0,
                        has_tables=self._detect_tables_in_text(text)
                    )
                    
                    # Assess extraction quality for this page
                    page_data.extraction_quality = self._assess_page_quality(page_data)
                    pages_data.append(page_data)
                    
                doc.close()
                
            elif self.backend == 'pdfplumber':
                with pdfplumber.open(file_path) as pdf:
                    for page_num, page in enumerate(pdf.pages):
                        if target_pages and (page_num + 1) not in target_pages:
                            continue
                            
                        text = page.extract_text() or ""
                        
                        page_data = PageData(
                            page_number=page_num + 1,
                            text=text,
                            word_count=len(text.split()) if text else 0,
                            char_count=len(text),
                            has_images=len(page.images) > 0 if hasattr(page, 'images') else False,
                            has_tables=len(page.extract_tables()) > 0
                        )
                        
                        page_data.extraction_quality = self._assess_page_quality(page_data)
                        pages_data.append(page_data)
                        
            elif self.backend == 'pypdf2':
                with open(file_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    for page_num, page in enumerate(reader.pages):
                        if target_pages and (page_num + 1) not in target_pages:
                            continue
                            
                        text = page.extract_text()
                        
                        page_data = PageData(
                            page_number=page_num + 1,
                            text=text,
                            word_count=len(text.split()) if text else 0,
                            char_count=len(text),
                            has_images=False,  # PyPDF2 doesn't easily detect images
                            has_tables=self._detect_tables_in_text(text)
                        )
                        
                        page_data.extraction_quality = self._assess_page_quality(page_data)
                        pages_data.append(page_data)
                        
        except Exception as e:
            logger.error(f"Error extracting page content from {file_path}: {e}")
            
        return pages_data
    
    def _detect_tables_in_text(self, text: str) -> bool:
        """Simple heuristic to detect table-like structures in text."""
        if not text:
            return False
            
        lines = text.split('\n')
        aligned_lines = 0
        
        for line in lines:
            # Look for multiple whitespace-separated columns
            if len(line.split()) >= 3 and '  ' in line:
                aligned_lines += 1
                
        return aligned_lines >= 3  # At least 3 lines that look like table rows
    
    def _assess_page_quality(self, page_data: PageData) -> float:
        """Assess extraction quality for a single page."""
        if page_data.char_count == 0:
            return 0.0
            
        # Basic quality metrics
        quality_score = 1.0
        
        # Penalize very short extractions (might indicate extraction failure)
        if page_data.char_count < 50:
            quality_score *= 0.5
            
        # Penalize if word/char ratio is too low (garbled text)
        if page_data.word_count > 0:
            char_per_word = page_data.char_count / page_data.word_count
            if char_per_word > 15:  # Very long "words" might indicate extraction issues
                quality_score *= 0.7
                
        # Check for common extraction artifacts
        if '�' in page_data.text or page_data.text.count('\n') / max(1, page_data.char_count) > 0.1:
            quality_score *= 0.8
            
        return min(1.0, quality_score)
    
    def _assess_extraction_quality(self, pages_data: List[PageData], full_text: str) -> float:
        """Assess overall extraction quality."""
        if not pages_data:
            return 0.0
            
        # Average page quality
        avg_page_quality = sum(page.extraction_quality for page in pages_data) / len(pages_data)
        
        # Overall text quality indicators
        total_chars = len(full_text)
        total_words = len(full_text.split())
        
        if total_chars == 0:
            return 0.0
            
        # Additional quality checks on full text
        quality_score = avg_page_quality
        
        # Check for reasonable word distribution
        if total_words > 0:
            avg_word_length = total_chars / total_words
            if 2 <= avg_word_length <= 12:  # Reasonable average word length
                quality_score *= 1.1
            else:
                quality_score *= 0.9
                
        return min(1.0, quality_score)
    
    def _has_fallback_backend(self) -> bool:
        """Check if fallback backend is available."""
        current_backends = [self.backend]
        all_backends = []
        
        if _has_pymupdf:
            all_backends.append('pymupdf')
        if _has_pdfplumber:
            all_backends.append('pdfplumber')
        if _has_pypdf2:
            all_backends.append('pypdf2')
            
        return len(set(all_backends) - set(current_backends)) > 0
    
    def _try_fallback_extraction(self, file_path: Path, 
                                pages: Optional[List[int]] = None) -> ExtractionResult:
        """Try extraction with a different backend."""
        # Save current backend
        original_backend = self.backend
        
        try:
            # Try other available backends
            fallback_order = ['pymupdf', 'pdfplumber', 'pypdf2']
            for backend in fallback_order:
                if backend != original_backend and self._backend_available(backend):
                    logger.info(f"Trying fallback backend: {backend}")
                    self.backend = backend
                    result = self.extract_text(file_path, pages)
                    if result.success:
                        return result
                        
        finally:
            # Restore original backend
            self.backend = original_backend
            
        # Return failed result if no fallback worked
        return ExtractionResult(
            success=False,
            text="",
            pages=[],
            metadata=PDFMetadata(),
            backend_used="fallback_failed",
            extraction_time=0.0,
            error_message="All fallback backends failed"
        )
    
    def _backend_available(self, backend: str) -> bool:
        """Check if a specific backend is available."""
        if backend == 'pymupdf':
            return _has_pymupdf
        elif backend == 'pdfplumber':
            return _has_pdfplumber
        elif backend == 'pypdf2':
            return _has_pypdf2
        return False
    
    def get_page_count(self, file_path: Union[str, Path]) -> int:
        """Quick page count without full extraction."""
        try:
            metadata = self._extract_metadata(Path(file_path))
            return metadata.page_count
        except Exception:
            return 0
    
    def split_by_pages(self, pages_data: List[PageData], 
                      chunk_strategy: ChunkStrategy = None) -> List[Dict[str, Any]]:
        """Split pages into chunks based on strategy."""
        chunk_strategy = chunk_strategy or self.chunk_strategy
        chunks = []
        
        if chunk_strategy == ChunkStrategy.PAGE:
            # One chunk per page
            for page in pages_data:
                if page.text.strip():
                    chunks.append({
                        'text': page.text,
                        'metadata': {
                            'page_number': page.page_number,
                            'word_count': page.word_count,
                            'char_count': page.char_count,
                            'extraction_quality': page.extraction_quality,
                            'has_images': page.has_images,
                            'has_tables': page.has_tables
                        }
                    })
                    
        elif chunk_strategy == ChunkStrategy.FIXED_SIZE:
            # Fixed size chunks across all pages
            all_text = "\n\n".join(page.text for page in pages_data if page.text.strip())
            fixed_chunks = self._split_fixed_size(all_text)
            
            for i, chunk_text in enumerate(fixed_chunks):
                chunks.append({
                    'text': chunk_text,
                    'metadata': {
                        'chunk_index': i,
                        'chunk_strategy': 'fixed_size',
                        'char_count': len(chunk_text)
                    }
                })
                
        return chunks
    
    def _split_fixed_size(self, text: str) -> List[str]:
        """Split text into fixed-size chunks with smart boundaries."""
        chunks = []
        current_chunk = ""
        
        # Split by sentences for better boundaries
        sentences = text.replace('. ', '.\n').split('\n')
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= self.max_chunk_size:
                current_chunk += sentence + " "
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + " "
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
            
        return chunks