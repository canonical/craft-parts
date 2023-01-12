*******
Actions
*******

Actions are the execution units needed to move the project state to
a given step through the parts lifecycle. The action behavior is
determined by its action type.

.. autoclass:: craft_parts.ActionType
   :members:

   .. autoattribute:: RUN
   .. autoattribute:: RERUN
   .. autoattribute:: SKIP
   .. autoattribute:: UPDATE

.. autoclass:: craft_parts.Action
   :members:




