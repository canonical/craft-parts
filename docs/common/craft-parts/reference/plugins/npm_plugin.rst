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
~~~~~~~~~~~~~~~~
**Type:** boolean
**Default:** False

When set to ``true``, the plugin downloads and includes the 
Node.js binaries and its dependencies in the resulting package.
If ``npm-include-node`` is ``true``, then :ref:`npm-node-version` must be defined.

.. _npm-node-version:

npm-node-version
~~~~~~~~~~~~~~~~
**Type:** string
**Default:** ``null``

Which version of Node.js to download and include in the final package.
Required if ``npm-include-node`` is set to ``true``.

The option accepts an NVM-style version string; you can specify one of:

* exact version (e.g. ``"20.12.2"``)
* major+minor version (e.g. ``"20.12"``)
* major version (e.g. ``"20"``)
* LTS code name (e.g. ``"lts/iron"``)
* latest mainline version (``"node"``)

When specifying a non-exact version identifier, the plugin selects
the latest version that satisfies the specified version range. If
the version picked by the plugin does not publish binaries for the
target architecture, the plugin picks the nearest version that 
both satisfies the version range and also publishes binaries
for the target architecture.

.. warning::
    In the ``nvm`` utility, you can specify ``system`` to use the system
    Node.js package, but this is unsupported in this plugin, as we
    are using upstream Node.js binaries.

    Also, the ``iojs`` specifier is unsupported in this plugin,
    as the ``iojs`` project was merged back to Node.js circa. 2015.
    Using a very old ``iojs`` runtime poses a significant security
    hazard. If your project still requires a JavaScript runtime
    from nearly a decade ago, consider
    migrating to the modern Node.js runtime.

Examples
--------

The following example declares a part using the ``npm`` plugin.
In this example, we show how you may build the ``terser`` utility
(a utility for compressing and obfuscating JavaScript code).
It uses the latest mainline stable version of Node.js and includes
a copy of the Node.js runtime inside the final package.

.. code-block:: yaml

    parts:
        app:
            plugin: npm
            source: https://github.com/terser/terser
            source-type: git
            npm-include-node: true
            npm-node-version: "node"

Another example that shows how to install an application that
is published to the npm registry but does not require a Node.js runtime
to run.

.. code-block:: yaml

    parts:
        app:
            plugin: npm
            source: https://registry.npmjs.org/esbuild/-/esbuild-0.21.3.tgz
            source-type: tar
            npm-include-node: false
            build-snaps:
            # use Node.js Snap during the build-time only
                - node
