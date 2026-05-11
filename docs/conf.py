import datetime
import logging
import os
import pathlib
import re
import sys

# Configuration for the Sphinx documentation builder.
# All configuration specific to your project should be done in this file.
#
# A complete list of built-in Sphinx configuration values:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
#
# Our starter pack uses the custom Canonical Sphinx extension
# to keep all documentation based on it consistent and on brand:
# https://github.com/canonical/canonical-sphinx

#######################
# Project information #
#######################

# Project name
project = "Craft Parts"
author = "Canonical Ltd."

# Sidebar documentation title; best kept reasonably short
html_title = f"{project} documentation"

# Copyright string; shown at the bottom of the page
copyright = f"2023-{datetime.date.today().year}, {author}"

# Documentation website URL
ogp_site_url = "https://canonical-craft-parts.readthedocs-hosted.com/"

# Preview name of the documentation website
ogp_site_name = project

# Preview image URL
#
# TODO: To customise the preview image, update as needed.
ogp_image = "https://assets.ubuntu.com/v1/cc828679-docs_illustration.svg"

# Product favicon; shown in bookmarks, browser tabs, etc.
# html_favicon = ".sphinx/_static/favicon.png"

# Dictionary of values to pass into the Sphinx context for all pages:
# https://www.sphinx-doc.org/en/master/usage/configuration.html#confval-html_context
html_context = {
    # Product page URL; can be different from product docs URL
    "product_page": "github.com/canonical/craft-parts",
    # Product tag image; the orange part of your logo, shown in the page header
    # "product_tag": "_static/tag.png",
    "discourse": "",
    # Your Mattermost channel URL
    "mattermost": "https://chat.canonical.com/canonical/channels/documentation",
    # Your Matrix channel URL
    "matrix": "https://matrix.to/#/#starcraft-development:ubuntu.com",
    # Your documentation GitHub repository URL
    "github_url": "https://github.com/canonical/craft-parts",
    # Docs branch in the repo; used in links for viewing the source files
    "repo_default_branch": "main",
    # Docs location in the repo; used in links for viewing the source files
    "repo_folder": "/docs/",
    # List contributors on individual pages
    "display_contributors": False,
    # Required for feedback button
    "github_issues": "enabled",
}

#html_extra_path = []

# Enable the edit button on pages
html_theme_options = {
    "source_edit_link": "https://github.com/canonical/craft-parts",
}

# Project slug; see https://meta.discourse.org/t/what-is-category-slug/87897
# slug = ""


#########################
# Sitemap configuration #
#########################

# Use RTD canonical URL to ensure duplicate pages have a specific canonical URL
html_baseurl = os.environ.get("READTHEDOCS_CANONICAL_URL", "/")

# sphinx-sitemap uses html_baseurl to generate the full URL for each page:
sitemap_url_scheme = "{link}"

# Include `lastmod` dates in the sitemap:
# sitemap_show_lastmod = True

# Exclude generated pages from the sitemap:
sitemap_excludes = [
    "404/",
    "genindex/",
    "search/",
]


################################
# Template and asset locations #
################################

html_static_path = ["_static"]
templates_path = ["_templates"]


#############
# Redirects #
#############

rediraffe_redirects = "redirects.txt"


###########################
# Link checker exceptions #
###########################

# Whole sites and individual URLs to ignore
linkcheck_ignore = [
    # Entire domains to ignore due to flakiness or issues
    r"^https://github.com",
    r"^https://www.gnu.org/",
    r"^https://crates.io/",
    r"^https://([\w-]*\.)?npmjs.(org|com)",
    r"^https://rsync.samba.org",
    r"^https://ubuntu.com",
    r"^https://matrix.to/#",
    r"^https://gitlab.gnome.org",
    # Known good links that if they break we'll hear it in the news.
    r"^https://([\w-]*\.)?apache.org/?$",
    r"^https://canonical.com/legal/contributors$",
    r"^https://([\w-]*\.)?cmake.org/?$",
    r"^https://([\w-]*\.)?curl.se/?$",
    r"^https://dnf.readthedocs.io/?$",
    r"^https://dotnet.microsoft.com/?$",
    r"^https://([\w-]*\.)?git-scm.com/?$",
    r"^https://go.dev/?$",
    r"^https://([\w-]*\.)?mesonbuild.com/?$",
    r"^https://([\w-]*\.)?ninja-build.org/?$",
    r"^https://pip.pypa.(com|io)/?$",
    r"^https://([\w-]*\.)?pydantic.dev/?$",
    r"^https://([\w-]*\.)?python-poetry.org/?$",
    r"^https://([\w-]*\.)?rust-lang.org(/(stable/?)?)?$",
    r"^https://([\w-]*\.)?rustup.rs/?$",
    r"^https://([\w-]*\.)?scons.org/?$",
    r"^https://([\w-]*\.)?semver.org/?$",
    r"^https://([\w-]*\.)?yum.baseurl.org/?$",
    # Fake link
    r"^https://foo.org/?$",
]

# Anchor strings to ignore
linkcheck_anchors_ignore = [
    "#",
    ":",
]

