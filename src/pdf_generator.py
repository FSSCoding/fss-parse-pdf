#!/usr/bin/env python3
"""
PDF Generator - Professional PDF generation from Markdown and other formats
Designed for CLI agents with modern typography and enterprise-grade templates.
"""

import logging
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
import json
import hashlib

try:
    import yaml
    _has_yaml = True
except ImportError:
    _has_yaml = False

from safety_manager import SafetyManager

logger = logging.getLogger(__name__)

@dataclass
class GenerationConfig:
    """Configuration for PDF generation."""
    template: str = "eisvogel"
    engine: str = "auto"  # auto, xelatex, pdflatex, lualatex, typst
    font_main: str = "Inter"
    font_code: str = "JetBrains Mono"
    font_size: int = 11
    color_theme: str = "professional"
    margins: str = "normal"  # narrow, normal, wide
    include_toc: bool = False
    number_sections: bool = False
    syntax_highlighting: bool = True
    bibliography: Optional[str] = None
    cover_page: Optional[str] = None
    custom_template_path: Optional[str] = None

@dataclass
class GenerationResult:
    """Result of PDF generation operation."""
    success: bool
    output_path: Optional[str] = None
    engine_used: Optional[str] = None
    template_used: Optional[str] = None
    generation_time: float = 0.0
    warnings: List[str] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.errors is None:
            self.errors = []

class TemplateManager:
    """Manages PDF generation templates and their installation."""
    
    def __init__(self):
        self.templates_dir = Path.home() / ".local" / "share" / "pandoc" / "templates"
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Built-in template configurations
        self.template_configs = {
            "eisvogel": {
                "name": "Eisvogel LaTeX Template",
                "url": "https://github.com/Wandmalfarbe/pandoc-latex-template/releases/latest/download/eisvogel.zip",
                "engines": ["xelatex", "lualatex", "pdflatex"],
                "preferred_engine": "xelatex",
                "requires_packages": ["texlive-latex-extra", "texlive-fonts-extra"]
            },
            "typst-modern": {
                "name": "Modern Typst Template",
                "engines": ["typst"],
                "preferred_engine": "typst",
                "builtin": True
            },
            "academic": {
                "name": "Academic Paper Template",
                "engines": ["xelatex", "pdflatex"],
                "preferred_engine": "xelatex",
                "builtin": True
            },
            "corporate": {
                "name": "Corporate Document Template", 
                "engines": ["xelatex", "lualatex"],
                "preferred_engine": "xelatex",
                "builtin": True
            },
            "technical": {
                "name": "Technical Documentation Template",
                "engines": ["xelatex", "lualatex"],
                "preferred_engine": "xelatex",
                "builtin": True
            }
        }
    
    def is_template_installed(self, template_name: str) -> bool:
        """Check if a template is installed."""
        if template_name == "eisvogel":
            return (self.templates_dir / "eisvogel.latex").exists()
        elif template_name.startswith("typst-"):
            return self._check_typst_available()
        else:
            # Built-in templates are always available
            return template_name in self.template_configs
    
    def install_eisvogel(self) -> bool:
        """Download and install the Eisvogel template."""
        try:
            import urllib.request
            import zipfile
            
            logger.info("Downloading Eisvogel template...")
            
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                zip_path = temp_path / "eisvogel.zip"
                
                # Download template
                url = self.template_configs["eisvogel"]["url"]
                urllib.request.urlretrieve(url, zip_path)
                
                # Extract template
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_path)
                
                # Find and copy template files
                template_files = list(temp_path.glob("**/eisvogel.latex"))
                if template_files:
                    shutil.copy2(template_files[0], self.templates_dir)
                    logger.info(f"Eisvogel template installed to {self.templates_dir}")
                    return True
                else:
                    logger.error("Eisvogel template file not found in download")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to install Eisvogel template: {e}")
            return False
    
    def _check_typst_available(self) -> bool:
        """Check if Typst is available on the system."""
        return shutil.which("typst") is not None
    
    def get_template_info(self, template_name: str) -> Dict[str, Any]:
        """Get information about a template."""
        return self.template_configs.get(template_name, {})

