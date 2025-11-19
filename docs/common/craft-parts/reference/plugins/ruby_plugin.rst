.. _craft_parts_ruby_plugin:

Ruby plugin
===========

The Ruby plugin manages Ruby gems and the Ruby interpreter. It can compile and
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

**Default:** ruby

The Ruby interpreter to compile and include. The supported interpreters are:

- ``ruby``
- ``jruby``
- ``rbx``
- ``truffleruby``
- ``mruby``


ruby-version
~~~~~~~~~~~~

**Type:** string

**Default:** "3.2"

The version of Ruby to build.


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

When set to ``true``, the plugin compiles Ruby with support for the jemalloc
Whether to compile Ruby with support for jemalloc.


ruby-configure-options
~~~~~~~~~~~~~~~~~~~~~~

**Type:** list of strings

Extra arguments to pass to the compiler when building the Ruby interpreter.


.. _ruby-details-begin:

Dependencies
------------

By default, this plugin downloads and runs the `ruby-install
<https://github.com/postmodern/ruby-install>` tool.

If a project has multiple Ruby parts, by default each compiles and bundles its
own Ruby interpreter. If a special Ruby part named ``ruby-deps`` is defined, it
creates a shared interpreter and shared gems that the other Ruby parts can use.
For a Ruby part to use these shared files, it must list ``ruby-deps`` in its
``after`` key.

.. code-block:: yaml

  parts:
    ruby-deps:
      plugin: ruby
      ruby-version: "3.4"
      ruby-gems:
        - rackup
    my-project:
      plugin: ruby
      source: .
      ruby-use-bundler: true
      after: [ruby-deps]

.. _ruby-details-end:
