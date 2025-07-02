Changelog
=========

.. changelog template:

  .. _release-X.Y.Z:

  X.Y.Z (YYYY-MM-DD)
  ------------------

  New features:

  Bug fixes:

  Documentation:

  For a complete list of commits, check out the `X.Y.Z`_ release on GitHub.

.. _release-2.15.0:

2.15.0 (2025-07-02)
-------------------

New features:

- Make the error message more detailed and traceable when the maven-use plugin
  encounters invalid XML in the software's :file:`pom.xml` file.
- Add support for the ``parent`` tag on a :file:`pom.xml` file with the maven-use plugin.

Bug fixes:

- With the maven-use plugin, don't raise errors if dependency versions aren't specified
  in the software's :file:`pom.xml` file.
- With the maven-use plugin, don't create :file:`pom.xml` files with duplicate
  ``<distributionManagement>`` tags.
- Fix content migration when using :class:`~craft_parts.FilesystemMount` during the
  prime step. Instead of relying on the content of the overlay, gather the list of
  files and directories from the stage directory and the state of the stage
  migration.
  
For a complete list of commits, check out the `2.15.0`_ release on GitHub.

.. _release-2.14.0:

2.14.0 (2025-06-20)
-------------------

New features:

- Use the default :class:`~craft_parts.FilesystemMount` to distribute content
  between partitions when migrating content from the overlay.
- Track migrated content per partition in the default state file via a new
  ``partitions_contents`` field in :class:`~craft_parts.MigrationState`.
- Support source types that list snaps as requirements.

Bug fixes:

- Rely on the migrated content tracked per partition in state files to properly
  clean shared areas (stage and prime directories) in partitions. Also make sure
  to account for content coming from the overlay.

Documentation:

- Update the contribution guidelines and move them to ``CONTRIBUTING.md``.

2.14.0 includes changes from the 2.10.1 release.

For a complete list of commits, check out the `2.14.0`_ release on GitHub.

.. _release-2.10.1:

2.10.1 (2025-06-18)
-------------------

Documentation:

- Document the fields in the ``PartSpec`` and ``Permissions`` models.

For a complete list of commits, check out the `2.10.1`_ release on GitHub.

.. _release-2.13.0:

2.13.0 (2025-06-18)
-------------------

New features:

- Add the maven-use plugin.

Documentation:

- Expand the :ref:`uv plugin reference <craft_parts_uv_plugin>`
  to include more details on how to install uv.

For a complete list of commits, check out the `2.13.0`_ release on GitHub.

.. _release-2.12.0:

2.12.0 (2025-06-06)
-------------------

New features:

- Add a :class:`~craft_parts.FilesystemMount` model and a ``filesystem_mounts``
  parameter to the :doc:`/reference/lifecycle_manager`. A future release will use
  filesystem mounts to distribute content between partitions when migrating from the
  overlay step.

For a complete list of commits, check out the `2.12.0`_ release on GitHub.

.. _release-2.11.0:

2.11.0 (2025-06-04)
-------------------

New features:

- Add the :ref:`craft_parts_dotnet_v2_plugin`.
- The :ref:`craft_parts_go_use_plugin` uses the ``backstage`` directory.

Documentation:

- Move :ref:`how-to-use-parts` out of the common directory.

For a complete list of commits, check out the `2.11.0`_ release on GitHub.

.. _release-2.10.0:

2.10.0 (2025-05-06)
-------------------

Documentation:

- Revise the :doc:`craftctl how-to guide
  </common/craft-parts/how-to/customise-the-build-with-craftctl>` to better reflect how
  it can be used to override parts in apps.

For a complete list of commits, check out the `2.10.0`_ release on GitHub.

.. _release-2.4.4:

2.4.4 (2025-05-01)
------------------

Bug fixes:

- Fix the uv plugin breaking with uv 0.7

For a complete list of commits, check out the `2.4.4`_ release on GitHub.

.. _release-2.9.1:

2.9.1 (2025-05-01)
------------------

Bug fixes:

- Update the uv plugin to work with uv 0.7.0 and up.

For a complete list of commits, check out the `2.9.1`_ release on GitHub.

.. _release-2.9.0:

2.9.0 (2025-04-28)
------------------

New features:

