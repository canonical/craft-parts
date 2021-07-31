***************
Parts and Steps
***************

Parts and steps are the basic data types craft-parts will work with.
Together, they define the lifecycle of a project (i.e. how to process
each step of each part in order to obtain the final primed result).

Parts
-----

When the :class:`LifecycleManager <craft_parts.LifecycleManager>` is
invoked, parts are defined in a dictionary under the ``parts`` key.
If the dictionary contains other keys, they will be ignored.


Steps
-----

Steps are used to establish plan targets and in informational data
structures such as :class:`StepInfo <craft_parts.StepInfo>`. They are
defined by the :class:`Step <craft_parts.Step>` enumeration, containing
entries for the lifecycle steps ``PULL``, ``BUILD``, ``STAGE``, and
``PRIME``.

