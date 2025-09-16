#!/usr/bin/env python3
"""
PDF Engine - Main CLI Interface for Professional PDF Operations
Designed for CLI agents and automated workflows with comprehensive PDF manipulation.
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import click
from rich.console import Console
from rich.table import Table
from rich.progress import track
from rich.panel import Panel

from .pdf_parser import PDFParser, ExtractionMode, ChunkStrategy
from .pdf_manipulator import PDFManipulator
from .converters import PDFConverter
from .safety_manager import SafetyManager

console = Console()

class PDFEngine:
    """
    Main PDF manipulation engine for CLI agents.
    Provides high-level interface for all PDF operations.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Initialize components
        self.parser = PDFParser(self.config.get('parser', {}))
        self.manipulator = PDFManipulator(self.config.get('manipulator', {}))
        self.converter = PDFConverter(self.config.get('converter', {}))
        self.safety = SafetyManager(self.config.get('safety', {}))
    
    def extract_text(self, file_path: str, pages: Optional[List[int]] = None,
                    include_metadata: bool = False) -> Dict[str, Any]:
        """Extract text from PDF."""
        result = self.parser.extract_text(file_path, pages)
        
        if not result.success:
            return {"success": False, "error": result.error_message}
        
        output = {
            "success": True,
            "text": result.text,
            "page_count": len(result.pages),
            "backend_used": result.backend_used,
            "extraction_time": result.extraction_time,
            "quality_score": result.quality_score
        }
        
        if include_metadata:
            output["metadata"] = {
                "title": result.metadata.title,
                "author": result.metadata.author,
                "subject": result.metadata.subject,
                "page_count": result.metadata.page_count,
                "file_size": result.metadata.file_size,
                "is_encrypted": result.metadata.is_encrypted
            }
            
            output["pages"] = [
                {
                    "page_number": page.page_number,
                    "word_count": page.word_count,
                    "char_count": page.char_count,
                    "extraction_quality": page.extraction_quality,
                    "has_images": page.has_images,
                    "has_tables": page.has_tables
                }
                for page in result.pages
            ]
        
        return output
    
    def convert_pdf(self, input_path: str, output_path: str, 
                   format_type: str = "auto") -> bool:
        """Convert PDF to another format."""
        return self.converter.convert(input_path, output_path, format_type)
    
    def split_pdf(self, input_path: str, output_pattern: str,
                 pages: Optional[List[int]] = None, 
                 page_ranges: Optional[List[str]] = None) -> List[str]:
        """Split PDF into separate files."""
        return self.manipulator.split_pdf(input_path, output_pattern, pages, page_ranges)
    
    def merge_pdfs(self, input_files: List[str], output_path: str) -> bool:
        """Merge multiple PDFs into one."""
        return self.manipulator.merge_pdfs(input_files, output_path)
    
    def get_info(self, file_path: str, verbose: bool = False) -> Dict[str, Any]:
        """Get PDF information and metadata."""
        result = self.parser.extract_text(file_path)
        
        if not result.success:
            return {"success": False, "error": result.error_message}
        
        info = {
            "success": True,
            "file_path": file_path,
            "file_size": result.metadata.file_size,
            "page_count": result.metadata.page_count,
            "title": result.metadata.title,
            "author": result.metadata.author,
            "subject": result.metadata.subject,
            "creator": result.metadata.creator,
            "producer": result.metadata.producer,
            "is_encrypted": result.metadata.is_encrypted,
            "backend_used": result.backend_used,
            "quality_score": result.quality_score
        }
        
        if verbose:
            info.update({
                "keywords": result.metadata.keywords,
                "creation_date": str(result.metadata.creation_date) if result.metadata.creation_date else None,
                "modification_date": str(result.metadata.modification_date) if result.metadata.modification_date else None,
                "is_linearized": result.metadata.is_linearized,
                "pdf_version": result.metadata.pdf_version,
                "total_words": sum(page.word_count for page in result.pages),
                "total_characters": sum(page.char_count for page in result.pages),
                "pages_with_images": sum(1 for page in result.pages if page.has_images),
                "pages_with_tables": sum(1 for page in result.pages if page.has_tables),
                "average_quality": sum(page.extraction_quality for page in result.pages) / len(result.pages) if result.pages else 0
            })
            
            info["page_details"] = [
                {
                    "page": page.page_number,
                    "words": page.word_count,
                    "chars": page.char_count,
                    "quality": page.extraction_quality,
                    "has_images": page.has_images,
                    "has_tables": page.has_tables
                }
                for page in result.pages
            ]
        
        return info


@click.group()
@click.option('--config', help='Configuration file path')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.option('--backend', help='PDF backend to use (pymupdf, pdfplumber, pypdf2)')
@click.pass_context
def cli(ctx, config, verbose, backend):
    """FSS Parse PDF - Professional PDF manipulation for CLI agents."""
    ctx.ensure_object(dict)
    
    # Load configuration
    config_data = {}
    if config:
        try:
            with open(config) as f:
                if config.endswith('.json'):
                    config_data = json.load(f)
                elif config.endswith(('.yml', '.yaml')):
                    import yaml
                    config_data = yaml.safe_load(f)
        except Exception as e:
            console.print(f"[red]Error loading config: {e}[/red]")
            sys.exit(1)
    
    # Override backend if specified
    if backend:
        config_data.setdefault('parser', {})['backend'] = backend
    
    # Set verbosity
    if verbose:
        import logging
        logging.basicConfig(level=logging.INFO)
    
    ctx.obj['engine'] = PDFEngine(config_data)
    ctx.obj['verbose'] = verbose


