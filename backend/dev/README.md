# backend/dev — manual checking kit (local only)

Everything here runs against your **local** database (`APP_ENV=local` in `backend/.env`) and refuses to
run anywhere else. Nothing here needs Docker.

| File | What it does |
|---|---|
| `seed.py` (`python dev/seed.py`) | Demo tenants, clients and managers, then demo requisitions created **through the API** |
| `make_token.py` (`python dev/make_token.py`) | Prints an access token for a demo manager (there is no login screen yet) |
| `requests.http` | Step-by-step walkthrough of FR-007 → FR-004 → FR-006 for VS Code's REST Client |
| `demo.py` | The fixed demo ids used by all of the above |

The scripts read `backend/.env` themselves.

## Quick start (PowerShell, from `backend/`, with the venv active)

```powershell
python -m auth_service.migrate --env-file .env; python -m requisition_service.migrate --env-file .env
python -m requisition_service --env-file .env      # window 1 - leave running
python dev/seed.py                                  # window 2
python dev/make_token.py                            # copy the token it prints
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

Tokens: `python dev/make_token.py` = agency manager; `python dev/make_token.py employer` = direct-employer
manager. A token only sees its own tenant's data (try it: the employer token gets 404 on agency requisitions).

`python dev/seed.py` is safe to re-run; `python dev/seed.py --force` adds another set of requisitions.
To look at the tables directly: `psql -h localhost -U postgres -d teamora`.
