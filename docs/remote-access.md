# Watching the sim from somewhere else

Headless means no window on the workstation — not "no picture". There are two transports, and which
one you can use depends on whether UDP reaches you.

| | `SIM_VIEW=web` | `SIM_VIEW=webrtc` |
|---|---|---|
| What you get | still frames in a browser, ~1 fps, look only | full interactive Isaac UI |
| Transport | **one TCP port** (`SIM_WEB_PORT`, default 8899) | TCP 49100 + **UDP 47998** |
| Client | any browser, VS Code Simple Browser included | Isaac Sim WebRTC Streaming Client (desktop app) |
| Through a VS Code / SSH tunnel | **yes** | no — tunnels forward TCP only |
| Through a VPN (Tailscale, WireGuard) | yes | yes |
| Cost | one viewport capture per interval | continuous encode (NVENC) |

`SIM_VIEW=both` runs the two at once, and `gui+web` / `gui+webrtc` add a stream on top of the local
window. Either transport forces rendering on, so never use one for a timing or regression run.

## You are on another network: the `vpn` service

A Tailscale node runs as a compose service (`vpn`, ADR-009) on the host network. This server gets a
`100.x.y.z` tailnet address, and everything listening here (browser view, WebRTC, SSH, MAVLink) is reachable from
your other devices on the same tailnet. It makes outbound connections only: no port forwarding, no public IP,
and it works behind NAT and campus firewalls (falling back to Tailscale's HTTPS relays when UDP is blocked).
Nothing is exposed to the internet. Only devices logged into your tailnet can connect.

**On the sim server, once:**

```
echo SIM_VIEW_ADDR=vpn >> docker/.env     # WebRTC advertises this host's tailnet IP
./bisg vpn up                             # first time: prints a login URL, open it in any browser
```

The login is kept in the `bisg-vpn_vpn-state` volume, and the container restarts with the machine
(`restart: unless-stopped`), so later runs need nothing. For an unattended setup, put a reusable auth key from
the Tailscale admin console in `docker/.env` as `TS_AUTHKEY=tskey-...`. It is a secret, so never put it in `config/bisg.conf`.

**On the machine you watch from:** install Tailscale (Windows/macOS/Linux/iOS/Android app) and log in with the
same account. If that machine is a Linux box with this repo, `./bisg vpn up` there works too.

**Then:**

```
./bisg up webrtc        # or: ./bisg up web     (on the sim server)
./bisg vpn status       # prints the address and what to open
```

| From the remote machine | Open |
|---|---|
| Interactive Isaac UI | Isaac Sim WebRTC Streaming Client → the server's `100.x` address |
| Still frames in a browser | `http://100.x.y.z:8899/` |
| Shell | `ssh <user>@100.x.y.z` (or the MagicDNS name, `VPN_HOSTNAME`, default `bisg-<hostname>`) |
| QGroundControl | on the server `GCS_URL=udp://@<remote's 100.x IP>:14550` in `docker/.env`, then `./bisg mavros up`; QGC listens on 14550 by default |

`./bisg down` stops the sim but not the VPN (own compose project `bisg-vpn`). `./bisg vpn down` disconnects;
`./bisg vpn logout` also forgets the login. `--accept-dns=false` is set, so the host's DNS is not touched
(this matters on a shared machine). ROS 2 DDS discovery does not cross the tailnet (no multicast); use the views above or
`./bisg shell` over SSH.

## You are on a VS Code tunnel (this workstation's usual case)

```
./bisg up web                   # boot headless, serve the view on TCP 8899
./bisg view                     # prints every URL below, and whether the port is listening
```

Then, in VS Code:

1. **Ports** panel (next to the terminal) → *Forward a Port* → `8899`. With a `code tunnel` session the
   port is usually detected automatically once the sim starts listening.
2. `Ctrl+Shift+P` → **Simple Browser: Show** → `http://localhost:8899/`.

The page shows the latest frame and reloads it every `SIM_WEB_INTERVAL` seconds. It is a viewer, not a
control surface: fly the drone with `./bisg smoke`, MAVROS, or QGroundControl, and watch the result here.

Equivalent without VS Code:

```
ssh -L 8899:127.0.0.1:8899 <this-host>      # then open http://localhost:8899/ locally
```

## You want the real, interactive Isaac UI

WebRTC media is UDP, so it needs a network path that carries UDP — a LAN, or a VPN that gives both
machines an IP.

```
# config/bisg.conf
SIM_VIEW=webrtc
SIM_VIEW_ADDR=100.x.y.z        # this host's address as the client sees it (Tailscale IP, LAN IP, …)
```

```
./bisg up webrtc
./bisg view                    # address + ports to type into the client
```

Install the **Isaac Sim WebRTC Streaming Client** ([NVIDIA docs](https://docs.isaacsim.omniverse.nvidia.com/latest/installation/manual_livestream_clients.html)),
connect it to that address, and open TCP 49100 + UDP 47998 on the host firewall. The viewing machine
needs no GPU. Without `SIM_VIEW_ADDR` a remote client connects to the signalling port and then
receives no video, which looks like a hang.

From another network, use the `vpn` service above (`SIM_VIEW_ADDR=vpn`). On a LAN, the LAN IP is enough.

## What does not work

- **Cloudflare Tunnel / `cloudflared`** for WebRTC: it carries HTTP and TCP (`cloudflared access tcp`),
  not arbitrary UDP, so signalling connects and the video never arrives. Cloudflare One private networks
  can route UDP, but only with the WARP client on the viewing machine — at which point a plain VPN is
  simpler. `cloudflared` *is* a reasonable way to expose the **web** view (one TCP port) to the internet;
  put authentication in front of it, because that page has no access control of its own.
- **A browser URL for WebRTC.** NVIDIA removed the in-browser WebRTC client after Isaac Sim 4.0, and this
  image ships only the server extensions (Isaac Sim 6.0: `omni.kit.livestream.app` + `omni.kit.livestream.webrtc`; 5.1 used `omni.services.livestream.nvcf`, which no longer exists).
  The browser route is the `web` mode above.
- **Forwarding UDP 47998 over SSH or VS Code.** Both forward TCP. `socat`/`udp-over-tcp` bridges exist and
  are not worth the trouble; use a VPN.

## Settings

All in the "What you see" block of [`config/bisg.conf`](../config/bisg.conf):

| Key | Default | Meaning |
|---|---|---|
| `SIM_VIEW` | `auto` | `gui` \| `headless` \| `web` \| `webrtc` \| `both` \| `auto`, combined with `+` |
| `SIM_VIEW_ADDR` | empty | address advertised to remote clients; required for remote WebRTC; `vpn` = this host's tailnet IP. Per machine: `docker/.env` |
| `VPN_HOSTNAME` | `bisg-<hostname>` | this host's name on the tailnet (`vpn` service) |
| `TAILSCALE_TAG` | `v1.102.5` | image pin of the `vpn` service (ADR-009) |
| `TS_AUTHKEY` | empty | `docker/.env` only: auth key for an unattended `./bisg vpn up` |
| `SIM_WEB_PORT` | `8899` | TCP port of the browser view |
| `SIM_WEB_INTERVAL` | `1.0` | seconds between captured frames |

Per-run overrides: `./bisg up web`, `webrtc`, `both`, `gui+webrtc`, or the flags `--web`, `--stream`,
`--both`, `--no-stream` (these change only the stream half and keep the configured window).

## Troubleshooting

| Symptom | Cause |
|---|---|
| "waiting for the first frame" forever | the world is still loading (~4–5 min cold), or `./bisg logs` shows `web view: capture failed` — the viewport was not available |
| `ERR_CONNECTION_REFUSED` on `http://127.0.0.1:8899/` | nothing is listening: the sim is not running (`./bisg status`), still booting, or was started with no web view. `./bisg view` says which. A GPU/driver problem stops the container before any port opens — `./bisg up` reports that case directly |
| Page does not load at all | port not forwarded, or the sim was started with no web view: `./bisg view` says which |
| WebRTC client connects, black window | no UDP path, or `SIM_VIEW_ADDR` unset/wrong |
| `SIM_VIEW_ADDR=vpn but the vpn service has no address` | `./bisg vpn up` (and finish the login), then `./bisg up` again |
| Remote machine cannot reach `100.x` | it is not on the same tailnet (`tailscale status` there), or the server's node is logged out (`./bisg vpn status`) |
| Everything is slower | expected: a view forces rendering; use `SIM_VIEW=headless` for tests |
| Frames look stale | `SIM_WEB_INTERVAL` is the refresh rate; lower it, at the cost of GPU time |
