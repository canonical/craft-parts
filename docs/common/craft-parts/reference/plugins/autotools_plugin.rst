.. _craft_parts_autotools_plugin:

Autotools plugin
================

The plugin makes use of the following tools:

* Autogen_
* Autoconf_
* Automake_
* `GNU Make`_

The Autotools plugin builds using the ``./configure``, ``make`` and ``make install``
sequence seen in most GNU projects.

After a successful build, this plugin will install the generated binaries in
``$CRAFT_PART_INSTALL``.

Keywords
--------

In addition to the common :ref:`plugin <part-properties-plugin>` and
:ref:`sources <part-properties-sources>` keywords, this plugin provides the following
plugin-specific keywords:

autotools-bootstrap-parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Type:** list of strings
**Default:** []

Bootstrap flags to pass to the build if a bootstrap file is found in
the project. These can in some cases be seen by running ``./bootstrap
--help``.

autotools-configure-parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Type:** list of strings
**Default:** []

configure flags to pass to the build such as those shown by running
``./configure --help``.

Environment variables
---------------------

The plugin does not set any environment variables.

Dependencies
------------

The Autotools plugin needs the ``autoconf``, ``automake``, ``make``,
``autopoint`` and ``libtool`` executables to work.  These are provided
by the plugin as a ``build-packages`` entry.

The plugin also sets up ``gcc`` as it is the most commonly used
compiler for an Autotools based project.  Other compiler or library
dependencies the source requires to build are to be provided.

How it works
------------

During the build step the plugin performs the following actions:

* If the source does not provide a ``configure`` file, one will be
  generated through the following options:
  
  1. If an ``autogen.sh`` file is found in the sources it will be run
     with ``NOCONFIGURE`` set to generate a ``configure`` file;
  2. Alternatively, if a ``bootstrap`` file is found in the sources,
     it will run the ``bootstrap`` with any set
     ``autotools-bootstrap-parameters`` without *configuring* the
     project;
     
* Call ``configure`` with any set ``autotools-configure-parameters``;
* Call ``make`` to build;
* Call ``make install`` with ``DESTDIR`` set to ``$CRAFT_PART_INSTALL``.

Examples
--------

The following snippet declares a part using the ``autotools``
plugin. It sets GNU Hello as a source, which has a ``bootstrap``
file. To setup the ``configure`` file to not care for translations
``autotools-bootstrap-parameters`` is using the project's option
``--skip-po``. During ``configure`` the installation ``--prefix`` is
set to ``/usr`` with ``autotools-configure-parameters``.

The source also requires the following packages to correctly build:
``git``, ``gperf``, ``help2man`` and texinfo.

.. code-block:: yaml

    parts:
      hello:
        source: https://git.savannah.gnu.org/git/hello.git
        plugin: autotools
        autotools-bootstrap-parameters:
          - --skip-po
        autotools-configure-parameters:
          - --prefix=/usr/
        build-packages:
          - git
          - gperf
          - help2man
          - texinfo


.. _Autogen: https://www.gnu.org/software/autogen/
.. _Autoconf: https://www.gnu.org/software/autoconf/
.. _Automake: https://www.gnu.org/software/automake/
.. _GNU Make: https://www.gnu.org/software/make/
