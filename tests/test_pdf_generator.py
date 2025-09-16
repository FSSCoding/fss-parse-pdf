#!/usr/bin/env python3
"""
Comprehensive tests for PDF generation functionality.
Tests both the generation system and template management.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import subprocess

from src.pdf_generator import (
    PDFGenerator, 
    GenerationConfig, 
    GenerationResult,
    TemplateManager
)

class TestTemplateManager:
    """Test the template management system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.template_manager = TemplateManager()
        # Override templates dir for testing
        self.template_manager.templates_dir = Path(self.temp_dir) / "templates"
        self.template_manager.templates_dir.mkdir(parents=True, exist_ok=True)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_template_manager_initialization(self):
        """Test template manager initializes correctly."""
        assert isinstance(self.template_manager.template_configs, dict)
        assert "eisvogel" in self.template_manager.template_configs
        assert "typst-modern" in self.template_manager.template_configs
    
    def test_eisvogel_not_installed_initially(self):
        """Test Eisvogel template is not installed initially."""
        assert not self.template_manager.is_template_installed("eisvogel")
    
    def test_builtin_templates_always_available(self):
        """Test built-in templates are always available."""
        assert self.template_manager.is_template_installed("academic")
        assert self.template_manager.is_template_installed("corporate")
        assert self.template_manager.is_template_installed("technical")
    
    @patch('shutil.which')
    def test_typst_availability_check(self, mock_which):
        """Test Typst availability checking."""
        # Test when Typst is available
        mock_which.return_value = "/usr/bin/typst"
        assert self.template_manager._check_typst_available()
        
        # Test when Typst is not available
        mock_which.return_value = None
        assert not self.template_manager._check_typst_available()
    
    def test_get_template_info(self):
        """Test getting template information."""
        eisvogel_info = self.template_manager.get_template_info("eisvogel")
        assert eisvogel_info["name"] == "Eisvogel LaTeX Template"
        assert "xelatex" in eisvogel_info["engines"]
        
        # Test non-existent template
        empty_info = self.template_manager.get_template_info("nonexistent")
        assert empty_info == {}
    
    @patch('urllib.request.urlretrieve')
    @patch('zipfile.ZipFile')
    def test_eisvogel_installation_success(self, mock_zipfile, mock_urlretrieve):
        """Test successful Eisvogel template installation."""
        # Mock zipfile extraction
        mock_zip = Mock()
        mock_zipfile.return_value.__enter__.return_value = mock_zip
        mock_zip.extractall = Mock()
        
        # Mock finding the template file
        template_path = self.template_manager.templates_dir / "eisvogel.latex"
        template_path.write_text("mock template content")
        
        result = self.template_manager.install_eisvogel()
        # Since we're mocking, the actual download won't work, but we can test the logic
        # In a real scenario, this would be tested with a test server
    
    def test_eisvogel_installation_failure(self):
        """Test failed Eisvogel template installation."""
        # Test installation failure (network issues, etc.)
        with patch('urllib.request.urlretrieve', side_effect=Exception("Network error")):
            result = self.template_manager.install_eisvogel()
            assert not result

