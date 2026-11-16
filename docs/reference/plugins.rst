.. _plugins:

Plugins
=======

Plugins are used to provide support for specific technologies during the parts
lifecycle. They're grouped here by the kind of sources they build.


Utility plugins
---------------

These plugins provide minimal-to-no processing for sources in any language. They're for
when you need complete control over the build process.

- :ref:`craft_parts_dump_plugin`
- :ref:`craft_parts_nil_plugin`


Build system plugins
--------------------

These plugins drive general-purpose build systems that can build sources in more than
one language.

- :ref:`craft_parts_autotools_plugin`
- :ref:`craft_parts_bazel_plugin`
- :ref:`craft_parts_cmake_plugin`
- :ref:`craft_parts_colcon_plugin`
- :ref:`craft_parts_make_plugin`
- :ref:`craft_parts_meson_plugin`
- :ref:`craft_parts_qmake_plugin`
- :ref:`craft_parts_scons_plugin`


Language-specific plugins
-------------------------

These plugins build sources written in a particular language or for a particular
runtime. Where a plugin has more than one version, the version you get depends on your
project's base.


.NET plugins
~~~~~~~~~~~~

These plugins build sources written with the .NET SDK.

- :ref:`.NET (ubuntu@22.04 and lower) <craft_parts_dotnet_plugin>`
- :ref:`.NET (ubuntu@24.04 and higher) <craft_parts_dotnet_v2_plugin>`


Go plugins
~~~~~~~~~~

This plugin builds Go sources.

- :ref:`craft_parts_go_plugin`


Java plugins
~~~~~~~~~~~~

These plugins build Java and other JVM sources, and build minimal Java runtime images.

- :ref:`craft_parts_ant_plugin`
- :ref:`craft_parts_gradle_plugin`
- :ref:`craft_parts_jlink_plugin`
- :ref:`craft_parts_maven_plugin`


npm plugins
~~~~~~~~~~~

This plugin builds Node.js sources with npm.

- :ref:`craft_parts_npm_plugin`


Python plugins
~~~~~~~~~~~~~~

These plugins build Python sources with uv, pip, or Poetry.

- :ref:`craft_parts_uv_plugin`
- Python

  - :ref:`Python (ubuntu@24.04 and lower) <craft_parts_python_plugin>`
  - :ref:`Python (ubuntu@25.10 and higher) <python_v2_plugin>`

- :ref:`craft_parts_poetry_plugin`


Ruby plugins
~~~~~~~~~~~~

This plugin builds Ruby sources, and can build and bundle a custom Ruby interpreter.

- :ref:`craft_parts_ruby_plugin`


Rust plugins
~~~~~~~~~~~~

This plugin builds Rust sources with Cargo.

- :ref:`craft_parts_rust_plugin`


Offline build plugins (deprecated)
----------------------------------

These plugins share build artifacts between parts through a local directory, so that
dependencies don't need to be fetched from the internet. They aren't currently used in
production.

- :ref:`craft_parts_cargo_use_plugin`
- :ref:`craft_parts_go_use_plugin`
- :ref:`craft_parts_gradle_use_plugin`
- :ref:`craft_parts_maven_use_plugin`
- :ref:`craft_parts_npm_use_plugin`


When documenting a new plugin, follow the guidelines in :ref:`how_to_document_a_plugin`.


.. toctree::
   :hidden:

   /common/craft-parts/reference/plugins/dump_plugin.rst
   /common/craft-parts/reference/plugins/nil_plugin.rst
   /common/craft-parts/reference/plugins/autotools_plugin.rst
   /common/craft-parts/reference/plugins/bazel_plugin.rst
   /common/craft-parts/reference/plugins/cmake_plugin.rst
   /common/craft-parts/reference/plugins/colcon_plugin.rst
   /common/craft-parts/reference/plugins/make_plugin.rst
   /common/craft-parts/reference/plugins/meson_plugin.rst
   /common/craft-parts/reference/plugins/qmake_plugin.rst
   /common/craft-parts/reference/plugins/scons_plugin.rst
   /common/craft-parts/reference/plugins/dotnet_plugin.rst
   /common/craft-parts/reference/plugins/dotnet_v2_plugin.rst
   /common/craft-parts/reference/plugins/go_plugin.rst
   /common/craft-parts/reference/plugins/ant_plugin.rst
   /common/craft-parts/reference/plugins/gradle_plugin.rst
   /common/craft-parts/reference/plugins/jlink_plugin.rst
   /common/craft-parts/reference/plugins/maven_plugin.rst
   /common/craft-parts/reference/plugins/npm_plugin.rst
   /common/craft-parts/reference/plugins/uv_plugin.rst
   /common/craft-parts/reference/plugins/python_plugin.rst
   /common/craft-parts/reference/plugins/python_v2_plugin.rst
   /common/craft-parts/reference/plugins/poetry_plugin.rst
   /common/craft-parts/reference/plugins/ruby_plugin.rst
   /common/craft-parts/reference/plugins/rust_plugin.rst
   /common/craft-parts/reference/plugins/cargo_use_plugin.rst
   /common/craft-parts/reference/plugins/go_use_plugin.rst
   /common/craft-parts/reference/plugins/gradle_use_plugin.rst
   /common/craft-parts/reference/plugins/maven_use_plugin.rst
   /common/craft-parts/reference/plugins/npm_use_plugin.rst