- Add a :ref:`Gradle plugin <craft_parts_gradle_plugin>`.
- Add ``backstage`` and ``part/export`` directories for plugin use.

Documentation:

- Fix an issue where the documentation was hosting pages at URLs that contained the
  ``.html`` extension. This regression was causing links to the site to break.

For a complete list of commits, check out the `2.9.0`_ release on GitHub.

.. _release-2.8.0:

2.8.0 (2025-04-10)
-------------------

New features:

- With the new ``maven-use-wrapper`` key in the Maven plugin, you can enable
  your project's ``mvnw`` wrapper script.
- Add a :ref:`cargo-use plugin<craft_parts_cargo_use_plugin>` that creates
  a local Cargo registry for :ref:`rust plugin<craft_parts_rust_plugin>`.


.. _release-2.7.0:

2.7.0 (2025-03-18)
------------------

New features:

- Previously, ``source-commit`` could only accept full length (40 character)
  hashes. Now, ``source-commit`` can accept short hashes.
- Allow usage of the overlay and partitions features simultaneously.

Bug fixes:

- Fix the default behavior of the :ref:`jlink plugin <craft_parts_jlink_plugin>`
  only finding JAR files in the top-level directory. It now searches all
  subdirectories too.

.. note::

    2.7.0 includes changes from the 2.4.3 release.

.. _release-2.4.3:

2.4.3 (2025-03-11)
------------------

Bug fixes:

- Address race condition when collecting subprocess output.
- Update jinja2 dependency to address CVE-2025-27516

For a complete list of commits, check out the `2.4.3`_ release on GitHub.

.. _release-2.4.2:

2.4.2 (2025-03-04)
------------------

Bug fixes:

- Allow for a non-specific system Python interpreter when using the
  :ref:`uv plugin<craft_parts_uv_plugin>`.

For a complete list of commits, check out the `2.4.2`_ release on GitHub.

.. _release-2.6.2:

2.6.2 (2025-02-20)
------------------

Bug fixes:

- Fix handling and propagation of Python plugin error messages.

.. _release-2.6.1:

2.6.1 (2025-02-12)
------------------

Bug fixes:

- Fix CPATH variable scope in the :ref:`jlink plugin<craft_parts_jlink_plugin>`.
- Fix Jdeps parameter ordering in the
  :ref:`jlink plugin<craft_parts_jlink_plugin>`.

.. _release-2.3.1:

2.3.1 (2025-02-07)
------------------

Bug fixes:

- Allow for a non-specific system Python interpreter when using the
  :ref:`uv plugin<craft_parts_uv_plugin>`.

For a complete list of commits, check out the `2.3.1`_ release on GitHub.

.. _release-2.6.0:

2.6.0 (2025-02-06)
------------------

New features:

- Partition names can include slashes.

Bug fixes:

- Allow for a non-specific system Python interpreter when using the
  :ref:`uv plugin<craft_parts_uv_plugin>`.

.. _release-2.5.0:

2.5.0 (2025-01-30)
------------------

New features:

- Add the :ref:`jlink plugin<craft_parts_jlink_plugin>` for setting up
  Java runtime.

.. _release-2.4.1:

2.4.1 (2025-01-24)
------------------

Bug fixes:

- Preserve the ``pcfiledir`` tag in ``pkgconfig`` files.

Documentation:

- Reorganise and improve the :ref:`craft_parts_step_execution_environment`
  reference, including example values and documentation of additional
  environment variables.

.. _release-2.4.0:

2.4.0 (2025-01-23)
------------------

New features:

- Add new PartSpec property ``source-channel``.

Bug fixes:

- Correctly handle ``source-subdir`` values on the ``go-use`` plugin.

Documentation:

- Add missing links to GitHub releases.

For a complete list of commits, check out the `2.4.0`_ release on GitHub.

.. _release-2.3.0:

2.3.0 (2025-01-20)
------------------

New features:

- Change craftctl communication mechanism to unix sockets to consolidate
  the ctl server and output stream processing selector loops.
- Get the error output from step scriptlet execution and surface it when
  raising ScriptletRunError.

Bug fixes:

- Make sure the :ref:`uv plugin<craft_parts_uv_plugin>` is re-entrant on
  source changes.

Documentation:

- Correct the Maven plugin docstring to refer to Maven from Go.

For a complete list of commits, check out the `2.3.0`_ release on GitHub.

