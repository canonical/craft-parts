.. _explanation_cryptographic-technology:

Cryptographic technology in Craft Parts
=======================================

Craft Parts uses cryptographic technologies to obtain and process data from remote
sources. It does not directly implement its own cryptography, but it does depend
on external libraries to do so.

Communication with local processes
----------------------------------

Craft Parts uses the `Requests <https://requests.readthedocs.io/en/latest/>`_ and
`requests-unixsockets2 <https://gitlab.com/thelabnyc/requests-unixsocket2>`_
libraries to communicate over Unix sockets with the local `snap daemon (snapd)
<https://snapcraft.io/docs/installing-snapd>`_. These requests are used to
fetch information about required snaps. If the snap is missing, Craft
Parts will install it through snapd. This is done by querying the `snapd
API <https://snapcraft.io/docs/snapd-api>`_ with URLs built dynamically and
sanitized by `urllib <https://docs.python.org/3/library/urllib.html>`_.

Overlays
--------

When :ref:`overlays <overlays>` are enabled, Craft Parts calculates a checksum
for each part's overlay layer to track when changes are made. The checksums are
generated using the SHA1 algorithm from the `hashlib
<https://docs.python.org/3/library/hashlib.html>`_ library.

Sources
-------

Downloading repositories
~~~~~~~~~~~~~~~~~~~~~~~~

When a part sources a remote Git repository, Craft Parts uses `Git
<https://git-scm.com/>`_ to clone it. Depending on the URL provided, Git uses either SSH
or HTTPS as the secure communication protocol.

Downloading source files
~~~~~~~~~~~~~~~~~~~~~~~~

When a part sources a ``.deb``, ``.rpm``, ``.snap``, ``.tar``, ``.zip``, or ``.7z``
file, Craft Parts calls the Requests library to download it.

The integrity of these files can be verified using a :ref:`checksum
<reference-part-properties-source-checksum>`. The checksum is verified using hashlib, so
all `algorithms available to the hashlib library
<https://docs.python.org/3/library/hashlib.html#hashlib.algorithms_available>`_ can be
used.

Dependencies
------------

Downloading system packages
~~~~~~~~~~~~~~~~~~~~~~~~~~~

System dependencies are downloaded and verified using snapd,
`Apt <https://wiki.debian.org/AptCLI>`_, `DNF <https://dnf.readthedocs.io>`_, and
`Yum <http://yum.baseurl.org>`_.

Downloading build dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:ref:`Plugins <plugins>` use build tools to download and verify build dependencies.
Some plugins can provision their own build tools, while others require the build
tools to be available on the system. The table below summarizes how plugins provision
build tools and which build tools are used to download and verify dependencies.

.. list-table::
  :header-rows: 1

  * - Plugin
    - Build tools used
    - Method of provisioning the build tools

  * - :ref:`Cargo Use <craft_parts_cargo_use_plugin>`

      :ref:`Rust <craft_parts_rust_plugin>`
    - `Cargo <https://doc.rust-lang.org/stable/cargo/>`_
    - `rustup <https://rustup.rs>`_

  * - :ref:`dotnet <craft_parts_dotnet_plugin>`
    - `dotnet SDK <https://dotnet.microsoft.com>`_
    - not provisioned

  * - :ref:`Go <craft_parts_go_plugin>`

      :ref:`Go Use <craft_parts_go_use_plugin>`
    - `Go toolchain <https://go.dev/ref/mod>`_
    - not provisioned

  * - :ref:`Maven <craft_parts_maven_plugin>`
    - `Maven <https://maven.apache.org>`_
    - not provisioned

  * - :ref:`Meson <craft_parts_meson_plugin>`
    - `Meson <https://mesonbuild.com>`_
    - not provisioned

  * - :ref:`NPM <craft_parts_npm_plugin>`
    - `npm <https://www.npmjs.com/>`_
    - Requests library and `curl <https://curl.se/>`_

  * - :ref:`Poetry <craft_parts_poetry_plugin>`
    - `Poetry <https://python-poetry.org>`_
    - not provisioned

  * - :ref:`Python <craft_parts_python_plugin>`
    - `pip <https://pip.pypa.io>`_
    - not provisioned

  * - :ref:`uv <craft_parts_uv_plugin>`
    - `uv <https://docs.astral.sh/uv>`_
    - not provisioned
