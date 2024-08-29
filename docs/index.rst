.. Craft Parts documentation main file
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

======================================
Welcome to Craft Parts' documentation!
======================================

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


.. grid:: 1 1 2 2

   .. grid-item-card:: :ref:`Tutorial <tutorial>`

      **Get started** with a hands-on introduction to Craft Parts

   .. grid-item-card:: :ref:`How-to guides <howto>`

      **Step-by-step guides** covering key operations and common tasks

.. grid:: 1 1 2 2
   :reverse:

   .. grid-item-card:: :ref:`Reference <reference>`

      **Technical information** about Craft Parts' components and modules

   .. grid-item-card:: :ref:`Explanation <explanation>`

      **Discussion and clarification** of key topics
