# AMP TRADE FIND V8 – Render Deployment

## Test deployment
The included `render.yaml` creates a free Render web service.

Health check:
`/ready`

The readiness endpoint checks the local database and reports WebSocket / push status.

## Important persistence warning
The free Render web-service filesystem is ephemeral.

That means the SQLite database can disappear when the service restarts, redeploys or spins down.

For the first Android live test this is acceptable.

For permanent paper-trade statistics, migrate the storage layer to:
- Render Postgres, or
- a paid Render service with persistent disk.

Do not treat a free SQLite deployment as permanent performance history.

## Firebase push
V8 server push is optional.

Default:
`FIREBASE_ENABLED=false`

To enable later:
1. Create a Firebase project.
2. Create a server service-account credential.
3. Put the complete service-account JSON into Render secret:
   `FIREBASE_SERVICE_ACCOUNT_JSON`
4. Set:
   `FIREBASE_ENABLED=true`
5. Redeploy.

Never commit the service-account JSON to GitHub.

## Push endpoints
- GET `/api/v1/push/status`
- POST `/api/v1/push/register`
- POST `/api/v1/push/unregister`
- POST `/api/v1/push/test` with header `X-Admin-Key`

Production signal pushes remain logically blocked until the trading validation gate is explicitly approved.