.. _release-2.2.2:

2.2.2 (2025-01-13)
------------------

Documentation:

- Add a cross-reference target for Poetry external links.

For a complete list of commits, check out the `2.2.2`_ release on GitHub.

.. _release-2.2.1:

2.2.1 (2024-12-19)
------------------

Bug fixes:

- Fix how extras and groups are parsed for the
  :ref:`uv plugin<craft_parts_uv_plugin>`.

For a complete list of commits, check out the `2.2.1`_ release on GitHub.

.. _release-2.2.0:

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

.. _release-2.1.4:

2.1.4 (2024-12-04)
------------------

Bug fixes:

- Fix a regression where trying to use the poetry plugin without poetry
  installed on the system would give an error.

For a complete list of commits, check out the `2.1.4`_ release on GitHub.

.. _release-2.1.3:

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

.. _release-2.1.2:

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

.. _release-1.25.3:

1.25.3 (2024-09-27)
-------------------

- Replace requests-unixsocket with requests-unixsocket2
- Bump minimum Python version to 3.8 (required for requests-unixsocket2)

For a complete list of commits, check out the `1.25.3`_ release on GitHub.

.. _release-2.1.1:

2.1.1 (2024-09-13)
------------------

- This release brings the bug fix from ``1.33.1`` into the ``2.1.x`` series.

For a complete list of commits, check out the `2.1.1`_ release on GitHub.

.. _release-1.33.1:

1.33.1 (2024-09-13)
-------------------

- Fix NPM plugin to be stateless, allowing lifecycle steps to be
  executed in separate runs.

For a complete list of commits, check out the `1.33.1`_ release on GitHub.

.. _release-2.1.0:

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

.. _release-2.0.0:

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

.. _release-1.34.0:

1.34.0 (2024-08-01)
-------------------
- Allow numbers in partitions, partition namespaces, and namespaced partitions.
- Add documentation for chisel and the overlay step
- Improve README onboarding

.. _release-1.33.0:

1.33.0 (2024-07-02)
-------------------

- Add doc slugs for errors during build, linking to plugin docs
- Add docs for partitions

.. _release-1.32.0:

1.32.0 (2024-06-24)
-------------------

- Add support for 7z sources
- Add reference documentation for the qmake plugin
- Improve logging output when fetching packages
- Improve errors for when sources cannot be fetched
- Fix a behavior where apt packages would be fetched when the user was
  not a superuser
- Fix list of ignored packages in core24 bases when fetching stage-packages

.. _release-1.31.0:

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

.. _release-1.30.1:

1.30.1 (2024-06-21)
-------------------

- Fix list of ignored packages in core24 bases when fetching stage-packages

.. _release-1.30.0:

1.30.0 (2024-05-16)
-------------------

- Add support for armv8l
- Add support for unregistering plugins

.. _release-1.29.0:

1.29.0 (2024-03-20)
-------------------

- Add maven plugin documentation
- Add documentation linters
- Rework bundling of shared docs

.. _release-1.28.1:

1.28.1 (2024-03-19)
-------------------

- Fix organize directories

.. _release-1.28.0:

1.28.0 (2024-03-13)
-------------------

- Add namespaced partitions support

.. _release-1.27.0:

1.27.0 (2024-03-07)
-------------------

- Add base layer data to ProjectInfo
- Add qmake plugin
- Add proxy support to ant plugin
- Use rustup snap in the Rust plugin
- Update documentation

.. _release-1.26.2:

1.26.2 (2024-02-07)
-------------------

- Fix default setting in aliased part fields
- Fix proxy setting in ant plugin

.. _release-1.26.1:

1.26.1 (2023-12-13)
-------------------

- Fix chisel slice normalization
- Address sphinx warnings

.. _release-1.26.0:

1.26.0 (2023-11-21)
-------------------

- Documentation updates
- Build system, requirements and CI updates
- Misc unit test fixes and updates

.. _release-1.25.2:

1.25.2 (2023-10-24)
-------------------

- Fix compiler plugin priming in Rust plugin
- Fix redundant channel override in Rust plugin
- Fix validation of part dependency names
- Fix expansion of environment variables

.. _release-1.25.1:

1.25.1 (2023-09-12)
-------------------

- Remove direct dependency to python-apt tarball

