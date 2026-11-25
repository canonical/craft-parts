use anyhow::Result;
use pyo3::{
    exceptions::PyException,
    prelude::*,
    types::{PyDict, PyTuple},
};

#[pyclass(extends = PyException, subclass)]
pub struct PartsError {
    #[pyo3(get)]
    brief: String,
    details: Option<String>,
    #[pyo3(get)]
    resolution: Option<String>,
    #[pyo3(get)]
    doc_slug: Option<String>,
}

/// Unexpected error.
///
/// :param brief: Brief description of error.
/// :param details: Detailed information.
/// :param resolution: Recommendation, if any.
/// :param doc_slug: Reusable documentation slug for consumers adopting the
///   Craft Parts documentation.
#[pymethods]
impl PartsError {
    // Exception subclasses cannot accept keyword arguments through `__new__`:
    // CPython's `BaseException.tp_new` rejects them before pyo3 runs. Allocate
    // permissively here, and do real argument parsing in `__init__` instead.
    #[new]
    #[pyo3(signature = (*_args, **_kwargs))]
    fn new(_args: &Bound<'_, PyTuple>, _kwargs: Option<&Bound<'_, PyDict>>) -> Self {
        Self {
            brief: String::new(),
            details: None,
            resolution: None,
            doc_slug: None,
        }
    }

    #[pyo3(signature = (brief, details=None, resolution=None, doc_slug=None))]
    fn __init__(
        slf: &Bound<'_, Self>,
        brief: String,
        details: Option<String>,
        resolution: Option<String>,
        doc_slug: Option<String>,
    ) {
        let mut borrowed = slf.borrow_mut();
        borrowed.brief = brief;
        borrowed.details = details;
        borrowed.resolution = resolution;
        borrowed.doc_slug = doc_slug;
    }

    #[getter]
    fn details(&self) -> Option<&str> {
        self.details.as_deref()
    }

    fn __str__(slf: &Bound<'_, Self>) -> Result<String> {
        // Read `details` through the Python object so that subclass property
        // overrides (e.g. UserExecutionError.details) are honored. Must happen
        // before borrowing the struct, since the property may run Python code.
        let details = slf.getattr("details")?.extract::<Option<String>>()?;
        let borrowed = slf.borrow();
        let mut components = vec![borrowed.brief.clone()];
        if let Some(d) = details {
            components.push(d);
        }
        if let Some(r) = &borrowed.resolution {
            components.push(r.clone());
        }
        Ok(components.join("\n"))
    }

    fn __repr__(slf: &Bound<'_, Self>) -> Result<String> {
        let class_name = slf.get_type().name()?;

        let to_repr = |field: Option<String>| -> Result<String> {
            Ok(field.into_pyobject(slf.py())?.repr()?.to_str()?.into())
        };

        let details = slf.getattr("details")?.extract::<Option<String>>()?;
        let borrowed = slf.borrow();

        Ok(format!(
            "{}(brief={}, details={}, resolution={}, doc_slug={})",
            class_name,
            to_repr(Some(borrowed.brief.clone()))?,
            to_repr(details)?,
            to_repr(borrowed.resolution.clone())?,
            to_repr(borrowed.doc_slug.clone())?,
        ))
    }
}

#[pymodule(submodule)]
pub mod errors {
    use super::*;

    #[pymodule_export]
    use self::PartsError;
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_str_joining_optional() {
        let err = PartsError {
            brief: "A brief description".to_string(),
            details: Some("Details".to_string()),
            resolution: None,
            doc_slug: None,
        };

        let expected = "A brief description\nDetails";

        Python::attach(|py| -> Result<()> {
            let bound = Bound::new(py, err)?;
            let actual = PartsError::__str__(&bound)?;
            assert_eq!(actual, expected);
            Ok(())
        })
        .unwrap();
    }

    #[test]
    fn test_repr_format() {
        let err = PartsError {
            brief: "A brief description".to_string(),
            details: Some("Details".to_string()),
            resolution: None,
            doc_slug: None,
        };

        let expected = "PartsError(brief='A brief description', details='Details', resolution=None, doc_slug=None)";

        Python::attach(|py| -> Result<()> {
            let bound = Bound::new(py, err)?;
            let actual = PartsError::__repr__(&bound)?;
            assert_eq!(actual, expected);
            Ok(())
        })
        .unwrap();
    }
}
