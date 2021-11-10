*********
Changelog
*********

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
