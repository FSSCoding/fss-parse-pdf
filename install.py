#!/usr/bin/env python3
"""
FSS Parse PDF Installation Script
Professional installation with dependency management and system integration
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

def run_command(command, description="Running command"):
    """Run a shell command with error handling."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Error: {result.stderr}")
            return False
        if result.stdout.strip():
            print(f"✅ {result.stdout.strip()}")
        return True
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"   Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def install_dependencies():
    """Install required Python packages."""
    print("📦 Installing dependencies...")
    
    # Core dependencies with fallback options
    core_deps = [
        "click>=8.0.0",
        "rich>=12.0.0", 
        "PyYAML>=6.0",
        "tabulate>=0.9.0"
    ]
    
    # PDF backends (install with graceful failure)
    pdf_backends = [
        ("PyMuPDF>=1.21.0", "PyMuPDF (preferred PDF backend)"),
        ("pdfplumber>=0.7.0", "pdfplumber (alternative PDF backend)"), 
        ("PyPDF2>=3.0.0", "PyPDF2 (fallback PDF backend)")
    ]
    
    # Install core dependencies
    for dep in core_deps:
        if not run_command(f"pip install '{dep}'", f"Installing {dep.split('>=')[0]}"):
            return False
    
    # Install PDF backends with graceful handling
    backend_success = False
    for backend, description in pdf_backends:
        if run_command(f"pip install '{backend}'", f"Installing {description}"):
            backend_success = True
        else:
            print(f"⚠️  {description} failed - will try alternatives")
    
    if not backend_success:
        print("❌ No PDF backends installed successfully")
        print("   Please install manually: pip install PyMuPDF")
        return False
    
    return True

def create_global_command():
    """Create global 'fss-parse-pdf' command."""
    print("🔗 Creating global command...")
    
    # Get the current script directory
    pdf_dir = Path(__file__).parent.resolve()
    
    # Create executable script
    pdf_script = pdf_dir / "bin" / "fss-parse-pdf"
    pdf_script.parent.mkdir(exist_ok=True)
    
    script_content = f'''#!/usr/bin/env python3
"""
FSS Parse PDF Global Command
"""
import sys
import os

# Add the src directory to Python path
pdf_dir = r"{pdf_dir}"
sys.path.insert(0, os.path.join(pdf_dir, "src"))

# Import and run the main module
try:
    from pdf_engine import main
    if __name__ == "__main__":
        main()
except ImportError as e:
    print(f"❌ Error: Cannot import pdf_engine: {{e}}")
    print(f"   PDF directory: {{pdf_dir}}")
    print(f"   Python path: {{sys.path}}")
    sys.exit(1)
'''
    
    with open(pdf_script, 'w') as f:
        f.write(script_content)
    
    # Make executable
    os.chmod(pdf_script, 0o755)
    
    # Try to add to system PATH
    try:
        # Check if ~/bin exists and is in PATH
        home_bin = Path.home() / "bin"
        home_bin.mkdir(exist_ok=True)
        
        # Create symlink
        global_pdf = home_bin / "fss-parse-pdf"
        if global_pdf.exists():
            global_pdf.unlink()
        global_pdf.symlink_to(pdf_script)
        
        print(f"✅ Global command created: {global_pdf}")
        print(f"   Make sure {home_bin} is in your PATH")
        
        return True
    except Exception as e:
        print(f"⚠️  Could not create global command: {e}")
        print(f"   You can run directly: {pdf_script}")
        return False

def verify_installation():
    """Verify the installation works."""
    print("🧪 Verifying installation...")
    
    # Test imports
    test_imports = [
        ("click", "CLI framework"),
        ("rich", "Rich terminal output"),
        ("yaml", "YAML configuration support")
    ]
    
    # Test PDF backends
    pdf_backends = [
        ("fitz", "PyMuPDF (preferred)"),
        ("pdfplumber", "pdfplumber (alternative)"),
        ("PyPDF2", "PyPDF2 (fallback)")
    ]
    
    # Test core imports
    for module, description in test_imports:
        try:
            __import__(module)
            print(f"✅ {description}: {module}")
        except ImportError:
            print(f"❌ {description}: {module} not available")
            return False
    
    # Test PDF backend availability
    available_backends = []
    for module, description in pdf_backends:
        try:
            __import__(module)
            print(f"✅ {description}: available")
            available_backends.append(module)
        except ImportError:
            print(f"⚠️  {description}: not available")
    
    if not available_backends:
        print("❌ No PDF backends available")
        return False
    
    # Test our modules
    pdf_dir = Path(__file__).parent.resolve()
    sys.path.insert(0, str(pdf_dir / "src"))
    
    try:
        import pdf_engine
        import pdf_parser
        print("✅ PDF engine modules loaded")
    except ImportError as e:
        print(f"❌ PDF engine modules failed: {e}")
        return False
    
    return True

def display_usage_examples():
    """Display usage examples."""
    print("\n📋 Usage Examples:")
    print("   # Extract text from PDF")
    print("   fss-parse-pdf extract document.pdf")
    print("")
    print("   # Convert PDF to markdown")  
    print("   fss-parse-pdf convert document.pdf output.md")
    print("")
    print("   # Split PDF by pages")
    print("   fss-parse-pdf split document.pdf --pages 1-5")
    print("")
    print("   # Merge multiple PDFs")
    print("   fss-parse-pdf merge output.pdf file1.pdf file2.pdf file3.pdf")
    print("")
    print("   # Get PDF information")
    print("   fss-parse-pdf info document.pdf --verbose")
    print("")

def main():
    """Main installation process."""
    print("🚀 FSS Parse PDF Installation")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Dependency installation failed")
        sys.exit(1)
    
    # Create global command
    create_global_command()
    
    # Verify installation
    if not verify_installation():
        print("❌ Installation verification failed")
        sys.exit(1)
    
    print("=" * 50)
    print("✅ FSS Parse PDF installation complete!")
    print("")
    print("🎯 Part of the FSS Parsers collection:")
    print("   • fss-parse-word  - Word document processing") 
    print("   • fss-parse-excel - Spreadsheet manipulation")
    print("   • fss-parse-pdf   - PDF extraction & conversion")
    print("")
    
    display_usage_examples()
    
    print("📚 Documentation: README.md")
    print("🧪 Run tests: python -m pytest tests/")
    print("🛡️  Built with production safety and enterprise quality standards")

if __name__ == "__main__":
    main()