# ADR-009 — Remote access from another network: a Tailscale node as a compose service

Status: accepted (2026-10-06)

## Context
The sim runs on a workstation behind a campus/institute NAT; users want to watch and drive it from a machine on a
different network. The full Isaac UI is WebRTC, whose media is **UDP 47998**. TCP-only tunnels (SSH, VS Code, Cloudflare
Tunnel, ngrok) carry the `web` still-frame view but never the WebRTC video (`docs/remote-access.md`, "What does not work").
A host-installed VPN works but is not reproducible (ADR-002), and on a shared machine a host daemon is not ours to own.
ZeroTier was considered and not wanted by the user.

## Decision
- A compose service **`vpn`** (`tailscale/tailscale:${TAILSCALE_TAG}`, pinned `v1.102.5`) on `network_mode: host` with
  `/dev/net/tun` + `NET_ADMIN`: the host gets a tailnet address and every service already listening (web view, WebRTC,
  SSH, MAVLink) is reachable from the user's tailnet devices. Outbound only; no port forwarding; DERP relays over HTTPS
  when UDP is blocked.
- Own compose project (`bisg-vpn`) and `restart: unless-stopped`: `./bisg down` / sim restarts never cut remote access.
- `--accept-dns=false`: the shared host's resolver is untouched. Login state in volume `bisg-vpn_vpn-state`.
- `SIM_VIEW_ADDR=vpn` resolves to the tailnet IP at `./bisg up` (what WebRTC advertises). `TS_AUTHKEY` (secret) lives in
  `docker/.env` only; without it `./bisg vpn up` prints a login URL.

## Consequences
- The viewing machine needs Tailscale (any OS app) on the same tailnet; it needs no GPU.
- A third-party coordination service (Tailscale) is in the access path; the data path is end-to-end WireGuard.
- ROS 2 DDS discovery does not cross the tailnet (no multicast); remote ROS work goes through SSH into the containers.
- Kernel tun mode adds a `tailscale0` interface to the host while the service runs.
