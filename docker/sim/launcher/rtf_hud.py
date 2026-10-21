"""
Real-time factor (sim seconds per wall second) as one more line of Kit's own viewport HUD, under "FPS".

Kit's stats HUD has no plug-in point: `ViewportStatsGroup` is handed a fixed factory list. So we wrap the group's
constructor to add one `ViewportStatistic` to the right-hand "Viewport HUD" group, then toggle the HUD's visible setting
once so Kit rebuilds it. Shown whenever the HUD is (Display > Heads Up Display). Any failure only logs a warning.
"""
import logging
import time

import carb

LOG = logging.getLogger("launch")


def install(get_sim_time, window_s: float = 1.0):
    import omni.kit.viewport.window.stats as stats  # noqa: WPS433
    from omni.kit.viewport.utility import get_active_viewport  # noqa: WPS433

    class RtfStat(stats.ViewportStatistic):
        def __init__(self, *args, **kwargs):
            super().__init__("RTF", *args, **kwargs)
            self._wall, self._sim = time.monotonic(), float(get_sim_time())
            self._text = "Sim speed: --"

        def update_stats(self, update_info):
            now = time.monotonic()
            if now - self._wall >= window_s:
                sim = float(get_sim_time())
                rtf = max(0.0, sim - self._sim) / (now - self._wall)
                self._text = f"Sim speed: {rtf:.2f}x real time"
                self._wall, self._sim = now, sim
            return [self._text]

    if getattr(stats.ViewportStatsGroup, "_bisg_rtf", False):
        return
    orig_init = stats.ViewportStatsGroup.__init__

    def init(self, factories, name, alignment, viewport_api):
        if name == "Viewport HUD":
            factories = list(factories)
            factories.insert(1, RtfStat)         # right under FPS
        orig_init(self, factories, name, alignment, viewport_api)

    stats.ViewportStatsGroup.__init__ = init
    stats.ViewportStatsGroup._bisg_rtf = True

    # Rebuild the HUD once so the new line appears: it is rebuilt whenever its visible setting flips.
    key = f"/persistent/app/viewport/{get_active_viewport().id}/hud/visible"
    settings = carb.settings.get_settings()
    was = settings.get(key)
    if was is None or was:
        settings.set(key, False)
        settings.set(key, True)
    LOG.info("rtf hud: 'Sim speed' line added to the viewport HUD")
