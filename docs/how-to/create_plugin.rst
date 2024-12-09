.. _how_to_create_plugin:

How to create a plugin
======================

Plugins help to bring new tools and programming languages into craft-parts.
This document contains instructions on how to recreate the simple
:py:class:`~craft-parts.plugins.dump_plugin.DumpPlugin` plugin.

A plugin is made up of two major components: its properties and its
functionality. The properties of a plugin are the unique pieces of
configuration that make up the user interface of the plugin. These include
things like specifying a Python version to use in a Python-based plugin, or
the authentication scheme to use to connect to a remote server - it all
depends on what your plugin does, and what it needs to do its job! The
functionality of the plugin is the Python code that makes up its actual
execution. The functionality of the plugin should take in configuration from
the plugin's properties.

Create your plugin file
-----------------------
The first step in creating a plugin is deciding where it will live. If you're
adding a plugin directly to ``craft-parts``, then it should go in
:file:`craft_parts/plugins`. Since we're re-creating the ``dump`` plugin,
we'll put it in :file:`craft_parts/plugins/new_dump_plugin.py`.

Imports
~~~~~~~
First, we'll have to pull in our imports. Since this is such a simple plugin,
the list of necessary imports is quite small:

.. code:: py

    from typing import Literal
    from overrides import override

    from .base import Plugin
    from .properties import PluginProperties

Defining a properties class
~~~~~~~~~~~~~~~~~~~~~~~~~~~
All plugins make use of a "properties" class to describe their unique parameters.
The dump class is very basic, so we only need to define the required parameters:

.. code:: py

    class NewDumpPluginProperties(PluginProperties, frozen=True):
        """The part properties used by the new dump plugin."""

        # The human-friendly name of the plugin
        plugin: Literal["new-dump"] = "new-dump"
        # The "source" parameter is special - we'll talk about it more soon.
        source: str

Creating the plugin class
~~~~~~~~~~~~~~~~~~~~~~~~~
The plugin class itself contains the functionality of the plugin. Start by
declaring the properties class:

.. code:: py

    class NewDumpPlugin(Plugin):
        """Copy the content from the part source."""
        
        properties_class = NewDumpPluginProperties
    
Next, we'll have to start defining the special methods that make this plugin
"work". Since this is such a simple plugin, many of these methods are empty:

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

The last method that we have to define, however, is where the actual build
commands are defined. These are the exact commands executed by a subprocess
during the build process:

.. code:: py

    @override
    def get_build_commands(self) -> list[str]:
        """Return a list of commands to run during the build step."""
        install_dir = self._part_info.part_install_dir
        return [f'cp --archive --link --no-dereference . "{install_dir}"']

Notice we don't require a user-provided source directory/file - this is because
we let the ``source`` parameter do the heavy-lifting. The source parameter is a
mandatory parameter that specifies the working files of a part. It has a lot of
specialised logic for different file types ranging from tar files to git
repositories, so we can leverage that to get much stronger functionality out of
our otherwise simple plugin.

Final steps
~~~~~~~~~~~
Now that we have our very own plugin, the last step is to make the lifecycle
manager aware of this plugin. Since we created our plugin directly in
``craft-parts``, all that's needed is to add it to a dictionary in
:file:`craft_parts/plugins/plugins.py`:

.. code:: py

    from .new_dump_plugin import NewDumpPlugin

    # ...

    _BUILTIN_PLUGINS: dict[str, PluginType] = {
        # ...
        "new-dump": NewDumpPlugin,
    }
