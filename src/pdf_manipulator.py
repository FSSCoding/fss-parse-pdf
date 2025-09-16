#!/usr/bin/env python3
"""
PDF Manipulator - Professional PDF Split, Merge, and Page Operations
Handles complex PDF manipulation with safety and error recovery.
"""

import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
import tempfile
import shutil

logger = logging.getLogger(__name__)

try:
    import PyPDF2
    _has_pypdf2 = True
except ImportError:
    _has_pypdf2 = False

try:
    import fitz  # PyMuPDF
    _has_pymupdf = True
except ImportError:
    _has_pymupdf = False


class PDFManipulator:
    """
    Professional PDF manipulation with multiple backend support.
    
    Features:
    - Split PDFs by pages or ranges
    - Merge multiple PDFs
    - Extract specific pages
    - Safety mechanisms and error handling
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize PDF manipulator with configuration."""
        self.config = config or {}
        self.backend = self._select_backend()
        self.temp_dir = None
        
        logger.info(f"PDF Manipulator initialized with backend: {self.backend}")
    
    def _select_backend(self) -> str:
        """Select best available backend for manipulation."""
        preferred = self.config.get('backend', 'auto')
        
        if preferred == 'pymupdf' and _has_pymupdf:
            return 'pymupdf'
        elif preferred == 'pypdf2' and _has_pypdf2:
            return 'pypdf2'
        elif _has_pymupdf:
            return 'pymupdf'  # Preferred for quality
        elif _has_pypdf2:
            return 'pypdf2'   # Fallback
        else:
            raise ImportError("No PDF manipulation libraries available. Install PyMuPDF or PyPDF2")
    
    def split_pdf(self, input_path: str, output_pattern: str,
                 pages: Optional[List[int]] = None,
                 page_ranges: Optional[List[str]] = None) -> List[str]:
        """
        Split PDF into separate files.
        
        Args:
            input_path: Path to input PDF
            output_pattern: Output filename pattern (e.g., '{stem}_part_{index}.pdf')
            pages: Specific pages to extract (1-indexed)
            page_ranges: Page ranges (e.g., ['1-5', '10-15'])
            
        Returns:
            List of created output file paths
        """
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        # Parse ranges into page lists
        if page_ranges:
            pages = pages or []
            for range_str in page_ranges:
                if '-' in range_str:
                    start, end = map(int, range_str.split('-'))
                    pages.extend(range(start, end + 1))
                else:
                    pages.append(int(range_str))
        
        if self.backend == 'pymupdf':
            return self._split_with_pymupdf(input_path, output_pattern, pages)
        elif self.backend == 'pypdf2':
            return self._split_with_pypdf2(input_path, output_pattern, pages)
        else:
            raise RuntimeError(f"Backend {self.backend} not available for splitting")
    
    def _split_with_pymupdf(self, input_path: Path, output_pattern: str,
                           pages: Optional[List[int]] = None) -> List[str]:
        """Split PDF using PyMuPDF."""
        doc = fitz.open(input_path)
        output_files = []
        
        try:
            if pages:
                # Extract specific pages
                pages = sorted(set(p for p in pages if 1 <= p <= doc.page_count))
                
                if len(pages) == 1:
                    # Single page extraction
                    output_path = self._format_output_path(
                        output_pattern, input_path.stem, 0, f"page_{pages[0]}"
                    )
                    
                    new_doc = fitz.open()
                    new_doc.insert_pdf(doc, from_page=pages[0]-1, to_page=pages[0]-1)
                    new_doc.save(output_path)
                    new_doc.close()
                    output_files.append(str(output_path))
                    
                else:
                    # Multiple specific pages - create separate files
                    for i, page_num in enumerate(pages):
                        output_path = self._format_output_path(
                            output_pattern, input_path.stem, i, f"page_{page_num}"
                        )
                        
                        new_doc = fitz.open()
                        new_doc.insert_pdf(doc, from_page=page_num-1, to_page=page_num-1)
                        new_doc.save(output_path)
                        new_doc.close()
                        output_files.append(str(output_path))
            else:
                # Split every page
                for page_num in range(doc.page_count):
                    output_path = self._format_output_path(
                        output_pattern, input_path.stem, page_num, f"page_{page_num + 1}"
                    )
                    
                    new_doc = fitz.open()
                    new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                    new_doc.save(output_path)
                    new_doc.close()
                    output_files.append(str(output_path))
        
        finally:
            doc.close()
        
        return output_files
    
    def _split_with_pypdf2(self, input_path: Path, output_pattern: str,
                          pages: Optional[List[int]] = None) -> List[str]:
        """Split PDF using PyPDF2."""
        output_files = []
        
        with open(input_path, 'rb') as input_file:
            reader = PyPDF2.PdfReader(input_file)
            
            if pages:
                # Extract specific pages
                pages = sorted(set(p for p in pages if 1 <= p <= len(reader.pages)))
                
                for i, page_num in enumerate(pages):
                    writer = PyPDF2.PdfWriter()
                    writer.add_page(reader.pages[page_num - 1])
                    
                    output_path = self._format_output_path(
                        output_pattern, input_path.stem, i, f"page_{page_num}"
                    )
                    
                    with open(output_path, 'wb') as output_file:
                        writer.write(output_file)
                    
                    output_files.append(str(output_path))
            else:
                # Split every page
                for page_num, page in enumerate(reader.pages):
                    writer = PyPDF2.PdfWriter()
                    writer.add_page(page)
                    
                    output_path = self._format_output_path(
                        output_pattern, input_path.stem, page_num, f"page_{page_num + 1}"
                    )
                    
                    with open(output_path, 'wb') as output_file:
                        writer.write(output_file)
                    
                    output_files.append(str(output_path))
        
        return output_files
    
    def merge_pdfs(self, input_files: List[str], output_path: str,
                  bookmarks: bool = False) -> bool:
        """
        Merge multiple PDF files into one.
        
        Args:
            input_files: List of input PDF file paths
            output_path: Output file path
            bookmarks: Create bookmarks for each input file
            
        Returns:
            True if successful, False otherwise
        """
        if len(input_files) < 2:
            logger.error("At least 2 input files required for merging")
            return False
        
        # Validate input files
        for file_path in input_files:
            if not Path(file_path).exists():
                logger.error(f"Input file not found: {file_path}")
                return False
        
        try:
            if self.backend == 'pymupdf':
                return self._merge_with_pymupdf(input_files, output_path, bookmarks)
            elif self.backend == 'pypdf2':
                return self._merge_with_pypdf2(input_files, output_path, bookmarks)
            else:
                logger.error(f"Backend {self.backend} not available for merging")
                return False
                
        except Exception as e:
            logger.error(f"Error merging PDFs: {e}")
            return False
    
    def _merge_with_pymupdf(self, input_files: List[str], output_path: str,
                           bookmarks: bool = False) -> bool:
        """Merge PDFs using PyMuPDF."""
        merged_doc = fitz.open()
        
        try:
            for i, file_path in enumerate(input_files):
                logger.info(f"Merging file {i+1}/{len(input_files)}: {file_path}")
                
                input_doc = fitz.open(file_path)
                
                if bookmarks:
                    # Add bookmark for this document
                    bookmark_title = Path(file_path).stem
                    merged_doc.insert_pdf(input_doc)
                    
                    # Note: PyMuPDF bookmark creation is complex
                    # This is a simplified version
                    toc_entry = [1, bookmark_title, merged_doc.page_count - input_doc.page_count + 1]
                    current_toc = merged_doc.get_toc()
                    current_toc.append(toc_entry)
                    merged_doc.set_toc(current_toc)
                else:
                    merged_doc.insert_pdf(input_doc)
                
                input_doc.close()
            
            merged_doc.save(output_path)
            logger.info(f"Successfully merged {len(input_files)} files to {output_path}")
            return True
            
        finally:
            merged_doc.close()
    
    def _merge_with_pypdf2(self, input_files: List[str], output_path: str,
                          bookmarks: bool = False) -> bool:
        """Merge PDFs using PyPDF2."""
        writer = PyPDF2.PdfWriter()
        
        try:
            for i, file_path in enumerate(input_files):
                logger.info(f"Merging file {i+1}/{len(input_files)}: {file_path}")
                
                with open(file_path, 'rb') as input_file:
                    reader = PyPDF2.PdfReader(input_file)
                    
                    start_page = len(writer.pages)
                    
                    for page in reader.pages:
                        writer.add_page(page)
                    
                    if bookmarks:
                        # Add bookmark for this document
                        bookmark_title = Path(file_path).stem
                        writer.add_outline_item(bookmark_title, start_page)
            
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            logger.info(f"Successfully merged {len(input_files)} files to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error in PyPDF2 merge: {e}")
            return False
    
    def extract_pages(self, input_path: str, output_path: str,
                     pages: List[int]) -> bool:
        """
        Extract specific pages to a new PDF.
        
        Args:
            input_path: Input PDF path
            output_path: Output PDF path
            pages: List of page numbers to extract (1-indexed)
            
        Returns:
            True if successful, False otherwise
        """
        if not pages:
            logger.error("No pages specified for extraction")
            return False
        
        try:
            if self.backend == 'pymupdf':
                return self._extract_pages_pymupdf(input_path, output_path, pages)
            elif self.backend == 'pypdf2':
                return self._extract_pages_pypdf2(input_path, output_path, pages)
            else:
                logger.error(f"Backend {self.backend} not available")
                return False
                
        except Exception as e:
            logger.error(f"Error extracting pages: {e}")
            return False
    
    def _extract_pages_pymupdf(self, input_path: str, output_path: str,
                              pages: List[int]) -> bool:
        """Extract pages using PyMuPDF."""
        input_doc = fitz.open(input_path)
        output_doc = fitz.open()
        
        try:
            # Validate and sort pages
            valid_pages = sorted(set(p for p in pages if 1 <= p <= input_doc.page_count))
            
            if not valid_pages:
                logger.error("No valid pages to extract")
                return False
            
            for page_num in valid_pages:
                output_doc.insert_pdf(input_doc, from_page=page_num-1, to_page=page_num-1)
            
            output_doc.save(output_path)
            logger.info(f"Extracted {len(valid_pages)} pages to {output_path}")
            return True
            
        finally:
            input_doc.close()
            output_doc.close()
    
    def _extract_pages_pypdf2(self, input_path: str, output_path: str,
                             pages: List[int]) -> bool:
        """Extract pages using PyPDF2."""
        with open(input_path, 'rb') as input_file:
            reader = PyPDF2.PdfReader(input_file)
            writer = PyPDF2.PdfWriter()
            
            # Validate and sort pages
            valid_pages = sorted(set(p for p in pages if 1 <= p <= len(reader.pages)))
            
            if not valid_pages:
                logger.error("No valid pages to extract")
                return False
            
            for page_num in valid_pages:
                writer.add_page(reader.pages[page_num - 1])
            
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            logger.info(f"Extracted {len(valid_pages)} pages to {output_path}")
            return True
    
    def _format_output_path(self, pattern: str, stem: str, index: int, 
                           suffix: str = "") -> Path:
        """Format output path using pattern."""
        # Replace placeholders in pattern
        formatted = pattern.format(
            stem=stem,
            index=index,
            suffix=suffix,
            i=index,
            page=index + 1
        )
        
        return Path(formatted)
    
    def get_page_count(self, file_path: str) -> int:
        """Get number of pages in PDF."""
        try:
            if self.backend == 'pymupdf':
                doc = fitz.open(file_path)
                count = doc.page_count
                doc.close()
                return count
            elif self.backend == 'pypdf2':
                with open(file_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    return len(reader.pages)
            else:
                return 0
        except Exception as e:
            logger.error(f"Error getting page count: {e}")
            return 0
    
    def validate_page_ranges(self, file_path: str, 
                           pages: Optional[List[int]] = None,
                           ranges: Optional[List[str]] = None) -> List[int]:
        """
        Validate and return list of valid page numbers.
        
        Args:
            file_path: PDF file path
            pages: List of specific pages
            ranges: List of page ranges
            
        Returns:
            List of valid page numbers (1-indexed)
        """
        page_count = self.get_page_count(file_path)
        if page_count == 0:
            return []
        
        all_pages = []
        
        if pages:
            all_pages.extend(pages)
        
        if ranges:
            for range_str in ranges:
                if '-' in range_str:
                    try:
                        start, end = map(int, range_str.split('-'))
                        all_pages.extend(range(start, min(end + 1, page_count + 1)))
                    except ValueError:
                        logger.warning(f"Invalid range format: {range_str}")
                else:
                    try:
                        all_pages.append(int(range_str))
                    except ValueError:
                        logger.warning(f"Invalid page number: {range_str}")
        
        # Return valid, unique, sorted page numbers
        valid_pages = sorted(set(p for p in all_pages if 1 <= p <= page_count))
        return valid_pages