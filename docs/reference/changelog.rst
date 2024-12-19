*********
Changelog
*********

2.2.1 (2024-12-19)
------------------

Bug fixes:

- Fix how extras and groups are parsed for the
  :ref:`uv plugin<craft_parts_uv_plugin>`.

2.2.0 (2024-12-16)
------------------

New features:

- Add a :ref:`uv plugin<craft_parts_uv_plugin>` for projects that use the `uv
  <https://docs.astral.sh/uv/>`_ build system.
- Add a :ref:`Go Use plugin<craft_parts_go_use_plugin>` for setting up a
  `workspace <https://go.dev/ref/mod#workspaces>`_ for Go modules.
- Add new ``poetry-export-extra-args`` and ``poetry-pip-extra-args`` keys
  to the :ref:`poetry plugin<craft_parts_poetry_plugin>`.
- Add an API for :ref:`registering custom source types
  <how_to_add_a_source_handler>`.
- Prefer ``craft.git`` as the binary to handle git sources, in environments
  where it's available.
- Set ``JAVA_HOME`` environment variable in Java-based plugins. The plugin will
  try to detect the latest available JDK.
- Add a ``part_has_slices`` function to determine if a part has slices in its
  ``stage-packages`` key.
- Add a ``part_has_chisel_as_build_snap`` function to determine if a part
  lists ``chisel`` as a ``build-snap``.
- Add ``chisel`` as a ``build-snap`` if any part has slices and ``chisel``
  isn't already listed as a ``build-snap``.
- Split stdout and stderr from ``subprocess`` calls for better presentation of
  build errors.

Bug fixes:

- Remove redundant ``Captured standard error:`` text from plugin build errors.
- Fix dependency validation for the ``rust`` plugin when a ``rust-deps`` part
  exists.

Documentation:

- Add labels to the :ref:`ant plugin<craft_parts_ant_plugin>` and
  :ref:`maven plugin<craft_parts_maven_plugin>` reference pages.
- Add a link to common part properties from the :ref:`npm
  plugin<craft_parts_npm_plugin>` reference page.

For a complete list of commits, check out the `2.2.0`_ release on GitHub.

2.1.4 (2024-12-04)
------------------

Bug fixes:

- Fix a regression where trying to use the poetry plugin without poetry
  installed on the system would give an error.

For a complete list of commits, check out the `2.1.4`_ release on GitHub.

2.1.3 (2024-11-20)
------------------

Bug fixes:

- Fix an issue where the ``poetry`` plugin would still try to install poetry
  from the package repositories when ``poetry-deps`` was declared as a
  dependency

Documentation:

- Add some missing references in the
  :doc:`Poetry plugin</common/craft-parts/reference/plugins/poetry_plugin>` and
  :doc:`Python plugin</common/craft-parts/reference/plugins/python_plugin>` pages.
- Fix a broken link in the :doc:`Tutorial examples</tutorials/examples>`.

For a complete list of commits, check out the `2.1.3`_ release on GitHub.

2.1.2 (2024-10-04)
------------------

- Replace the dependency on requests-unixsocket with requests-unixsocket2

Bug Fixes:

- Fixed an issue where the ``python`` plugin would fail to build if the part
  had no Python scripts.

Documentation:

- Update the :doc:`Rust
  plugin</common/craft-parts/reference/plugins/rust_plugin>` doc with recent
  changes to the Rust toolchain.

For a complete list of commits, check out the `2.1.2`_ release on GitHub.

2.1.1 (2024-09-13)
------------------

- This release brings the bug fix from ``1.33.1`` into the ``2.1.x`` series.

For a complete list of commits, check out the `2.1.1`_ release on GitHub.

1.33.1 (2024-09-13)
-------------------

- Fix NPM plugin to be stateless, allowing lifecycle steps to be
  executed in separate runs.

For a complete list of commits, check out the `1.33.1`_ release on GitHub.

2.1.0 (2024-09-09)
------------------

New features:

- Add a :doc:`Poetry plugin</common/craft-parts/reference/plugins/poetry_plugin>`
  for Python projects that use the `Poetry`_ build system.
- Add a new error message when getting a directory for a non-existent partition.

Bug fixes:

- Fix a regression where numeric part properties could not be parsed.
- Fix a bug where stage-packages tracking would fail when files were organized
  into a non-default partition.

For a complete list of commits, check out the `2.1.0`_ release on GitHub.

2.0.0 (2024-08-08)
------------------

Breaking changes:

- Set minimum Python version to 3.10
- Plugin models are restructured
- Migrate to Pydantic 2
- API uses Debian architecture names rather than Python platform names

New features:

- Plugin models can use Pydantic JSON schema export
- Partition names can include hyphens

Bug fixes:

- Xattrs raise FileNotFoundError when appropriate
- Partition names are more strictly checked.

For a complete list of commits, check out the `2.0.0`_ release on GitHub.

1.34.0 (2024-08-01)
-------------------
- Allow numbers in partitions, partition namespaces, and namespaced partitions.
- Add documentation for chisel and the overlay step
- Improve README onboarding

1.33.0 (2024-07-02)
-------------------

- Add doc slugs for errors during build, linking to plugin docs
- Add docs for partitions

1.32.0 (2024-06-24)
-------------------

- Add support for 7z sources
- Add reference documentation for the qmake plugin
- Improve logging output when fetching packages
- Improve errors for when sources cannot be fetched
- Fix a behavior where apt packages would be fetched when the user was
  not a superuser
- Fix list of ignored packages in core24 bases when fetching stage-packages

1.31.0 (2024-05-16)
-------------------

- Refactor npm plugin
  - npm-node-version option now accepts a NVM-style version identifier
  - Move Node.js download to pull commands
  - Verify SHA256 checksums after node.js download
  - Use new-style npm-install commands if npm version is newer than 8.x
  - Set NODE_ENV to production by default
- New and improved documentation
  - Add go plugin reference
  - Add nil plugin reference
  - Add make plugin reference
  - Add autotools plugin reference
  - Add cmake plugin reference
  - Add scons plugin reference
  - Add ant plugin reference
  - Add dotnet plugin reference
  - Add meson plugin reference
  - Documentation fixes

1.30.1 (2024-06-21)
-------------------

- Fix list of ignored packages in core24 bases when fetching stage-packages

1.30.0 (2024-05-16)
-------------------

- Add support for armv8l
- Add support for unregistering plugins

1.29.0 (2024-03-20)
-------------------

- Add maven plugin documentation
- Add documentation linters
- Rework bundling of shared docs

1.28.1 (2024-03-19)
-------------------

- Fix organize directories

1.28.0 (2024-03-13)
-------------------

- Add namespaced partitions support

1.27.0 (2024-03-07)
-------------------

- Add base layer data to ProjectInfo
- Add qmake plugin
- Add proxy support to ant plugin
- Use rustup snap in the Rust plugin
- Update documentation

1.26.2 (2024-02-07)
-------------------

- Fix default setting in aliased part fields
- Fix proxy setting in ant plugin

1.26.1 (2023-12-13)
-------------------

- Fix chisel slice normalization
- Address sphinx warnings

1.26.0 (2023-11-21)
-------------------

- Documentation updates
- Build system, requirements and CI updates
- Misc unit test fixes and updates

1.25.2 (2023-10-24)
-------------------

- Fix compiler plugin priming in Rust plugin
- Fix redundant channel override in Rust plugin
- Fix validation of part dependency names
- Fix expansion of environment variables

1.25.1 (2023-09-12)
-------------------

- Remove direct dependency to python-apt tarball

1.25.0 (2023-09-08)
-------------------

- Add rustup support to the Rust plugin
- Add the ability to specify ``no-default-features`` for the Rust plugin
- Add the ability to install virtual workspace crates for the Rust plugin
- Add the option to enable LTO for the Rust plugin

1.24.1 (2023-08-25)
-------------------

- Don't write log information in overlays (workaround for `craft-cli
  issue #172`_)

1.24.0 (2023-08-24)
-------------------

- Add support to partitions
- Add lifecycle prologue log messages
- Add build-on/for architecture environment variables
- Add bootstrap parameters to autotools plugin
- Documentation updates

1.23.1 (2023-08-15)
-------------------

- Only load project variables in adopting part

1.23.0 (2023-07-06)
-------------------

- Improve interpreter version detection in the Python plugin
- Fix and improve documentation
- Pin Pydantic to version 1.x

1.22.0 (2023-06-25)
-------------------

- Add helper to query overlay use
- Improve architecture mapping
- Forward unmatched snap source parameters
- Build system updates
- Documentation updates

1.21.1 (2023-06-09)
-------------------

- Revert subdir changes in pull and build steps

1.21.0 (2023-05-20)
-------------------