# Give linkcheck multiple tries on failure
linkcheck_retries = 20


########################
# Configuration extras #
########################

# Custom Sphinx extensions; see
# https://www.sphinx-doc.org/en/master/usage/extensions/index.html
# NOTE: The canonical_sphinx extension is required for the starter pack.
extensions = [
    "canonical_sphinx",
    "notfound.extension",
    "sphinx_design",
    # "sphinx_tabs.tabs",
    # "sphinxcontrib.jquery"
    "sphinxext.opengraph",
    # "sphinx_config_options",
    # "sphinx_contributor_listing",
    # "sphinx_filtered_toctree",
    "sphinx_related_links",
    "sphinx_roles",
    "sphinx_terminal",
    # "sphinx_ubuntu_images",
    # "sphinx_youtube_links",
    # "sphinxcontrib.cairosvgconverter",
    # "sphinx_last_updated_by_git",
    "sphinx.ext.intersphinx",
    "sphinx_sitemap",
    # Custom Craft extensions
    "pydantic_kitbash",
    "sphinxext.rediraffe",
    "sphinx.ext.autodoc",
    "sphinx_autodoc_typehints",
    "sphinx.ext.doctest",
    "sphinx.ext.ifconfig",
    "sphinx.ext.viewcode",
    "sphinx_substitution_extensions",
]

# Excludes files or directories from processing
exclude_patterns = [
    "README.md",  # Docs README
    "_build",
    "Thumbs.db",
    ".DS_Store",
    "**venv",
    "base",
    "reuse",
    "sphinx-docs-starter-pack",
    "common/README.md",
    # These RST files are explicitly excluded here because they are included by
    # other files - without this exclusion, Sphinx will complain about duplicate
    # labels.
    "common/craft-parts/explanation/overlay_parameters.rst",
    "common/craft-parts/explanation/how_parts_are_built.rst",
    "common/craft-parts/reference/parts_steps.rst",
    "common/craft-parts/reference/step_execution_environment.rst",
    "common/craft-parts/reference/step_output_directories.rst",
]

# Adds custom CSS files, located under html_static_path
html_css_files = [
    "css/cookie-banner.css",
]

# Adds custom JavaScript files, located under html_static_path
html_js_files = [
    "js/bundle.js",
]

# Specifies a reST snippet to be appended to each .rst file
rst_epilog = """
.. include:: /common/craft-parts/reuse/links.txt
"""

# Feedback button at the top; enabled by default
# disable_feedback_button = True

# Your manpage URL
# manpages_url = "https://manpages.ubuntu.com/manpages/{codename}/en/" + \
#     "man{section}/{page}.{section}.html"

# Specifies a reST snippet to be prepended to each .rst file
# This defines a :center: role that centers table cell content.
# This defines a :h2: role that styles content for use with PDF generation.
rst_prolog = """
.. role:: center
   :class: align-center
.. role:: h2
    :class: hclass2
.. role:: woke-ignore
    :class: woke-ignore
.. role:: vale-ignore
    :class: vale-ignore
"""

# Workaround for https://github.com/canonical/canonical-sphinx/issues/34
if "discourse_prefix" not in html_context and "discourse" in html_context:
    html_context["discourse_prefix"] = f"{html_context['discourse']}/t/"

# Add configuration for intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "starflow": ("https://canonical-starflow.readthedocs-hosted.com", None),
    "starter-pack": (
        "https://canonical-example-product-documentation.readthedocs-hosted.com/en/latest",
        None,
    ),
    "sphinxcontrib-mermaid": (
        "https://sphinxcontrib-mermaid-demo.readthedocs.io/en/latest",
        None,
    ),
}

# Block Intersphinx from looking up external sources with internal references. In other
# words, only :external+<project>... will search in other projects.
intersphinx_disabled_reftypes = ["std:*"]

##############################
# Custom Craft configuration #
##############################

# Type hints configuration
set_type_checking_flag = True
typehints_fully_qualified = False
always_document_param_types = True

# Automated documentation
project_dir = pathlib.Path(__file__).parents[1].resolve()
sys.path.insert(0, str(project_dir.absolute()))


def run_apidoc(_):
    import os
    import sys

    from sphinx.ext.apidoc import main

    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    cur_dir = os.path.abspath(os.path.dirname(__file__))
    # Add the apidoc-generated rst files inside of "reference/gen", to avoid
    # cluttering the "main" docs dirs.
    output_dir = os.path.join(cur_dir, "reference/gen")
    module = os.path.join(cur_dir, "..", "craft_parts")
    main(["-e", "-o", output_dir, module, "--no-toc", "--force"])


def filter_errordict_warnings(log_record: logging.LogRecord):
    """A filter that drops warnings related to Pydantic.ErrorDict."""
    return "name 'ErrorDict'" not in log_record.getMessage()


def setup(app):
    app.connect("builder-inited", run_apidoc)

    logger = logging.getLogger("sphinx.sphinx_autodoc_typehints")
    logger.addFilter(filter_errordict_warnings)
