"""Sphinx configuration for Agentic RAG documentation."""

import sys
from datetime import datetime
from pathlib import Path

# Add source directory to path for autodoc
sys.path.insert(0, str(Path("../src").resolve()))

# Project information
project = "Agentic RAG System"
copyright = f"{datetime.now().year}, Luminari AI"
author = "Luminari AI Team"
version = "0.8.0"
release = "0.8.0"

# General configuration
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.coverage",
    "sphinx.ext.githubpages",
    "sphinx_rtd_theme",
    "sphinx.ext.autosummary",
    "sphinx.ext.duration",
    "sphinx.ext.doctest",
    "myst_parser",
    "sphinx_copybutton",
]

# Add support for Markdown files
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# Master document
master_doc = "index"

# Templates path
templates_path = ["_templates"]

# Exclude patterns
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# HTML theme configuration
html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "navigation_depth": 4,
    "collapse_navigation": False,
    "sticky_navigation": True,
    "includehidden": True,
    "titles_only": False,
    "logo_only": False,
    "display_version": True,
    "prev_next_buttons_location": "bottom",
    "style_external_links": True,
}

# Static files
html_static_path = ["_static"]

# Logo and favicon
# html_logo = "_static/logo.png"
# html_favicon = "_static/favicon.ico"

# Output file base name
htmlhelp_basename = "AgenticRAGDoc"

# LaTeX configuration
latex_elements = {
    "papersize": "letterpaper",
    "pointsize": "10pt",
    "preamble": "",
    "fncychap": "\\usepackage[Bjornstrup]{fncychap}",
}

latex_documents = [
    (
        master_doc,
        "AgenticRAG.tex",
        "Agentic RAG System Documentation",
        "Luminari AI Team",
        "manual",
    ),
]

# Napoleon settings for Google and NumPy style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_type_aliases = None

# Autodoc settings
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
}

# Intersphinx mapping to other documentations
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable", None),
    "pandas": ("https://pandas.pydata.org/docs", None),
    "pydantic": ("https://docs.pydantic.dev", None),
    "fastapi": ("https://fastapi.tiangolo.com", None),
}

# Todo extension settings
todo_include_todos = True

# Copy button for code blocks
copybutton_prompt_text = r">>> |\.\.\. |\$ |In \[\d*\]: | {2,5}\.\.\.: | {5,8}: "
copybutton_prompt_is_regexp = True

# MyST parser configuration
myst_enable_extensions = [
    "dollarmath",
    "amsmath",
    "deflist",
    "fieldlist",
    "html_admonition",
    "html_image",
    "colon_fence",
    "smartquotes",
    "replacements",
    "linkify",
    "strikethrough",
    "substitution",
    "tasklist",
    "attrs_inline",
]

myst_heading_anchors = 3
