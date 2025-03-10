.. _how-to-use-parts:

Using parts in a project file
=============================

When packing, :ref:`parts <parts>` are used to describe your package, where its various
components can be found, its build and run-time requirements, and its dependencies.
Consequently, all packages will have one or more parts.

.. _how-to-use-parts_details:

Parts are purposefully flexible to allow for varied and disparate sources. At its
simplest, a part will locate a project's source code and invoke a
:ref:`plugin <plugins>` to build the application in the environment. However, a part
can just as easily be used to source and extract a binary executable from an RPM file.
It can also download tagged code from a remote repository, pull in dependencies,
define a build order, or completely override any stage of the
:ref:`lifecycle <lifecycle>`.

.. _how-to-use-parts_defining:

Defining a part
===============

Let's define a simple part that just packages a simple "hello world" shell script.

First, create the shell script:

.. code:: shell

   echo "echo 'Hello world!'" >> hello.sh

Next, create a simple part named my-part:

.. literalinclude:: code/use_parts.yaml
   :language: yaml
   :end-at: my-part:

This block does two things: it begins the list of all parts in the project, and then
declares a singular part named "my-part". However, in this form, the the part won't
do very much. Let's start by declaring a plugin:

.. literalinclude:: code/use_parts.yaml
   :language: yaml
   :end-at: plugin: dump

This "dump" plugin is quite simple - it simply takes the source and dumps it directly
into the staging directory of the project. So, next, you need to give it a source to
work with:

.. literalinclude:: code/use_parts.yaml
   :language: yaml
   :end-at: source-type: file

With this, you have a complete part that packs a :file:`hello.sh` into your project's
final artifact. For more information on keys available to use within a part, see the
:ref:`parts reference <part_properties>`.

