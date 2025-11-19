.. _craft_parts_ruby_plugin:

Ruby plugin
===========

The Ruby plugin can be used in projects that need to bundle a specific
version and variant of the Ruby interpreter within the final artifact. The
plugin can further be used to install individual gems or trigger a build tool
such as rake or bundler.

.. _craft_parts_ruby_plugin-keywords:

Keys
----

This plugin provides the following unique keys.


ruby-gems
~~~~~~~~~

**Type:** list of strings

List of gems to be installed.


ruby-use-bundler
~~~~~~~~~~~~~~~~

**Type:** boolean

**Default:** False

When set to ``true``, the plugin runs the ``bundle`` command as part of the
``build`` step.


ruby-flavor
~~~~~~~~~~~

**Type:** string

**Default:** ruby

Specifies which implementation of the Ruby interpreter the plugin
should build. Supported values are ``ruby``, ``jruby``, ``rbx``,
``truffleruby``, and ``mruby``.


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
memory allocator.


ruby-configure-options
~~~~~~~~~~~~~~~~~~~~~~

**Type:** list of strings

Extra arguments to pass to the compiler when building the Ruby interpreter.


.. _ruby-details-begin:

Dependencies
------------

By default, this plugin downloads and runs the `ruby-install
<https://github.com/postmodern/ruby-install>` tool. If recompiling the
interpreter for every Ruby-based part is not desired, a ``ruby-deps`` part
can install Ruby and any gems in the build system. Other parts that use this
interpreter must run ``after`` the ``ruby-deps`` part:

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
