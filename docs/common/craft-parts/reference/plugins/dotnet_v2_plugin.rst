.. _craft_parts_dotnet_v2_plugin:

.NET plugin (v2)
================

The .NET plugin (v2) builds .NET projects using the `dotnet
<https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet>`_ tool. It's the successor
to the :ref:`craft_parts_dotnet_plugin`.

Keywords
--------

In addition to the common :ref:`plugin <part-properties-plugin>` and
:ref:`sources <part-properties-sources>` keywords, this plugin provides the
following plugin-specific keywords:

.. _craft_parts_dotnet_v2_plugin-global_flags:

Global Flags
~~~~~~~~~~~~

dotnet-configuration
^^^^^^^^^^^^^^^^^^^^
**Type:** string

**Default:** ``"Release"``

The .NET build configuration to use. Possible values are ``"Debug"`` and
``"Release"``.

dotnet-project
^^^^^^^^^^^^^^
**Type:** string

**Default:** Unset

The path to the solution or project file to build, relative to the root of the
snap source. If a path isn't specified, MSBuild will search the root of the
source for a file with the ``.*proj`` or ``.sln`` extension.

dotnet-properties
^^^^^^^^^^^^^^^^^
**Type:** dict of strings to strings

**Default:** Unset

A list of MSBuild properties to be appended to the restore, build, and publish
commands in the format of ``-p:<Key>=<Value>``.

.. _craft_parts_dotnet_v2_plugin-dotnet_self_contained:

dotnet-self-contained
^^^^^^^^^^^^^^^^^^^^^
**Type:** boolean

**Default:** ``False``

Create a self-contained .NET application. The Runtime Identifier (RID) will be
automatically set based on the ``$CRAFT_BUILD_FOR`` variable for a given
build, such that:

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

.. _craft_parts_dotnet_v2_plugin-dotnet_version:

dotnet-version
^^^^^^^^^^^^^^
**Type:** string

**Default:** Unset

Sets the .NET version to build the project with. By setting this key, the
plugin will download the necessary .NET SDK content snap and use it to build
the application.

See the :ref:`craft_parts_dotnet_v2_plugin-details-begin` section for a more
detailed explanation of this property.

.. _craft_parts_dotnet_v2_plugin-restore_flags:

Restore Flags
~~~~~~~~~~~~~

dotnet-restore-configfile
^^^^^^^^^^^^^^^^^^^^^^^^^
**Type:** string

**Default:** Unset

A path to the NuGet configuration file (nuget.config) to use. If specified,
only the settings from this file will be used. If not specified, the hierarchy
of configuration files from the current directory will be used. For more
information, see `Common NuGet Configurations`_.

dotnet-restore-properties
^^^^^^^^^^^^^^^^^^^^^^^^^
**Type:** dict of strings to strings

**Default:** Unset

A list of MSBuild properties to be appended to the restore command in the
format of ``-p:<Key>=<Value>``.

dotnet-restore-sources
^^^^^^^^^^^^^^^^^^^^^^
**Type:** list of strings

**Default:** Unset

Specifies the URIs of the NuGet package sources to use during the restore
operation. This setting overrides all of the sources specified in the
*nuget.config* files.

.. _craft_parts_dotnet_v2_plugin-build_flags:

Build Flags
~~~~~~~~~~~

dotnet-build-framework
^^^^^^^^^^^^^^^^^^^^^^

**Type:** string

**Default:** Unset

Compiles for a specific `framework`_. The framework must be defined in the
`project file`_. Examples: ``net7.0``, ``net462``.

dotnet-build-properties
^^^^^^^^^^^^^^^^^^^^^^^^^
**Type:** dict of strings to strings

**Default:** Unset

A list of MSBuild properties to be appended to the build command in the format
of ``-p:<Key>=<Value>``.

.. _craft_parts_dotnet_v2_plugin-publish_flags:

Publish Flags
~~~~~~~~~~~~~

dotnet-publish-properties
^^^^^^^^^^^^^^^^^^^^^^^^^
**Type:** dict of strings to strings

**Default:** Unset

A list of MSBuild properties to be appended to the publish command in the
format of ``-p:<Key>=<Value>``.

.. _craft_parts_dotnet_v2_plugin-details-begin:

Dependencies
------------

The .NET plugin needs the dotnet CLI tool to build programs. The plugin
will provision it by itself if
:ref:`craft_parts_dotnet_v2_plugin-dotnet_version` is set.

If not, some common means of providing the dotnet tool are:

* A .NET SDK package available from the Ubuntu archive, declared as a
  ``build-package``. Example: `dotnet-sdk-8.0`_.
* A .NET SDK content snap, declared as a ``build-snap`` from the desired
  channel. Example: `dotnet-sdk-80`_.

Another alternative is to define a separate part called ``dotnet-deps``
and have the part using the .NET plugin (v2) build :ref:`after <after>` the
``dotnet-deps`` part. In this case, the plugin assumes that ``dotnet-deps``
will stage the dotnet CLI tool to be used during build. This can be useful in
cases where a specific, unreleased version of .NET is desired but unavailable
as a snap or Ubuntu package.

This plugin validates the presence of .NET by running ``dotnet --version``.
Therefore, it assumes that the dotnet executable is visible in the PATH. To
achieve that, make sure to append the location of the staged .NET SDK from
``dotnet-deps`` to the PATH using the :ref:`build-environment
<build_environment>` key in your application part.

Finally, whether the resulting build artifact will also need a
.NET runtime installed in the snap environment depends on the value of the
:ref:`craft_parts_dotnet_v2_plugin-dotnet_self_contained` property:
self-contained builds bundle the runtime in the generated executable and
don't require a global .NET Runtime installed in the system.

.. _craft_parts_dotnet_v2_plugin-details-end:

How it works
------------

During the build step the plugin performs the following actions:

* Call ``dotnet restore`` with the relevant
  :ref:`global flags <craft_parts_dotnet_v2_plugin-global_flags>` and
  :ref:`restore-specific flags <craft_parts_dotnet_v2_plugin-restore_flags>`.
* Call ``dotnet build --no-restore`` with the relevant
  :ref:`global flags <craft_parts_dotnet_v2_plugin-global_flags>` and
  :ref:`build-specific flags <craft_parts_dotnet_v2_plugin-build_flags>`.
* Call ``dotnet publish --no-restore --no-build`` with the relevant
  :ref:`global flags <craft_parts_dotnet_v2_plugin-global_flags>` and
  :ref:`publish-specific flags <craft_parts_dotnet_v2_plugin-publish_flags>`.
  The generated assets are placed by default into ``${CRAFT_PART_INSTALL}``.


Examples
--------

The following example uses the .NET (v2) plugin to build an application with
.NET 8 using the debug configuration, generating assets that are
self-contained.


.. code-block:: yaml
  :caption: Project file

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
.. _dotnet-sdk-8.0: https://packages.ubuntu.com/noble/dotnet-sdk-8.0
.. _dotnet-sdk-80: https://snapcraft.io/dotnet-sdk-80