.. _release-1.25.0:

1.25.0 (2023-09-08)
-------------------

- Add rustup support to the Rust plugin
- Add the ability to specify ``no-default-features`` for the Rust plugin
- Add the ability to install virtual workspace crates for the Rust plugin
- Add the option to enable LTO for the Rust plugin

.. _release-1.24.1:

1.24.1 (2023-08-25)
-------------------

- Don't write log information in overlays (workaround for `craft-cli
  issue #172`_)

.. _release-1.24.0:

1.24.0 (2023-08-24)
-------------------

- Add support to partitions
- Add lifecycle prologue log messages
- Add build-on/for architecture environment variables
- Add bootstrap parameters to autotools plugin
- Documentation updates

.. _release-1.23.1:

1.23.1 (2023-08-15)
-------------------

- Only load project variables in adopting part

.. _release-1.23.0:

1.23.0 (2023-07-06)
-------------------

- Improve interpreter version detection in the Python plugin
- Fix and improve documentation
- Pin Pydantic to version 1.x

.. _release-1.22.0:

1.22.0 (2023-06-25)
-------------------

- Add helper to query overlay use
- Improve architecture mapping
- Forward unmatched snap source parameters
- Build system updates
- Documentation updates

.. _release-1.21.1:

1.21.1 (2023-06-09)
-------------------

- Revert subdir changes in pull and build steps

.. _release-1.21.0:

1.21.0 (2023-05-20)
-------------------

- Add callback to explicitly list base packages
- Add callback to configure overlay package layer

.. _release-1.20.0:

1.20.0 (2023-05-15)
-------------------

- Add initial support for dnf-based distros
- Add support for pyproject.toml projects in Python plugin
- Improve interpreter detection in Python plugin
- Fix subdir in pull and build steps
- Tox and packaging updates
- Documentation updates

.. _release-1.19.8:

1.19.8 (2024-09-24)
-------------------

- Replace requests-unixsocket with requests-unixsocket2
- Bump minimum Python version to 3.8 (required for requests-unixsocket2)

.. _release-1.19.7:

1.19.7 (2023-08-09)
-------------------

- Only load project variables in adopting part

.. _release-1.19.6:

1.19.6 (2023-06-09)
-------------------

- Revert subdir changes in pull and build steps

.. _release-1.19.5:

1.19.5 (2023-05-23)
-------------------

- Revert pyproject.toml change (breaks semantic versioning)

.. _release-1.19.4:

1.19.4 (2023-05-19)
-------------------

- Backport support for pyproject.toml projects from 1.20.0
- Backport pull and build steps subdir from 1.20.0

.. _release-1.19.3:

1.19.3 (2023-04-30)
-------------------

- Fix plugin properties state in planning phase

.. _release-1.19.2:

1.19.2 (2023-04-24)
-------------------

- Fix ignored files exclusion in local source

.. _release-1.19.1:

1.19.1 (2023-04-18)
-------------------

- Allow git+ssh in git source type
- Loosen pydantic dependency

.. _release-1.19.0:

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

.. _release-1.18.4:

1.18.4 (2023-03-09)
-------------------

- Make chroot /dev mount private

.. _release-1.18.3:

1.18.3 (2023-02-27)
-------------------

- Fix pip path in Python plugin

.. _release-1.18.2:

1.18.2 (2023-02-24)
-------------------

- Refactor Python plugin for subclassing

.. _release-1.18.1:

1.18.1 (2023-02-10)
-------------------

- Fix ignore patterns in local sources

.. _release-1.18.0:

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

.. _release-1.17.1:

1.17.1 (2022-11-23)
-------------------

- Allow plus symbol in git url scheme

.. _release-1.17.0:

1.17.0 (2022-11-14)
-------------------

- Fix go plugin mod download in jammy
- Remove hardcoded ubuntu version in chisel call
- Add plain file source handler
- Pass build attributes and state to post-step callback

.. _release-1.16.0:

1.16.0 (2022-10-20)
-------------------

- Add file permission setting
- Take permissions into account when checking file collisions
- Only refresh overlay packages if necessary
- Generate separate environment setup file
- Make changed file list available to plugins

.. _release-1.15.1:

1.15.1 (2022-10-14)
-------------------

- Fix device nodes in overlay base image

.. _release-1.15.0:

