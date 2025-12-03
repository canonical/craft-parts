.. _craft_parts_ruby_plugin:

Ruby plugin
===========

The Ruby plugin manages Ruby gems and the Ruby interpreter. It can build and
bundle different variants of the interpreter, build gems with tools like rake or
Bundler, and install gems.

.. _craft_parts_ruby_plugin-keywords:

Keys
----

This plugin provides the following unique keys.


ruby-gems
~~~~~~~~~

**Type:** list of strings

The gems to install.


ruby-use-bundler
~~~~~~~~~~~~~~~~

**Type:** boolean

**Default:** False

Whether to use Bundler to build the gems.


ruby-flavor
~~~~~~~~~~~

**Type:** string

**Default:** None

The Ruby interpreter to build and include. The supported interpreters are:

- ``ruby``
- ``jruby``
- ``truffleruby``
- ``mruby``


ruby-version
~~~~~~~~~~~~

**Type:** string

**Default:** None

The version of the Ruby interpreter to build.


ruby-shared
~~~~~~~~~~~

**Type:** boolean

**Default:** False

When set to ``true``, the plugin builds ``libruby.so``, a shared library that
other binaries can link against.


ruby-use-jemalloc
~~~~~~~~~~~~~~~~~

**Type:** boolean

**Default:** False

Whether to build Ruby with support for jemalloc.


ruby-configure-options
~~~~~~~~~~~~~~~~~~~~~~

**Type:** list of strings

Extra arguments to pass to the ``configure`` script when building the Ruby
interpreter.


.. _ruby-details-begin:

Dependencies
------------

`By default this plugin uses Ruby from the base when it is available and appropriate to
`use. However, the core images used by Snapcraft do not contain Ruby, so it will need to be
supplied in snaps that use it. Snaps that use classic confinement will use the host system's
Ruby.

Use of ``ruby-<gem-package>`` in stage-packages will force the inclusion of the
Ruby interpreter.

If ``ruby-flavor`` and ``ruby-version`` are specified, this plugin downloads
and runs the `ruby-install
<https://github.com/postmodern/ruby-install>` tool.

If a special Ruby part named ``ruby-deps`` is defined, it
creates a shared interpreter and shared gems that the other Ruby parts can use.
For a Ruby part to use these shared files, it must list ``ruby-deps`` in its
``after`` key.

.. code-block:: yaml

  parts:
    ruby-deps:
      plugin: ruby
      ruby-flavor: mruby
      ruby-version: "3.4"
      ruby-gems:
        - bundler
        - rackup
    my-project:
      plugin: ruby
      source: .
      ruby-use-bundler: true
      after: [ruby-deps]

.. _ruby-details-end:
