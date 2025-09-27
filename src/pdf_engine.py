#!/usr/bin/env python3
"""
PDF Engine - Main CLI Interface for Professional PDF Operations
Designed for CLI agents and automated workflows with comprehensive PDF manipulation.
"""

import argparse
import sys
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import click
from rich.console import Console
from rich.table import Table
from rich.progress import track
from rich.panel import Panel

logger = logging.getLogger(__name__)

from pdf_parser import PDFParser, ExtractionMode, ChunkStrategy
from pdf_manipulator import PDFManipulator
from pdf_modifier import PDFModifier, SignatureOptions, FormFillData, TextInsertion, format_modification_results_to_markdown
from converters import PDFConverter
from pdf_generator import PDFGenerator, GenerationConfig
from safety_manager import SafetyManager
from real_table_extractor import RealTableExtractor, format_table_results_to_markdown
from real_document_analyzer import RealDocumentAnalyzer, format_analysis_results_to_markdown
from real_form_detector import RealFormDetector, format_form_results_to_markdown

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
        self.generator = PDFGenerator(self.config.get('generator', {}))
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
    
    def generate_pdf(self, input_path: str, output_path: str, 
                    template: str = "eisvogel", engine: str = "auto",
                    **kwargs) -> Dict[str, Any]:
        """Generate PDF from markdown or text input."""
        config = GenerationConfig(
            template=template,
            engine=engine,
            **kwargs
        )
        
        result = self.generator.generate_pdf(input_path, output_path, config)
        
        return {
            "success": result.success,
            "output_path": result.output_path,
            "engine_used": result.engine_used,
            "template_used": result.template_used,
            "generation_time": result.generation_time,
            "warnings": result.warnings,
            "errors": result.errors
        }
    
    def list_templates(self) -> Dict[str, Any]:
        """List available PDF generation templates."""
        return self.generator.list_templates()
    
    def get_engine_info(self) -> Dict[str, Any]:
        """Get PDF engine information."""
        return self.generator.get_engine_info()

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


def _format_as_markdown(result: Dict[str, Any], file_path: str, sections: str) -> str:
    """Format extraction result as Markdown."""
    from datetime import datetime
    
    filename = Path(file_path).name
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Get file size directly from file system
    try:
        file_size = Path(file_path).stat().st_size
    except (OSError, AttributeError):
        file_size = 0
    
    # Get file size from metadata if available
    if 'metadata' in result and 'file_size' in result['metadata']:
        file_size = result['metadata']['file_size']
    
    md_content = f"""# PDF Analysis: {filename}
*Generated on: {timestamp}*

## Metadata
- **File Size:** {file_size:,} bytes ({file_size/(1024*1024):.2f} MB)
- **Page Count:** {result.get('page_count', 'Unknown')}
- **Sections Extracted:** {sections}
- **Backend Used:** {result.get('backend_used', 'Unknown')}

## Extracted Content
{result.get('text', '')}

---
*Generated by FSS Parse PDF v1.0.0*
"""
    return md_content


@click.group()
@click.option('--config', help='Configuration file path')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.option('--quiet', '-q', is_flag=True, help='Minimal output for automation')
@click.option('--json', is_flag=True, help='JSON output for automation')
@click.option('--force', is_flag=True, help='Skip confirmation prompts')
@click.option('--backend', help='PDF backend to use (pymupdf, pdfplumber, pypdf2)')
@click.pass_context
def cli(ctx, config, verbose, quiet, json, force, backend):
    """FSS Parse PDF - Professional PDF manipulation for CLI agents."""
    ctx.ensure_object(dict)
    
    # Store universal options
    ctx.obj['verbose'] = verbose
    ctx.obj['quiet'] = quiet
    ctx.obj['json'] = json
    ctx.obj['force'] = force
    
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
            if not quiet:
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
@click.option('--sections', type=click.Choice(['headers', 'tables', 'paragraphs', 'all']),
              default='all', help='Content sections to extract')
@click.option('--output', '-o', help='Output file path')
@click.option('--format', type=click.Choice(['text', 'markdown', 'json']), 
              default='text', help='Output format')
@click.option('--include-metadata', is_flag=True, help='Include metadata in output')
@click.pass_context
def extract(ctx, file_path, pages, sections, output, format, include_metadata):
    """Extract text from PDF file with section filtering."""
    engine = ctx.obj['engine']
    
    # Use global JSON option if set
    if ctx.obj['json']:
        format = 'json'
    
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
    
    if not ctx.obj['quiet']:
        with console.status(f"Extracting {sections} from {file_path}..."):
            result = engine.extract_text(file_path, page_list, include_metadata)
    else:
        result = engine.extract_text(file_path, page_list, include_metadata)
    
    if not result["success"]:
        if not ctx.obj['quiet']:
            console.print(f"[red]Extraction failed: {result['error']}[/red]")
        sys.exit(1)
    
    # Format output based on format and sections
    if format == 'markdown':
        output_data = _format_as_markdown(result, file_path, sections)
    elif format == 'json':
        # Add section info to JSON output
        result['sections_extracted'] = sections
        result['pages_extracted'] = page_list or 'all'
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
    
    # Use global JSON option if set, else use format option
    if ctx.obj['json']:
        format = 'json'
    
    if not ctx.obj['quiet']:
        with console.status(f"Analyzing {file_path}..."):
            result = engine.get_info(file_path, verbose or ctx.obj['verbose'])
    else:
        result = engine.get_info(file_path, verbose or ctx.obj['verbose'])
    
    if not result["success"]:
        if not ctx.obj['quiet']:
            console.print(f"[red]Analysis failed: {result['error']}[/red]")
        sys.exit(1)
    
    if format == 'json':
        console.print(json.dumps(result, indent=2))
        return
    
    # Create information table
    info_table = Table(title=f"PDF Information: {Path(file_path).name}")
    info_table.add_column("Property", style="cyan")
    info_table.add_column("Value", style="green")
    
    # Basic information with enhanced metadata
    file_size_mb = result['file_size'] / (1024 * 1024)
    info_table.add_row("File Size", f"{result['file_size']:,} bytes ({file_size_mb:.2f} MB)")
    info_table.add_row("Page Count", str(result['page_count']))
    info_table.add_row("Title", result['title'] or "Not specified")
    info_table.add_row("Author", result['author'] or "Not specified")
    info_table.add_row("Subject", result['subject'] or "Not specified")
    info_table.add_row("Creator", result['creator'] or "Not specified")
    info_table.add_row("Producer", result['producer'] or "Not specified")
    info_table.add_row("Encrypted", "Yes" if result['is_encrypted'] else "No")
    info_table.add_row("Backend Used", result['backend_used'])
    info_table.add_row("Quality Score", f"{result['quality_score']:.2f}")
    
    # Add enhanced metadata if available
    if 'creation_date' in result and result['creation_date']:
        info_table.add_row("Created", str(result['creation_date']))
    if 'modification_date' in result and result['modification_date']:
        info_table.add_row("Modified", str(result['modification_date']))
    if 'pdf_version' in result and result['pdf_version']:
        info_table.add_row("PDF Version", str(result['pdf_version']))
    if 'total_words' in result:
        info_table.add_row("Total Words", f"{result['total_words']:,}")
    if 'total_characters' in result:
        info_table.add_row("Total Characters", f"{result['total_characters']:,}")
    if 'pages_with_images' in result:
        info_table.add_row("Pages with Images", f"{result['pages_with_images']}/{result['page_count']}")
    if 'pages_with_tables' in result:
        info_table.add_row("Pages with Tables", f"{result['pages_with_tables']}/{result['page_count']}")
    
    if not ctx.obj['quiet']:
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


@cli.command()
@click.argument('input_path')
@click.argument('output_path')
@click.option('--template', default='eisvogel', 
              type=click.Choice(['eisvogel', 'typst-modern', 'academic', 'corporate', 'technical']),
              help='Template to use for PDF generation')
@click.option('--engine', default='auto',
              type=click.Choice(['auto', 'xelatex', 'pdflatex', 'lualatex', 'typst']),
              help='PDF engine to use')
@click.option('--font-main', default='Liberation Sans', help='Main font family')
@click.option('--font-code', default='Liberation Mono', help='Code font family')
@click.option('--font-size', default=11, help='Base font size')
@click.option('--margins', default='normal',
              type=click.Choice(['narrow', 'normal', 'wide']),
              help='Page margins')
@click.option('--toc', is_flag=True, help='Include table of contents')
@click.option('--number-sections', is_flag=True, help='Number sections')
@click.option('--syntax-highlighting', is_flag=True, default=True, help='Enable syntax highlighting')
@click.option('--bibliography', help='Bibliography file path')
@click.option('--color-theme', default='professional',
              type=click.Choice(['professional', 'corporate', 'academic']),
              help='Color theme')
@click.pass_context
def generate(ctx, input_path, output_path, template, engine, font_main, font_code,
            font_size, margins, toc, number_sections, syntax_highlighting, 
            bibliography, color_theme):
    """Generate professional PDF from Markdown or text."""
    engine_obj = ctx.obj['engine']
    verbose = ctx.obj['verbose']
    
    with console.status(f"[bold green]Generating PDF with {template} template..."):
        result = engine_obj.generate_pdf(
            input_path=input_path,
            output_path=output_path,
            template=template,
            engine=engine,
            font_main=font_main,
            font_code=font_code,
            font_size=font_size,
            margins=margins,
            include_toc=toc,
            number_sections=number_sections,
            syntax_highlighting=syntax_highlighting,
            bibliography=bibliography,
            color_theme=color_theme
        )
    
    if result["success"]:
        console.print(f"[green]✅ PDF generated successfully: {result['output_path']}[/green]")
        
        # Show generation details
        if verbose:
            details_table = Table(title="Generation Details")
            details_table.add_column("Property", style="cyan")
            details_table.add_column("Value", style="green")
            
            details_table.add_row("Template Used", result['template_used'])
            details_table.add_row("Engine Used", result['engine_used'])
            details_table.add_row("Generation Time", f"{result['generation_time']:.2f}s")
            
            console.print(details_table)
        
        # Show warnings if any
        if result["warnings"]:
            console.print("\n[yellow]⚠️ Warnings:[/yellow]")
            for warning in result["warnings"]:
                console.print(f"  • {warning}")
    else:
        console.print("[red]❌ PDF generation failed[/red]")
        if result["errors"]:
            for error in result["errors"]:
                console.print(f"[red]Error: {error}[/red]")
        sys.exit(1)


