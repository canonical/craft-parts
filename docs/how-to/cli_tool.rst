***************************************
Using craft-parts from the command line
***************************************

The CLI tool
============

Parts processing can be also executed directly from the command line
by invoking the module's main entry point. This can be useful for
debugging, or to experiment different configuration options::

  $ python3 -mcraft_parts pull
  Execute: Pull foo
  $ python3 -mcraft_parts --dry-run --show-skipped
  Skip pull foo (already ran)
  Build foo
  Stage foo
  Prime foo

By default, parts will be read from a file called ``parts.yaml``. Run
the tool with ``--help`` for a list of valid arguments.
