*****************************************
Adding parts processing to an application
*****************************************

A simple example
================

To add parts processing to an application, instantiate the
:class:`LifecycleManager <craft_parts.LifecycleManager>` class passing the
parts dictionary. Plan actions for the ``PRIME`` target step, and execute
them::

  import yaml
  from craft_parts import LifecycleManager, Step
  
  parts_yaml = """
  parts:
    hello:
      plugin: autotools
      source: https://ftp.gnu.org/gnu/hello/hello-2.10.tar.gz
      prime:
        - usr/local/bin/hello
        - usr/local/share/man/*
  """
  
  parts = yaml.safe_load(parts_yaml)
  
  lcm = LifecycleManager(parts, application_name="example", cache_dir=".")
  actions = lcm.plan(Step.PRIME)
  with lcm.action_executor() as aex:
      aex.execute(actions)
  
When executed, the lifecycle manager will download the tarball we specified,
unpack it, run its configuration script, compile the source code, install
the resulting artifacts, and extract only the files we want to deploy. The
final result is a subtree containing the files we wanted to prime::

  prime
  prime/usr
  prime/usr/local
  prime/usr/local/bin
  prime/usr/local/bin/hello
  prime/usr/local/share
  prime/usr/local/share/man
  prime/usr/local/share/man/man1
  prime/usr/local/share/man/man1/hello.1


Learning more
=============

- The :class:`LifecycleManager <craft_parts.LifecycleManager>` class offers many options to
  configure parts processing.

- The `CLI tool source code <https://github.com/canonical/craft-parts/blob/main/craft_parts/main.py>`_
  is a good reference for a real world usage of the lifecycle manager.

- Parts are similar to those used in Snapcraft, including some of its V2 plugins.
  See the `Snapcraft parts documentation <https://snapcraft.io/docs/adding-parts>`_
  for details.