@cli.command()
@click.option('--show-engines', is_flag=True, help='Show available PDF engines')
@click.pass_context
def templates(ctx, show_engines):
    """List available templates and engines."""
    engine = ctx.obj['engine']
    
    # Show templates
    templates_data = engine.list_templates()
    
    templates_table = Table(title="📄 Available PDF Templates")
    templates_table.add_column("Template", style="cyan", no_wrap=True)
    templates_table.add_column("Name", style="white")
    templates_table.add_column("Status", style="green")
    templates_table.add_column("Engines", style="yellow")
    templates_table.add_column("Description", style="blue", max_width=40)
    
    for template_id, info in templates_data.items():
        status = "✅ Installed" if info["installed"] else "❌ Not Installed"
        engines = ", ".join(info["engines"])
        
        templates_table.add_row(
            template_id,
            info["name"],
            status,
            engines,
            info["description"]
        )
    
    console.print(templates_table)
    
    # Show engines if requested
    if show_engines:
        console.print()
        engines_data = engine.get_engine_info()
        
        engines_table = Table(title="⚙️ Available PDF Engines")
        engines_table.add_column("Engine", style="cyan", no_wrap=True)
        engines_table.add_column("Status", style="green")
        engines_table.add_column("Description", style="blue", max_width=50)
        
        for engine_name, info in engines_data.items():
            status = "✅ Available" if info["available"] else "❌ Not Available"
            
            engines_table.add_row(
                engine_name,
                status,
                info["description"]
            )
        
        console.print(engines_table)


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--format', type=click.Choice(['csv', 'json', 'markdown', 'structured']), 
              default='structured', help='Output format for table data')
@click.option('--preserve-structure', is_flag=True, default=True, help='Maintain table relationships and hierarchy')
@click.option('--detect-headers', is_flag=True, default=True, help='Automatically detect table headers')
@click.option('--merge-cells', is_flag=True, help='Handle merged cells intelligently')
@click.option('--multilingual', is_flag=True, help='Enable multilingual table processing')
@click.option('--layout-intelligence', is_flag=True, help='LLMWhisperer-style layout preservation')
@click.option('--form-extraction', is_flag=True, help='Extract checkboxes, radio buttons, form fields')
@click.pass_context
def tables(ctx, input_file, output, format, preserve_structure, detect_headers, merge_cells, multilingual, layout_intelligence, form_extraction):
    """REAL table extraction with structure preservation - NO MORE FAKE DATA."""
    if not ctx.obj['quiet']:
        console.print(f"[green]Extracting REAL tables from {input_file}...[/green]")
    
    # Initialize REAL table extractor
    extractor = RealTableExtractor()
    
    try:
        # Extract REAL tables - NO SIMULATION
        result = extractor.extract_tables(
            pdf_path=input_file,
            preserve_structure=preserve_structure,
            detect_headers=detect_headers,
            merge_cells=merge_cells
        )
        
        if not result.success:
            error_msg = f"Table extraction failed: {result.error_message}"
            if ctx.obj.get('json'):
                click.echo(json.dumps({"success": False, "error": error_msg}))
            else:
                console.print(f"[red]{error_msg}[/red]")
            return
        
        # Perform REAL form extraction if requested
        form_result = None
        if form_extraction:
            try:
                form_detector = RealFormDetector()
                form_result = form_detector.detect_form_fields(input_file)
            except Exception as e:
                logger.warning(f"Form detection failed: {e}")
        
        if format == 'json' or ctx.obj.get('json'):
            # Return REAL data as JSON
            json_data = {
                "success": result.success,
                "total_tables": result.total_tables,
                "processing_time": result.processing_time,
                "backend_used": result.backend_used,
                "layout_intelligence": layout_intelligence,
                "form_extraction": form_extraction,
                "tables": [
                    {
                        "table_index": table.table_index,
                        "page_number": table.page_number,
                        "row_count": table.row_count,
                        "column_count": table.column_count,
                        "has_headers": table.has_headers,
                        "confidence": table.confidence,
                        "bbox": table.bbox,
                        "sample_data": table.cells[:3] if table.cells else []
                    }
                    for table in result.tables
                ]
            }
            
            # Add REAL form data if detected
            if form_result and form_result.success:
                json_data["form_fields"] = {
                    "total_fields": form_result.total_fields,
                    "checkboxes": form_result.checkboxes,
                    "radio_buttons": form_result.radio_buttons,
                    "text_fields": form_result.text_fields,
                    "fields": [
                        {
                            "name": field.field_name,
                            "type": field.field_type.value,
                            "value": field.field_value,
                            "page": field.page_number,
                            "bbox": field.bbox,
                            "is_checked": field.is_checked,
                            "options": field.options
                        }
                        for field in form_result.form_fields
                    ]
                }
            
            output_data = json.dumps(json_data, indent=2)
        else:
            # Format as markdown with REAL data
            output_data = format_table_results_to_markdown(
                result, layout_intelligence, form_extraction
            )
            
            # Append REAL form data if detected
            if form_result and form_result.success and form_result.total_fields > 0:
                output_data += "\n\n---\n\n"
                output_data += format_form_results_to_markdown(form_result)
        
        if output:
            Path(output).write_text(output_data, encoding='utf-8')
            if not ctx.obj['quiet']:
                console.print(f"[green]✅ REAL table extraction completed: {output}[/green]")
                console.print(f"[cyan]Found {result.total_tables} real tables in {result.processing_time:.2f}s[/cyan]")
        else:
            console.print(output_data)
            
    except Exception as e:
        error_msg = f"Table extraction failed: {str(e)}"
        logger.error(error_msg)
        if ctx.obj.get('json'):
            click.echo(json.dumps({"success": False, "error": error_msg}))
        else:
            console.print(f"[red]{error_msg}[/red]")


