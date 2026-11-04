//! Rust extensions for Craft Parts.
//!
//! Compiled to `craft_parts._rs`. These symbols must be re-exported as
//! public for downstream consumers.

use pyo3::prelude::*;

mod errors;
mod register_submodules;

#[pymodule(name = "_rs")]
mod rs {
    use anyhow::Result;

    use super::*;

    #[pymodule_export]
    use crate::errors::errors;

    /// The package version, derived from `git describe` at compile time.
    #[pyfunction(name = "_get_craft_parts_version")]
    fn version() -> &'static str {
        env!("CRAFT_PARTS_CARGO_VERSION")
    }

    #[pymodule_init]
    fn init(m: &Bound<'_, PyModule>) -> Result<()> {
        use crate::register_submodules::RegisterSubmodules as _;

        m.add("__version__", env!("CRAFT_PARTS_CARGO_VERSION"))?;
        m.register_submodules("craft_parts._rs")
    }
}
