.. _plugins:

Plugins
=======

Plugins are used to provide support for specific technologies during the parts
lifecycle. They are grouped here by the language or technology they support.


Built-in
--------

These plugins cover the basic cases -- copying files verbatim, or bypassing
the build altogether. They are available in every application built on Craft
Parts.

.. toctree::
   :maxdepth: 1

   /common/craft-parts/reference/plugins/dump_plugin.rst
   /common/craft-parts/reference/plugins/nil_plugin.rst


Multi-language
--------------

These plugins drive general-purpose build systems that aren't tied to a
single language.

.. toctree::
   :maxdepth: 1

   /common/craft-parts/reference/plugins/autotools_plugin.rst
   /common/craft-parts/reference/plugins/bazel_plugin.rst
   /common/craft-parts/reference/plugins/cmake_plugin.rst
   /common/craft-parts/reference/plugins/colcon_plugin.rst
   /common/craft-parts/reference/plugins/make_plugin.rst
   /common/craft-parts/reference/plugins/meson_plugin.rst
   /common/craft-parts/reference/plugins/qmake_plugin.rst
   /common/craft-parts/reference/plugins/scons_plugin.rst


.NET
----

These plugins build projects with the .NET SDK.

.. toctree::
   :maxdepth: 1

   /common/craft-parts/reference/plugins/dotnet_plugin.rst
   /common/craft-parts/reference/plugins/dotnet_v2_plugin.rst


Go
--

These plugins build Go projects and set up shared Go workspaces.

.. toctree::
   :maxdepth: 1

   /common/craft-parts/reference/plugins/go_plugin.rst
   /common/craft-parts/reference/plugins/go_use_plugin.rst


Java
----

These plugins build Java projects and assemble minimal Java runtimes.

.. toctree::
   :maxdepth: 1

   /common/craft-parts/reference/plugins/ant_plugin.rst
   /common/craft-parts/reference/plugins/gradle_plugin.rst
   /common/craft-parts/reference/plugins/gradle_use_plugin.rst
   /common/craft-parts/reference/plugins/jlink_plugin.rst
   /common/craft-parts/reference/plugins/maven_plugin.rst
   /common/craft-parts/reference/plugins/maven_use_plugin.rst


JavaScript
----------

These plugins build JavaScript projects with npm.

.. toctree::
   :maxdepth: 1

   /common/craft-parts/reference/plugins/npm_plugin.rst
   /common/craft-parts/reference/plugins/npm_use_plugin.rst


Python
------

These plugins build Python projects with pip, Poetry, or uv.

.. toctree::
   :maxdepth: 1

   /common/craft-parts/reference/plugins/poetry_plugin.rst
   /common/craft-parts/reference/plugins/python_plugin.rst
   /common/craft-parts/reference/plugins/python_v2_plugin.rst
   /common/craft-parts/reference/plugins/uv_plugin.rst


Ruby
----

This plugin builds Ruby projects.

.. toctree::
   :maxdepth: 1

   /common/craft-parts/reference/plugins/ruby_plugin.rst


Rust
----

These plugins build Rust projects with Cargo and set up local crate
registries.

.. toctree::
   :maxdepth: 1

   /common/craft-parts/reference/plugins/cargo_use_plugin.rst
   /common/craft-parts/reference/plugins/rust_plugin.rst


When documenting a new plugin, follow the guidelines in :ref:`how_to_document_a_plugin`.