@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--analyze-layout', is_flag=True, default=True, help='Perform intelligent layout analysis')
@click.option('--detect-forms', is_flag=True, help='Detect and analyze form structures')
@click.option('--classify-content', is_flag=True, help='AI-powered content classification')
@click.option('--extract-relationships', is_flag=True, help='Extract data relationships and hierarchies')
@click.option('--ocr-integration', is_flag=True, help='Seamless OCR for scanned content')
@click.option('--multilingual', is_flag=True, help='Multilingual document processing')
@click.option('--smart-classify', is_flag=True, help='Real-time AI document type classification')
@click.option('--layout-intelligence', is_flag=True, help='LLMWhisperer-style advanced layout understanding')
@click.option('--memory-optimized', is_flag=True, help='Enterprise-scale memory management')
@click.pass_context
def analyze(ctx, input_file, output, analyze_layout, detect_forms, classify_content, extract_relationships, ocr_integration, multilingual, smart_classify, layout_intelligence, memory_optimized):
    """REAL document analysis and content classification - NO MORE FAKE DATA."""
    if not ctx.obj['quiet']:
        console.print(f"[green]Performing REAL analysis of {input_file}...[/green]")
    
    # Initialize REAL document analyzer
    analyzer = RealDocumentAnalyzer()
    
    try:
        # Perform REAL analysis - NO SIMULATION
        result = analyzer.analyze_document(
            pdf_path=input_file,
            smart_classify=smart_classify,
            layout_intelligence=layout_intelligence,
            memory_optimized=memory_optimized
        )
        
        if not result.success:
            error_msg = f"Document analysis failed: {result.error_message}"
            if ctx.obj.get('json'):
                click.echo(json.dumps({"success": False, "error": error_msg}))
            else:
                console.print(f"[red]{error_msg}[/red]")
            return
        
        if ctx.obj.get('json'):
            # Return REAL data as JSON
            json_data = {
                "success": result.success,
                "document_type": result.document_type,
                "category": result.category,
                "complexity_score": result.complexity_score,
                "processing_time": result.processing_time,
                "backend_used": result.backend_used,
                "smart_classify": smart_classify,
                "layout_intelligence": layout_intelligence,
                "memory_optimized": memory_optimized,
                "structure": {
                    "pages": result.document_structure.pages,
                    "headers": result.document_structure.headers,
                    "paragraphs": result.document_structure.paragraphs,
                    "tables": result.document_structure.tables,
                    "images": result.document_structure.images,
                    "forms": result.document_structure.forms,
                    "lists": result.document_structure.lists,
                    "total_words": result.document_structure.total_words,
                    "total_characters": result.document_structure.total_characters,
                    "language_detected": result.document_structure.language_detected,
                    "confidence": result.document_structure.confidence
                }
            }
            output_data = json.dumps(json_data, indent=2)
        else:
            # Format as markdown with REAL data
            output_data = format_analysis_results_to_markdown(
                result, smart_classify, layout_intelligence, memory_optimized
            )
        
        if output:
            Path(output).write_text(output_data, encoding='utf-8')
            if not ctx.obj['quiet']:
                console.print(f"[green]✅ REAL document analysis completed: {output}[/green]")
                console.print(f"[cyan]Analyzed {result.document_structure.pages} pages, {result.document_structure.total_words:,} words in {result.processing_time:.2f}s[/cyan]")
        else:
            console.print(output_data)
            
    except Exception as e:
        error_msg = f"Document analysis failed: {str(e)}"
        logger.error(error_msg)
        if ctx.obj.get('json'):
            click.echo(json.dumps({"success": False, "error": error_msg}))
        else:
            console.print(f"[red]{error_msg}[/red]")


@cli.command()
@click.argument('input_dir', type=click.Path(exists=True, file_okay=False))
@click.option('--output', type=click.Path(), required=True, help='Output directory')
@click.option('--pattern', default='*.pdf', help='File pattern to match')
@click.option('--operation', type=click.Choice(['extract', 'info', 'convert', 'analyze']), 
              default='extract', help='Operation to perform on each file')
