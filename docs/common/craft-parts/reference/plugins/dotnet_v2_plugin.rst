.. _craft_parts_dotnet_v2_plugin:

.NET plugin (v2)
================

The ``dotnet`` plugin builds .NET projects using the ``dotnet`` tool.

.. note::
    This plugin is only available on ``core24`` and later. If you're on ``core22``,
    please refer to :ref:`.NET plugin <craft_parts_dotnet_plugin>`.

Keywords
--------

In addition to the common :ref:`plugin <part-properties-plugin>` and
:ref:`sources <part-properties-sources>` keywords, this plugin provides the following
plugin-specific keywords:

.. _global_flags:

Global Flags
~~~~~~~~~~~~

dotnet-configuration
^^^^^^^^^^^^^^^^^^^^
**Type:** string

**Default:** ``"Release"``

The .NET build configuration to use. Possible values are ``"Debug"`` and ``"Release"``.

dotnet-project
^^^^^^^^^^^^^^
**Type:** string

**Default:** ``None``

Path to the solution or project file to build relative to the root of the snap source.
If a project or solution file is not specified, MSBuild will search t he root of the snap
source for a file that has an extension that ends in either ``proj`` or ``sln``.

dotnet-properties
^^^^^^^^^^^^^^^^^
**Type:** dict of strings to strings

**Default:** Empty

A list of MSBuild properties to be appended to the restore, build, and publish commands
in the format of ``-p:<Key>=<Value>``.

.. _dotnet_self_contained:

dotnet-self-contained
^^^^^^^^^^^^^^^^^^^^^
**Type:** boolean

**Default:** ``False``

Create a self-contained .NET application. The Runtime Identifier (RID) will be automatically
set based on the ``$CRAFT_BUILD_FOR`` variable for a given build, such that:

+------------------------------+------------------------+
| ``$CRAFT_BUILD_FOR`` value   | .NET RID               |
+==============================+========================+
| ``amd64``                    | ``linux-x64``          |
+------------------------------+------------------------+
| ``arm64``                    | ``linux-arm64``        |
+------------------------------+------------------------+

dotnet-verbosity
^^^^^^^^^^^^^^^^
**Type:** string

**Default:** ``"normal"``

Sets the MSBuild log output verbosity for the build. Possible values are:
``q[uiet]``, ``m[inimal]``, ``n[ormal]``, ``d[etailed]``, and ``diag[nostic]``.

.. _dotnet_version:

dotnet-version
^^^^^^^^^^^^^^
**Type:** string

**Default:** ``None``

Sets the .NET version to build the project with. By setting this property, the plugin
will download the necessary .NET SDK content snap and use it to build the application.

See the :ref:`dotnet-v2-details-begin` section for a more detailed explanation of this property.

.. _restore_flags:

Restore Flags
~~~~~~~~~~~~~

dotnet-restore-configfile
^^^^^^^^^^^^^^^^^^^^^^^^^
**Type:** string

**Default:** ``None``

A path to the NuGet configuration file (nuget.config) to use. If specified, only the
settings from this file will be used. If not specified, the hierarchy of configuration
files from the current directory will be used. For more information, see
`Common NuGet Configurations`_.

dotnet-restore-properties
^^^^^^^^^^^^^^^^^^^^^^^^^
**Type:** dict of strings to strings

**Default:** Empty

A list of MSBuild properties to be appended to the restore command in the format of
``-p:<Key>=<Value>``.

dotnet-restore-sources
^^^^^^^^^^^^^^^^^^^^^^
**Type:** list of strings

**Default:** Empty

Specifies the URIs of the NuGet package sources to use during the restore operation.
This setting overrides all of the sources specified in the *nuget.config* files.

.. _build_flags:

Build Flags
~~~~~~~~~~~

dotnet-build-framework
^^^^^^^^^^^^^^^^^^^^^^

**Type:** string

**Default:** ``None``

Compiles for a specific `framework`_. The framework must be defined in the `project file`_.
Examples: ``net7.0``, ``net462``.

dotnet-build-properties
^^^^^^^^^^^^^^^^^^^^^^^^^
**Type:** dict of strings to strings

**Default:** Empty

A list of MSBuild properties to be appended to the build command in the format of
``-p:<Key>=<Value>``.

.. _publish_flags:

Publish Flags
~~~~~~~~~~~~~

dotnet-publish-properties
^^^^^^^^^^^^^^^^^^^^^^^^^
**Type:** dict of strings to strings

**Default:** Empty

A list of MSBuild properties to be appended to the publish command in the format of
``-p:<Key>=<Value>``.

.. _dotnet-v2-details-begin:

Dependencies
------------

The .NET plugin needs the ``dotnet`` executable to build programs. The plugin will
provision it by itself if :ref:`dotnet_version` is set.

If not, some common means of providing ``dotnet`` are:

* The ``dotnet8`` Ubuntu package, declared as a ``build-package``.
* The ``dotnet-sdk-80`` snap, declared as a ``build-snap`` from the desired channel.

Another alternative is to define another part with the name ``dotnet-deps``, and
declare that the part using the ``dotnet`` plugin comes :ref:`after <after>` the
``dotnet-deps`` part. In this case, the plugin will assume that this new part will
stage the ``dotnet`` executable to be used in the build step. This can be useful,
for example, in cases where a specific, unreleased version of ``dotnet`` is desired
but unavailable as a snap or an Ubuntu package.

.. note::
    This plugin will validate the presence of .NET by running ``dotnet --version``.
    Therefore, it is assumed that the ``dotnet`` executable is visible in the PATH.
    To achieve that, make sure to append the location of the staged .NET SDK from
    ``dotnet-deps`` to the PATH using the :ref:`build-environment <build_environment>`
    property.

Finally, whether the resulting built artifact will need the presence of the .NET
runtime to execute depends on the value of the :ref:`dotnet_self_contained` property:
self-contained builds bundle the necessary portions of the runtime in the generated
executable.

.. _dotnet-v2-details-end:

How it works
------------

During the build step the plugin performs the following actions:

* Call ``dotnet restore`` with the relevant :ref:`global flags <global_flags>` and
  :ref:`restore-specific flags <restore_flags>`.
* Call ``dotnet build --no-restore`` with the relevant :ref:`global flags <global_flags>` and
  :ref:`build-specific flags <build_flags>`.
* Call ``dotnet publish --no-restore --no-build`` with the relevant
  :ref:`global flags <global_flags>` and :ref:`publish-specific flags <publish_flags>`.
  The generated assets are placed by default into ``${CRAFT_PART_INSTALL}``.


Examples
--------

The following example uses the ``dotnet`` plugin to build an application with .NET 8 using
the ``Debug`` configuration, generating assets that are self-contained.


.. code-block:: yaml

    parts:
      my-dotnet-part:
        source: .
        plugin: dotnet
        dotnet-version: "8.0"
        dotnet-configuration: "Debug"
        dotnet-self-contained: true


.. _Common NuGet Configurations: https://learn.microsoft.com/en-us/nuget/consume-packages/configuring-nuget-behavior
.. _framework: https://learn.microsoft.com/en-us/dotnet/standard/frameworks
.. _project file: https://learn.microsoft.com/en-us/dotnet/core/project-sdk/overview
