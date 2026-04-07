`src/backend/src/api/properties.py` and `src/backend/src/services/property_viewport.py`

The canonical backend tree is now `src/backend/`.

The dedicated assessment property viewport endpoint is exposed through:

- `GET /api/v1/properties`

Relevant implementation files:

- `src/backend/src/api/properties.py`
- `src/backend/src/services/property_viewport.py`

The endpoint supports:

- viewport-bounded property retrieval
- clustered low-zoom rendering
- high-zoom individual property retrieval
- pagination via `cursor=offset:N`

Any future backend work on assessment-property viewport loading should be made in the `src/backend/` tree rather than the legacy `backend/` tree.
