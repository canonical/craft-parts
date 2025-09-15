.. Craft Parts documentation main file
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Craft Parts
===========

Craft Parts is a Python package to support a family of tools that create
standalone software packages for deployment on Linux-based systems.

Craft Parts provides a mechanism to obtain data from different sources,
process it in various ways, and prepare a filesystem subtree suitable for
deployment. The components used in its project specification are called
*parts*, which are independently downloaded, built and installed, but can
also depend on each other.

This package implements common functionality to prepare package data that
would otherwise be duplicated in separate tools.

Craft Parts is useful for implementers of packaging tools that share a
similar view of how data should be processed and prepared for deployment.

.. toctree::
   :maxdepth: 1
   :hidden:

   tutorials/index
   how-to/index
   reference/index
   explanation/index


.. list-table::

    * - | :ref:`Tutorial <tutorials>`
        | **Get started** with a hands-on introduction to Craft Parts
    * - | :ref:`How-to guides <how-to-guides>`
        | **Step-by-step guides** covering key operations and common tasks
    * - | :ref:`Reference <reference>`
        | **Technical information** about Craft Parts
    * - | :ref:`Explanation <explanation>`
        | **Discussion and clarification** of key topics

Project and community
---------------------

Craft Parts is a member of the Canonical family. It's an open source project
that warmly welcomes community projects, contributions, suggestions, fixes
and constructive feedback.

* `Ubuntu Code of Conduct <https://ubuntu.com/community/docs/ethos/code-of-conduct>`_
* `Canonical Contributor License Agreement
  <https://ubuntu.com/legal/contributors>`_
