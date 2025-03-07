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

A simple part that just packages a simple "hello world" shell script might look like
this:

.. code:: yaml

   parts:
     my-part:
       plugin: dump
       source: hello.sh
       source-type: file

A part starts with an arbitrary name, in this case, ``my-part``. They go under the
top-level ``parts`` key, which can contain as many parts as your package requires. In
this case, there is only one part.

Next, a source should be specified. The ``source`` key can dynamically handle many
kinds of inputs, such as tarballs, remote repositories, local directories, or Debian
packages. In this case, the source is just a single file.

Finally, a plugin should be specified. In this example, the ``dump`` plugin is used to
simply copy the content of :file:`hello.sh` into the final artifact. A plugin can
handle much more complex operations if desired though. For example, a plugin could
invoke an entire build system or create a workspace for offline builds.

For more information on keys available to use within a part, see the :ref:`parts
reference <part_properties>`.