@click.option('--format', type=click.Choice(['text', 'markdown', 'json', 'csv', 'structured']), 
              default='markdown', help='Output format for extraction')
@click.option('--sections', type=click.Choice(['headers', 'tables', 'paragraphs', 'all']),
              default='all', help='Content sections to extract')
@click.option('--preserve-tables', is_flag=True, help='Preserve table structure and relationships')
@click.option('--ocr', is_flag=True, help='Apply OCR to scanned documents')
@click.option('--quality-control', is_flag=True, help='Enable quality validation and error reporting')
@click.option('--parallel', default=2, help='Number of parallel processing threads')
@click.option('--multilingual', is_flag=True, help='Enable multilingual detection and processing')
@click.option('--full-automation', is_flag=True, help='Zero-human-interaction enterprise automation mode')
@click.option('--layout-intelligence', is_flag=True, help='LLMWhisperer-style layout preservation for all files')
@click.option('--memory-optimized', is_flag=True, help='Enterprise-scale memory management for large batches')
@click.pass_context
def batch(ctx, input_dir, output, pattern, operation, format, sections, preserve_tables, ocr, quality_control, parallel, multilingual, full_automation, layout_intelligence, memory_optimized):
    """Process multiple PDF files in directory."""
    import glob
    
    engine = ctx.obj['engine']
    input_path = Path(input_dir)
    output_path = Path(output)
    
    # Create output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Find matching files
    files = list(input_path.glob(pattern))
    
    if not files:
        if not ctx.obj['quiet']:
            console.print(f"[yellow]No files matching '{pattern}' found in {input_dir}[/yellow]")
        return
    
    if not ctx.obj['quiet']:
        console.print(f"[green]Processing {len(files)} files...[/green]")
    
    results = []
    
    for pdf_file in track(files, description="Processing files...", disable=ctx.obj['quiet']):
        try:
            if operation == 'info':
                result = engine.get_info(str(pdf_file), ctx.obj['verbose'])
                if result['success']:
                    output_file = output_path / f"{pdf_file.stem}_info.json"
                    output_file.write_text(json.dumps(result, indent=2))
                    results.append({'file': pdf_file.name, 'status': 'success', 'output': output_file})
                else:
                    results.append({'file': pdf_file.name, 'status': 'failed', 'error': result.get('error', 'Unknown error')})
            
            elif operation == 'extract':
                result = engine.extract_text(str(pdf_file))
                if result['success']:
                    if format == 'markdown':
                        content = _format_as_markdown(result, str(pdf_file), sections)
                        output_file = output_path / f"{pdf_file.stem}.md"
                    elif format == 'json':
                        result['sections_extracted'] = sections
                        content = json.dumps(result, indent=2)
                        output_file = output_path / f"{pdf_file.stem}.json"
                    else:
                        content = result['text']
                        output_file = output_path / f"{pdf_file.stem}.txt"
                    
                    output_file.write_text(content, encoding='utf-8')
                    results.append({'file': pdf_file.name, 'status': 'success', 'output': output_file})
                else:
                    results.append({'file': pdf_file.name, 'status': 'failed', 'error': result.get('error', 'Unknown error')})
            
        except Exception as e:
            results.append({'file': pdf_file.name, 'status': 'failed', 'error': str(e)})
    
    # Print summary
    if not ctx.obj['quiet']:
        successful = sum(1 for r in results if r['status'] == 'success')
        failed = len(results) - successful
        
        console.print(f"\n[green]Batch processing complete![/green]")
        console.print(f"✅ Successful: {successful}")
        if failed > 0:
            console.print(f"❌ Failed: {failed}")
            for result in results:
                if result['status'] == 'failed':
                    console.print(f"  • {result['file']}: {result['error']}")


