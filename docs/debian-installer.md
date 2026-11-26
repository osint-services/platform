# Install OSINT Services on Debian or Ubuntu

The amd64 package includes Whoisit, the release's Compose configuration, and prebuilt images for the five backend services and nginx. Install Docker Engine 28 or newer and the [Compose v2 or v5 plugin](https://docs.docker.com/compose/install/linux/) first. Use a local Docker context and make sure the account that runs Whoisit can access the daemon. Both of these commands should work from that account without `sudo`.

```sh
docker info
docker compose version
```

Check the server version in `docker info`. Docker Engine releases before 28 can expose ports published to localhost to peers on the same network segment. Install [Docker Engine for Debian](https://docs.docker.com/engine/install/debian/) or [Docker Engine for Ubuntu](https://docs.docker.com/engine/install/ubuntu/) if your distribution packages ship an older engine. [Docker port publishing](https://docs.docker.com/engine/network/port-publishing/)

Compose v5 support starts with platform v1.2.1. Installations using v1.2.0 require Compose v2.

## Install and launch

1. From [platform releases](https://github.com/osint-services/platform/releases), download the `whoisit_<version>_amd64.deb` and its `.sha256` file. Run these commands from the download directory and substitute the published version.
   ```sh
   sha256sum -c whoisit_1.2.4_amd64.deb.sha256
   sudo apt install ./whoisit_1.2.4_amd64.deb
   ```
2. Open **whoisit** from the application menu or run `whoisit`. Whoisit checks Docker, imports any missing release images, and starts the Compose project. The first launch can take a few minutes while Docker loads the images. When the gateway and backend services respond, Whoisit shows **Services online**. If startup fails, the app displays the issue and a **Retry** button. For Docker permission errors, see [Docker is running but Whoisit cannot connect](#docker-is-running-but-whoisit-cannot-connect).
3. To use live X or Twilio results, enter credentials in **Integrations**. Imported datasets and dataset-backed maps work without these credentials. The gateway stays on `http://127.0.0.1:80`, and the backend continues running when you close Whoisit.

The installer keeps the Compose files and archive in `/usr/lib/whoisit/resources/osint-platform`. Whoisit writes settings in `${XDG_CONFIG_HOME:-$HOME/.config}/whoisit/platform/.env`. Use this settings file to configure `CERTIFICATE_INVENTORY_DOMAINS` and other [optional platform values](../README.md#environment-values). Reopen Whoisit to apply file edits.

## Docker is running but Whoisit cannot connect

If `docker info` reports permission denied for `/var/run/docker.sock`, compare the groups in your current shell with those configured for your account.

```sh
id -nG
id -nG "$USER"
```

If `docker` is missing from the second command and you administer the machine, follow [Docker's instructions for configuring access](https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user). Membership in the `docker` group grants root-level privileges.

If only the second command lists `docker`, your current session still has the old group memberships. Signing out and back in refreshes the whole desktop session. If you have work running and need to stay signed in, quit Whoisit completely and run the following from your desktop terminal. The second command launches Whoisit as your account with refreshed group memberships after Docker access succeeds.

```sh
sudo -u "$USER" docker info --format '{{.ServerVersion}}' &&
  sudo -u "$USER" --preserve-env=DISPLAY,WAYLAND_DISPLAY,XAUTHORITY,XDG_RUNTIME_DIR,DBUS_SESSION_BUS_ADDRESS /usr/bin/whoisit
```

Keep `-u "$USER"` in both commands. Plain `sudo whoisit` runs the app as root, which Electron rejects. After your next normal sign-in, open Whoisit from the application menu.

## Upgrade an existing installation

Install the newer `.deb` with the same `apt install` command and reopen Whoisit. Use the same Docker context. The Compose project stays named `platform` and reuses Docker volumes `platform_dataset_data` and `platform_social_mapping_cache`. These hold imported datasets, certificate inventory, and the geocoder cache. Whoisit also keeps its existing desktop profile and settings.

For a previous source-based installation, check the existing project with `docker compose ls` before the first unified launch.

- If it is named `platform`, the installer picks up those volumes on the same daemon. To carry over settings, copy the checkout's `.env` into the per-user settings path before first launch. Create the settings directory with mode `700` and use `install -m 600` to copy the file.
- If it uses a different project name or daemon, its volumes remain separate. Back up and migrate those volumes to the `platform` project before switching. Stop the old project if it still owns port 80.
- Keep the volumes when stopping the old stack. `docker compose down --volumes` deletes data.

## Build and publish

From the platform root, check out the intended release commit and initialize its pinned submodules. On an amd64 Linux build host, install Docker Engine 28 or newer with Compose v2 or v5 and Buildx, Node.js 22.17 or newer, `fakeroot`, and `dpkg`. Run the build script from the platform root.

```sh
git submodule update --init --recursive
scripts/make-debian-installer.sh 1.2.4 dist
```

The platform **Debian installer** workflow builds and smoke-tests an artifact for installer-related pull requests. A manual run also produces a test artifact. To publish, add a new version heading to the changelog and merge it to `main`, or push a new platform version tag. The workflow publishes the package and checksum after the installer checks pass. Use the Platform release for changes to the unified installer, including desktop and backend changes after their submodule pins are updated. Documentation and CI maintenance alone can ship on `main`. Use a new version for every published installer so Docker image references and Debian package versions advance together.

Installer CI audits the Whoisit and Social Mapping JavaScript lockfiles, including development dependencies. It also uses Trivy on the images extracted from the checksummed installer to scan system and application packages. Publication requires successful scans and install tests. High and critical JavaScript advisories and high and critical image advisories with a published fix block publication. The **dependency-scan-reports** workflow artifact retains the full scan results, including image findings without fixes.
