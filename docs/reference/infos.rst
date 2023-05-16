*******************
Project information
*******************

Project parameters are provided to callback functions by passing an
instance of the :class:`StepInfo <craft_parts.infos.StepInfo>` class.
It consolidates properties from the
:class:`PartInfo <craft_parts.infos.PartInfo>`,
:class:`ProjectInfo <craft_parts.infos.ProjectInfo>` and
:class:`ProjectDirs <craft_parts.infos.ProjectDirs>` classes, including custom
application-specific parameters passed as keyword arguments when
instantiating
:class:`LifecycleManager <craft_parts.lifecycle_manager.LifecycleManager>`.

.. autoclass:: craft_parts.infos.ProjectDirs
   :members:
   :noindex:

.. autoclass:: craft_parts.infos.ProjectInfo
   :members:
   :noindex:

.. autoclass:: craft_parts.infos.PartInfo
   :members:
   :noindex:

.. autoclass:: craft_parts.infos.StepInfo
   :members:
   :noindex:
