class PartsError(Exception):
    """Unexpected error.

    :param brief: Brief description of error.
    :param details: Detailed information.
    :param resolution: Recommendation, if any.
    :param doc_slug: Reusable documentation slug for consumers adopting
        the Craft Parts documentation.
    """

    brief: str
    resolution: str | None
    doc_slug: str | None

    def __init__(
        self,
        brief: str,
        details: str | None = None,
        resolution: str | None = None,
        doc_slug: str | None = None,
    ) -> None: ...
    @property
    def details(self) -> str | None: ...
