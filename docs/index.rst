.. Craft Parts documentation master file
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

======================================
Welcome to Craft Parts' documentation!
======================================

Craft Parts provides a mechanism to obtain data from different sources,
process it in various ways, and prepare a filesystem subtree suitable for
deployment. The components used in its project specification are called
*parts*, which can be independently downloaded, built and installed, and
also depend on each other in order to assemble the subtree containing the
final artifacts.

.. toctree::
   :caption: Getting started
   :maxdepth: 2

   examples

   cli_tool


.. toctree::
   :caption: Public API
   :maxdepth: 1

   lifecycle_manager

   parts_steps

   actions

   infos

   exceptions


.. toctree::
   :caption: Internals
   :maxdepth: 1

   lifecycle

   implementation

   reference

.. toctree::
   :caption: About the project

   changelog

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
