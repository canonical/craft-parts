*******************
Project information
*******************

Project parameters are provided to callback functions by passing an
instance of the :class:`StepInfo <craft_parts.StepInfo>` class. It
consolidates properties from classes :class:`PartInfo <craft_parts.PartInfo>`,
:class:`ProjectInfo <craft_parts.ProjectInfo>` and
:class:`ProjectDirs <craft_parts.ProjectDirs>`, including custom
application-specific parameters passed as keyword arguments when
instantiating :class:`LifecycleManager <craft_parts.LifecycleManager>`.

.. autoclass:: craft_parts.ProjectDirs
   :members:

.. autoclass:: craft_parts.ProjectInfo
   :members:

.. autoclass:: craft_parts.PartInfo
   :members:

.. autoclass:: craft_parts.StepInfo
   :members:
