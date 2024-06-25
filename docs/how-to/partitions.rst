******************************************
Adding partition support to an application
******************************************

Partitions basics
=================

In the below examples, we work with three partitions: ``default``, ``kernel``, and ``bar-baz``.  The ``default`` and ``kernel`` partitions do not have a namespace.  The ``bar-baz`` partition is part of the ``component`` namespace.

``default`` must always be the first listed partition.

Partition names and namespace names must consist of `only` lower-case alphabetic characters, unless a partition exists under a namespace, in which case it may also contain hyphen characters, though the first and last characters must still be alphabetic.

.. _app_changes:

Required application changes
============================

To add partition support to an application, two basic changes are needed to the ``craft-application``.

#. Enable the feature

   When creating the :class:`AppMetadata <craft_application.AppMetadata>`, specify that the application will use the partitions feature::

     from craft_application import AppMetadata, AppFeatures

     APP_METADATA = AppMetadata(
       ...
       features=AppFeatures(enable_partitions=True),
     )

#. Define the list of partitions

   We need to tell the :class:`LifecycleManager <craft_parts.LifecycleManager>` class about our partitions, but applications do not usually directly instantiate the LifecycleManager.

   Inside your :class:`Application <craft_application.Application>` class, the :class:`ServiceFactory <craft_application.ServiceFactory>` can be told to instantiate the :class:`LifecycleService <craft_application.LifecycleService` with specific ``custom_args`` by calling ``set_kwargs``.

   Override the ``_configure_services`` method, and use ``set_kwargs`` to define the partitions that will eventually be passed to the :class:`LifecycleManager <craft_parts.LifecycleManager>`::

     @override
     def _configure_services(self, provider_name: str | None) -> None:
       super()._configure_services(provider_name)

       ...

       self.services.set_kwargs(
         "lifecycle",
         ...
         partitions=["default", "kernel", "component/bar-baz"],
       )

Using the partitions
====================

Partitions cannot be used until `after you have configured your application <#app-changes>`_.

In configuration yaml lifecycle
-------------------------------

Defined partitions may be referenced in the ``organize``, ``stage``, and ``prime`` sections of your configuration yaml files::

  organize:
    <source-path>: (<partition>)/<path>
  stage:
    - (<partition>)/<path>
  prime:
    - (<partition>)/<path>

Paths in the configuration yaml not beginning with a partition label will implicitly use the default partition.

The source path of an ``organize`` entry can only be from the default partition.  For example::

  organize:
    (kernel)/usr/local/bin/hello: bin/hello

  Cannot organize files from 'kernel' partition.
  Files can only be organized from the 'default' partition

When the ``stage`` and ``prime`` keywords are not provided for a part, craft-parts' default behavior is to stage and prime all files for the part in all partitions.

(If a stage or prime filter `is` applied to a partition, the default behavior will not be affected for the other partitions.)

In environment variables
------------------------

Environment variables are created containing the namespace and partition name, formatted as ``$CRAFT_[<namespace>_]<partition>_{STAGE|PRIME}``.

From the previous example, these variables would be available::

  $CRAFT_STAGE                   -> stage
  $CRAFT_DEFAULT_STAGE           -> stage
  $CRAFT_KERNEL_STAGE            -> partitions/kernel/stage
  $CRAFT_COMPONENT_BAR_BAZ_STAGE -> partitions/component/bar-baz/stage

  $CRAFT_PRIME                   -> prime
  $CRAFT_DEFAULT_PRIME           -> prime
  $CRAFT_KERNEL_PRIME            -> partitions/kernel/prime
  $CRAFT_COMPONENT_BAR_BAZ_PRIME -> partitions/component/bar-baz/prime

(Note that the hyphen in the partition ``component/bar-baz`` is converted to an underscore in the corresponding variable name.)

You might use these variables in a lifecycle override section of a configuration yaml.  For instance::

  ...
  prime-override: |
    cp -R $CRAFT_KERNEL_STAGE/vmlinux $CRAFT_KERNEL_PRIME/
    chmod -R 444 $CRAFT_KERNEL_PRIME/*
    cp -R $CRAFT_STAGE/lib/modules/6.x/* $CRAFT_PRIME
    chmod -R 600 $CRAFT_PRIME/*

From code
---------

Application code that can access ``Part`` or ``ProjectDirs`` objects may get partition information from them::

  >>> Part(name="my-part").part_install_dirs["kernel"]
  Path("partitions/kernel/parts/my-part/install")

  >>> ProjectDirs.get_stage_dir(partition="kernel")
  Path("/root/partitions/kernel/stage")

  >>> ProjectDirs.get_prime_dir(partition="component/bar-baz")
  Path("/root/partitions/component/bar-baz/prime")