class PDFGenerator:
    """
    Professional PDF generation engine supporting multiple templates and engines.
    
    Features:
    - Eisvogel LaTeX template integration
    - Typst engine support
    - Modern typography and styling
    - Corporate template system
    - CLI agent optimization
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize PDF generator with configuration."""
        self.config = config or {}
        self.template_manager = TemplateManager()
        self.safety_manager = SafetyManager(self.config.get('safety', {}))
        
        # Engine availability cache
        self._engine_cache = {}
    
    def generate_pdf(self, input_path: str, output_path: str, 
                    config: Optional[GenerationConfig] = None) -> GenerationResult:
        """
        Generate PDF from markdown or text input.
        
        Args:
            input_path: Path to input file (markdown, text, etc.)
            output_path: Path to output PDF file
            config: Generation configuration
            
        Returns:
            GenerationResult with success status and details
        """
        import time
        start_time = time.time()
        
        # Initialize result
        result = GenerationResult(success=False)
        
        # Use provided config or create default
        if config is None:
            config = GenerationConfig()
        
        # Validate input
        input_path = Path(input_path)
        output_path = Path(output_path)
        
        if not input_path.exists():
            result.errors.append(f"Input file not found: {input_path}")
            return result
        
        try:
            # Safety validation
            safety_result = self.safety_manager.validate_file(str(input_path))
            if not safety_result.get('is_safe', True):
                result.errors.extend(safety_result.get('issues', []))
                return result
            
            # Ensure template is installed
            if not self.template_manager.is_template_installed(config.template):
                if config.template == "eisvogel":
                    logger.info("Installing Eisvogel template...")
                    if not self.template_manager.install_eisvogel():
                        result.errors.append("Failed to install Eisvogel template")
                        return result
                else:
                    result.warnings.append(f"Template '{config.template}' not found, using default")
                    config.template = "academic"
            
            # Determine best engine
            engine = self._select_engine(config)
            if not engine:
                result.errors.append("No suitable PDF engine found")
                return result
            
            # Generate PDF based on engine
            if engine == "typst":
                success = self._generate_with_typst(input_path, output_path, config)
            else:
                success = self._generate_with_pandoc(input_path, output_path, config, engine)
            
            # Finalize result
            result.success = success
            result.output_path = str(output_path) if success else None
            result.engine_used = engine
            result.template_used = config.template
            result.generation_time = time.time() - start_time
            
            if success:
                logger.info(f"PDF generated successfully: {output_path}")
            else:
                result.errors.append("PDF generation failed")
                
        except Exception as e:
            result.errors.append(f"Generation error: {str(e)}")
            logger.error(f"PDF generation failed: {e}", exc_info=True)
        
        return result
    
    def _select_engine(self, config: GenerationConfig) -> Optional[str]:
        """Select the best available PDF engine."""
        if config.engine != "auto":
            if self._is_engine_available(config.engine):
                return config.engine
            else:
                logger.warning(f"Requested engine '{config.engine}' not available")
        
        # Get template preferences
        template_info = self.template_manager.get_template_info(config.template)
        preferred_engines = template_info.get('engines', ['xelatex', 'pdflatex', 'typst'])
        
        # Check engines in preference order
        for engine in preferred_engines:
            if self._is_engine_available(engine):
                return engine
        
        # Fallback to any available engine
        for engine in ['xelatex', 'pdflatex', 'lualatex', 'typst']:
            if self._is_engine_available(engine):
                return engine
        
        return None
    
    def _is_engine_available(self, engine: str) -> bool:
        """Check if a PDF engine is available."""
        if engine in self._engine_cache:
            return self._engine_cache[engine]
        
        available = shutil.which(engine) is not None
        self._engine_cache[engine] = available
        return available
    
    def _generate_with_pandoc(self, input_path: Path, output_path: Path, 
                             config: GenerationConfig, engine: str) -> bool:
        """Generate PDF using Pandoc with LaTeX engines."""
        try:
            # Build pandoc command
            cmd = [
                "pandoc",
                str(input_path),
                "-o", str(output_path),
                f"--pdf-engine={engine}"
            ]
            
            # Add template
            if config.template == "eisvogel":
                cmd.extend(["--template", "eisvogel"])
            
            # Typography settings
            cmd.extend([
                f"--variable", f"fontsize={config.font_size}pt",
                f"--variable", f"mainfont={config.font_main}",
                f"--variable", f"monofont={config.font_code}"
            ])
            
            # Margin settings
            if config.margins == "narrow":
                cmd.extend(["--variable", "geometry:margin=0.5in"])
            elif config.margins == "wide":
                cmd.extend(["--variable", "geometry:margin=1.25in"])
            else:
                cmd.extend(["--variable", "geometry:margin=1in"])
            
            # Additional options
            if config.include_toc:
                cmd.append("--toc")
            
            if config.number_sections:
                cmd.append("--number-sections")
            
            if config.syntax_highlighting:
                cmd.extend(["--highlight-style", "pygments"])
            
            if config.bibliography:
                cmd.extend(["--bibliography", config.bibliography])
            
            # Color theme variables for Eisvogel
            if config.template == "eisvogel":
                if config.color_theme == "corporate":
                    cmd.extend([
                        "--variable", "titlepage=true",
                        "--variable", "colorlinks=true",
                        "--variable", "linkcolor=blue"
                    ])
            
            # Execute pandoc
            logger.debug(f"Running pandoc command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                return True
            else:
                logger.error(f"Pandoc failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Pandoc command timed out")
            return False
        except Exception as e:
            logger.error(f"Pandoc execution failed: {e}")
            return False
    
    def _generate_with_typst(self, input_path: Path, output_path: Path, 
                           config: GenerationConfig) -> bool:
        """Generate PDF using Typst engine."""
        try:
            # For now, convert markdown to text and use basic Typst
            # In future, create proper Typst templates
            
            # Read input content
            content = input_path.read_text(encoding='utf-8')
            
            # Create basic Typst document
            typst_content = self._create_typst_document(content, config)
            
            # Write to temporary Typst file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.typ', delete=False, encoding='utf-8') as f:
                f.write(typst_content)
                typst_path = f.name
            
            try:
                # Run Typst compiler
                cmd = ["typst", "compile", typst_path, str(output_path)]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    return True
                else:
                    logger.error(f"Typst failed: {result.stderr}")
                    return False
                    
            finally:
                # Clean up temporary file
                Path(typst_path).unlink(missing_ok=True)
                
        except Exception as e:
            logger.error(f"Typst execution failed: {e}")
            return False
    
    def _create_typst_document(self, content: str, config: GenerationConfig) -> str:
        """Create a basic Typst document from markdown content."""
        # This is a simplified conversion - in production, you'd want
        # a proper markdown-to-typst converter
        
        typst_doc = f"""
#set text(font: "{config.font_main}", size: {config.font_size}pt)
#set raw(font: "{config.font_code}")
#set page(margin: 1in)

"""
        
        if config.include_toc:
            typst_doc += "#outline()\n\n"
        
        # Basic markdown-to-typst conversion
        lines = content.split('\n')
        in_code_block = False
        
        for line in lines:
            if line.strip().startswith('```'):
                if in_code_block:
                    typst_doc += "```\n"
                    in_code_block = False
                else:
                    typst_doc += "```\n"
                    in_code_block = True
            elif line.startswith('# '):
                typst_doc += f"= {line[2:]}\n"
            elif line.startswith('## '):
                typst_doc += f"== {line[3:]}\n"
            elif line.startswith('### '):
                typst_doc += f"=== {line[4:]}\n"
            else:
                typst_doc += f"{line}\n"
        
        return typst_doc
    
    def list_templates(self) -> Dict[str, Dict[str, Any]]:
        """List available templates and their status."""
        templates = {}
        
        for name, info in self.template_manager.template_configs.items():
            templates[name] = {
                "name": info["name"],
                "engines": info["engines"],
                "installed": self.template_manager.is_template_installed(name),
                "preferred_engine": info.get("preferred_engine"),
                "description": self._get_template_description(name)
            }
        
        return templates
    
    def _get_template_description(self, template_name: str) -> str:
        """Get description for a template."""
        descriptions = {
            "eisvogel": "Professional LaTeX template with modern typography, ideal for technical documents",
            "typst-modern": "Clean, modern template using Typst engine for fast compilation",
            "academic": "Traditional academic paper format with proper citations and structure",
            "corporate": "Business-focused template with professional styling and branding",
            "technical": "Code-heavy documentation template with excellent syntax highlighting"
        }
        return descriptions.get(template_name, "Custom template")
    
    def get_engine_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about available PDF engines."""
        engines = {}
        
        for engine in ['xelatex', 'pdflatex', 'lualatex', 'typst']:
            engines[engine] = {
                "available": self._is_engine_available(engine),
                "description": self._get_engine_description(engine)
            }
        
        return engines
    
    def _get_engine_description(self, engine: str) -> str:
        """Get description for a PDF engine."""
        descriptions = {
            "xelatex": "Modern LaTeX engine with excellent Unicode and font support",
            "pdflatex": "Traditional LaTeX engine, fast and reliable for basic documents", 
            "lualatex": "Lua-powered LaTeX engine with advanced scripting capabilities",
            "typst": "Modern typesetting system, fast compilation and clean syntax"
        }
        return descriptions.get(engine, "PDF generation engine")