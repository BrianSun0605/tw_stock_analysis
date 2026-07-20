# Privacy and Network Connections

This project has two explicitly different runtime modes, with different data paths.

## Windows Local App

- The App provides its interface only on local `127.0.0.1`; it does not accept connections from a LAN or the Internet.
- The App does not require an account and does not collect names, email addresses, trading records, or portfolios.
- Queried stock codes are sent from the user's computer to data sources such as TWSE, TPEx, the Market Observation Post System, FinMind, Yahoo Finance, and news RSS. Those sources may record IP addresses, User-Agent values, and requests under their own policies.
- Analysis cache, SQLite, logs, and PDFs remain on the local computer. The release build uses each Windows user's LocalAppData; development mode uses the project directory.
- Each PDF is retained for three days by default, and the oldest files are removed first when output exceeds 250 MiB. Cache is reduced to 160 MiB when it exceeds 200 MiB.
- Local mode does not upload analysis results to a server operated by this project.

Users can delete PDFs from the App's output directory. The uninstaller should provide an option to retain or remove user data.

## Render Public Demo Website

- A site is public only when it is explicitly deployed with `TWSTOCK_APP_MODE=web`. A security code/name and analysis request first reach the project service on Render, which then retrieves upstream data. Upstream sources normally see the host IP rather than the visitor connecting to them directly.
- The site has no accounts, login, user database, advertising tracking, or project-added analysis telemetry. Investment Learning Lab answers and starred questions remain only in the user's browser `localStorage`.
- The public service keeps task data, cache, operational logs, and PDFs in the Render container's temporary directory. They can disappear after a free-service restart, redeploy, wake from sleep, or capacity cleanup; download PDFs immediately after creation.
- The project does not write analysis results to a self-managed persistent database. Render and upstream sources can still retain connection IPs, access logs, User-Agent values, or request metadata under their own policies. A public-deployment operator should review Render's and each upstream provider's current privacy terms.
- The public demo limits search and analysis starts per source and runs only one heavy job. This protects resources; it is not account authentication or complete privacy/data isolation.

See [DEPLOYMENT_RENDER.en.md](DEPLOYMENT_RENDER.en.md) for full GitHub + Render deployment, quota, and operations limitations.
