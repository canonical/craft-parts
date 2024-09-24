*********
Changelog
*********

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
