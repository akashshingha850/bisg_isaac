# ADR-009 — Remote access from another network: a Tailscale node as a compose service

Status: accepted (2026-10-06)

## Context
The sim runs on a workstation behind a campus/institute NAT; users want to watch and drive it from a machine on a
different network. The full Isaac UI is WebRTC, whose media is **UDP 47998**. TCP-only tunnels (SSH, VS Code, Cloudflare
Tunnel, ngrok) carry the `web` still-frame view but never the WebRTC video (`docs/remote-access.md`, "What does not work").
A host-installed VPN works but is not reproducible (ADR-002), and on a shared machine a host daemon is not ours to own.
ZeroTier was considered and not wanted by the user.

## Decision
- A compose service **`tailscale`** (`tailscale/tailscale:${TAILSCALE_TAG}`, pinned `v1.102.5`) on `network_mode: host` with
  `/dev/net/tun` + `NET_ADMIN`: the host gets a tailnet address and every service already listening (web view, WebRTC,
  SSH, MAVLink) is reachable from the user's tailnet devices. Outbound only; no port forwarding; DERP relays over HTTPS
  when UDP is blocked.
- Own compose project (`bisg-tailscale`) and `restart: unless-stopped`: `./bisg down` / sim restarts never cut remote access.
- `--accept-dns=false`: the shared host's resolver is untouched. Login state in volume `bisg-tailscale_tailscale-state`.
- The container runs plain `tailscaled` (not the image's `containerboot`, whose 60 s login deadline restarts the container
  with a new URL). Login is explicit: `./bisg tailscale login` in a terminal prints a URL (or `--qr`) for a browser on any device.
- `SIM_VIEW_ADDR=tailscale` resolves to the tailnet IP at `./bisg up` (what WebRTC advertises). 
- **No auth keys.** The only login is the browser one (`./bisg tailscale login`, URL or `--qr`, opened on any device). A reusable
  `tskey-auth-...` stored in `docker/.env` on a shared, multi-user machine is a standing secret: anyone who reads it can join
  the tailnet. The login itself persists in the `tailscale-state` volume, so it is needed once per machine.

## Consequences
- The viewing machine needs Tailscale (any OS app) on the same tailnet; it needs no GPU.
- A third-party coordination service (Tailscale) is in the access path; the data path is end-to-end WireGuard.
- ROS 2 DDS discovery does not cross the tailnet (no multicast); remote ROS work goes through SSH into the containers.
- Kernel tun mode adds a `tailscale0` interface to the host while the service runs.
