.. meta::
    :description: Reference for parts built with the Ruby plugin. Review the plugin's special configuration keys and see working examples of Ruby parts in YAML.

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

.. py:currentmodule:: craft_parts.plugins.ruby_plugin

.. kitbash-field:: RubyPluginProperties ruby_gems

.. kitbash-field:: RubyPluginProperties ruby_use_bundler

.. kitbash-field:: RubyPluginProperties ruby_flavor

.. kitbash-field:: RubyPluginProperties ruby_version

.. kitbash-field:: RubyPluginProperties ruby_shared

.. kitbash-field:: RubyPluginProperties ruby_use_jemalloc

.. kitbash-field:: RubyPluginProperties ruby_configure_options


.. _ruby_self-contained_start:

Attributes
----------

This plugin supports the ``self-contained`` build attribute. Declaring this attribute
prevents access to remote repositories, such as rubygems.org. All dependencies,
including plugins, must then be provided as packaged gems or in an earlier part.

When used in conjunction with ``ruby-use-bundler``, the build phase invokes
the ``bundle`` command with the ``--local`` argument.

.. _ruby_self-contained_end:

.. _ruby-details-begin:

Dependencies
------------

The Ruby plugin needs a Ruby interpreter to run Ruby programs but does not
provide it by default, to give you flexibility in the choice of interpreter flavor
and version.

A common means of including Ruby is to declare the ``ruby`` Ubuntu package,
or any ``ruby-<gem_name>`` Ubuntu package, as a ``stage-package``.

Alternatively, if ``ruby-flavor`` and ``ruby-version`` are declared, this plugin
downloads and runs the `ruby-install
<https://github.com/postmodern/ruby-install>`_ tool.

If a special Ruby part named ``ruby-deps`` is defined, it
creates a shared interpreter that the other Ruby parts can use.
For a Ruby part to use these shared files, it must list ``ruby-deps`` in its
``after`` key.

.. _ruby-details-end:


Examples
--------

The following example compiles version 3.2.0 of the Ruby interpreter from
source, installs the rackup gem, and finally builds the project directory as a
Ruby project.

.. code-block:: yaml

  parts:
    my-part:
      plugin: ruby
      source: .
      ruby-flavor: ruby
      ruby-version: "3.2.0"
      ruby-gems:
        - rackup

The following example shows how to use a shared Ruby interpreter provided by an
earlier part. Because the ``ruby-deps`` part specifies ``ruby-bundler`` as a
stage package, both the Bundler and Ruby executables from the Ubuntu archive
are included in the output artifact.

.. code-block:: yaml

  parts:
    ruby-deps:
      plugin: nil
      stage-packages:
        - ruby-bundler
    my-project:
      plugin: ruby
      source: .
      ruby-use-bundler: true
      ruby-gems:
        - rackup
      after: [ruby-deps]
