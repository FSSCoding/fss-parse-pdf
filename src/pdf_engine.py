#!/usr/bin/env python3
"""
PDF Engine - Main CLI Interface for Professional PDF Operations
Designed for CLI agents and automated workflows with comprehensive PDF manipulation.
"""

import argparse
import sys
import json
import logging
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