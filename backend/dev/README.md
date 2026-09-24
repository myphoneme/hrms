# backend/dev — manual checking kit (local only)

Everything here runs against your **local** database (`APP_ENV=local` in `backend/.env`) and refuses to
run anywhere else. Nothing here needs Docker.

| File | What it does |
|---|---|
| `seed.js` (`npm run dev:seed`) | Demo tenants, clients and managers, then demo requisitions created **through the API** |
| `token.js` (`npm run dev:token`) | Prints an access token for a demo manager (there is no login screen yet) |
| `requests.http` | Step-by-step walkthrough of FR-007 → FR-004 → FR-006 for VS Code's REST Client |
| `demo.js` | The fixed demo ids used by all of the above |

## Quick start (PowerShell, from `backend/`)

```powershell
npm install; npm run build; npm run migrate:local
npm run start:requisition          # window 1 - leave running
npm run dev:seed                   # window 2
npm run dev:token                  # copy the token it prints
```

Then open **http://localhost:3002/api/docs** (the interactive API page, local/test only), click
**Authorize**, paste the token, and use **Try it out** on any endpoint. Bodies come pre-filled with
examples using the demo ids.

Or open `dev/requests.http` in VS Code with the **REST Client** extension, paste the token into
`@token`, and click **Send Request** from top to bottom.

## Demo data

| Tenant | Client | Requisition | State |
|---|---|---|---|
| Demo Staffing Agency | Retail Co | Senior Data Analyst | **Frozen_Open**: v1 Approved (matrix 100%), v2 revision in review (matrix only 90%) |
| Demo Staffing Agency | Fintech Co | Backend Engineer | **Draft**: v1 draft, empty matrix |
| Demo Direct Employer | - | HR Executive | **PendingApproval**: matrix 100%, ready for you to freeze |

Tokens: `npm run dev:token` = agency manager; `npm run dev:token -- employer` = direct-employer manager.
A token only sees its own tenant's data (try it: the employer token gets 404 on agency requisitions).

`npm run dev:seed` is safe to re-run; `npm run dev:seed -- --force` adds another set of requisitions.
To look at the tables directly: `psql -h localhost -U postgres -d teamora`.
