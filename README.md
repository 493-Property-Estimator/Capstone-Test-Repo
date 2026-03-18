# Group 14 Capstone Repo

## Current Status

This repository currently contains:

- the full user-story and per-feature spec structure under [`specs/`](/root/Speckit-Constitution-To-Tasks/specs)
- a shared frontend/backend API contract in [`frontend_api_contract.md`](/root/Speckit-Constitution-To-Tasks/frontend_api_contract.md)
- a shared upstream data-fetching specification in [`specs/shared-data-fetching.md`](/root/Speckit-Constitution-To-Tasks/specs/shared-data-fetching.md)
- a modular frontend scaffold in [`frontend/`](/root/Speckit-Constitution-To-Tasks/frontend)

## Frontend Status

The frontend currently implements the UI-side skeleton for the stories that fall within frontend scope:

- address search and suggestion handling
- map click selection
- OpenStreetMap rendering for the Edmonton area
- open-data layer toggles and viewport refresh handling
- estimate request form with minimal and standard property details
- estimate rendering, confidence display, and warning UI
- client-side validation and invalid-input messaging

The current frontend is organized as:

- [`frontend/index.html`](/root/Speckit-Constitution-To-Tasks/frontend/index.html)
- [`frontend/styles/app.css`](/root/Speckit-Constitution-To-Tasks/frontend/styles/app.css)
- [`frontend/src/app.js`](/root/Speckit-Constitution-To-Tasks/frontend/src/app.js)
- feature modules under [`frontend/src/features/`](/root/Speckit-Constitution-To-Tasks/frontend/src/features)
- backend integration client under [`frontend/src/services/api/apiClient.js`](/root/Speckit-Constitution-To-Tasks/frontend/src/services/api/apiClient.js)

## How To Run The App

Serve the frontend as a static site:

```bash
cd /root/Speckit-Constitution-To-Tasks/frontend
python3 -m http.server 8080
```

Then open:

```text
http://localhost:8080
```

## Runtime Notes

- The frontend expects the backend API at `http://localhost:8000/api/v1`.
- That value is configured in [`frontend/src/config.js`](/root/Speckit-Constitution-To-Tasks/frontend/src/config.js).
- The browser needs internet access for:
  - Leaflet CDN assets
  - OpenStreetMap tile loading
- Map clicks send coordinate payloads to the backend through the map-click resolution endpoint.
- A guard is in place so hold-and-drag map movement does not send click payloads.

## Next Integration Steps

- connect the Python backend to the contract in [`frontend_api_contract.md`](/root/Speckit-Constitution-To-Tasks/frontend_api_contract.md)
- implement the data-fetching rules from [`specs/shared-data-fetching.md`](/root/Speckit-Constitution-To-Tasks/specs/shared-data-fetching.md)
- test the frontend against live backend responses for search, estimate, and layer data
