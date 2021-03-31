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

Application development
=======================

Public APIs
-----------

.. toctree::

   parts_steps

   actions

   infos

   lifecycle

   exceptions

Examples
--------


Craft-parts development
=======================

Internal APIs
-------------

.. toctree::

   sequencer

.. toctree::
   :caption: Reference:

   craft_parts

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