@cli.command()
@click.argument('file_path')
@click.option('--pages', help='Specific pages to extract (e.g., 1,3,5-10)')
@click.option('--output', '-o', help='Output file path')
@click.option('--format', default='text', help='Output format (text, json)')
@click.option('--include-metadata', is_flag=True, help='Include metadata in output')
@click.pass_context
def extract(ctx, file_path, pages, output, format, include_metadata):
    """Extract text from PDF file."""
    engine = ctx.obj['engine']
    
    # Parse page specification
    page_list = None
    if pages:
        page_list = []
        for part in pages.split(','):
            if '-' in part:
                start, end = map(int, part.split('-'))
                page_list.extend(range(start, end + 1))
            else:
                page_list.append(int(part))
    
    with console.status(f"Extracting text from {file_path}..."):
        result = engine.extract_text(file_path, page_list, include_metadata)
    
    if not result["success"]:
        console.print(f"[red]Extraction failed: {result['error']}[/red]")
        sys.exit(1)
    
    # Format output
    if format == 'json':
        output_data = json.dumps(result, indent=2)
    else:
        output_data = result["text"]
    
    # Write or display output
    if output:
        Path(output).write_text(output_data, encoding='utf-8')
        console.print(f"[green]Text extracted to {output}[/green]")
    else:
        console.print(output_data)
    
    # Show extraction stats
    if ctx.obj['verbose']:
        stats = Table(title="Extraction Statistics")
        stats.add_column("Metric", style="cyan")
        stats.add_column("Value", style="green")
        
        stats.add_row("Pages processed", str(result["page_count"]))
        stats.add_row("Backend used", result["backend_used"])
        stats.add_row("Extraction time", f"{result['extraction_time']:.2f}s")
        stats.add_row("Quality score", f"{result['quality_score']:.2f}")
        
        console.print(stats)


@cli.command()
@click.argument('input_path')
@click.argument('output_path')
@click.option('--format', help='Output format (auto-detected from extension)')
@click.option('--preserve-structure', is_flag=True, help='Preserve document structure')
@click.pass_context
def convert(ctx, input_path, output_path, format, preserve_structure):
    """Convert PDF to another format."""
    engine = ctx.obj['engine']
    
    with console.status(f"Converting {input_path} to {output_path}..."):
        success = engine.convert_pdf(input_path, output_path, format or "auto")
    
    if success:
        console.print(f"[green]Successfully converted to {output_path}[/green]")
    else:
        console.print(f"[red]Conversion failed[/red]")
        sys.exit(1)


@cli.command()
@click.argument('input_path')
@click.option('--pages', help='Pages to extract (e.g., 1,3,5-10)')
@click.option('--ranges', help='Page ranges (e.g., 1-5,10-15)')
@click.option('--output-pattern', default='{stem}_part_{index}.pdf', 
              help='Output filename pattern')
@click.option('--output-dir', help='Output directory')
@click.pass_context
def split(ctx, input_path, pages, ranges, output_pattern, output_dir):
    """Split PDF into separate files."""
    engine = ctx.obj['engine']
    
    # Parse pages and ranges
    page_list = None
    range_list = None
    
    if pages:
        page_list = []
        for part in pages.split(','):
            if '-' in part:
                start, end = map(int, part.split('-'))
                page_list.extend(range(start, end + 1))
            else:
                page_list.append(int(part))
    
    if ranges:
        range_list = ranges.split(',')
    
    # Prepare output pattern
    if output_dir:
        output_pattern = str(Path(output_dir) / output_pattern)
    
    with console.status(f"Splitting {input_path}..."):
        output_files = engine.split_pdf(input_path, output_pattern, page_list, range_list)
    
    if output_files:
        console.print(f"[green]Created {len(output_files)} files:[/green]")
        for file_path in output_files:
            console.print(f"  • {file_path}")
    else:
        console.print(f"[red]Split operation failed[/red]")
        sys.exit(1)


@cli.command()
@click.argument('output_path')
@click.argument('input_files', nargs=-1, required=True)
@click.option('--bookmarks', is_flag=True, help='Create bookmarks for each input file')
@click.pass_context
def merge(ctx, output_path, input_files, bookmarks):
    """Merge multiple PDF files into one."""
    engine = ctx.obj['engine']
    
    if len(input_files) < 2:
        console.print("[red]At least 2 input files required for merging[/red]")
        sys.exit(1)
    
    with console.status(f"Merging {len(input_files)} files..."):
        success = engine.merge_pdfs(list(input_files), output_path)
    
    if success:
        console.print(f"[green]Successfully merged to {output_path}[/green]")
    else:
        console.print(f"[red]Merge operation failed[/red]")
        sys.exit(1)


