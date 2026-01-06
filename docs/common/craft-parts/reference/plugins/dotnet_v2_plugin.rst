.. _craft_parts_dotnet_v2_plugin:

.NET plugin (v2)
================

The .NET plugin (v2) builds .NET projects using the `dotnet`_ tool. It's the successor
to the .NET plugin.


Keys
----

This plugin provides the following unique keys.


.. _craft_parts_dotnet_v2_plugin-global_flags:

Global flags
~~~~~~~~~~~~

dotnet-configuration
^^^^^^^^^^^^^^^^^^^^

**Type:** string

**Default:** ``"Release"``

The .NET build configuration to use. Possible values are ``"Debug"`` and ``"Release"``.


dotnet-project
^^^^^^^^^^^^^^

**Type:** string

The path to the solution or project file to build, relative to the root of the snap
source. If a path isn't specified, MSBuild will search the root of the source for a file
with the ``.*proj`` or ``.sln`` extension.


dotnet-properties
^^^^^^^^^^^^^^^^^

**Type:** dict of strings to strings

A list of MSBuild properties to be appended to the restore, build, and publish commands
in the format of ``-p:<Key>=<Value>``.


.. _craft_parts_dotnet_v2_plugin-dotnet_self_contained:

dotnet-self-contained
^^^^^^^^^^^^^^^^^^^^^

**Type:** boolean

**Default:** ``False``

Create a self-contained .NET application. The Runtime Identifier (RID) will be
automatically set based on the ``$CRAFT_BUILD_FOR`` variable for a given build, such
that:

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

Sets the MSBuild log output verbosity for the build. Possible values are: ``q[uiet]``,
``m[inimal]``, ``n[ormal]``, ``d[etailed]``, and ``diag[nostic]``.


.. _craft_parts_dotnet_v2_plugin-dotnet_version:

dotnet-version
^^^^^^^^^^^^^^

**Type:** string

Sets the .NET version to build the project with. By setting this key, the plugin will
download the necessary .NET SDK content snap and use it to build the application.

See the :ref:`craft_parts_dotnet_v2_plugin-details-begin` section for a more detailed
explanation of this key.


.. _craft_parts_dotnet_v2_plugin-restore_flags:

Restore flags
~~~~~~~~~~~~~

dotnet-restore-configfile
^^^^^^^^^^^^^^^^^^^^^^^^^

**Type:** string

A path to the NuGet configuration file (nuget.config) to use. If specified, only the
settings from this file will be used. If not specified, the hierarchy of configuration
files from the current directory will be used. For more information, see `Common NuGet
Configurations`_.


dotnet-restore-properties
^^^^^^^^^^^^^^^^^^^^^^^^^

**Type:** dict of strings to strings

A list of MSBuild properties to be appended to the restore command in the format of
``-p:<Key>=<Value>``.


dotnet-restore-sources
^^^^^^^^^^^^^^^^^^^^^^

**Type:** list of strings

Specifies the URIs of the NuGet package sources to use during the restore operation.
This setting overrides all of the sources specified in the *nuget.config* files.


.. _craft_parts_dotnet_v2_plugin-build_flags:

Build flags
~~~~~~~~~~~

dotnet-build-framework
^^^^^^^^^^^^^^^^^^^^^^

**Type:** string

Compiles for a specific `framework`_. The framework must be defined in the `project
file`_. Examples: ``net7.0``, ``net462``.


dotnet-build-properties
^^^^^^^^^^^^^^^^^^^^^^^^^

**Type:** dict of strings to strings

A list of MSBuild properties to be appended to the build command in the format of
``-p:<Key>=<Value>``.


.. _craft_parts_dotnet_v2_plugin-publish_flags:

Publish flags
~~~~~~~~~~~~~

dotnet-publish-properties
^^^^^^^^^^^^^^^^^^^^^^^^^

**Type:** dict of strings to strings

A list of MSBuild properties to be appended to the publish command in the format of
``-p:<Key>=<Value>``.


.. _craft_parts_dotnet_v2_plugin-details-begin:

Dependencies
------------

The .NET plugin needs the dotnet CLI tool to build programs. The plugin will provision
it by itself if :ref:`craft_parts_dotnet_v2_plugin-dotnet_version` is set.

.. important::

  The .NET SDK the plugin provisions is provided by the official Canonical .NET SDK
  `content snaps`_, which are available for various .NET versions starting with .NET 6.
  The .NET SDK provided by the content snaps are compatible with Ubuntu 22.04 LTS
  (Jammy Jellyfish) and later releases.

If :ref:`craft_parts_dotnet_v2_plugin-dotnet_version` is not set, the plugin assumes
that the dotnet CLI tool is already available in the build environment. This option is
particularly useful when building on bases that don't support the .NET SDK content snaps
(e.g., Ubuntu 20.04).

Some common means of providing the dotnet tool are:

* A .NET SDK package available from the Ubuntu archive, declared as a ``build-package``.
  Example: `dotnet-sdk-8.0`_.
* A .NET SDK content snap, declared as a ``build-snap`` from the desired channel.
  Example: `dotnet-sdk-80`_.

