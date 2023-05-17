*******
Actions
*******

Actions are the execution units needed to move the project state to
a given step through the parts lifecycle. The action behavior is
determined by its action type.

.. autoclass:: craft_parts.actions.ActionType
   :members:
   :noindex:

   .. autoattribute:: RUN
      :noindex:
   .. autoattribute:: RERUN
      :noindex:
   .. autoattribute:: SKIP
      :noindex:
   .. autoattribute:: UPDATE
      :noindex:

.. autoclass:: craft_parts.actions.Action
   :members:
   :noindex:
