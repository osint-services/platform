# Install OSINT Services on Debian or Ubuntu

The amd64 package includes Whoisit, the release's Compose configuration, and prebuilt images for the five backend services and nginx. Install Docker Engine and the [Compose v2 plugin](https://docs.docker.com/compose/install/linux/) first. Use a local Docker context and make sure the account that runs Whoisit can access the daemon. Both of these commands should work from that account without `sudo`:

```sh
docker info
docker compose version
```

Verify that the Compose version starts with `v2`. On Ubuntu 24.04, the distribution provides `docker.io` and `docker-compose-v2`. Sign out and back in after changing Docker group membership.

## Install and launch

1. From [platform releases](https://github.com/osint-services/platform/releases), download the `whoisit_<version>_amd64.deb` and its `.sha256` file. Use the following commands from the download directory, substituting the published version:
   ```sh
   sha256sum -c whoisit_1.2.0_amd64.deb.sha256
   sudo apt install ./whoisit_1.2.0_amd64.deb
   ```
2. Open **whoisit** from the application menu or run `whoisit`. Whoisit checks Docker, imports any missing release images, and starts the Compose project. The first launch can take a few minutes while Docker loads the images. When the gateway and backend services respond, Whoisit shows **Services online**. If startup fails, the app displays the issue and a **Retry** button.
3. To use live X or Twilio results, enter credentials in **Integrations**. Imported datasets and dataset-backed maps work without these credentials. The gateway stays on `http://127.0.0.1:80`, and the backend continues running when you close Whoisit.

The installer keeps the Compose files and archive in `/usr/lib/whoisit/resources/osint-platform`. Whoisit writes settings in `${XDG_CONFIG_HOME:-$HOME/.config}/whoisit/platform/.env`. Use this settings file to configure `CERTIFICATE_INVENTORY_DOMAINS` and other [optional platform values](../README.md#environment-values). Reopen Whoisit to apply file edits.

## Upgrade an existing installation

Install the newer `.deb` with the same `apt install` command and reopen Whoisit. Use the same Docker context. The Compose project stays named `platform` and reuses Docker volumes `platform_dataset_data` and `platform_social_mapping_cache`. These hold imported datasets, certificate inventory, and the geocoder cache. Whoisit also keeps its existing desktop profile and settings.

For a previous source-based installation, check the existing project with `docker compose ls` before the first unified launch:

- If it is named `platform`, the installer picks up those volumes on the same daemon. To carry over settings, copy the checkout's `.env` into the per-user settings path before first launch. Create the settings directory with mode `700` and use `install -m 600` to copy the file.
- If it uses a different project name or daemon, its volumes remain separate. Back up and migrate those volumes to the `platform` project before switching. Stop the old project if it still owns port 80.
- Keep the volumes when stopping the old stack. `docker compose down --volumes` deletes data.

## Build and publish

From the platform root, check out the intended release commit and initialize its pinned submodules. On an amd64 Linux build host, install Docker with Compose v2, Node.js 22, `fakeroot`, and `dpkg`, then run:

```sh
git submodule update --init --recursive
scripts/make-debian-installer.sh 1.2.0 dist
```

Run the platform **Debian installer** workflow manually to build and smoke-test an artifact before tagging. A new platform tag such as `v1.2.0` builds and tests the package again, then publishes it and its checksum to platform releases. Use a new version for every published installer so Docker image references and Debian package versions advance together.