Another alternative is to define a separate part called ``dotnet-deps`` and have your
application's part build after the ``dotnet-deps`` part with the ``after`` key. In this
case, the plugin assumes that ``dotnet-deps`` will stage the dotnet CLI tool to be used
during build. This can be useful in cases where a specific, unreleased version of .NET
is desired but unavailable as a snap or Ubuntu package.

This plugin validates the presence of .NET by running ``dotnet --version``. Therefore,
it assumes that the dotnet executable is visible in the PATH. To achieve that, make sure
to append the location of the staged .NET SDK from ``dotnet-deps`` to the PATH using the
``build-environment`` key in your application part.

See :ref:`user-provided-sdk-example` for an example of this approach.

Finally, whether the resulting build artifact will also need a .NET runtime installed in
its environment depends on the value of the
:ref:`craft_parts_dotnet_v2_plugin-dotnet_self_contained` key. Self-contained
builds bundle the runtime in the generated executable and don't require a global .NET
Runtime installed in the system.

.. _craft_parts_dotnet_v2_plugin-details-end:


How it works
------------

During the build step the plugin performs the following actions:

#. Call ``dotnet restore`` with the relevant
   :ref:`global flags <craft_parts_dotnet_v2_plugin-global_flags>` and
   :ref:`restore-specific flags <craft_parts_dotnet_v2_plugin-restore_flags>`.
#. Call ``dotnet build --no-restore`` with the relevant
   :ref:`global flags <craft_parts_dotnet_v2_plugin-global_flags>` and
   :ref:`build-specific flags <craft_parts_dotnet_v2_plugin-build_flags>`.
#. Call ``dotnet publish --no-restore --no-build`` with the relevant
   :ref:`global flags <craft_parts_dotnet_v2_plugin-global_flags>` and
   :ref:`publish-specific flags <craft_parts_dotnet_v2_plugin-publish_flags>`.
   The generated assets are placed by default into ``${CRAFT_PART_INSTALL}``.


Example
-------

Plugin self-provisioned .NET SDK
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following example uses the .NET (v2) plugin to build an application with .NET 8
using the debug configuration, generating assets that are self-contained. Since the
``dotnet-version`` key is set, the plugin will provision the necessary .NET SDK by
itself.


.. code-block:: yaml
  :caption: Project file

    parts:
      my-dotnet-part:
        source: .
        plugin: dotnet
        dotnet-version: "8.0"
        dotnet-configuration: "Debug"
        dotnet-self-contained: true

This is the simplest way to build a .NET application using the .NET (v2) plugin.

.. _user-provided-sdk-example:

User-provided .NET SDK
~~~~~~~~~~~~~~~~~~~~~~

The following example builds a .NET application with a custom user-provided .NET SDK.
By providing a ``dotnet-deps`` part, the plugin will not attempt to provision the .NET
SDK by itself and will instead rely on the user-provided SDK staged by the
``dotnet-deps`` part.

.. code-block:: yaml
  :caption: Project file

    parts:
      dotnet-deps:
        plugin: dump
        source: https://builds.dotnet.microsoft.com/dotnet/Sdk/8.0.416/dotnet-sdk-8.0.416-linux-x64.tar.gz
        source-checksum: sha512/633cb85673e3519c825532f780f6750ff24ed248ef8df68885540e510b559b6adc2c8d940e4c349fc0cf2c9caf184f1efeaccbc5e952d6e435f3da027cae4188
        organize:
          '*': dotnet-sdk/
        prime:
          - -dotnet-sdk/

      my-dotnet-part:
        after: [dotnet-deps]
        source: .
        plugin: dotnet
        dotnet-configuration: "Release"
        dotnet-self-contained: true
        build-packages:
          - libicu74
        stage-packages:
          - libicu74
        build-environment:
          - PATH: ${PATH}:${CRAFT_STAGE}/dotnet-sdk

There are a few important details to note in this example.

The ``dotnet-deps`` part uses the ``dump`` plugin to download and stage a specific
version of the .NET SDK directly from Microsoft's official distribution site. The
``organize`` key is used to place the contents of the SDK into a dedicated subdirectory
(called ``dotnet-sdk/`` in this case) to avoid polluting the root of the part's staged
files. Then, in the ``my-dotnet-part`` part, we append this subdirectory to the PATH
using the ``build-environment`` key, so that the ``dotnet`` executable is visible during
the build step.

As we don't want to have the .NET SDK included in the final artifact, we remove the
entire ``dotnet-sdk/`` subdirectory from the staged files using the ``prime`` key.

Note that we also need to include the ``libicu74`` package in both the build and stage
steps, as it's a dependency of the .NET SDK used during build and .NET Runtime used at
runtime.


.. _Common NuGet Configurations: https://learn.microsoft.com/en-us/nuget/consume-packages/configuring-nuget-behavior
.. _framework: https://learn.microsoft.com/en-us/dotnet/standard/frameworks
.. _project file: https://learn.microsoft.com/en-us/dotnet/core/project-sdk/overview
.. _content snaps: https://github.com/canonical/dotnet-content-snaps
.. _dotnet-sdk-8.0: https://packages.ubuntu.com/noble/dotnet-sdk-8.0
.. _dotnet-sdk-80: https://snapcraft.io/dotnet-sdk-80
.. _dotnet: https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet
