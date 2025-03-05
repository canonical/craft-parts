.. _how-to-use-parts:

Using parts in a project file
=============================

When packing, :ref:`parts <parts>` are used to describe your package, where its various
components can be found, its build and run-time requirements, and its dependencies.
Consequently, all package will have one or more parts.

.. _how-to-use-parts_details:

Parts are purposefully flexible to allow for varied and disparate sources. At its
simplest, a part will locate a project's source code and invoke a
:ref:`plugin <plugins>` to build the application in the environment. However, a part
can just as easily be used to source and extract a binary executable from an RPM file.
They can also download tagged code from a remote repository, pull in dependencies,
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

A part starts with an arbitrary name, in this case, ``my-part``. They always will go
under the top-level ``parts`` key, which can contain as many parts as your application
requires. In this case, there is only one part.

Next, a source should be specified. The ``source`` key can dynamically handle many
kinds of inputs, such as tarballs, remote repositories, local directories, or Debian
packages. In this case, the source is just a single file.

Finally, a plugin should be specified. In this example, the ``dump`` plugin is used to
simply copy the content of :file:`hello.sh` into the final artifact. A plugin can
handle much more complex operations if desired though. For example, a plugin could
invoke an entire build system or create a workspace for offline builds.

.. _how-to-use-parts_keys-intro:

Common keywords
---------------

A typical part may also commonly make use of the following keys.

.. _how-to-use-parts_keys-list:

build-packages
~~~~~~~~~~~~~~
**Type**: List of strings

**Example**: ``[pkg-config, libncursesw5-dev, sed]``

A list of packages to install during build time using the build host's package manager,
such as *apt* or *dnf*.

stage-packages
~~~~~~~~~~~~~~
**Type**: List of strings

**Example**: ``[gnome-themes-standard, libncursesw5, dbus]``

A list of packages to include in the final artifact using the build host's package
manager, such as *apt* or *dnf*.

build-snaps
~~~~~~~~~~~
**Type**: List of strings

**Example**: ``[go/1.16/stable, kde-frameworks-5-core18-sdk]``

A list of ``snap`` packages to install during build time. Snap names can include
`tracks and channels`_.

stage-snaps
~~~~~~~~~~~
**Type**: List of strings

**Example**: ``[ffmpeg-sdk-gplv3, codium/latest/stable]``

A list of ``snap`` packages to include in the final artifact. Snap names can include
`tracks and channels`_.

plugin
~~~~~~
**Type**: String

**Examples**: ``make``, ``go``, ``uv``

The plugin to use with the part. A plugin will often add, and perhaps require, its own
additional keys. Check the documentation for each plugin to find out more about these
keys.

source
~~~~~~
**Type**: File path or URL

**Examples**: ``.``, ``https://github.com/snapcrafters/discord``, ``gnu-hello.tar.gz``

The location of the file(s) needed to build your part. It can refer to a single file,
a directory tree, a compressed archive, or a revision control repository.

.. _how-to-use-parts_end:

.. _tracks and channels: https://snapcraft.io/docs/channels
