.. _craft_parts_npm_plugin:

npm plugin
==========

The npm plugin can be used for Node.js projects that use npm (or Yarn) as the package
manager.


Keys
----

This plugin provides the following unique keys.

.. py:currentmodule:: craft_parts.plugins.npm_plugin

.. kitbash-field:: NpmPluginProperties npm_include_node

.. kitbash-field:: NpmPluginProperties npm_node_version


Attributes
----------

This plugin supports the ``self-contained`` build attribute. Declaring this attribute
enables offline builds by blocking all npm registry access and installing dependencies from
pre-cached tarballs.

Parts that produce dependencies should use the :ref:`craft_parts_npm_use_plugin` to publish their
tarballs to a shared cache.


In self-contained builds, ``package-lock.json`` is ignored. Dependencies
are resolved at build time from cached tarballs produced by other parts.
The ``npm-include-node`` option is not supported with this build attribute.
Node.js must be provided by a build snap or build package.


Examples
--------

The following example declares a part using the ``npm`` plugin. In this example, we show
how you may build the ``terser`` utility (a utility for compressing and obfuscating
JavaScript code). It uses the latest mainline stable version of Node.js and includes a
copy of the Node.js runtime inside the final package.

.. code-block:: yaml

    parts:
        app:
            plugin: npm
            source: https://github.com/terser/terser
            source-type: git
            npm-include-node: true
            npm-node-version: "node"

Another example that shows how to install an application that is published to the npm
registry but does not require a Node.js runtime to run.

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