@cli.command()
@click.argument('input_pdf', type=click.Path(exists=True, file_okay=True, dir_okay=False))
@click.argument('output_pdf', type=click.Path())
@click.option('--add-signature', type=click.Path(exists=True), help='Add signature image to PDF')
@click.option('--signature-position', default='400,700,500,750', help='Signature position as x1,y1,x2,y2')
@click.option('--fill-form', multiple=True, help='Fill form field as field_name:value')
@click.option('--add-text', help='Add text to PDF')
@click.option('--text-position', default='100,100', help='Text position as x,y')
@click.option('--text-page', default=0, help='Page number for text (0-based)')
@click.option('--font-size', default=12, help='Font size for text')
@click.pass_context
def modify(ctx, input_pdf, output_pdf, add_signature, signature_position, fill_form, add_text, text_position, text_page, font_size):
    """Modify PDF by adding signatures, filling forms, or inserting text."""
    engine = ctx.obj['engine']
    
    try:
        # Initialize PDF modifier
        modifier = PDFModifier()
        
        # Parse options
        signatures = []
        form_data = []
        text_insertions = []
        
        # Handle signature addition
        if add_signature:
            pos_parts = [float(x.strip()) for x in signature_position.split(',')]
            if len(pos_parts) != 4:
                raise ValueError("Signature position must be x1,y1,x2,y2")
            
            signatures.append(SignatureOptions(
                position=tuple(pos_parts),
                image_path=add_signature
            ))
        
        # Handle form filling
        for form_item in fill_form:
            if ':' in form_item:
                field_name, field_value = form_item.split(':', 1)
                form_data.append(FormFillData(
                    field_name=field_name.strip(),
                    field_value=field_value.strip()
                ))
        
        # Handle text insertion
        if add_text:
            pos_parts = [float(x.strip()) for x in text_position.split(',')]
            if len(pos_parts) != 2:
                raise ValueError("Text position must be x,y")
            
            text_insertions.append(TextInsertion(
                text=add_text,
                position=tuple(pos_parts),
                page_number=text_page,
                font_size=font_size
            ))
        
        if not signatures and not form_data and not text_insertions:
            console.print("[yellow]No modifications specified. Use --help to see available options.[/yellow]")
            return
        
        # Perform modifications
        console.print(f"[blue]Modifying PDF: {input_pdf}[/blue]")
        result = modifier.modify_pdf(
            input_pdf,
            output_pdf,
            signatures=signatures,
            form_data=form_data,
            text_insertions=text_insertions
        )
        
        if result.success:
            console.print(f"[green]✅ PDF modified successfully![/green]")
            console.print(f"[green]📄 Output: {result.output_path}[/green]")
            console.print(f"[blue]📊 {result.modifications_applied} total modifications applied[/blue]")
            console.print(f"[blue]⏱️  Processing time: {result.processing_time:.2f}s[/blue]")
            
            if result.signatures_added > 0:
                console.print(f"[green]✍️  {result.signatures_added} signature(s) added[/green]")
            if result.forms_filled > 0:
                console.print(f"[green]📝 {result.forms_filled} form field(s) filled[/green]")
            if result.text_insertions > 0:
                console.print(f"[green]📄 {result.text_insertions} text element(s) inserted[/green]")
                
        else:
            console.print(f"[red]❌ PDF modification failed: {result.error_message}[/red]")
            
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        if not ctx.obj['quiet']:
            logger.exception("Modify command failed")


