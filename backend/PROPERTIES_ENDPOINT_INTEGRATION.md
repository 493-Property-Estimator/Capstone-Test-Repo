`backend/src/api/properties.py` and `backend/src/services/property_viewport.py`
are intentionally added as new files only, so they should merge cleanly with the
existing `backend` branch.

After the `backend` branch is merged, wire the route into
`backend/src/app.py` with one include:

```python
from backend.src.api.properties import router as properties_router
app.include_router(properties_router, prefix="/api/v1")
```

This route implements:

- `GET /api/v1/properties`
- clustered viewport responses for low zoom
- individual property responses for high zoom
- cursor-based pagination for dense high-zoom views

It is designed to match `frontend_api_contract.md`.