@cli.command()
@click.argument('file_path')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed information')
@click.option('--format', default='table', help='Output format (table, json)')
@click.pass_context
def info(ctx, file_path, verbose, format):
    """Get PDF file information and metadata."""
    engine = ctx.obj['engine']
    
    with console.status(f"Analyzing {file_path}..."):
        result = engine.get_info(file_path, verbose or ctx.obj['verbose'])
    
    if not result["success"]:
        console.print(f"[red]Analysis failed: {result['error']}[/red]")
        sys.exit(1)
    
    if format == 'json':
        console.print(json.dumps(result, indent=2))
        return
    
    # Create information table
    info_table = Table(title=f"PDF Information: {Path(file_path).name}")
    info_table.add_column("Property", style="cyan")
    info_table.add_column("Value", style="green")
    
    # Basic information
    info_table.add_row("File Size", f"{result['file_size']:,} bytes")
    info_table.add_row("Page Count", str(result['page_count']))
    info_table.add_row("Title", result['title'] or "Not specified")
    info_table.add_row("Author", result['author'] or "Not specified")
    info_table.add_row("Subject", result['subject'] or "Not specified")
    info_table.add_row("Creator", result['creator'] or "Not specified")
    info_table.add_row("Producer", result['producer'] or "Not specified")
    info_table.add_row("Encrypted", "Yes" if result['is_encrypted'] else "No")
    info_table.add_row("Backend Used", result['backend_used'])
    info_table.add_row("Quality Score", f"{result['quality_score']:.2f}")
    
    console.print(info_table)
    
    # Verbose details
    if verbose and 'page_details' in result:
        page_table = Table(title="Page Details")
        page_table.add_column("Page", style="cyan")
        page_table.add_column("Words", style="green")
        page_table.add_column("Characters", style="green")
        page_table.add_column("Quality", style="yellow")
        page_table.add_column("Images", style="blue")
        page_table.add_column("Tables", style="magenta")
        
        for page in result['page_details']:
            page_table.add_row(
                str(page['page']),
                str(page['words']),
                str(page['chars']),
                f"{page['quality']:.2f}",
                "Yes" if page['has_images'] else "No",
                "Yes" if page['has_tables'] else "No"
            )
        
        console.print(page_table)


@cli.command()
@click.argument('file_path')
@click.argument('search_term')
@click.option('--case-sensitive', is_flag=True, help='Case sensitive search')
@click.option('--whole-words', is_flag=True, help='Match whole words only')
@click.option('--page-numbers', is_flag=True, help='Show page numbers for matches')
@click.pass_context
def search(ctx, file_path, search_term, case_sensitive, whole_words, page_numbers):
    """Search for text in PDF file."""
    engine = ctx.obj['engine']
    
    with console.status(f"Searching in {file_path}..."):
        result = engine.extract_text(file_path, include_metadata=True)
    
    if not result["success"]:
        console.print(f"[red]Search failed: {result['error']}[/red]")
        sys.exit(1)
    
    # Perform search
    import re
    
    flags = 0 if case_sensitive else re.IGNORECASE
    if whole_words:
        pattern = r'\b' + re.escape(search_term) + r'\b'
    else:
        pattern = re.escape(search_term)
    
    matches = []
    if page_numbers and 'pages' in result:
        # Search page by page
        for page_info in result['pages']:
            page_result = engine.extract_text(file_path, [page_info['page_number']])
            if page_result["success"]:
                page_text = page_result["text"]
                page_matches = list(re.finditer(pattern, page_text, flags))
                for match in page_matches:
                    # Get context around match
                    start = max(0, match.start() - 50)
                    end = min(len(page_text), match.end() + 50)
                    context = page_text[start:end].replace('\n', ' ')
                    
                    matches.append({
                        'page': page_info['page_number'],
                        'position': match.start(),
                        'context': context,
                        'match': match.group()
                    })
    else:
        # Search full text
        full_matches = list(re.finditer(pattern, result["text"], flags))
        for match in full_matches:
            start = max(0, match.start() - 50)
            end = min(len(result["text"]), match.end() + 50)
            context = result["text"][start:end].replace('\n', ' ')
            
            matches.append({
                'position': match.start(),
                'context': context,
                'match': match.group()
            })
    
    # Display results
    if matches:
        console.print(f"[green]Found {len(matches)} matches for '{search_term}'[/green]")
        
        for i, match in enumerate(matches, 1):
            if 'page' in match:
                console.print(f"\n[cyan]Match {i} (Page {match['page']}):[/cyan]")
            else:
                console.print(f"\n[cyan]Match {i}:[/cyan]")
            
            # Highlight the match in context
            context = match['context']
            highlighted = context.replace(
                match['match'], 
                f"[yellow bold]{match['match']}[/yellow bold]"
            )
            console.print(f"  {highlighted}")
    else:
        console.print(f"[yellow]No matches found for '{search_term}'[/yellow]")


def main():
    """Main entry point."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[red]Operation cancelled[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


if __name__ == '__main__':
    main()