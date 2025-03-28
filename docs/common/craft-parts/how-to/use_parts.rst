.. _how-to-use-parts:

Using parts in a project file
=============================

When packing, :ref:`parts <parts>` are used to describe your package, where its various
components can be found, its build and run-time requirements, and its dependencies.
Consequently, all packages will have one or more parts.

.. _how-to-use-parts_details:

Parts are purposefully flexible to allow for varied and disparate sources. At its
simplest, a part will locate a project's source code and invoke a
:ref:`plugin <plugins>` to build the application in the environment. However, you can
just as easily use a part to source and extract a binary executable from an RPM file.
It can also download tagged code from a remote repository, pull in dependencies,
define a build order, or completely override any stage of the
:ref:`lifecycle <lifecycle>`.

.. _how-to-use-parts_defining:

Define a part
-------------

To define a part, give it a name and declare its keys. The rest of this section uses a
part that packs a "Hello, world!" shell script as an example.

First, create the shell script:

.. code:: shell

   echo "echo 'Hello, world!'" >> hello.sh

Next, create a simple part named my-part:

.. literalinclude:: code/use_parts.yaml
   :language: yaml
   :end-at: my-part:

This block starts the list of all parts in the project and declares the singular part
named my-part.

All parts need a plugin. Declare the part's plugin:

.. literalinclude:: code/use_parts.yaml
   :language: yaml
   :end-at: plugin: dump

The dump plugin is the simplest of all the plugins. It takes source files and copies
them directly into the staging directory of the project.

Next, give the plugin a source to copy:

.. literalinclude:: code/use_parts.yaml
   :language: yaml
   :end-at: source-type: file

With this, you have a complete part that packs the :file:`hello.sh` file into your
project's final artifact. For more information on keys available to use within a part,
see the :ref:`parts reference <part_properties>`.

