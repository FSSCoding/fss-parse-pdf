#!/usr/bin/env python3
"""
PDF Converters - Format conversion from PDF to various output formats
Handles conversion to markdown, JSON, YAML, HTML, and plain text.
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
import re
from datetime import datetime

from .pdf_parser import PDFParser, ExtractionResult

logger = logging.getLogger(__name__)

try:
    import yaml
    _has_yaml = True
except ImportError:
    _has_yaml = False


class PDFConverter:
    """
    Professional PDF format converter with multiple output formats.
    
    Supported outputs:
    - Plain text (.txt)
    - Markdown (.md)
    - JSON (.json)
    - YAML (.yml, .yaml)
    - HTML (.html)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize converter with configuration."""
        self.config = config or {}
        self.parser = PDFParser(self.config.get('parser', {}))
        
        # Conversion settings
        self.preserve_structure = self.config.get('preserve_structure', True)
        self.include_metadata = self.config.get('include_metadata', True)
        self.include_page_numbers = self.config.get('include_page_numbers', False)
        self.markdown_format = self.config.get('markdown_format', 'github')
        
    def convert(self, input_path: str, output_path: str, 
               format_type: str = "auto") -> bool:
        """
        Convert PDF to specified format.
        
        Args:
            input_path: Path to input PDF
            output_path: Path to output file
            format_type: Output format ('auto', 'text', 'markdown', 'json', 'yaml', 'html')
            
        Returns:
            True if successful, False otherwise
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        
        if not input_path.exists():
            logger.error(f"Input file not found: {input_path}")
            return False
        
        # Determine format from extension if auto
        if format_type == "auto":
            format_type = self._detect_format(output_path)
        
        # Extract content from PDF
        extraction_result = self.parser.extract_text(str(input_path))
        
        if not extraction_result.success:
            logger.error(f"Failed to extract text from PDF: {extraction_result.error_message}")
            return False
        
        try:
            # Convert based on format
            if format_type == "text":
                content = self._convert_to_text(extraction_result)
            elif format_type == "markdown":
                content = self._convert_to_markdown(extraction_result)
            elif format_type == "json":
                content = self._convert_to_json(extraction_result)
            elif format_type == "yaml":
                content = self._convert_to_yaml(extraction_result)
            elif format_type == "html":
                content = self._convert_to_html(extraction_result)
            else:
                logger.error(f"Unsupported format: {format_type}")
                return False
            
            # Write output file
            if isinstance(content, str):
                output_path.write_text(content, encoding='utf-8')
            else:
                with open(output_path, 'w', encoding='utf-8') as f:
                    if format_type == "json":
                        json.dump(content, f, indent=2, default=str, ensure_ascii=False)
                    elif format_type == "yaml" and _has_yaml:
                        yaml.dump(content, f, default_flow_style=False, allow_unicode=True)
            
            logger.info(f"Successfully converted {input_path} to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error converting PDF: {e}")
            return False
    
    def _detect_format(self, output_path: Path) -> str:
        """Detect output format from file extension."""
        suffix = output_path.suffix.lower()
        
        format_map = {
            '.txt': 'text',
            '.md': 'markdown',
            '.markdown': 'markdown',
            '.json': 'json',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.html': 'html',
            '.htm': 'html'
        }
        
        return format_map.get(suffix, 'text')
    
    def _convert_to_text(self, result: ExtractionResult) -> str:
        """Convert to plain text format."""
        content_parts = []
        
        # Add metadata header if requested
        if self.include_metadata and result.metadata.title:
            content_parts.append(f"Title: {result.metadata.title}")
            if result.metadata.author:
                content_parts.append(f"Author: {result.metadata.author}")
            content_parts.append("")  # Empty line
        
        # Add page content
        if self.include_page_numbers and len(result.pages) > 1:
            for page in result.pages:
                if page.text.strip():
                    content_parts.append(f"=== Page {page.page_number} ===")
                    content_parts.append(page.text.strip())
                    content_parts.append("")  # Empty line between pages
        else:
            content_parts.append(result.text)
        
        return "\n".join(content_parts)
    
    def _convert_to_markdown(self, result: ExtractionResult) -> str:
        """Convert to Markdown format with structure preservation."""
        content_parts = []
        
        # Add metadata header
        if self.include_metadata:
            if result.metadata.title:
                content_parts.append(f"# {result.metadata.title}")
                content_parts.append("")
            
            if any([result.metadata.author, result.metadata.subject, result.metadata.page_count]):
                content_parts.append("## Document Information")
                content_parts.append("")
                
                if result.metadata.author:
                    content_parts.append(f"**Author:** {result.metadata.author}")
                if result.metadata.subject:
                    content_parts.append(f"**Subject:** {result.metadata.subject}")
                if result.metadata.page_count:
                    content_parts.append(f"**Pages:** {result.metadata.page_count}")
                
                content_parts.append("")
        
        # Process content with structure preservation
        if self.preserve_structure:
            content_parts.append(self._structure_markdown_content(result))
        else:
            # Simple page-by-page conversion
            if self.include_page_numbers and len(result.pages) > 1:
                for page in result.pages:
                    if page.text.strip():
                        content_parts.append(f"## Page {page.page_number}")
                        content_parts.append("")
                        content_parts.append(self._format_markdown_text(page.text))
                        content_parts.append("")
            else:
                content_parts.append(self._format_markdown_text(result.text))
        
        return "\n".join(content_parts)
    
    def _structure_markdown_content(self, result: ExtractionResult) -> str:
        """Apply intelligent structure to markdown content."""
        text = result.text
        
        # Split into paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        structured_parts = []
        
        for paragraph in paragraphs:
            # Detect headings (lines that are shorter and followed by content)
            lines = paragraph.split('\n')
            
            if len(lines) == 1 and len(lines[0]) < 80:
                # Potential heading
                line = lines[0].strip()
                
                # Check for numbered sections
                if re.match(r'^\d+\.?\s+', line):
                    structured_parts.append(f"## {line}")
                # Check for all caps (often headings)
                elif line.isupper() and len(line.split()) <= 8:
                    structured_parts.append(f"### {line.title()}")
                # Check for title case
                elif line.istitle() and len(line.split()) <= 8:
                    structured_parts.append(f"### {line}")
                else:
                    structured_parts.append(self._format_markdown_text(paragraph))
            else:
                structured_parts.append(self._format_markdown_text(paragraph))
            
            structured_parts.append("")  # Empty line between sections
        
        return "\n".join(structured_parts)
    
    def _format_markdown_text(self, text: str) -> str:
        """Format text for markdown with basic styling."""
        # Handle bullet points
        text = re.sub(r'^\s*[•·▪▫]\s*', '- ', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*[-*]\s*', '- ', text, flags=re.MULTILINE)
        
        # Handle numbered lists
        text = re.sub(r'^\s*(\d+)[\.)]\s*', r'\1. ', text, flags=re.MULTILINE)
        
        # Handle emphasis (preserve existing markdown)
        # Don't modify text that already has markdown formatting
        
        return text
    
    def _convert_to_json(self, result: ExtractionResult) -> Dict[str, Any]:
        """Convert to JSON format with structured data."""
        json_data = {
            "document": {
                "extraction_info": {
                    "backend_used": result.backend_used,
                    "extraction_time": result.extraction_time,
                    "quality_score": result.quality_score,
                    "extraction_date": datetime.now().isoformat()
                }
            }
        }
        
        # Add metadata
        if self.include_metadata:
            metadata_dict = {
                "title": result.metadata.title,
                "author": result.metadata.author,
                "subject": result.metadata.subject,
                "keywords": result.metadata.keywords,
                "creator": result.metadata.creator,
                "producer": result.metadata.producer,
                "page_count": result.metadata.page_count,
                "file_size": result.metadata.file_size,
                "is_encrypted": result.metadata.is_encrypted,
                "creation_date": result.metadata.creation_date.isoformat() if result.metadata.creation_date else None,
                "modification_date": result.metadata.modification_date.isoformat() if result.metadata.modification_date else None
            }
            # Remove None values
            json_data["document"]["metadata"] = {k: v for k, v in metadata_dict.items() if v is not None}
        
        # Add content
        json_data["document"]["content"] = {
            "full_text": result.text,
            "pages": []
        }
        
        # Add page-level data
        for page in result.pages:
            page_data = {
                "page_number": page.page_number,
                "text": page.text,
                "word_count": page.word_count,
                "char_count": page.char_count,
                "extraction_quality": page.extraction_quality,
                "has_images": page.has_images,
                "has_tables": page.has_tables
            }
            json_data["document"]["content"]["pages"].append(page_data)
        
        return json_data
    
    def _convert_to_yaml(self, result: ExtractionResult) -> Dict[str, Any]:
        """Convert to YAML format."""
        if not _has_yaml:
            logger.error("PyYAML not available for YAML conversion")
            return {}
        
        # Use same structure as JSON but optimize for YAML readability
        yaml_data = {
            "document": {
                "metadata": {},
                "content": {},
                "extraction_info": {
                    "backend": result.backend_used,
                    "extraction_time_seconds": round(result.extraction_time, 2),
                    "quality_score": round(result.quality_score, 2),
                    "extracted_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            }
        }
        
        # Add metadata
        if self.include_metadata:
            metadata = {}
            if result.metadata.title:
                metadata["title"] = result.metadata.title
            if result.metadata.author:
                metadata["author"] = result.metadata.author
            if result.metadata.subject:
                metadata["subject"] = result.metadata.subject
            if result.metadata.page_count:
                metadata["pages"] = result.metadata.page_count
            
            yaml_data["document"]["metadata"] = metadata
        
        # Add content
        yaml_data["document"]["content"] = {
            "text": result.text,
            "statistics": {
                "total_pages": len(result.pages),
                "total_words": sum(page.word_count for page in result.pages),
                "total_characters": sum(page.char_count for page in result.pages),
                "pages_with_images": sum(1 for page in result.pages if page.has_images),
                "pages_with_tables": sum(1 for page in result.pages if page.has_tables)
            }
        }
        
        # Add page breakdown if requested
        if self.include_page_numbers:
            yaml_data["document"]["pages"] = []
            for page in result.pages:
                page_data = {
                    "number": page.page_number,
                    "words": page.word_count,
                    "quality": round(page.extraction_quality, 2),
                    "features": []
                }
                
                if page.has_images:
                    page_data["features"].append("images")
                if page.has_tables:
                    page_data["features"].append("tables")
                
                # Include text for small pages, summary for large ones
                if page.char_count < 1000:
                    page_data["text"] = page.text
                else:
                    page_data["text_preview"] = page.text[:200] + "..."
                
                yaml_data["document"]["pages"].append(page_data)
        
        return yaml_data
    
    def _convert_to_html(self, result: ExtractionResult) -> str:
        """Convert to HTML format."""
        html_parts = []
        
        # HTML header
        html_parts.append("<!DOCTYPE html>")
        html_parts.append("<html lang=\"en\">")
        html_parts.append("<head>")
        html_parts.append("    <meta charset=\"UTF-8\">")
        html_parts.append("    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">")
        
        title = result.metadata.title or "PDF Document"
        html_parts.append(f"    <title>{self._escape_html(title)}</title>")
        
        # CSS styles
        html_parts.append("    <style>")
        html_parts.append("        body { font-family: Arial, sans-serif; line-height: 1.6; margin: 40px; max-width: 800px; }")
        html_parts.append("        .metadata { background: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 30px; }")
        html_parts.append("        .page { margin-bottom: 30px; padding-bottom: 20px; border-bottom: 1px solid #eee; }")
        html_parts.append("        .page-header { font-weight: bold; color: #666; margin-bottom: 10px; }")
        html_parts.append("        .content { white-space: pre-wrap; }")
        html_parts.append("    </style>")
        
        html_parts.append("</head>")
        html_parts.append("<body>")
        
        # Add metadata section
        if self.include_metadata:
            html_parts.append("    <div class=\"metadata\">")
            if result.metadata.title:
                html_parts.append(f"        <h1>{self._escape_html(result.metadata.title)}</h1>")
            
            metadata_items = []
            if result.metadata.author:
                metadata_items.append(f"<strong>Author:</strong> {self._escape_html(result.metadata.author)}")
            if result.metadata.subject:
                metadata_items.append(f"<strong>Subject:</strong> {self._escape_html(result.metadata.subject)}")
            if result.metadata.page_count:
                metadata_items.append(f"<strong>Pages:</strong> {result.metadata.page_count}")
            
            if metadata_items:
                html_parts.append("        <p>" + " | ".join(metadata_items) + "</p>")
            
            html_parts.append("    </div>")
        
        # Add content
        if self.include_page_numbers and len(result.pages) > 1:
            for page in result.pages:
                if page.text.strip():
                    html_parts.append("    <div class=\"page\">")
                    html_parts.append(f"        <div class=\"page-header\">Page {page.page_number}</div>")
                    html_parts.append(f"        <div class=\"content\">{self._escape_html(page.text)}</div>")
                    html_parts.append("    </div>")
        else:
            html_parts.append("    <div class=\"content\">")
            html_parts.append(f"        {self._escape_html(result.text)}")
            html_parts.append("    </div>")
        
        # HTML footer
        html_parts.append("</body>")
        html_parts.append("</html>")
        
        return "\n".join(html_parts)
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        if not text:
            return ""
        
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        text = text.replace('"', "&quot;")
        text = text.replace("'", "&#x27;")
        
        return text