# Copyright 2023-2024 Canonical Ltd.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License version 3 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

import datetime
import logging
import pathlib
import re
import sys

project = "Craft Parts"
author = "Canonical Group Ltd"

copyright = "2023-%s, %s" % (datetime.date.today().year, author)

# region Configuration for canonical-sphinx
ogp_site_url = "https://canonical-craft-parts.readthedocs-hosted.com/"
ogp_site_name = project

html_context = {
    "product_page": "github.com/canonical/craft-parts",
    "github_url": "https://github.com/canonical/craft-parts",
}

extensions = [
    "canonical_sphinx",
    "pydantic_kitbash",
]
# endregion

extensions.extend(
    [
        "sphinx.ext.autodoc",
        "sphinx.ext.autosummary",
        "sphinx.ext.ifconfig",
        "sphinx.ext.napoleon",
        "sphinx.ext.viewcode",
        "sphinx_autodoc_typehints",  # must be loaded after napoleon
        "sphinx-pydantic",
        "sphinxcontrib.details.directive",
        "sphinxext.rediraffe",
    ]
)

# region Options for extensions

exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    "**venv",
    "base",
    "sphinx-resources",
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

# We have many links on sites that frequently respond with 503s to GitHub runners.
# https://www.sphinx-doc.org/en/master/usage/configuration.html#confval-linkcheck_retries
linkcheck_retries = 20
linkcheck_anchors_ignore = ["#", ":"]
linkcheck_ignore = [
    # Ignore releases, since we'll include the next release before it exists.
    r"^https://github.com/canonical/[a-z]*craft[a-z-]*/releases/.*",
    # Entire domains to ignore due to flakiness or issues
    r"^https://www.gnu.org/",
    r"^https://crates.io/",
    r"^https://([\w-]*\.)?npmjs.(org|com)",
    r"^https://rsync.samba.org",
    r"^https://ubuntu.com",
    # Known good links that if they break we'll hear it in the news.
    r"^https://([\w-]*\.)?apache.org\/?$",
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
    # Add project-specific ignores below
    re.escape(
        r"^https://github.com/canonical/craft-parts/blob/main/craft_parts/main.py$"
    ),
    re.escape(r"^https://github.com/opencontainers/image-spec/blob/main/layer.md$"),
]

rst_epilog = """
.. include:: /common/craft-parts/reuse/links.txt
"""

autodoc_mock_imports = ["apt"]

# Type annotations config
add_module_names = True

# sphinx_autodoc_typehints
set_type_checking_flag = True
typehints_fully_qualified = False
always_document_param_types = True
typehints_document_rtype = True

# Enable support for google-style instance attributes.
napoleon_use_ivar = True

# Github config
github_username = "canonical"
github_repository = "craft-parts"

rediraffe_redirects = "redirects.txt"

# endregion

# region Automated documentation

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


# endregion
