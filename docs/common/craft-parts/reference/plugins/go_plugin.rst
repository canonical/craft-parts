.. _craft_parts_go_plugin:

Go plugin
=========

The Go plugin builds `Go`_ modules, which are collections of packages stored
in a file tree containing a ``go.mod`` file at the root. After a successful
build, this plugin will install the generated binaries in
``$CRAFT_PART_INSTALL/bin``.


Keywords
--------

In addition to the common :ref:`plugin <part-properties-plugin>` and
:ref:`sources <part-properties-sources>` keywords, this plugin provides the following
plugin-specific keywords:

go-buildtags
~~~~~~~~~~~~
**Type:** list of strings
**Default:** []

`Build tags`_ to use during the build. The default behavior is not to use any
build tags.

go-generate
~~~~~~~~~~~
**Type:** list of strings
**Default:** []

Parameters to pass to `go generate`_ before building. Each item on the list
will be a separate ``go generate`` call. The default behavior is not to call
``go generate``.

Environment variables
---------------------

During build, this plugin sets ``GOBIN`` to ``${CRAFT_PART_INSTALL}/bin``.

.. _go-details-begin:

Dependencies
------------

The Go plugin needs the ``go`` executable to build Go programs but does not
provision it by itself, to allow flexibility in the choice of compiler version.

Common means of providing ``go`` are:

* The ``golang`` Ubuntu package, declared as a ``build-package``.
* The ``go`` snap, declared as a ``build-snap`` from the desired channel.

Another alternative is to define another part with the name ``go-deps``, and
declare that the part using the ``go`` plugin comes :ref:`after <after>` the
``go-deps`` part. In this case, the plugin will assume that this new part will
stage the ``go`` executable to be used in the build step. This can be useful,
for example, in cases where a specific, unreleased version of ``go`` is desired
but unavailable as a snap or an Ubuntu package.

.. _go-details-end:

How it works
------------

During the build step the plugin performs the following actions:

* Call ``go mod download all`` to find and download all necessary modules;
* Call ``go generate <item>`` for each item in ``go-generate``;
* Call ``go install  ./...``, passing the items in ``go-buildtags`` through the
  ``--tags`` parameter.

Examples
--------

The following snippet declares a part using the ``go`` plugin. It uses the stable
1.22 version of the ``go`` snap, enables the build tag ``experimental`` and calls
``go generate ./cmd`` before building:

.. code-block:: yaml

    parts:
      go:
        plugin: go
        source: .
        build-snaps:
          - go/1.22/stable
        go-buildtags:
          - experimental
        go-generate:
          - ./cmd


.. _Build tags: https://pkg.go.dev/cmd/go#hdr-Build_constraints
.. _Go: https://go.dev/
.. _go generate: https://go.dev/blog/generate

