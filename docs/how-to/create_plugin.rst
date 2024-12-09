.. _how_to_create_plugin:

How to create a plugin
======================

Plugins help to bring new tools and programming languages into Craft Parts.
This document contains instructions on how to recreate the simple
:py:class:`~craft-parts.plugins.dump_plugin.DumpPlugin` plugin.

Create your plugin file
-----------------------
The first step in creating a plugin is deciding where it will live. If you're
adding a plugin directly to Craft Parts, then it should go in
:file:`craft_parts/plugins`. For re-creating the ``dump`` plugin,
you can put it in :file:`craft_parts/plugins/new_dump_plugin.py`.

Imports
~~~~~~~
First, you have to pull in the imports. Since this is such a simple plugin,
the list of necessary imports is quite small:

.. code:: py

    from typing import Literal
    from overrides import override

    from .base import Plugin
    from .properties import PluginProperties

Defining a properties class
~~~~~~~~~~~~~~~~~~~~~~~~~~~
All plugins make use of a "properties" class to describe their metadata.
This encompasses two kinds of property: common ones and unique ones. Common
properties are those that are used by every plugin. Currently, there are just
two common properties.

plugin:
    The ``plugin`` property is the front-facing name of a plugin. This is the
    string that will be typed into a configuration file such as a
    `snapcraft.yaml`_ file to select the plugin.
source:
    The ``source`` property specifies the working files of a part. It has a
    lot of specialised logic for different file types ranging from tar files
    to git repositories, so you can leverage it to get much broader
    functionality out of an otherwise simple plugin.

Unique properties are those that are specific to a plugin. For example, a
plugin based on Java might have a unique property to specify the Java version,
or a Python-based plugin might have one to specify a requirements file. The 
``new-dump`` plugin will be quite simple, so there's no need for unique
properties.

.. code:: py

    class NewDumpPluginProperties(PluginProperties, frozen=True):
        """The part properties used by the new dump plugin."""

        plugin: Literal["new-dump"] = "new-dump"
        source: str

Creating the plugin class
~~~~~~~~~~~~~~~~~~~~~~~~~
The plugin class itself contains the functionality of the plugin. Start by
declaring the properties class:

.. code:: py

    class NewDumpPlugin(Plugin):
        """Copy the content from the part source."""
        
        properties_class = NewDumpPluginProperties
    
Next, you have to start defining the special methods that make this plugin
work. Since this is such a simple plugin, many of these methods are empty:

.. code:: py

    @override
    def get_build_snaps(self) -> set[str]:
        """Return a set of required snaps to install in the build
        environment."""
        return set()

    @override
    def get_pull_commands(self) -> list[str]:
        """Return a list of commands to retrieve dependencies during the
        pull step."""
        return []

    @override
    def get_build_packages(self) -> set[str]:
        """Return a set of required packages to install in the build
        environment."""
        return set()

    @override
    def get_build_environment(self) -> dict[str, str]:
        """Return a dictionary with the environment to use in the build
        step."""
        return {}

The last method that you have to define, however, is where the actual
:ref:`build commands <lifecycle>` are defined. These are the exact commands
executed by a subprocess during the build process:

.. code:: py

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        install_dir = self._part_info.part_install_dir
        return [f'cp --archive --link --no-dereference . "{install_dir}"']

Notice you don't require a user-provided source directory/file - this is because
the ``source`` parameter will the heavy-lifting. The source parameter is a
mandatory parameter that specifies the working files of a part. It has a lot of
specialised logic for different file types ranging from tar files to git
repositories, so you can leverage it to get much stronger functionality out of
an otherwise simple plugin.

Final steps
~~~~~~~~~~~
Now that you have your very own plugin, the last step is to make the 
lifecycle manager aware of this plugin. Since you created your plugin 
directly in Craft Parts, all that's needed is to add it to a dictionary in
:file:`craft_parts/plugins/plugins.py`:

.. code:: py

    from .new_dump_plugin import NewDumpPlugin

    # ...

    _BUILTIN_PLUGINS: dict[str, PluginType] = {
        # ...
        "new-dump": NewDumpPlugin,
    }

Next steps
~~~~~~~~~~

:ref:`How to document a plugin <how_to_document_a_plugin>`

.. LINKS
.. _snapcraft.yaml: https://snapcraft.io/docs/build-configuration