1.15.0 (2022-10-11)
-------------------

- Add support to chisel slices
- Add ``go-generate`` property to the go plugin

.. _release-1.14.2:

1.14.2 (2022-09-22)
-------------------

- Fix pypi release package

.. _release-1.14.1:

1.14.1 (2022-09-21)
-------------------

- Fix stage/prime filter combination

.. _release-1.14.0:

1.14.0 (2022-09-09)
-------------------

- Add API call to validate parts

.. _release-1.13.0:

1.13.0 (2022-09-05)
-------------------

- Add go generate support to go plugin
- Add support for deb sources
- Add source download request timeout
- Remove unnecessary overlay whiteout files

.. _release-1.12.1:

1.12.1 (2022-08-19)
-------------------

- Revert changes to install prefix in cmake plugin to prevent
  stable base incompatibilities

.. _release-1.12.0:

1.12.0 (2022-08-12)
-------------------

- Set install prefix in the cmake plugin
- Fix prefix path in the cmake plugin

.. _release-1.11.0:

1.11.0 (2022-08-12)
-------------------

- Add API call to list registered plugins

.. _release-1.10.2:

1.10.2 (2022-08-03)
-------------------

- Fix git source format error when cloning using depth
- Use host architecture when installing stage packages

.. _release-1.10.1:

1.10.1 (2022-07-29)
-------------------

- Change staged snap pkgconfig prefix normalization to be predictable
  regardless of the path used for destructive mode packing

.. _release-1.10.0:

1.10.0 (2022-07-28)
-------------------

- Add plugin class method to check for out of source builds
- Normalize file copy functions signatures
- Fix pkgconfig prefix in staged snaps

.. _release-1.9.0:

1.9.0 (2022-07-14)
------------------

- Prevent wildcard symbol conflict in stage and prime filters
- Apt installer changed to collect installed package versions after the
  installation

.. _release-1.8.1:

1.8.1 (2022-07-05)
------------------

- Fix execution of empty scriptlets
- List primed stage packages only if deb stage packages are defined

.. _release-1.8.0:

1.8.0 (2022-06-30)
------------------

- Add list of primed stage packages to prime state
- Add lifecycle manager methods to obtain pull state assets and the list
  of primed stage packages

.. _release-1.7.2:

1.7.2 (2022-06-14)
------------------

- Fix git repository updates
- Fix stage packages removal on build update

.. _release-1.7.1:

1.7.1 (2022-05-21)
------------------

- Fix stdout leak during snap package installation
- Fix plugin validation dependencies

.. _release-1.7.0:

1.7.0 (2022-05-20)
------------------

- Add support for application-defined environment variables
- Add package filter for core22
- Refresh packages list before installing packages
- Expand global variables in parts definition
- Adjust prologue/epilogue callback parameters
- Make plugin options available in plugin environment validator
- Fix readthedocs documentation generation

.. _release-1.6.1:

1.6.1 (2022-05-02)
------------------

- Fix stage package symlink normalization

.. _release-1.6.0:

1.6.0 (2022-04-29)
------------------

- Add zip source handler
- Clean up source provisioning
- Fix project variable setting for skipped parts

.. _release-1.5.1:

1.5.1 (2022-04-25)
------------------

- Fix extra build snaps installation

.. _release-1.5.0:

1.5.0 (2022-04-25)
------------------

- Add rust plugin
- Add npm plugin
- Add project name argument to LifecycleManager and set ``CRAFT_PROJECT_NAME``
- Export symbols needed by application-defined plugins
- Refactor plugin environment validation

.. _release-1.4.2:

1.4.2 (2022-04-01)
------------------

- Fix craftctl error handling
- Fix long recursions in dirty step verification

.. _release-1.4.1:

1.4.1 (2022-03-30)
------------------

- Fix project variable adoption scope

.. _release-1.4.0:

1.4.0 (2022-03-24)
------------------

- Add cmake plugin
- Mount overlays using fuse-overlayfs
- Send execution output to user-specified streams
- Update craftctl commands
- Update step execution environment variables

.. _release-1.3.0:

1.3.0 (2022-03-05)
------------------

- Add meson plugin
- Adjustments in git source tests

.. _release-1.2.0:

1.2.0 (2022-03-01)
------------------

- Make git submodules fetching configurable
- Fix source type specification
- Fix testing in Python 3.10
- Address issues found by linters

.. _release-1.1.2:

1.1.2 (2022-02-07)
------------------

- Do not refresh already installed snaps
- Fix URL in setup.py
- Fix pydantic validation error handling
- Unpin pydantic and pydantic-yaml dependency versions
- Unpin pylint dependency version
- Remove unused requirements files

.. _release-1.1.1:

1.1.1 (2022-01-05)
------------------

- Pin pydantic and pydantic-yaml dependency versions

.. _release-1.1.0:

1.1.0 (2021-12-08)
------------------

- Add support to overlay step
- Use bash as step scriptlet interpreter
- Add plugin environment validation
- Add go plugin
- Add dotnet plugin

.. _release-1.0.4:

1.0.4 (2021-11-10)
------------------

- Declare additional public API names
- Add git source handler

.. _release-1.0.3:

1.0.3 (2021-10-19)
------------------

- Properly declare public API names
- Allow non-snap applications running on non-apt systems to invoke parts
  processing on build providers
- Use Bash as script interpreter instead of /bin/sh to stay compatible
  with Snapcraft V2 plugins

.. _release-1.0.2:

1.0.2 (2021-09-16)
------------------

- Fix local source updates causing removal of build artifacts and new
  files created in ``override-pull``

.. _release-1.0.1:

1.0.1 (2021-09-13)
------------------

- Fix plugin properties test
- Use local copy of mutable source handler ignore patterns
- Use host state for apt cache and remove stage package refresh
- Add information to parts error in CLI tool
- Change CLI tool ``--debug`` option to ``--trace`` to be consistent
  with craft tools


.. _release-1.0.0:

1.0.0 (2021-08-05)
------------------

- Initial release


.. _craft-cli issue #172: https://github.com/canonical/craft-cli/issues/172
.. _Poetry: https://python-poetry.org

.. _2.15.0: https://github.com/canonical/craft-parts/releases/tag/2.15.0
.. _2.14.0: https://github.com/canonical/craft-parts/releases/tag/2.14.0
.. _2.13.0: https://github.com/canonical/craft-parts/releases/tag/2.13.0
.. _2.12.0: https://github.com/canonical/craft-parts/releases/tag/2.12.0
.. _2.11.0: https://github.com/canonical/craft-parts/releases/tag/2.11.0
.. _2.10.1: https://github.com/canonical/craft-parts/releases/tag/2.10.1
.. _2.10.0: https://github.com/canonical/craft-parts/releases/tag/2.10.0
.. _2.9.1: https://github.com/canonical/craft-parts/releases/tag/2.9.1
.. _2.9.0: https://github.com/canonical/craft-parts/releases/tag/2.9.0
.. _2.4.4: https://github.com/canonical/craft-parts/releases/tag/2.4.4
.. _2.4.3: https://github.com/canonical/craft-parts/releases/tag/2.4.3
.. _2.4.2: https://github.com/canonical/craft-parts/releases/tag/2.4.2
.. _2.4.0: https://github.com/canonical/craft-parts/releases/tag/2.4.0
.. _2.3.1: https://github.com/canonical/craft-parts/releases/tag/2.3.1
.. _2.3.0: https://github.com/canonical/craft-parts/releases/tag/2.3.0
.. _2.2.2: https://github.com/canonical/craft-parts/releases/tag/2.2.2
.. _2.2.1: https://github.com/canonical/craft-parts/releases/tag/2.2.1
.. _2.2.0: https://github.com/canonical/craft-parts/releases/tag/2.2.0
.. _2.1.4: https://github.com/canonical/craft-parts/releases/tag/2.1.4
.. _2.1.3: https://github.com/canonical/craft-parts/releases/tag/2.1.3
.. _2.1.2: https://github.com/canonical/craft-parts/releases/tag/2.1.2
.. _2.1.1: https://github.com/canonical/craft-parts/releases/tag/2.1.1
.. _1.25.3: https://github.com/canonical/craft-parts/releases/tag/1.25.3
.. _1.33.1: https://github.com/canonical/craft-parts/releases/tag/1.33.1
.. _2.1.0: https://github.com/canonical/craft-parts/releases/tag/2.1.0
.. _2.0.0: https://github.com/canonical/craft-parts/releases/tag/2.0.0
