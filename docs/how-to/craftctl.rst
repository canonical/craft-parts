*****************
The craftctl tool
*****************

Craft-parts installs the ``craftctl`` utility executable. It is
intended to be invoked from user-defined scriptlets in parts
to call the built-in handler for a given step or to manipulate
application-defined variables.

Calling default step handlers
=============================

Use ``craftctl default`` from within a overridden step scriptlet
to execute the built-in handler for the step being processed::

  import yaml
  from craft_parts import LifecycleManager, Step
  
  parts_yaml = """
  parts:
    hello:
      plugin: autotools
      source: https://ftp.gnu.org/gnu/hello/hello-2.10.tar.gz
      override-build: |
        echo "Running the build step"
        craftctl default
  """
  
  parts = yaml.safe_load(parts_yaml)
  
  lcm = LifecycleManager(parts, application_name="example", cache_dir=".")
  actions = lcm.plan(Step.PRIME)
  with lcm.action_executor() as aex:
      aex.execute(actions)

This example will result in the message being displayed, and the
part source being built::

  + echo 'Running the build step'
  Running the build step
  + craftctl default
  + '[' '!' -f ./configure ']'
  + '[' '!' -f ./configure ']'
  + '[' '!' -f ./configure ']'
  + ./configure
  checking for a BSD-compatible install... /usr/bin/install -c
  checking whether build environment is sane... yes
  checking for a thread-safe mkdir -p... /bin/mkdir -p
  ...


Using application variables
===========================

The application can define project variables that can be read and
written during execution of user-defined scriptlets by using ``craftctl get``
and ``craftctl set``. Valid variables and their initial values must be
specified when creating the :class:`LifecycleManager <craft_parts.LifecycleManager>`,
and the variable value must be consumed by the application after the parts
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
    application_name="example",
    cache_dir="."
    project_vars={"version": "1"}
  )
  actions = lcm.plan(Step.PRIME)
  with lcm.action_executor() as aex:
      aex.execute(actions)

  version = lf.project_info.get_project_variable("version")
  print(f"Version is version")

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