@cli.command()
@click.argument('input_dir', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.argument('output_dir', type=click.Path())
@click.option('--pattern', default='*.pdf', help='File pattern to match')
@click.option('--add-signature', type=click.Path(exists=True), help='Add signature image to all PDFs')
@click.option('--signature-position', default='400,700,500,750', help='Signature position as x1,y1,x2,y2')
@click.option('--fill-form', multiple=True, help='Fill form field as field_name:value')
@click.option('--add-text', help='Add text to all PDFs')
@click.option('--text-position', default='100,100', help='Text position as x,y')
@click.option('--text-page', default=0, help='Page number for text (0-based)')
@click.option('--font-size', default=12, help='Font size for text')
@click.option('--all-pages', is_flag=True, help='Apply text/signature to all pages')
@click.option('--config', type=click.Path(exists=True), help='JSON configuration file for complex modifications')
@click.option('--template', help='Use predefined modification template')
@click.option('--preview-only', is_flag=True, help='Preview modifications without applying')
@click.option('--parallel', is_flag=True, help='Process files in parallel')
@click.pass_context
def batch_modify(ctx, input_dir, output_dir, pattern, add_signature, signature_position, fill_form, add_text, text_position, text_page, font_size, all_pages, config, template, preview_only, parallel):
    """Batch modify multiple PDF files with same modifications."""
    import glob
    import json
    from pathlib import Path
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Find matching files
    input_path = Path(input_dir)
    files = list(input_path.glob(pattern))
    
    if not files:
        console.print(f"[yellow]No files matching '{pattern}' found in {input_dir}[/yellow]")
        return
    
    console.print(f"[blue]Found {len(files)} PDF files to modify[/blue]")
    
    # Load configuration if provided
    modifications = {}
    if config:
        with open(config, 'r') as f:
            modifications = json.load(f)
        console.print(f"[blue]Loaded configuration from {config}[/blue]")
    
    # Load template if provided
    if template:
        template_config = load_modification_template(template)
        if template_config:
            modifications.update(template_config)
            console.print(f"[blue]Applied template: {template}[/blue]")
        else:
            console.print(f"[yellow]Unknown template: {template}[/yellow]")
    
    # Build modification options from CLI args
    if not modifications:
        signatures = []
        form_data = []
        text_insertions = []
        
        if add_signature:
            pos_parts = [float(x.strip()) for x in signature_position.split(',')]
            signatures.append(SignatureOptions(
                position=tuple(pos_parts),
                image_path=add_signature
            ))
        
        for form_item in fill_form:
            if ':' in form_item:
                field_name, field_value = form_item.split(':', 1)
                form_data.append(FormFillData(
                    field_name=field_name.strip(),
                    field_value=field_value.strip()
                ))
        
        if add_text:
            pos_parts = [float(x.strip()) for x in text_position.split(',')]
            text_insertions.append(TextInsertion(
                text=add_text,
                position=tuple(pos_parts),
                page_number=text_page,
                font_size=font_size
            ))
        
        modifications = {
            'signatures': signatures,
            'form_data': form_data,
            'text_insertions': text_insertions,
            'all_pages': all_pages
        }
    
    if preview_only:
        console.print(f"[yellow]PREVIEW MODE - No files will be modified[/yellow]")
        console.print(f"[blue]Modifications to apply:[/blue]")
        preview_modifications(modifications)
        return
    
    # Process files
    results = []
    
    def process_single_file(pdf_file):
        """Process a single PDF file"""
        try:
            output_file = output_path / pdf_file.name
            
            modifier = PDFModifier()
            
            # Apply modifications based on config or CLI args
            if all_pages and 'text_insertions' in modifications:
                # Apply text to all pages
                result = apply_modifications_all_pages(
                    modifier, str(pdf_file), str(output_file), modifications
                )
            else:
                # Standard modification
                result = modifier.modify_pdf(
                    str(pdf_file),
                    str(output_file),
                    signatures=modifications.get('signatures', []),
                    form_data=modifications.get('form_data', []),
                    text_insertions=modifications.get('text_insertions', [])
                )
            
            if result.success:
                return {'file': pdf_file.name, 'status': 'success', 'modifications': result.modifications_applied, 'time': result.processing_time}
            else:
                return {'file': pdf_file.name, 'status': 'failed', 'error': result.error_message}
                
        except Exception as e:
            return {'file': pdf_file.name, 'status': 'failed', 'error': str(e)}
    
    if parallel and len(files) > 1:
        console.print(f"[blue]Processing {len(files)} files in parallel...[/blue]")
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_file = {executor.submit(process_single_file, f): f for f in files}
            
            with console.status("[bold blue]Processing files...", spinner="dots") as status:
                for future in as_completed(future_to_file):
                    result = future.result()
                    results.append(result)
                    
                    if result['status'] == 'success':
                        status.update(f"[green]✅ {result['file']} ({result['modifications']} mods)[/green]")
                    else:
                        status.update(f"[red]❌ {result['file']} failed[/red]")
    else:
        console.print(f"[blue]Processing {len(files)} files sequentially...[/blue]")
        for pdf_file in files:
            result = process_single_file(pdf_file)
            results.append(result)
            
            if result['status'] == 'success':
                console.print(f"[green]✅ {result['file']} - {result['modifications']} modifications applied[/green]")
            else:
                console.print(f"[red]❌ {result['file']} - {result['error']}[/red]")
    
    # Print summary
    successful = sum(1 for r in results if r['status'] == 'success')
    failed = len(results) - successful
    total_modifications = sum(r.get('modifications', 0) for r in results if r['status'] == 'success')
    
    console.print(f"\n[green]Batch modification complete![/green]")
    console.print(f"✅ Successful: {successful}/{len(files)}")
    console.print(f"📊 Total modifications applied: {total_modifications}")
    if failed > 0:
        console.print(f"❌ Failed: {failed}")


def load_modification_template(template_name: str) -> dict:
    """Load predefined modification template"""
    templates = {
        'approval-stamp': {
            'text_insertions': [
                TextInsertion(
                    text='APPROVED',
                    position=(450, 50),
                    font_size=16
                ),
                TextInsertion(
                    text=f'Date: {time.strftime("%Y-%m-%d")}',
                    position=(450, 30),
                    font_size=10
                )
            ]
        },
        'confidential-watermark': {
            'text_insertions': [
                TextInsertion(
                    text='CONFIDENTIAL',
                    position=(200, 400),
                    font_size=48
                )
            ],
            'all_pages': True
        },
        'signature-bottom-right': {
            'signatures': [
                SignatureOptions(
                    position=(400, 50, 500, 100),
                    text='Authorized Signature'
                )
            ]
        },
        'review-stamp': {
            'text_insertions': [
                TextInsertion(
                    text='REVIEWED',
                    position=(50, 50),
                    font_size=12
                ),
                TextInsertion(
                    text=f'Agent 2 - {time.strftime("%Y-%m-%d %H:%M")}',
                    position=(50, 30),
                    font_size=8
                )
            ]
        }
    }
    
    return templates.get(template_name)


def preview_modifications(modifications: dict):
    """Preview modifications without applying"""
    if modifications.get('signatures'):
        console.print(f"  📝 {len(modifications['signatures'])} signature(s)")
        for sig in modifications['signatures']:
            if hasattr(sig, 'image_path') and sig.image_path:
                console.print(f"    • Image signature: {sig.image_path}")
            elif hasattr(sig, 'text') and sig.text:
                console.print(f"    • Text signature: {sig.text}")
    
    if modifications.get('form_data'):
        console.print(f"  📋 {len(modifications['form_data'])} form field(s)")
        for form in modifications['form_data']:
            console.print(f"    • {form.field_name}: {form.field_value}")
    
    if modifications.get('text_insertions'):
        console.print(f"  📄 {len(modifications['text_insertions'])} text insertion(s)")
        for text in modifications['text_insertions']:
            console.print(f"    • '{text.text}' at {text.position}")
    
    if modifications.get('all_pages'):
        console.print(f"  🔄 Apply to all pages: Yes")


def apply_modifications_all_pages(modifier, input_path, output_path, modifications):
    """Apply modifications to all pages of a PDF"""
    import fitz
    
    # Get page count first
    doc = fitz.open(input_path)
    page_count = len(doc)
    doc.close()
    
    # Create text insertions for all pages
    all_text_insertions = []
    base_text_insertions = modifications.get('text_insertions', [])
    
    for page_num in range(page_count):
        for text_item in base_text_insertions:
            new_text_item = TextInsertion(
                text=text_item.text,
                position=text_item.position,
                page_number=page_num,
                font_size=text_item.font_size
            )
            all_text_insertions.append(new_text_item)
    
    # Apply all modifications
    return modifier.modify_pdf(
        input_path,
        output_path,
        signatures=modifications.get('signatures', []),
        form_data=modifications.get('form_data', []),
        text_insertions=all_text_insertions
    )


@cli.command()
@click.argument('pdf_path', type=click.Path(exists=True, file_okay=True, dir_okay=False))
@click.option('--page', default=0, help='Page number to analyze (0-based)')
@click.pass_context
def coordinates(ctx, pdf_path, page):
    """Show PDF page dimensions and coordinate helper grid."""
    import fitz
    
    try:
        doc = fitz.open(pdf_path)
        
        if page >= len(doc):
            console.print(f"[red]Error: Page {page} doesn't exist. PDF has {len(doc)} pages.[/red]")
            return
        
        pdf_page = doc.load_page(page)
        rect = pdf_page.rect
        
        console.print(f"[blue]📄 PDF: {Path(pdf_path).name}[/blue]")
        console.print(f"[blue]📋 Page {page + 1} of {len(doc)}[/blue]")
        console.print(f"[green]📐 Dimensions: {rect.width:.1f} x {rect.height:.1f} points[/green]")
        
        # Show coordinate system info
        console.print(f"\n[yellow]📍 COORDINATE SYSTEM:[/yellow]")
        console.print(f"  • Origin (0,0) is at BOTTOM-LEFT corner")
        console.print(f"  • X increases rightward (0 → {rect.width:.0f})")
        console.print(f"  • Y increases upward (0 → {rect.height:.0f})")
        
        # Show useful coordinate reference points
        console.print(f"\n[cyan]🎯 REFERENCE POINTS:[/cyan]")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Position", style="cyan")
        table.add_column("Coordinates", style="green")
        table.add_column("Use Case", style="yellow")
        
        positions = [
            ("Bottom-Left", f"(0, 0)", "Origin point"),
            ("Bottom-Right", f"({rect.width:.0f}, 0)", "Bottom edge signatures"),
            ("Top-Left", f"(0, {rect.height:.0f})", "Headers, titles"),
            ("Top-Right", f"({rect.width:.0f}, {rect.height:.0f})", "Page numbers, dates"),
            ("Center", f"({rect.width/2:.0f}, {rect.height/2:.0f})", "Watermarks, stamps"),
            ("Bottom Center", f"({rect.width/2:.0f}, 50)", "Footer text"),
            ("Top Center", f"({rect.width/2:.0f}, {rect.height-50:.0f})", "Header text"),
            ("Signature Area", f"(400, 50)", "Standard signature position"),
            ("Approval Stamp", f"(450, 100)", "Document approval area"),
            ("Margin Left", f"(50, {rect.height/2:.0f})", "Left margin notes"),
            ("Margin Right", f"({rect.width-100:.0f}, {rect.height/2:.0f})", "Right margin notes")
        ]
        
        for pos, coords, use_case in positions:
            table.add_row(pos, coords, use_case)
        
        console.print(table)
        
        # Show grid reference
        console.print(f"\n[magenta]📏 QUICK REFERENCE GRID:[/magenta]")
        console.print(f"  • Small text (8-10pt): Use for dates, footnotes")
        console.print(f"  • Normal text (12pt): Use for signatures, stamps")
        console.print(f"  • Large text (16-20pt): Use for titles, approvals")
        console.print(f"  • Watermark text (48pt): Use for confidential marks")
        
        # Signature size reference
        console.print(f"\n[blue]✍️  SIGNATURE AREA REFERENCE:[/blue]")
        console.print(f"  • Standard signature: 100x50 points")
        console.print(f"  • Large signature: 150x75 points")
        console.print(f"  • Bottom-right: ({rect.width-150:.0f}, 50, {rect.width-50:.0f}, 100)")
        console.print(f"  • Bottom-left: (50, 50, 150, 100)")
        
        # Common templates
        console.print(f"\n[green]📋 COMMON TEMPLATES:[/green]")
        console.print(f"  • approval-stamp: Text at (450, 50)")
        console.print(f"  • review-stamp: Text at (50, 50)")
        console.print(f"  • confidential-watermark: Large text at center")
        console.print(f"  • signature-bottom-right: Signature at (400, 50)")
        
        doc.close()
        
    except Exception as e:
        console.print(f"[red]❌ Error analyzing PDF: {e}[/red]")


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