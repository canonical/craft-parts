.. _craft_parts_dotnet_plugin:

.NET plugin
===========

The ``dotnet`` plugin builds .NET projects using the ``dotnet`` tool.

Keywords
--------

In addition to the common :ref:`plugin <part-properties-plugin>` and
:ref:`sources <part-properties-sources>` keywords, this plugin provides the following
plugin-specific keywords:

dotnet-build-configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~
**Type:** string

The dotnet build configuration to use. The default value is ``"Release"``.

dotnet-self-contained-runtime-identifier
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Type:** string

Create a self contained .NET application using the specified Runtime Identifier.
See the `Runtime Identifier catalogue`_ for a list of possible values. This
property has no default value, meaning that it won't create self-contained
executables unless set.


.. _dotnet-details-begin:

Dependencies
------------

The .NET plugin needs the ``dotnet`` executable to build programs but does not
provision it by itself, to allow flexibility in the choice of compiler version.

Some common means of providing ``dotnet`` are:

* The ``dotnet8`` Ubuntu package, declared as a ``build-package``.
* The ``dotnet-sdk`` snap, declared as a ``build-snap`` from the desired channel.

Another alternative is to define another part with the name ``dotnet-deps``, and
declare that the part using the ``dotnet`` plugin comes :ref:`after <after>` the
``dotnet-deps`` part. In this case, the plugin will assume that this new part will
stage the ``dotnet`` executable to be used in the build step. This can be useful,
for example, in cases where a specific, unreleased version of ``dotnet`` is desired
but unavailable as a snap or an Ubuntu package.

Finally, whether the resulting built artefact will need the presence of the .NET
runtime to execute depends on the value of the
``dotnet-self-contained-runtime-identifier`` property: self-contained builds
bundle the necessary portions of the runtime in the generated executable.

.. _dotnet-details-end:

How it works
------------

During the build step the plugin performs the following actions:

* Call ``dotnet build -c <config>`` where ``<config>`` is the value of the
  ``dotnet-build-configuration`` property.
* Call ``dotnet publish`` to install the generated assets into ``${CRAFT_PART_INSTALL}``,
  optionally passing the value of ``dotnet-self-contained-runtime-identifier`` if
  set.


Examples
--------

The following example uses the ``dotnet-sdk`` snap to build an application in
``Debug`` configuration, generating assets that are self-contained to execute on
``linux-x64`` environments.


.. code-block:: yaml

    parts:
      my-dotnet-part:
        source: .
        plugin: dotnet
        build-snaps: [dotnet-sdk]
        dotnet-build-configuration: Debug
        dotnet-self-contained-runtime-identifier: linux-x64


.. _Runtime Identifier catalogue: https://learn.microsoft.com/en-us/dotnet/core/rid-catalog
