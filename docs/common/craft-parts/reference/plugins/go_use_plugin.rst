.. _craft_parts_go_use_plugin:

Go Use plugin
=============

The Go Use plugin allows for setting up a `go workspace`_ for `Go`_ modules. It is
a companion plugin meant to be used with the :ref:`Go plugin <craft_parts_go_plugin>`.
Use of this plugin sets up ``go.work`` and affects all parts.

Keys
----

This plugin has no unique keys.

.. _go-use-details-begin:

Dependencies
------------

The Go plugin needs the ``go`` executable to build Go programs but does not provision it
by itself, to allow flexibility in the choice of compiler version.

Common means of providing ``go`` are:

* The ``golang`` Ubuntu package, declared as a ``build-package``.
* The ``go`` snap, declared as a ``build-snap`` from the desired channel.

Another alternative is to define another part with the name ``go-deps``, and declare
that the part using the ``go`` plugin comes after the ``go-deps`` part through the
``after`` key. In this case, the plugin will assume that this new part will stage the
``go`` executable to be used in the build step. This can be useful, for example, in
cases where a specific, unreleased version of ``go`` is desired but unavailable as a
snap or an Ubuntu package.

.. _go-use-details-end:

How it works
------------

During the build step the plugin performs the following actions:

* Setup a `go workspace`_ if ``go.work`` has not been setup;
* Call ``go work use <source-dir>`` to add the source for the part to the workspace;

Examples
--------

The following snippet declares a parts named ``go-flags`` using the ``go-use`` plugin and
a ``hello`` part that declares this ``go-flags``` in its ``go.mod`` using the ``go`` plugin.
Correct ordering is achieved with the use of the ``after`` key in the ``hello`` part.

.. code-block:: yaml

    parts:
      go-flags:
        source: https://github.com/jessevdk/go-flags.git
        plugin: go-use
      hello:
        build-snaps:
          - go/1.22/stable
        plugin: go
        source: .
        after:
        - go-flags


.. _Build tags: https://pkg.go.dev/cmd/go#hdr-Build_constraints
.. _Go: https://go.dev/
.. _go generate: https://go.dev/blog/generate
.. _go workspace: https://go.dev/blog/get-familiar-with-workspaces