- Add callback to explicitly list base packages
- Add callback to configure overlay package layer

1.20.0 (2023-05-15)
-------------------

- Add initial support for dnf-based distros
- Add support for pyproject.toml projects in Python plugin
- Improve interpreter detection in Python plugin
- Fix subdir in pull and build steps
- Tox and packaging updates
- Documentation updates

1.19.8 (2024-09-24)
-------------------

- Replace requests-unixsocket with requests-unixsocket2
- Bump minimum Python version to 3.8 (required for requests-unixsocket2)

1.19.7 (2023-08-09)
-------------------

- Only load project variables in adopting part

1.19.6 (2023-06-09)
-------------------

- Revert subdir changes in pull and build steps

1.19.5 (2023-05-23)
-------------------

- Revert pyproject.toml change (breaks semantic versioning)

1.19.4 (2023-05-19)
-------------------

- Backport support for pyproject.toml projects from 1.20.0
- Backport pull and build steps subdir from 1.20.0

1.19.3 (2023-04-30)
-------------------

- Fix plugin properties state in planning phase

1.19.2 (2023-04-24)
-------------------

- Fix ignored files exclusion in local source

1.19.1 (2023-04-18)
-------------------

- Allow git+ssh in git source type
- Loosen pydantic dependency

1.19.0 (2023-03-20)
-------------------

- Initial support for offline plugins
- Initial support for yum and CentOS
- Introduce feature selection, make overlay support optional
- Check if plugin-specific properties are dirty when computing
  lifecycle actions
- Add source handler for rpm packages
- Ignore unreadable files in /etc/apt
- Documentation updates
- OsRelease code cleanup

1.18.4 (2023-03-09)
-------------------

- Make chroot /dev mount private

1.18.3 (2023-02-27)
-------------------

- Fix pip path in Python plugin

1.18.2 (2023-02-24)
-------------------

- Refactor Python plugin for subclassing

1.18.1 (2023-02-10)
-------------------

- Fix ignore patterns in local sources

1.18.0 (2023-01-19)
-------------------

- Add SCons plugin
- Add Ant plugin
- Add Maven plugin
- Fix lifecycle work directory cleaning
- Make stage package tracking optional
- Improve chisel error handling
- Improve missing local source error message
- Documentation fixes and updates

1.17.1 (2022-11-23)
-------------------

- Allow plus symbol in git url scheme

1.17.0 (2022-11-14)
-------------------

- Fix go plugin mod download in jammy
- Remove hardcoded ubuntu version in chisel call
- Add plain file source handler
- Pass build attributes and state to post-step callback

1.16.0 (2022-10-20)
-------------------

- Add file permission setting
- Take permissions into account when checking file collisions
- Only refresh overlay packages if necessary
- Generate separate environment setup file
- Make changed file list available to plugins

1.15.1 (2022-10-14)
-------------------

- Fix device nodes in overlay base image

1.15.0 (2022-10-11)
-------------------

- Add support to chisel slices
- Add ``go-generate`` property to the go plugin

1.14.2 (2022-09-22)
-------------------

- Fix pypi release package

1.14.1 (2022-09-21)
-------------------

- Fix stage/prime filter combination

1.14.0 (2022-09-09)
-------------------

- Add API call to validate parts

1.13.0 (2022-09-05)
-------------------

- Add go generate support to go plugin
- Add support for deb sources
- Add source download request timeout
- Remove unnecessary overlay whiteout files

1.12.1 (2022-08-19)
-------------------

- Revert changes to install prefix in cmake plugin to prevent
  stable base incompatibilities

1.12.0 (2022-08-12)
-------------------

- Set install prefix in the cmake plugin
- Fix prefix path in the cmake plugin

1.11.0 (2022-08-12)
-------------------

- Add API call to list registered plugins

1.10.2 (2022-08-03)
-------------------

- Fix git source format error when cloning using depth
- Use host architecture when installing stage packages

1.10.1 (2022-07-29)
-------------------

- Change staged snap pkgconfig prefix normalization to be predictable
  regardless of the path used for destructive mode packing

1.10.0 (2022-07-28)
-------------------

- Add plugin class method to check for out of source builds
- Normalize file copy functions signatures
- Fix pkgconfig prefix in staged snaps

1.9.0 (2022-07-14)
------------------

- Prevent wildcard symbol conflict in stage and prime filters
- Apt installer changed to collect installed package versions after the
  installation

