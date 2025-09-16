#!/usr/bin/env python3
"""
Setup script for FSS Parse PDF - Professional PDF manipulation toolkit
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding='utf-8') if readme_path.exists() else ""

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    requirements = requirements_path.read_text(encoding='utf-8').strip().split('\n')
    requirements = [req.strip() for req in requirements if req.strip() and not req.startswith('#')]

setup(
    name="fss-parse-pdf",
    version="1.0.0",
    description="Professional PDF manipulation toolkit for CLI agents and automated workflows",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="FSS Coding Team",
    author_email="development@fsscoding.com",
    url="https://github.com/FSSCoding/fss-parse-pdf",
    
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    
    entry_points={
        'console_scripts': [
            'fss-parse-pdf=pdf_engine:main',
        ],
    },
    
    install_requires=requirements,
    
    extras_require={
        'dev': [
            'pytest>=6.0',
            'pytest-cov>=2.0',
            'black>=21.0',
            'flake8>=3.9',
            'mypy>=0.900',
        ],
        'docs': [
            'sphinx>=4.0',
            'sphinx-rtd-theme>=0.5',
        ],
        'ocr': [
            'pytesseract>=0.3.9',
            'Pillow>=8.0.0',
        ],
    },
    
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Office/Business",
        "Topic :: Text Processing",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
    ],
    
    python_requires=">=3.8",
    
    keywords="pdf parser extraction manipulation cli agent automation",
    
    project_urls={
        "Bug Reports": "https://github.com/FSSCoding/fss-parse-pdf/issues",
        "Source": "https://github.com/FSSCoding/fss-parse-pdf",
        "Documentation": "https://github.com/FSSCoding/fss-parse-pdf/blob/main/README.md",
    },
    
    include_package_data=True,
    zip_safe=False,
)