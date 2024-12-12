.. _how_to_add_a_source_handler:

How to add a custom source type to an application
=================================================

An application may need additional source types not included in craft-parts
by default. In this case, you can create and register a new non-default source
handler.

.. warning::
    New source handlers may be added in minor releases of craft-parts. If a
    custom source handler shares a ``source_type`` value with a new source
    handler, registering a custom source handler will override the existing
    source handler.

    Some source types are considered mandatory and cannot be overridden or
    unregistered. In a major release, the set of mandatory source types
    may change. At that point, an application-defined source type may not
    override the mandatory source type.


Write a new source handler
--------------------------

The first step in adding a new source handler is to write one. The components
of a source handler are its source model (a `Pydantic <https://pydantic.dev/>`_
model that defines the ``source-*`` keys that may be used in a part) and the
handler, a class that defines how the source type behaves during the ``PULL``
step.

The Pydantic model is a child class of
:py:class:`~craft_parts.sources.base.BaseSourceModel`. The only mandatory field
is :py:attr:`~craft_parts.sources.base.BaseSourceModel.source_type`.

.. literalinclude:: source-handler/rsync_source.py
    :language: python
    :pyobject: RsyncDirectorySourceModel

The :py:attr:`~craft_parts.sources.base.BaseSourceModel.pattern` attribute
allows Craft Parts to infer the source based on a regular expression. The first
source handler with a matching regular expression will be used, with built-in
source types matching before externally registered source types.

Once this is defined, a :py:class:`~craft_parts.sources.base.SourceHandler` is
needed to define the ``PULL`` behaviour of the source type.

.. literalinclude:: source-handler/rsync_source.py
    :language: python
    :pyobject: RsyncSource

.. note::
    Craft Parts does not install any required tools for custom source handlers.
    The handler in this example will fail on a machine that does not have
    `rsync <https://rsync.samba.org/>`_ installed before the part is pulled.


Register the source handler
---------------------------

Once created, a source must be registered to be used. This must occur before
entering the :py:class:`~craft_parts.executor.executor.ExecutionContext` with
the :py:class:`~craft_parts.lifecycle_manager.LifecycleManager`'s
:py:meth:`~craft_parts.lifecycle_manager.LifecycleManager.action_executor`
method.

.. literalinclude:: source-handler/rsync_source.py
    :language: python
    :start-after: # docs[register-source:start]
    :end-before: # docs[register-source:end]


Run the lifecycle
-----------------

With those steps completed, the new source handler is ready to use. A ``parts.yaml``
file such as the following will use the example rsync source type:

.. literalinclude:: source-handler/rsync_parts.yaml
    :language: yaml

After loading the parts into a YAML structure, all that's left is to run it:

.. literalinclude:: source-handler/rsync_source.py
    :language: python
    :start-after: # docs[run-lifecycle:start]
    :end-before: # docs[run-lifecycle:end]
