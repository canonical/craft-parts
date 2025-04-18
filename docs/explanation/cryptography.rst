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
generated using the sha1 algorithm from the `hashlib
<https://docs.python.org/3/library/hashlib.html>`_ library.

Downloading repositories
------------------------

For parts that source a git repository, `git <https://git-scm.com/>`_ is used to
clone the repository. Git uses SSH or HTTPS to communicate with the remote
repository, depending on the URL provided.

Downloading sources
-------------------

For parts that source a deb, rpm, snap, tar, zip, or 7z file, the files are
downloaded using the Requests library.

The integrity of these files can be verified using a
:ref:`checksum <source_checksum>`. The checksum is verified using hashlib, so all
`algorithms available
<https://docs.python.org/3/library/hashlib.html#hashlib.algorithms_available>`_
to the hashlib library can be used.

Downloading system packages
---------------------------

System dependencies are downloaded and verified using snapd,
`apt <https://wiki.debian.org/AptCLI>`_, `dnf <https://dnf.readthedocs.io>`_, and
`yum <http://yum.baseurl.org>`_.

Downloading build dependencies
------------------------------

:ref:`Plugins <plugins>` use build tools to download and verify build dependencies.
Some plugins can provision their own build tools, while others require the build
tools to be available on the system. The table below summarizes how plugins provision
build tools and which build tools are used to download and verify dependencies.

.. list-table::
  :header-rows: 1

  * - Plugin
    - Method of provisioning the build tools
    - Build tools used

  * - :ref:`Cargo Use <craft_parts_cargo_use_plugin>`

      :ref:`Rust <craft_parts_rust_plugin>`
    - `rustup <https://rustup.rs>`_
    - `Cargo <https://doc.rust-lang.org/stable/cargo/>`_

  * - :ref:`dotnet <craft_parts_dotnet_plugin>`
    - not provisioned
    - `dotnet SDK <https://dotnet.microsoft.com>`_

  * - :ref:`Go <craft_parts_go_plugin>`

      :ref:`Go Use <craft_parts_go_use_plugin>`
    - not provisioned
    - `Go toolchain <https://go.dev/ref/mod>`_

  * - :ref:`Maven <craft_parts_maven_plugin>`
    - not provisioned
    - `Maven <https://maven.apache.org>`_

  * - :ref:`Meson <craft_parts_meson_plugin>`
    - not provisioned
    - `Meson <https://mesonbuild.com>`_

  * - :ref:`NPM <craft_parts_npm_plugin>`
    - Requests library and `curl <https://curl.se/>`_
    - `npm <https://www.npmjs.com/>`_

  * - :ref:`Poetry <craft_parts_poetry_plugin>`
    - not provisioned
    - `Poetry <https://python-poetry.org>`_

  * - :ref:`Python <craft_parts_python_plugin>`
    - not provisioned
    - `pip <https://pip.pypa.io>`_

  * - :ref:`uv <craft_parts_uv_plugin>`
    - not provisioned
    - `uv <https://docs.astral.sh/uv>`_
