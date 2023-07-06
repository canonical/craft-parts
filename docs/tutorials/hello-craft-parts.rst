*****************
Hello craft-parts
*****************

In this tutorial, you will build a parts-based project from scratch, using only
a text editor, a terminal, and the ``craft-parts`` command line.

Prerequisites
-------------
- a text editor
- ``craft-parts`` installed in a Python virtual environment
- a terminal with that virtual environment activated.

Basic Parts File
----------------

Create a directory. Put the following text into a file called ``parts.yaml``:

.. literalinclude:: code/hello-craft-parts/parts-empty.yaml
    :language: yaml


Craft the Parts
===============

Now that you have a very basic ``parts.yaml`` file, it's time to build the
package. To begin with, examine what ``craft-parts`` plans to do without
actually doing any of it:

.. literalinclude:: code/hello-craft-parts/task.yaml
    :language: bash
    :start-after: [docs:first-dry-run]
    :end-before: [docs:first-dry-run-end]
    :dedent: 2

The output should be each of the :ref:`crafting steps <craft_parts_steps>`
on the ``hello`` part, in order:

.. code-block:: text

    Pull hello
    Overlay hello
    Build hello
    Stage hello
    Prime hello

Now, run the full lifecycle:

.. literalinclude:: code/hello-craft-parts/task.yaml
    :language: bash
    :start-after: [docs:first-real-run]
    :end-before: [docs:first-real-run-end]
    :dedent: 2

This will take a bit longer, but the output will be similar, with the notable
exception that ``craft-parts`` will tell you that it's actually executing
the steps.

.. code-block:: text

    Execute: Pull hello
    Execute: Overlay hello
    Execute: Build hello
    Execute: Stage hello
    Execute: Prime hello

You've done it! You've built a ``craft-parts`` project! The full directory
structure will now be set up. Check it with:

.. literalinclude:: code/hello-craft-parts/task.yaml
    :language: bash
    :start-after: [docs:find-directory-structure]
    :end-before: [docs:find-directory-structure-end]
    :dedent: 2

and see the newly created files and directories.

.. code-block:: text

    .
    ./prime
    ./stage
    ./parts
    ./parts/hello
    ./parts/hello/build
    ./parts/hello/install
    ./parts/hello/src
    ./parts/hello/run
    ./parts/hello/run/environment.sh
    ./parts/hello/run/build.sh
    ./parts/hello/state
    ./parts/hello/state/prime
    ./parts/hello/state/build
    ./parts/hello/state/stage
    ./parts/hello/state/overlay
    ./parts/hello/state/layer_hash
    ./parts/hello/state/pull
    ./parts/hello/layer
    ./parts.yaml

Say Hello
=========

This project isn't very useful, given that it's empty, but it has each of
the important elements. Let's expand on it a bit. Add two more lines to
``parts.yaml`` so it looks as follows:

.. literalinclude:: code/hello-craft-parts/parts-pull.yaml
    :language: yaml
    :emphasize-lines: 4-5

In the same directory, create a small shell script called ``hello.sh`` with
the following contents:

.. literalinclude:: code/hello-craft-parts/hello.sh
    :language: bash

Save your files and re-run ``craft-parts``. The changes will cause it to pull
the part again, which will lead to the re-run of each step in order.

.. literalinclude:: code/hello-craft-parts/task.yaml
    :language: bash
    :start-after: [docs:first-real-run]
    :end-before: [docs:first-real-run-end]
    :dedent: 2

.. code-block:: text
    :emphasize-lines: 1

    Execute: Repull hello (properties changed)
    Execute: Overlay hello
    Execute: Build hello
    Execute: Stage hello
    Execute: Prime hello

What does this mean in practice? It means that there is now a copy of
``hello.sh`` in ``parts/hello/src``, ready to be used as the source code for
your parts project. But it's a bash script, so it's not only the source of the
project, but the output too. Since we don't need to do any fancy filesystem
work, we can skip the ``overlay`` step and go straight to ``build``.

Time to build
=============

While by default the ``nil`` plugin doesn't do anything during the build step,
we're going to "build" the project by copying the script to the install
directory, where the ``STAGE`` step will read from. The location of the install
directory is in the ``$CRAFT_PART_INSTALL`` environment variable. During each
step, several ``CRAFT_*`` :ref:`variables <craft_parts_step_execution_environment>`
are added to the environment. Add an ``override-build`` step to ``parts.yaml``:

.. literalinclude:: code/hello-craft-parts/parts.yaml
    :language: yaml
    :emphasize-lines: 6-9

Running ``craft-parts`` with the ``--verbose`` flag:

.. literalinclude:: code/hello-craft-parts/task.yaml
    :language: bash
    :start-after: [docs:run-verbose]
    :end-before: [docs:run-verbose-end]
    :dedent: 2

will output not just which steps ``craft-parts`` executes, but what commands
it runs along the way:

.. code-block:: text

    Execute: Rebuild hello ('override-build' property changed)
    + pwd
    /home/ubuntu/hello-craft-parts/parts/hello/build
    + cp hello.sh /home/ubuntu/hello-craft-parts/parts/hello/install/hello
    Execute: Stage hello
    Execute: Prime hello

Late Stage
==========

At this point, ``craft-parts`` takes over, automatically staging and priming
the ``hello`` script for us. A ``part`` that's missing its ``stage``
and ``prime`` sections will have the entire contents of the ``install``
directory copied along at each stage. It is functionally equivalent to:

.. literalinclude:: code/hello-craft-parts/parts-stage-prime.yaml
    :language: yaml
    :emphasize-lines: 10-13

And so, at long last, we have a fully ``primed`` and functional ``craft-parts``
project. And with that, it's time to enter the ``prime`` directory and
run our program:

.. literalinclude:: code/hello-craft-parts/task.yaml
    :language: bash
    :start-after: [docs:execute-part]
    :end-before: [docs:execute-part-end]
    :dedent: 2

.. code-block:: text

    Hello craft-parts!

Hello craft-parts, indeed.
