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

    #[pymodule_init]
    fn init(m: &Bound<'_, PyModule>) -> Result<()> {
        use crate::register_submodules::RegisterSubmodules as _;

        m.register_submodules("craft_parts._rs")
    }
}
