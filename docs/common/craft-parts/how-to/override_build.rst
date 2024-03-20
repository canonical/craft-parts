****************************
Overriding the default build
****************************

Craft-parts provides built-in :ref:`plugins <plugins>` for a number of
different programming languages, frameworks, and build tools. Since it's not
possible to support *every* possible configuration and scenario for each of
these technologies, each plugin emits a series of build commands to reproduce
what is most typically done for the given domain; for instance, the ``make``
plugin generates code that calls ``make; make install`` at build-time.

For cases where a given project being built does *not* follow the typical path,
craft-parts provides a way to declare the build commands for a specific part
via the :ref:`override_build` keyword.

Typical reasons for using ``override-build`` include:

* Having to run commands before or after the plugin's default commands;
* Building a project that uses a technology (programming language, framework, or
  build tool) that is not supported by craft-part's :ref:`default plugins <plugins>`;
* More generally, using the ``nil`` plugin (which has no default build
  commands).

Follow these steps to ensure a successful build, and see also a general
description of the :ref:`build_process`.

Determine that you *do* need to use ``override-build``
------------------------------------------------------

The default plugins strive to implement the most common build process for a
given technology but they typically also provide plugin-specific options that
allow some degree of customization. As some examples:

* The ``make`` plugin exposes the ``make-parameters`` option to allow passing
  parameters that might be specific to the project's ``Makefile``;
* The ``npm`` plugin exposes the ``npm_node_version`` option to select the
  specific version of ``npm`` that should be used during the build;
* The ``python`` plugin exposes the ``python-packages`` and ``python-requirements``
  options to declare specific packages and requirements files that should be used
  when creating the build's virtual environment.

See the documentation for the plugins that are relevant to your project to
determine whether the default process is suitable for you.

Ensure you place the built artefacts in the correct place
---------------------------------------------------------

The purpose of the Build step in the lifecycle is to generate software artefacts
to be included in the final payload. This is achieved by populating a special
"install" directory - the contents of this directory will then move forward to
the Stage and Prime lifecycle steps. A very common mistake when overriding a
part's Build is failing to place the created artefacts in the correct directory.

The location of the "install" directory is stored in the ``${CRAFT_PART_INSTALL}``
environment variable. This variable is set by craft-parts' tooling when calling
the script contained in ``override-build``. Therefore, in many cases the build
script can simply call the project's build tool with ``${CRAFT_PART_INSTALL}`` as
the output directory. Some examples:

* Go projects can use either ``-o "${CRAFT_PART_INSTALL}"`` or set ``GOBIN`` to
  ``${CRAFT_PART_INSTALL}/bin`` when calling ``go build`` or ``go install``. This
  is in part what the ``go`` plugin does;
* The ``dump`` plugin copies the entire ``source`` to the "install" dir. This is
  achieved by ``cp``'ing the contents of the source directory directly to
  ``${CRAFT_PART_INSTALL}``;
* The ``npm`` plugin sets the ``--prefix`` option of ``npm install`` to
  ``${CRAFT_PART_INSTALL}``;
* The ``make`` plugin sets the commonly-used ``DESTDIR`` variable to
  ``${CRAFT_PART_INSTALL}`` to ensure that ``make install`` places the built
  artefacts in the correct location.

The last example merits extra clarification: while ``DESTDIR`` is a widely-used
convention, it is by no means mandatory. Since Makefiles are fairly free-form and
can call arbitrary programs, it's crucial to inspect your project's specific
``Makefile`` to discover the option that it exposes to control where artefacts
will be placed when ``make install`` is called, and adjust the contents of the
``override-build`` script to reflect this. Failure to do so will frequently *not*
result in a build error because the artefacts will be installed in a standard
location like ``/usr/local`` *in the build system*, which is typically an LXD
instance or a Multipass VM.
