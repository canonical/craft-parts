********************
Implementation notes
********************

Class layout
------------

The implementation reflects the two main lifecycle processing operations. All
planning is done by the :class:`Sequencer <craft_parts.sequencer.Sequencer>` class
based on the parts definition and existing state loaded from disk. Execution of planned
actions is handled by the :class:`Executor <craft_parts.executor.executor.Executor>`
class.

.. image:: /common/craft-parts/images/class_diagram.png
