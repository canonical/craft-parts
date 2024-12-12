.. _how_to_create_plugin:

How to create a plugin
======================

Plugins help to bring new tools and programming languages into Craft Parts.
This document contains instructions on how to recreate the simple :ref:`dump
plugin <craft_parts_dump_plugin>`.


Create your plugin file
-----------------------

The first step in creating a plugin is deciding where it will live. If you're
adding a plugin directly to Craft Parts, then it should go in
:file:`craft_parts/plugins`. For re-creating the ``dump`` plugin, you can put
it in :file:`craft_parts/plugins/new_dump_plugin.py`.


Imports
~~~~~~~

First, there are a couple of imports from Craft Parts that need to be brought
in. At the top of your new file, import:

.. code:: python

  from .base import Plugin
  from .properties import PluginProperties


Define the properties class
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Next, design the plugin's interface. All plugins make use of a ``properties``
class to describe their interfaces. There are two required properties that all
plugins have in common, and you can add more to account for additional
behavior:

.. code:: python

  class NewDumpPluginProperties(PluginProperties, frozen=True):
      """The part properties used by the new dump plugin."""

      plugin: Literal["new-dump"] = "new-dump"
      source: str

Add the two required properties:

#. ``plugin`` is a constant string literal. This property represents the
   exposed name of your plugin. It will be invoked in user-facing tools and
   configuration, such as keys that select your plugin in a Snapcraft recipe.
#. ``source`` is a string. This property is the path to the working files of a
   part. It has specialised logic for different file types ranging from
   tarballs to Git repositories, so you can leverage it to get much broader
   functionality out of an otherwise simple plugin.

Add any additional custom properties your plugin needs. For example, a plugin
based on Java might have a unique property to specify the Java version, or a
Python-based plugin might have one to specify a requirements file.

The ``new-dump`` plugin will be quite simple, so it doesn't need custom
properties.


Create the plugin class
~~~~~~~~~~~~~~~~~~~~~~~

The plugin class itself contains the functionality of the plugin. Start by
declaring the properties class:

.. code:: python

    class NewDumpPlugin(Plugin):
        """Copy the content from the part source."""

        properties_class = NewDumpPluginProperties


Define the mandatory methods
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Next, you have to start defining the special methods that make this plugin
work. Since this is such a simple plugin, many of these methods are empty:

.. code:: py

    @override
    def get_build_snaps(self) -> set[str]:
        return set()

    @override
    def get_build_packages(self) -> set[str]:
        return set()

    @override
    def get_build_environment(self) -> dict[str, str]:
        return {}

    @override
    def get_pull_commands(self) -> list[str]:
        return []

All of these methods are used to define the build environment before the build
steps themselves are run.

:py:meth:`get_build_snaps`:
  This method should return a collection of all snap packages to be installed.
  For example, you can put ``go`` into the set to install the go compiler.

:py:meth:`get_build_packages`:
  This method should return a collection of all apt packages to be installed.
  For example, you can put ``libssl-dev`` into the set to install SSL headers
  through ``apt install``.

:py:meth:`get_build_environment`:
  This method should return a list of environment variables and the value they
  should be set to. For example, if you want to enable the run-time debug trace
  for Rust programs, you can put ``"RUST_BACKTRACE": "1"`` into the dict.

:py:meth:`get_pull_commands`:
  This method should return a list of commands to run. This function should be
  used for any functionality not achievable by any of the previous methods.

The last method that you have to define, however, is where the actual
:ref:`build commands <lifecycle>` are defined. These are the exact commands
executed by a subprocess during the build process, using the environment set up
by the previous methods.

.. code:: python

  @override
  def get_build_commands(self) -> list[str]:
      """Return a list of commands to run during the build step."""
      install_dir = self._part_info.part_install_dir
      return [f'cp --archive --link --no-dereference . "{install_dir}"']


Add it to the lifecycle manager
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now that you have your very own plugin, the last step is to make the lifecycle
manager aware of this plugin. Since you created your plugin directly in Craft
Parts, all that's needed is to add it to a dictionary in
:file:`craft_parts/plugins/plugins.py`:

.. code:: python

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
.. _Snapcraft recipe: https://snapcraft.io/docs/build-configuration
