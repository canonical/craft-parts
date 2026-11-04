//! Shared helpers for declaring Rust submodules to be available as Python submodules.
//!
//! Workaround machinery for [PyO3#759](https://github.com/PyO3/pyo3/issues/759).

use anyhow::Result;
use pyo3::prelude::*;
use pyo3::types::PyModule;

/// Recursively register a module tree with Python's import machinery.
pub trait RegisterSubmodules {
    fn register_submodules(&self, name: &str) -> Result<()>;
}

impl RegisterSubmodules for Bound<'_, PyModule> {
    fn register_submodules(&self, name: &str) -> Result<()> {
        let sys_modules = self.py().import("sys")?.getattr("modules")?;
        register_recursive(self, name, &sys_modules)
    }
}

fn register_recursive(
    m: &Bound<'_, PyModule>,
    name: &str,
    sys_modules: &Bound<'_, PyAny>,
) -> Result<()> {
    let package = match name.rfind('.') {
        Some(idx) => &name[..idx],
        None => "",
    };

    m.setattr("__name__", name)?;
    m.setattr("__package__", package)?;
    sys_modules.set_item(name, m)?;

    for member in m.dir()? {
        let member = member.extract::<String>()?;

        // Skip dunder fields
        if member.starts_with("__") {
            continue;
        }

        let attr = m.getattr(&member)?;

        // If we're handling a submodule, then...
        if let Ok(submodule) = attr.cast::<PyModule>() {
            register_recursive(submodule, &format!("{name}.{member}"), sys_modules)?;
        } else {
            // PyO3 sets each pyfunction's __module__ to the bare rust module name at
            // build time; rewrite to the more familiar dotted Python module path.
            // Errors are ignored as some field types (e.g. consts) will refuse
            // assignment. We just wanna fixup what we can.
            let _ = attr.setattr("__module__", name);
        }
    }
    Ok(())
}
