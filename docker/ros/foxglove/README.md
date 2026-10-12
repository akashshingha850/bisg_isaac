# Foxglove layouts

Foxglove saves layouts in the app itself (the Layouts menu), so a layout you built once is there on the next start. This folder
keeps an exported copy in the repo, to move it to another machine or to recover it.

Save:   Layouts menu -> your layout -> "Export layout as JSON" -> save here as `raptor.json` (commit it).
Load:   Layouts menu -> "Import from file..." -> `docker/ros/foxglove/raptor.json`.

Connection: `./bisg ros start foxglove` (on by default, docker/ros/tools.yaml), then "Open connection -> Foxglove WebSocket"
-> `ws://<host>:8765` (`ws://127.0.0.1:8765` on the sim host, the tailnet address from `./bisg tailscale status` from afar).
The panels of the first layout (all /drone_1): 3D (TF, odom, ZED cloud), Image x3 (ZED left, ZED depth, chase), Plot (ToF vs
ground truth, odom vs /drone_1/state/pose), Topic Graph, Raw Messages, Log (/rosout).
The layout file is exported from the app, not hand-written: its panel settings are Foxglove's own format.

## Debugging: what does the app see?
`scripts/foxglove_probe.py -H <host> -f zed -s /drone_1/zed/zed_node/odom` connects like the app, lists the advertised topics and measures
rate and size of the ones you subscribe to (stdlib, runs on the host). A topic missing there is missing in the app: usually a message
package the bridge container lacks (`docker exec bisg-ros grep "Failed to load schema" /tmp/foxglove.log`; today: `zed_msgs` status
topics and the two `theora` topics).

Bandwidth (measured 2026-10-11, ZED HD720): raw left image 3.6 MB x 16 Hz = 58 MB/s, raw depth the same, point cloud 1.8 MB x 10 Hz =
18 MB/s; `.../left/color/rect/image/compressed` is 194 KiB x 16 Hz = 3 MB/s. Over a remote link use the `/compressed` image topic and
leave the raw depth and cloud for the sim host's LAN.
