# Setup

## Prerequisites

- Docker and Docker Compose
- Node.js 20+
- An AWS account with S3 access (for COG layers, watershed data, and media storage)

## Project Structure

```
geo-field-pipeline/
├── backend/          FastAPI + PostGIS + GDAL
│   ├── app/          Application code
│   │   ├── main.py              App entry point, router wiring
│   │   ├── shared/              Config, auth, DB, S3, access control
│   │   └── modules/
│   │       ├── accounts/        Auth, users, orgs, QField accounts
│   │       ├── diagnose/        Projects, zones, notes, QField sync
│   │       ├── design/          (boilerplate)
│   │       └── assess/          (boilerplate)
│   ├── db/init.sql              PostGIS schema
│   ├── docker-compose.yml       postgis + titiler + api
│   ├── Dockerfile               Python 3.12-slim + GDAL + Docker CLI
│   └── requirements.txt
└── frontend/         SvelteKit + Tailwind + MapLibre GL
    └── src/
        ├── lib/
        │   ├── shared/          Session store, API client, components
        │   └── modules/         Per-module API clients and components
        └── routes/              SvelteKit file-based routing
```

## Backend Setup

1. Copy the example environment file and fill in your values:

```bash
cd backend
cp .env.example .env
```

2. Configure the required environment variables in `.env`:

| Variable | Description |
|----------|-------------|
| `AWS_ACCESS_KEY_ID` | IAM key with S3 `GetObject`, `PutObject`, `DeleteObject` |
| `AWS_SECRET_ACCESS_KEY` | Corresponding secret |
| `AWS_S3_BUCKET` | S3 bucket name for COG layers, watersheds, and media |
| `AWS_DEFAULT_REGION` | AWS region (default: `us-east-1`) |
| `COG_LAYERS` | Comma-separated COG raster keys in the bucket |
| `WATERSHEDS_FGB_KEY` | FlatGeobuf watershed file key in the bucket |
| `POSTGIS_PUBLIC_HOST` | Public hostname QField can reach (not `localhost`) |
| `POSTGIS_PUBLIC_PORT` | Public PostgreSQL port (default: `5432`) |
| `QFIELD_CLOUD_URL` | QField Cloud API base URL |
| `QFIELD_PROJECT_NAME` | Prefix for QField Cloud project names |
| `FRONTEND_ORIGIN` | Frontend URL for CORS (default: `http://localhost:5173`) |
| `SESSION_COOKIE_SECURE` | Set `true` in production (HTTPS) |

3. Start all services:

```bash
docker compose up -d
```

This starts three containers:
- **postgis** — PostGIS 16 with the schema from `db/init.sql`
- **titiler** — COG tile server for raster layers
- **api** — FastAPI application on port 8080

The API container volume-mounts `./app` for hot-reload during development.

4. Verify the backend is running:

```bash
curl http://localhost:8080/health
# {"status":"ok"}
```

## Frontend Setup

1. Install dependencies:

```bash
cd frontend
npm install
```

2. Start the dev server:

```bash
npm run dev
```

The frontend runs on `http://localhost:5173` and proxies API requests to `http://localhost:8080`.

## S3 Bucket Layout

```
your-bucket/
├── lulc.cog.tif                     Shared COG raster layer(s)
├── watersheds.fbg                   FlatGeobuf watershed boundaries
├── {project_id}/media/{file}        Field note photos/audio
└── {project_id}/packages/{...}      QField package artifacts
```

IAM permissions needed: `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject` on `arn:aws:s3:::your-bucket/*`.

## Database Reset

To reset the database and rebuild from the schema:

```bash
cd backend
docker compose down -v
docker compose up -d
```

The `-v` flag removes the PostgreSQL data volume, so `init.sql` runs again on startup.