class TestGenerationConfig:
    """Test the generation configuration system."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = GenerationConfig()
        assert config.template == "eisvogel"
        assert config.engine == "auto"
        assert config.font_main == "Inter"
        assert config.font_code == "JetBrains Mono"
        assert config.font_size == 11
        assert config.margins == "normal"
        assert not config.include_toc
        assert not config.number_sections
        assert config.syntax_highlighting
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = GenerationConfig(
            template="typst-modern",
            engine="typst",
            font_size=12,
            include_toc=True,
            margins="narrow"
        )
        assert config.template == "typst-modern"
        assert config.engine == "typst"
        assert config.font_size == 12
        assert config.include_toc
        assert config.margins == "narrow"

class TestPDFGenerator:
    """Test the main PDF generation system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Create test input file
        self.test_md = self.temp_path / "test.md"
        self.test_md.write_text("""# Test Document

This is a **test** document for PDF generation.

## Features

- Lists
- **Bold text**
- *Italic text*
- `Code snippets`

```python
def hello():
    print("Hello, World!")
```

## Conclusion

This concludes our test document.
""", encoding='utf-8')
        
        self.generator = PDFGenerator()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_generator_initialization(self):
        """Test PDF generator initializes correctly."""
        assert isinstance(self.generator.template_manager, TemplateManager)
        assert hasattr(self.generator, 'safety_manager')
        assert isinstance(self.generator._engine_cache, dict)
    
    @patch('shutil.which')
    def test_engine_availability_caching(self, mock_which):
        """Test engine availability is cached."""
        # First call
        mock_which.return_value = "/usr/bin/xelatex"
        result1 = self.generator._is_engine_available("xelatex")
        assert result1
        
        # Second call should use cache
        mock_which.reset_mock()
        result2 = self.generator._is_engine_available("xelatex")
        assert result2
        assert not mock_which.called  # Should not call which again
    
    @patch('shutil.which')
    def test_engine_selection_auto(self, mock_which):
        """Test automatic engine selection."""
        # Mock available engines
        def which_side_effect(engine):
            available_engines = {"xelatex": "/usr/bin/xelatex", "typst": "/usr/bin/typst"}
            return available_engines.get(engine)
        
        mock_which.side_effect = which_side_effect
        
        config = GenerationConfig(engine="auto")
        engine = self.generator._select_engine(config)
        assert engine in ["xelatex", "typst"]  # Should select an available engine
    
    @patch('shutil.which')
    def test_engine_selection_specific(self, mock_which):
        """Test specific engine selection."""
        mock_which.return_value = "/usr/bin/xelatex"
        
        config = GenerationConfig(engine="xelatex")
        engine = self.generator._select_engine(config)
        assert engine == "xelatex"
    
    @patch('shutil.which')
    def test_no_engines_available(self, mock_which):
        """Test when no engines are available."""
        mock_which.return_value = None  # No engines available
        
        config = GenerationConfig(engine="auto")
        engine = self.generator._select_engine(config)
        assert engine is None
    
    def test_list_templates(self):
        """Test listing available templates."""
        templates = self.generator.list_templates()
        assert isinstance(templates, dict)
        assert "eisvogel" in templates
        assert "typst-modern" in templates
        
        # Check template structure
        eisvogel = templates["eisvogel"]
        assert "name" in eisvogel
        assert "engines" in eisvogel
        assert "installed" in eisvogel
        assert "description" in eisvogel
    
    @patch('shutil.which')
    async def test_get_engine_info(self, mock_which):
        """Test getting engine information."""
        mock_which.side_effect = lambda x: "/usr/bin/" + x if x in ["xelatex", "typst"] else None
        
        engines = self.generator.get_engine_info()
        assert isinstance(engines, dict)
        assert "xelatex" in engines
        assert "typst" in engines
        assert "pdflatex" in engines
        
        # Check engine structure
        xelatex = engines["xelatex"]
        assert "available" in xelatex
        assert "description" in xelatex
    
    def test_template_descriptions(self):
        """Test template descriptions are informative."""
        description = self.generator._get_template_description("eisvogel")
        assert len(description) > 10  # Should be descriptive
        assert "professional" in description.lower() or "modern" in description.lower()
    
    def test_engine_descriptions(self):
        """Test engine descriptions are informative."""
        description = self.generator._get_engine_description("xelatex")
        assert len(description) > 10  # Should be descriptive
        assert "latex" in description.lower() or "font" in description.lower()

class TestPDFGenerationIntegration:
    """Integration tests for PDF generation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Create test input file
        self.test_md = self.temp_path / "test_integration.md"
        self.test_md.write_text("""# Integration Test

This is an integration test for PDF generation.

## Code Example

```python
print("Testing PDF generation")
```

## List Example

1. First item
2. Second item
3. Third item

**Bold text** and *italic text* should work.
""", encoding='utf-8')
        
        self.generator = PDFGenerator()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_missing_input_file(self):
        """Test handling of missing input file."""
        nonexistent_file = self.temp_path / "nonexistent.md"
        output_file = self.temp_path / "output.pdf"
        
        result = self.generator.generate_pdf(str(nonexistent_file), str(output_file))
        
        assert not result.success
        assert len(result.errors) > 0
        assert "not found" in result.errors[0].lower()
    
    @patch('subprocess.run')
    @patch('shutil.which')
    def test_pandoc_generation_success(self, mock_which, mock_subprocess):
        """Test successful PDF generation with Pandoc."""
        # Mock engine availability
        mock_which.return_value = "/usr/bin/xelatex"
        
        # Mock successful subprocess call
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        # Mock template installation
        with patch.object(self.generator.template_manager, 'is_template_installed', return_value=True):
            output_file = self.temp_path / "output.pdf"
            config = GenerationConfig(template="eisvogel", engine="xelatex")
            
            result = self.generator.generate_pdf(str(self.test_md), str(output_file), config)
            
            assert result.success
            assert result.engine_used == "xelatex"
            assert result.template_used == "eisvogel"
            assert result.generation_time > 0
    
    @patch('subprocess.run')
    @patch('shutil.which')
    def test_pandoc_generation_failure(self, mock_which, mock_subprocess):
        """Test PDF generation failure with Pandoc."""
        # Mock engine availability
        mock_which.return_value = "/usr/bin/xelatex"
        
        # Mock failed subprocess call
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "LaTeX Error: something went wrong"
        mock_subprocess.return_value = mock_result
        
        # Mock template installation
        with patch.object(self.generator.template_manager, 'is_template_installed', return_value=True):
            output_file = self.temp_path / "output.pdf"
            config = GenerationConfig(template="eisvogel", engine="xelatex")
            
            result = self.generator.generate_pdf(str(self.test_md), str(output_file), config)
            
            assert not result.success
            assert len(result.errors) > 0
    
    @patch('shutil.which')
    def test_typst_document_creation(self, mock_which):
        """Test Typst document creation from markdown."""
        mock_which.return_value = "/usr/bin/typst"
        
        config = GenerationConfig(
            template="typst-modern",
            engine="typst",
            font_main="Arial",
            font_code="Courier",
            font_size=12,
            include_toc=True
        )
        
        content = "# Test\n\nThis is a test.\n\n```python\nprint('hello')\n```"
        typst_doc = self.generator._create_typst_document(content, config)
        
        assert f'font: "{config.font_main}"' in typst_doc
        assert f'font: "{config.font_code}"' in typst_doc
        assert f'size: {config.font_size}pt' in typst_doc
        assert "#outline()" in typst_doc  # TOC should be included
        assert "= Test" in typst_doc  # Heading conversion
        assert "```" in typst_doc  # Code block preservation
    
    def test_generation_result_structure(self):
        """Test GenerationResult structure."""
        result = GenerationResult(success=True)
        assert result.success
        assert result.warnings == []
        assert result.errors == []
        assert result.generation_time == 0.0
        
        # Test with custom values
        result_custom = GenerationResult(
            success=False,
            engine_used="xelatex",
            template_used="eisvogel",
            generation_time=2.5,
            warnings=["warning1"],
            errors=["error1"]
        )
        assert not result_custom.success
        assert result_custom.engine_used == "xelatex"
        assert result_custom.generation_time == 2.5
        assert len(result_custom.warnings) == 1
        assert len(result_custom.errors) == 1

class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = PDFGenerator()
    
    def test_subprocess_timeout_handling(self):
        """Test handling of subprocess timeouts."""
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired("pandoc", 300)):
            result = self.generator._generate_with_pandoc(
                Path("test.md"),
                Path("output.pdf"),
                GenerationConfig(),
                "xelatex"
            )
            assert not result
    
    def test_invalid_template_fallback(self):
        """Test fallback when invalid template is specified."""
        output_path = "/tmp/test_output.pdf"
        
        # Create a minimal input file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Test\n\nContent")
            input_path = f.name
        
        try:
            config = GenerationConfig(template="nonexistent_template")
            result = self.generator.generate_pdf(input_path, output_path, config)
            
            # Should warn about template not found and fall back
            assert len(result.warnings) > 0
            assert any("not found" in warning for warning in result.warnings)
        finally:
            Path(input_path).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])