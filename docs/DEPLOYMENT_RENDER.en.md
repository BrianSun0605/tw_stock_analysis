# Public Deployment with GitHub + Render

This guide deploys the project as a public website that users can open directly. The architecture is one Flask/Waitress Web Service: the UI, analysis API, SSE progress, CSV export, and PDF download all come from the same Render service. GitHub Pages and any additional AI API are not required.

## Project Configuration Already Added

- The root `render.yaml` defines a free Render Web Service in Singapore with Python 3.12, a health check, and automatic deployment.
- With `TWSTOCK_APP_MODE=web`, the service reads Render's `PORT`, binds to `0.0.0.0`, and does not open a local browser or use the desktop single-instance lock.
- Public mode does not render the shutdown button and does not register `/shutdown`. The existing desktop-only local shutdown flow remains unchanged.
- Caches, task charts, logs, and PDFs are written to `/tmp/twstock-analysis`. This is temporary storage, not the GitHub source tree, and is not guaranteed to persist.
- The public demo defaults to six analyses per source per hour and 60 searches per source per minute. The whole service runs only one analysis or PDF job at a time. These values can be changed in Render environment variables, but increasing them is not recommended on the free plan.
- `/healthz` returns service status and version for Render health checks.

## Required Decisions Before First Deployment

1. Change `name: tw-stock-research-demo` in `render.yaml` to an unused lowercase, hyphenated name, such as `yourname-tw-stock-research`. It determines the default `https://<name>.onrender.com` URL.
2. Choose repository visibility. A public repository is normally suitable for a competition demo. A private repository is possible if the Render GitHub App is granted access.
3. The free plan is suitable for a demo and judges, not for a promise of always-on, high-concurrency, or permanent storage. An idle service can sleep and the first visit can have a cold-start delay. Download PDFs immediately after creation.

## First Upload to GitHub

This workspace already has `.git`, but it has no remote and no usable local Git command is currently installed. Choose one of the following paths.

### Option A: GitHub Desktop

1. Install and sign in to [GitHub Desktop](https://desktop.github.com/).
2. Select **File → Add local repository** and choose the project root.
3. Create the first commit, for example `Prepare Render web deployment`.
4. Select **Publish repository**, then choose the repository name and visibility.
5. Confirm that `render.yaml`, `.python-version`, `docs/DEPLOYMENT_RENDER.md`, and source code are committed. Do not upload `cache/`, `output/`, `.venv/`, `dist/`, or `release/`.

### Option B: Install Git and use PowerShell

Create an empty repository on GitHub first; do not initialize it with a README, `.gitignore`, or license. Then run these commands from the project root:

```powershell
winget install --id Git.Git -e
git config --global user.name "Your GitHub name"
git config --global user.email "Your GitHub email"
git add .
git commit -m "Prepare Render web deployment"
git branch -M main
git remote add origin https://github.com/<account>/<repository>.git
git push -u origin main
```

The first `git push` asks you to sign in through a browser or configure a Personal Access Token. Never put a token in source code, `render.yaml`, a README, or a commit.

## Create the Render Service

1. Sign in to the [Render Dashboard](https://dashboard.render.com/) with GitHub and authorize access to the new repository.
2. Select **New → Blueprint**, then choose the repository and its `main` branch. Render reads the root `render.yaml`.
3. Confirm **Web Service**, **Free**, **Singapore**, and the unique service name you set in `render.yaml`.
4. Create the Blueprint. Render runs `python -m pip install -r requirements.txt` and starts the app with `python webui.py`.
5. Wait for the deployment log to show that the service started and `/healthz` passed. Render then provides `https://<service-name>.onrender.com`.
6. Test search, one analysis, Traditional Chinese/English switching, PDF generation, and PDF download. `https://<service-name>.onrender.com/healthz` should return `status: ok`.

`autoDeployTrigger: checksPass` is enabled. Future pushes to `main` deploy only after GitHub Actions checks pass. You can switch to commit-triggered deployment in Render, but it is not recommended for unverified changes.

## Operational Limits

- A Render Free Web Service is for demonstration. It can sleep when idle, and its filesystem is temporary. Old tasks, caches, and PDFs can disappear after a restart, redeploy, or storage cleanup.
- Learning Lab answers and starred questions stay in each user's browser `localStorage`, not in a server database. Clearing browser site data also clears them.
- This public site has no account system. Task IDs are high-entropy random values, one heavy job runs at a time, and source-based limits are enabled; this is not enterprise-grade multi-user isolation. A long-term public service should add authentication, shared rate limiting/WAF, monitoring, and persistent object storage.
- Data still depends on TWSE, TPEx, MOPS, FinMind/Yahoo fallback, and RSS availability and terms. FinMind activates only when the official monthly-revenue/quarterly-EPS path is temporarily unavailable and retains a `fallback` label plus an official-verification reminder. Keep the research/education and investment-disclaimer language in the public demo.
- Render deployment needs no AI API key. Analysis, question-bank content, and reports continue to run independently on the server.

## Adjust Public Demo Quotas

In Render **Environment**, update these non-secret variables and redeploy:

| Variable | Default | Purpose |
|---|---:|---|
| `TWSTOCK_ANALYSES_PER_HOUR` | 6 | Analyses a source can start per hour; range 1–60 |
| `TWSTOCK_SEARCHES_PER_MINUTE` | 60 | Searches a source can make per minute; range 10–600 |
| `TWSTOCK_DATA_ROOT` | `/tmp/twstock-analysis` | Temporary runtime root; keep a temporary path on the free service |

Do not increase Waitress workers or allow multiple heavy analysis jobs on the free service. The current single-heavy-job design keeps charts, PDFs, upstream data requests, and memory consumption predictable.

## Updates, Rollbacks, and Removal

- Update: commit and push to `main`; after GitHub Actions succeeds, Render deploys automatically.
- Roll back: choose an earlier successful deployment in Render's Deploys page, or restore a known-good GitHub commit and push it.
- Pause/remove: disable or delete the service in Render Dashboard. This does not delete the GitHub repository. Deleting the repository prevents subsequent automatic deployments.

Official references: [Render Blueprints](https://render.com/docs/blueprint-spec), [Render Web Services](https://render.com/docs/web-services), [Render Free](https://render.com/docs/free), and [Render GitHub integration](https://render.com/docs/github).
