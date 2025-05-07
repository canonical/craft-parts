.. |app| replace:: Craft Parts
.. |artifact| replace:: artifact
.. |artifact-indefinite| replace:: an artifact

Customise the build with craftctl
=================================

|app| ships with craftctl, a utility for executing steps in parts. When defining a part,
you can use it to customise the part's files and build environment before and after a
step.


Declare an override key
-----------------------

You can customise the lifecycle steps for any part in your |artifact|. Overriding the
step is achieved through the part ``override-*`` keys, which execute a scriptlet at that
step. The scriptlet is executed with ``/bin/bash``.

If an override key is declared at all, it entirely replaces the step's normal behavior.
Instead, whatever code in the key, even no code, is executed.

In the general case, you can override any step with this structure:

.. code-block:: yaml

    parts:
      <part-name>:
        override-<step>: |
          # Scriptlet code

Replace ``<step>`` with the name of a step in the lifecycle.


Override a step
---------------

Craftctl comes in most handy when when you need to tweak files or settings before or
after executing a step.

To specify where the regular step behavior occurs inside the scriptlet, call it with the
special ``craftctl default`` command. Using that command as an anchor point, alter the build files or environment with other commands before or after it.

.. admonition:: Don't forget to execute the step
    :class: caution

    If you don't call ``craftctl default`` inside a scriptlet, the step is skipped,
    and the part doesn't finish building.

Let's say you want to modify a file copied from a part's source. You would add an
override for the pull step with the ``override-pull`` key, run the default step with
craftctl, then change the copied source file.

The following example does just that. The icon path inside the part's desktop file in
the is tweaked after downloading it, but before |app| builds it.

.. code-block:: yaml

    parts:
      gnome-text-editor:
        source: https://gitlab.gnome.org/GNOME/gnome-text-editor
        override-pull: |
          craftctl default
          sed -i.bak -e 's|Icon=@app_id@$|Icon=snap.gnome-text-editor.icon|g' data/org.gnome.TextEditor.desktop


Override project variables
--------------------------

With craftctl, you can dynamically set project variables specific to |app| -- distinct
from environment variables -- within an override scriptlet. Set values with:

.. code-block:: bash

    craftctl set <key>=<value>

You can also retrieve the current value of a project key, with:

.. code-block:: bash

    craftctl get <key>

For example, if you want to set the ``version`` key of |artifact-indefinite| to the
latest Git tag in a part's source, declare this override:

.. code-block:: yaml
    :caption: Project file

    adopt-info: gnome-text-editor
    parts:
      gnome-text-editor:
        source: https://gitlab.gnome.org/GNOME/gnome-text-editor
        override-pull: |
          craftctl default
          craftctl set version=$(git describe --tags --abbrev=10)

For another example, let's say |artifact-indefinite| has a manually-set version number
in the project file. To append the latest Git commit hash to the version, declare this
override:

.. code-block:: yaml
    :caption: Project file

    version: "1.0"
    adopt-info: gnome-text-editor
    parts:
      gnome-text-editor:
        override-stage: |
          craftctl default
          craftctl set version="$(craftctl get version)-$(git rev-parse --short HEAD)"


Expose part variables in apps
-----------------------------

Apps can define project variables that can be read and
written during execution of user-defined scriptlets by using ``craftctl get``
and ``craftctl set``. Valid variables and their initial values must be
specified when creating the :class:`LifecycleManager <craft_parts.LifecycleManager>`,
and the variable value must be consumed by the app after the parts
lifecycle execution is finished::

  import yaml
  from craft_parts import LifecycleManager, Step
  
  parts_yaml = """
  parts:
    foo:
      plugin: nil
      override-pull: |
        echo "Running the pull step"
        craftctl set version="2"
  """
  
  parts = yaml.safe_load(parts_yaml)
  
  lcm = LifecycleManager(
    parts,
    app_name="example",
    cache_dir="."
    project_vars={"version": "1"}
  )
  actions = lcm.plan(Step.PRIME)
  with lcm.action_executor() as aex:
      aex.execute(actions)

  version = lf.project_info.get_project_variable("version")
  print(f"Version is {version}")

Execution of this example results in::

  + echo 'Running the pull step'
  Running the pull step
  + craftctl set version=2
  Version is 2

Note that project variables are not intended for use in logic
construction during parts processing, and each variable must not
be set more than once. Variable setting can also be restricted to
a specific part if ``project_vars_part_name`` is passed to
:class:`LifecycleManager <craft_parts.LifecycleManager>`.
