.. _craft_parts_bazel_plugin:

Bazel plugin
============

The Bazel plugin can be used with projects that use Bazel_.

After a successful build, this plugin copies ``bazel-bin`` artifacts into
``$CRAFT_PART_INSTALL``.


Keys
----

This plugin provides the following unique keys.


bazel-parameters
~~~~~~~~~~~~~~~~

**Type:** list of strings

Options to pass to ``bazel build``.

bazel-targets
~~~~~~~~~~~~~~

**Type:** list of strings

**Default:** ``["//..."]``

Targets to pass to ``bazel build``. By default, all targets are built.

Dependencies
------------

The plugin requires Bazel. By default, the plugin installs Bazel through
``build-packages``, via the ``bazel-bootstrap`` package.

If you provide Bazel from a separate part named ``bazel-deps``, add
``after: [bazel-deps]`` to the Bazel plugin part and the plugin will skip
installing ``bazel-bootstrap``.

From the project, the ``BUILD`` file must define the targets to be built.



How it works
------------

During the build step, the plugin performs the following actions:

#. Call ``bazel build`` with any parameters defined in ``bazel-parameters``
   for the targets defined in ``bazel-targets``.

#. Copy the ``bazel-bin`` contents into ``$CRAFT_PART_INSTALL``.

Example
-------

The following snippet declares a part using the ``bazel`` plugin, the source referred to
in the part contains a ``BUILD`` file at the root and defines the targets to be
built. An alternate build parameter is set using ``bazel-parameters``:

.. code-block:: yaml

    parts:
      bazel-part:
        source: .
        plugin: bazel
        bazel-targets:
          - //:hello
        bazel-parameters:
          - --compilation_mode=fastbuild


.. _Bazel: https://bazel.build/
