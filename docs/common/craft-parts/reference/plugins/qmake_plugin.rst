.. _craft_parts_qmake_plugin:

Qmake plugin
============

The qmake plugin configures projects using qmake_, and builds them
by processing the `project files`_ files to be run with using `GNU Make`_.

After a successful build, this plugin will install the generated
binaries in ``$CRAFT_PART_INSTALL``.

Keywords
--------

In addition to the common :ref:`plugin <part-properties-plugin>` and
:ref:`sources <part-properties-sources>` keywords, this plugin provides the following
plugin-specific keywords:

qmake-parameters
~~~~~~~~~~~~~~~~
**Type:** list of strings
**Default:** []

Parameters to configure the project using common qmake semantics.



qmake-project-file
~~~~~~~~~~~~~~~~~~
**Type:** string
**Default:** ""

The qmake project file to use. This is usually only needed if
qmake can not determine what project file to use on its own.

.. _qmake-major-version:

qmake-major-version
~~~~~~~~~~~~~~~~~~~
**Type:** int
**Default:** 5

Sets the Qt major version. The default is Qt 5, set to 6 for Qt 6 projects.


Environment variables
---------------------

The plugin sets the QT_SELECT environment variable to :ref:`qmake-major-version`.


Dependencies
------------

The qmake plugin needs the ``qmake`` executable to configure, and the
``make`` executable to build. These dependencies are provided by the
plugin as a ``build-packages`` entry.

The plugin also sets up ``g++``.  Other compiler or library
dependencies the source requires to build are to be provided.

How it works
------------

During the build step the plugin performs the following actions:

* Run ``qmake`` in the build directory to setup the ``Makefiles``, the
  project is configured with any ``qmake-parameters`` that might have
  been set. If ``qmake-project-file`` has been set, ``qmake`` refers to
  the defined file to configure the project;
* ``make`` is run to build the source;
* ``make`` calls the ``install`` target with ``DESTDIR`` set to
  ``$CRAFT_PART_INSTALL``.

Examples
--------

The following snippet declares a part using the ``qmake`` plugin for a
local source that contains a ``.pro`` project file. It specifies that the
major Qt version is 6, and that the project should be built with the Debug
configuration:

.. code-block:: yaml

    parts:
      hello:
        source: .
        plugin: qmake
        qmake-major-version: 6
        qmake-parameters:
          - "CONFIG+=debug"


.. _qmake: https://doc.qt.io/qt-6/qmake-manual.html
.. _project files: https://doc.qt.io/qt-6/qmake-project-files.html
.. _GNU Make: https://www.gnu.org/software/make/
