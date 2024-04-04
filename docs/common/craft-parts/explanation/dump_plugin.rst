.. _dump_plugin_explanation:

Dump Plugin
===========

The dump plugin is a simple plugin that by default is equivalent to running the
following command from the source directory:

.. code-block:: shell
    
    cp --archive --link --no-dereference . "${CRAFT_PART_INSTALL}"


The :ref:`source <source>` property is the key to this plugin. With some
additional properties, they define the location where to get the files from, or
which branch, tag, and/or commit to clone if it is a repository.


If you are not using the source files directly in the final payload, but want to
run some custom commands to generate them, then you should use the ``nil``
plugin instead to avoid copying any unnecessary files.


Combining the dump plugin with the :ref:`part properties <part_properties>`
allows extending the behavior to create new files, modify existing files,
and/or filter files for the final payload. For example, it could be used with
the :ref:`override-build <override_build>`, to convert file formats.


The plugin can also be used with the :ref:`organize <organize>` to reorganize
the files in the final payload. Like keep only libraries and exclude the
binaries and headers from SDKs.
