.. _craft_parts_dump_plugin:

Dump plugin
=============

The Dump plugin can be used for any project where you want to include existing files
from somewhere and keep the content as is. Its source can be a local directory, a remote
repository, or a URL. Common use cases include:

* Include static files like scripts or media from a local directory.
* Download and unpack pre-compiled proprietary software from a remote URL.
* Use git to clone a remote SDK, dataset, or model.


Keys
----

This plugin has no unique keys.

You must specify at least the ``source`` key. The ``source-type`` key is optional, but
recommended, as it is used to specify how the source should be handled.


Dependencies
------------

This plugin has no dependencies.


How it works
------------

During the build step, the plugin performs the following actions:

#. Check the ``source-type`` key to determine the type of the source if specified,
   otherwise, it will try to guess the type based on the ``source``.
#. Download the file or clone the repository if the ``source`` is a remote location.
#. Copy the file or directory if the ``source`` is a local location.
#. Unpack the file if it is an archive specified by the ``source-type`` key.
#. Copy all contents and preserve the directory structure to the part's install
   directory.

Examples
--------

Copy a local directory as-is
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following part copies all files and directories from ``./assets`` into the
part's install directory while preserving the source directory structure:

.. code-block:: yaml

  parts:
    assets:
      plugin: dump
      source: ./assets

For example, a source file at ``./assets/images/logo.png`` is copied to
``images/logo.png`` in the part's install directory.

Copy files to specific locations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use the ``organize`` key when files from the source tree must be copied to
specific locations in the final payload. In this example, the part copies a
service file and a configuration file from the local ``files`` directory:

.. code-block:: yaml

  parts:
    config:
      plugin: dump
      source: ./files
      organize:
        my-app.service: usr/lib/systemd/system/my-app.service
        my-app.conf: etc/my-app/my-app.conf

Copy directories with ``organize``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When organizing a directory, the destination controls where the directory
contents are placed. The following part copies the contents of ``scripts`` to
``usr/bin`` and the contents of ``templates`` to ``usr/share/my-app/templates``:

.. code-block:: yaml

  parts:
    resources:
      plugin: dump
      source: ./resources
      organize:
        scripts/*: usr/bin/
        templates/*: usr/share/my-app/templates/

Copy files into a charm payload
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Projects that build charms can also use the Dump plugin to copy local charm
files into the payload. This example copies hook files, library files, and charm
metadata from the ``charm`` directory:

.. code-block:: yaml

  parts:
    charm-files:
      plugin: dump
      source: ./charm
      organize:
        hooks/*: hooks/
        lib/*: lib/
        metadata.yaml: metadata.yaml
        actions.yaml: actions.yaml
