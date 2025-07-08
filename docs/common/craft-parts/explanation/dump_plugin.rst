.. _dump_plugin_explanation:

Dump Plugin
===========

The dump plugin is a simple plugin that by default is equivalent to running the
following command from the source directory:

.. code-block:: bash

    cp --archive --link --no-dereference . "${CRAFT_PART_INSTALL}"

The ``source`` key is the essential to this plugin. With some additional properties,
it defines the location where to get the files from, or which branch, tag, and/or
commit to clone if it is a repository.

If you are not using the source files directly in the final payload, but want to run
some custom commands to generate them, then you should use the ``nil`` plugin instead to
avoid copying any unnecessary files.

Combining the dump plugin with part keys allows extending the behavior to create new
files, modify existing files, and/or filter files for the final payload. For example, it
could be used with the ``override-build`` key to convert file formats.

The plugin can also be used with the ``organize`` key to remap the files in the final
payload. Like keep only libraries and exclude the binaries and headers from SDKs.
