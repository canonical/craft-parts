***************
Parts and Steps
***************

Parts and steps are the basic data types craft-parts will work with.
Together, they define the lifecycle of a project (i.e. how to process
each step of each part in order to obtain the final primed result).

Parts
=====

When the :class:`LifecycleManager <craft_parts.LifecycleManager>` is
invoked, parts are defined in a dictionary under the ``parts`` key.
If the dictionary contains other keys, they will be ignored.


Permissions
-----------

Parts can declare read/write/execute permissions and ownership for the
files they produce. This is achieved by adding a ``permissions`` subkey
in the specific part:

.. code-block:: yaml

    # ...
    parts:
      my-part:
        # ...
        permissions:
          - path: bin/my-binary
            owner: 1111
            group: 2222
            mode: "755"

The ``permissions`` subkey is a list of permissions definitions, each
with the following keys:

* ``path``: a string describing the file(s) and dir(s) that this definition
  applies to. The path should be relative, and supports wildcards. This field
  is *optional* and its absence is equivalent to ``"*"``, meaning that the
  definition applies to all files produced by the part;
* ``owner``: an integer describing the numerical id of the owner of the files.
  This field is *optional* in the general case but *mandatory* if ``group``
  is specified;
* ``group``: an integer describing the numerical id of the group for the files.
  The semantics are otherwise the same as ``owner``, including being *optional*
  in the general case and *mandatory* if ``owner`` is specified;
* ``mode``:  string describing the desired permissions for the files as a number
  in base 8. This field is *optional*.


.. _craft_parts_steps:

Steps
=====

Steps are used to establish plan targets and in informational data
structures such as :class:`StepInfo <craft_parts.StepInfo>`. They are
defined by the :class:`Step <craft_parts.Step>` enumeration, containing
entries for the lifecycle steps ``PULL``, ``OVERLAY``, ``BUILD``,
``STAGE``, and ``PRIME``.
