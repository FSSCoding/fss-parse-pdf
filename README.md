# FSS Parse PDF

**Professional-grade PDF manipulation toolkit for CLI agents and automated workflows**

Part of the **FSS Parsers** collection - individual parser tools with the `fss-parse-*` CLI prefix for comprehensive document operations. **Completely standalone** - no dependencies on other FSS parsers.

🛡️ **Built with production safety and enterprise quality standards**

🚀 **NEW: Professional PDF Generation from Markdown with modern templates!**

## 🚀 Quick Start

### Installation
```bash
# Clone the repository
git clone https://github.com/FSSCoding/fss-parse-pdf.git
cd fss-parse-pdf
python3 install.py

# Your tool is now available as 'fss-parse-pdf'
```

### Basic Usage
```bash
# Extract text from PDF
fss-parse-pdf extract document.pdf

# Convert PDF to markdown
fss-parse-pdf convert document.pdf output.md

# Split PDF by pages
fss-parse-pdf split document.pdf --pages 1-5 --output chapter1.pdf

# Merge multiple PDFs
fss-parse-pdf merge file1.pdf file2.pdf file3.pdf --output combined.pdf

# Get PDF information
fss-parse-pdf info document.pdf
```

## ✨ Key Features

### 🛡️ **Production Safety**
- **Hash Validation**: SHA256 checksums prevent data corruption
- **Collision Detection**: Prevents overwriting different files with same name
- **Automatic Backups**: Creates `.backup` files before overwriting
- **Confirmation Prompts**: Interactive safety checks before destructive operations
- **Never Destroys Documents**: Multiple safety layers protect your files

### 🎯 **Professional Quality**
- **Multiple PDF Backends**: PyMuPDF (preferred), pdfplumber, PyPDF2 with automatic fallback
- **Smart Text Extraction**: Layout-aware extraction preserving document structure
- **Metadata Preservation**: Complete document metadata extraction and preservation
- **Page-Level Control**: Precise page-by-page operations and chunking
- **Enterprise-Grade Output**: Professional documents optimized for CLI agents

### 🔧 **Robust Processing**
- **Multi-Backend Fallback**: Automatic library selection based on availability
- **Error Recovery**: Graceful handling of corrupted or complex PDFs
- **Performance Optimized**: 6x speed improvement through direct chunk production
- **Memory Efficient**: Streaming processing for large PDF files
- **Quality Assessment**: Automatic text quality validation and retry mechanisms

### 📊 **CLI Agent Features**
- **Text Extraction**: Clean text output for processing pipelines
- **Format Conversion**: PDF → Markdown, JSON, YAML, plain text
- **Page Operations**: Split, merge, extract specific pages
- **Metadata Operations**: Extract and manipulate PDF metadata
- **Search & Filter**: Find text patterns across documents
- **Batch Processing**: Process multiple PDFs efficiently

## 🔄 Multi-Format Support

### Input Formats
- **.pdf** - Portable Document Format (all versions)
- **Password-protected PDFs** - With authentication
- **Scanned PDFs** - OCR-enabled extraction (optional)

### Output Formats
- **.txt** - Plain text extraction
- **.md** - Markdown with preserved structure
- **.json** - Structured data with metadata
- **.yaml** - Configuration-friendly format
- **.html** - Web-ready format
- **.pdf** - Split, merged, or processed PDFs

## 🏗️ Architecture

### Modular Design
```
pdf/
├── src/                    # Core implementation
│   ├── pdf_engine.py      # Main CLI interface
│   ├── pdf_parser.py      # Core PDF parsing (from FSS-RAG)
│   ├── text_extractor.py  # Text extraction with quality assessment
│   ├── pdf_manipulator.py # Split, merge, page operations
│   ├── converters.py      # Format conversion modules
│   └── safety_manager.py  # File safety and validation
├── bin/                   # Executable scripts
├── config/               # Configuration files
├── tests/               # Test suite
└── docs/               # Documentation
```

### Safety First
- Same battle-tested safety system as Word and Excel parsers
- Hash validation prevents data corruption
- Automatic backups with collision detection
- Graceful error handling and recovery

## 🚀 NEW: Professional PDF Generation

### Generate Beautiful PDFs from Markdown
```bash
# Basic generation with Eisvogel template
fss-parse-pdf generate document.md output.pdf

# Corporate styling with custom fonts
fss-parse-pdf generate report.md corporate_report.pdf \
  --template eisvogel \
  --font-main "Calibri" \
  --font-code "Consolas" \
  --color-theme corporate \
  --toc \
  --number-sections

# Modern Typst engine for fast compilation
fss-parse-pdf generate document.md output.pdf \
  --template typst-modern \
  --engine typst \
  --margins narrow

# Academic paper with bibliography
fss-parse-pdf generate paper.md paper.pdf \
  --template academic \
  --bibliography references.bib \
  --syntax-highlighting
```

### Template Management
```bash
# List available templates and engines
fss-parse-pdf templates --show-engines

# Check what's installed
fss-parse-pdf templates
```

**Available Templates:**
- **eisvogel** - Professional LaTeX template with modern typography
- **typst-modern** - Fast, clean template using Typst engine  
- **academic** - Traditional academic paper format
- **corporate** - Business-focused professional styling
- **technical** - Code-heavy documentation template

## 🛠 CLI Interface

### Text Extraction
```bash
# Basic text extraction
fss-parse-pdf extract document.pdf

# Extract with page numbers
fss-parse-pdf extract document.pdf --include-page-numbers

# Extract specific pages
fss-parse-pdf extract document.pdf --pages 1,3,5-10

# Extract with metadata
fss-parse-pdf extract document.pdf --include-metadata --format json
```

### Format Conversion
```bash
# Convert to markdown
fss-parse-pdf convert document.pdf output.md

# Convert with structure preservation
fss-parse-pdf convert document.pdf output.md --preserve-structure

# Convert to JSON with metadata
fss-parse-pdf convert document.pdf data.json --include-metadata

# Batch conversion
fss-parse-pdf convert *.pdf --output-dir converted/ --format md
```

### PDF Manipulation
```bash
# Split PDF by pages
fss-parse-pdf split document.pdf --pages 1-5 --output chapter1.pdf

# Split by page count
fss-parse-pdf split document.pdf --every 10 --prefix section

# Merge PDFs
fss-parse-pdf merge file1.pdf file2.pdf --output combined.pdf

# Extract specific pages
fss-parse-pdf extract-pages document.pdf --pages 1,3,5 --output selected.pdf
```

### Information & Analysis
```bash
# Get PDF info
fss-parse-pdf info document.pdf

# Get detailed metadata
fss-parse-pdf info document.pdf --verbose

# Search text
fss-parse-pdf search document.pdf "search term"

# Count pages/words
fss-parse-pdf stats document.pdf
```

## 📋 Configuration

### Configuration Files
```yaml
# config/pdf.yml
extraction:
  backend: "auto"  # auto, pymupdf, pdfplumber, pypdf2
  quality_check: true
  include_metadata: true
  chunk_strategy: "page"  # page, paragraph, fixed_size

conversion:
  preserve_structure: true
  include_page_numbers: false
  markdown_format: "github"

safety:
  create_backup: true
  require_confirmation: true
  hash_validation: true

performance:
  max_file_size: "100MB"
  memory_limit: "500MB"
  parallel_processing: true
```

### Command-line Overrides
```bash
# Override backend selection
fss-parse-pdf extract document.pdf --backend pymupdf

# Skip safety checks
fss-parse-pdf split document.pdf --pages 1-5 --force --no-backup

# Custom chunk size
fss-parse-pdf extract document.pdf --chunk-size 2000
```

## 🧪 Testing

```bash
cd pdf
python -m pytest tests/
```

## 📋 Requirements

- Python 3.8+
- PyMuPDF (recommended) - `pip install PyMuPDF`
- pdfplumber (alternative) - `pip install pdfplumber` 
- PyPDF2 (fallback) - `pip install PyPDF2`
- Optional: Tesseract for OCR - `apt-get install tesseract-ocr`

## 🎯 Design Philosophy

Built for **CLI agents** and **automated workflows** with:

1. **Precision**: Exact page-level control and manipulation
2. **Reliability**: Enterprise-grade error handling and safety
3. **Performance**: Optimized for batch processing and large files
4. **Flexibility**: Multiple backends and output formats
5. **Simplicity**: Clean, intuitive interface for automation

## 🚨 Safety Features

- **Hash Validation**: Prevents accidental data corruption
- **Backup Creation**: Automatic backups before modifications
- **Collision Detection**: Prevents conflicting file operations
- **Quality Assessment**: Validates extraction quality with retry mechanisms
- **Memory Management**: Safe handling of large PDF files

## 🔗 Integration

Perfect companion to other FSS Parsers:
- **fss-parse-word** - Word document processing
- **fss-parse-excel** - Spreadsheet manipulation
- **fss-parse-pdf** - PDF extraction and conversion

---

**Professional PDF processing for the modern CLI workflow.**