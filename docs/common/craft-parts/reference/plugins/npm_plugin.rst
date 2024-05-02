.. _craft_parts_npm_plugin:

NPM Plugin
=============

The NPM plugin can be used for Node.js projects that use NPM (or Yarn) as the package manager.

Keywords
--------

In addition to the common :ref:`plugin <part-properties-plugin>` and
:ref:`sources <part-properties-sources>` keywords, this plugin provides the following
plugin-specific keywords:

npm-include-node
~~~~~~~~~~~~~~~~~~
**Type:** boolean
**Default:** False

If this option is set to ``true``, the plugin will download and include the 
Node.js binaries and its dependencies in the resulting package.
If ``npm-include-node`` is true, then :ref:`npm-node-version` must be defined.

.. _npm-node-version:

npm-node-version
~~~~~~~~~~~~~~~~~~~
**Type:** string
**Default:** ``null``

Which version of Node.js to download and include in the final package.
Required if ``npm-include-node`` is set to true.

The option accepts an NVM-style version string; you can specify one of:

* exact version (e.g. "20.12.2")
* major+minor version (e.g. "20.12")
* major version (e.g. "20")
* LTS code name (e.g. "lts/iron")
* latest mainline version ("node")

When specifying a non-exact version identifier, the plugin will select
the latest version that satisfies the specified version range. If
the version picked by the plugin does not publish binaries for the
target architecture, the plugin will pick the nearest version that 
both satisfies the version range and also publishes binaries
for the target architecture.

.. warning::
    In the ``nvm`` utility, you can specify "system" to use system
    Node.js package, but this is unsupported in this plugin, as we
    are using upstream Node.js binaries.

    Also, the ``iojs`` specifier is unsupported in this plugin,
    as the ``iojs`` project was merged back to Node.js circa. 2015.
    Using very old ``iojs`` runtime poses a significant security
    hazard. If your project still requires a JavaScript runtime
    from nearly a decade ago, you should seriously considering
    migrating to the modern Node.js runtime.
