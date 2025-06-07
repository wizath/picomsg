#!/usr/bin/env python3

from setuptools import setup, find_packages
import os

# Read version from version file
version_file = os.path.join(os.path.dirname(__file__), 'picomsg', '__version__.py')
version_dict = {}
with open(version_file) as f:
    exec(f.read(), version_dict)

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="picomsg",
    version=version_dict['__version__'],
    author="PicoMsg Team",
    author_email="team@picomsg.dev",
    description="Lightweight binary serialization format for embedded and performance-critical applications",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/picomsg/picomsg",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Networking",
        "Topic :: Software Development :: Code Generators",
    ],
    python_requires=">=3.8",
    install_requires=[
        "lark>=1.1.0",
        "click>=8.0.0",
        "jinja2>=3.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
        ],
        "test": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "hypothesis>=6.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "picomsg=picomsg.cli:main",
        ],
    },
) 