1.8.1 (2022-07-05)
------------------

- Fix execution of empty scriptlets
- List primed stage packages only if deb stage packages are defined

1.8.0 (2022-06-30)
------------------

- Add list of primed stage packages to prime state
- Add lifecycle manager methods to obtain pull state assets and the list
  of primed stage packages

1.7.2 (2022-06-14)
------------------

- Fix git repository updates
- Fix stage packages removal on build update

1.7.1 (2022-05-21)
------------------

- Fix stdout leak during snap package installation
- Fix plugin validation dependencies

1.7.0 (2022-05-20)
------------------

- Add support for application-defined environment variables
- Add package filter for core22
- Refresh packages list before installing packages
- Expand global variables in parts definition
- Adjust prologue/epilogue callback parameters
- Make plugin options available in plugin environment validator
- Fix readthedocs documentation generation

1.6.1 (2022-05-02)
------------------

- Fix stage package symlink normalization

1.6.0 (2022-04-29)
------------------

- Add zip source handler
- Clean up source provisioning
- Fix project variable setting for skipped parts

1.5.1 (2022-04-25)
------------------

- Fix extra build snaps installation

1.5.0 (2022-04-25)
------------------

- Add rust plugin
- Add npm plugin
- Add project name argument to LifecycleManager and set ``CRAFT_PROJECT_NAME``
- Export symbols needed by application-defined plugins
- Refactor plugin environment validation

1.4.2 (2022-04-01)
------------------

- Fix craftctl error handling
- Fix long recursions in dirty step verification

1.4.1 (2022-03-30)
------------------

- Fix project variable adoption scope

1.4.0 (2022-03-24)
------------------

- Add cmake plugin
- Mount overlays using fuse-overlayfs
- Send execution output to user-specified streams
- Update craftctl commands
- Update step execution environment variables

1.3.0 (2022-03-05)
------------------

- Add meson plugin
- Adjustments in git source tests

1.2.0 (2022-03-01)
------------------

- Make git submodules fetching configurable
- Fix source type specification
- Fix testing in Python 3.10
- Address issues found by linters

1.1.2 (2022-02-07)
------------------

- Do not refresh already installed snaps
- Fix URL in setup.py
- Fix pydantic validation error handling
- Unpin pydantic and pydantic-yaml dependency versions
- Unpin pylint dependency version
- Remove unused requirements files

1.1.1 (2022-01-05)
------------------

- Pin pydantic and pydantic-yaml dependency versions

1.1.0 (2021-12-08)
------------------

- Add support to overlay step
- Use bash as step scriptlet interpreter
- Add plugin environment validation
- Add go plugin
- Add dotnet plugin

1.0.4 (2021-11-10)
------------------

- Declare additional public API names
- Add git source handler

1.0.3 (2021-10-19)
------------------

- Properly declare public API names
- Allow non-snap applications running on non-apt systems to invoke parts
  processing on build providers
- Use Bash as script interpreter instead of /bin/sh to stay compatible
  with Snapcraft V2 plugins

1.0.2 (2021-09-16)
------------------

- Fix local source updates causing removal of build artifacts and new
  files created in ``override-pull``

1.0.1 (2021-09-13)
------------------

- Fix plugin properties test
- Use local copy of mutable source handler ignore patterns
- Use host state for apt cache and remove stage package refresh
- Add information to parts error in CLI tool
- Change CLI tool ``--debug`` option to ``--trace`` to be consistent
  with craft tools


1.0.0 (2021-08-05)
------------------

- Initial release


.. _craft-cli issue #172: https://github.com/canonical/craft-cli/issues/172
.. _Poetry: https://python-poetry.org

.. _2.2.0: https://github.com/canonical/craft-parts/releases/tag/2.2.0
.. _2.1.4: https://github.com/canonical/craft-parts/releases/tag/2.1.4
.. _2.1.3: https://github.com/canonical/craft-parts/releases/tag/2.1.3
.. _2.1.2: https://github.com/canonical/craft-parts/releases/tag/2.1.2
.. _2.1.1: https://github.com/canonical/craft-parts/releases/tag/2.1.1
.. _1.33.1: https://github.com/canonical/craft-parts/releases/tag/1.33.1
.. _2.1.0: https://github.com/canonical/craft-parts/releases/tag/2.1.0
.. _2.0.0: https://github.com/canonical/craft-parts/releases/tag/2.0.0
