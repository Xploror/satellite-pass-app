import math
import os
import sys
from datetime import datetime, timezone

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

from lib.access import compute_access
from lib.config import load_mission_info
from lib.providers.n2yo import fetch_trajectory
from lib.providers.tle import fetch_tle
from lib.report_config import ReportConfig
from lib.systems import Lab

CONF_PATH = os.getenv("CONFIG_FILENAME", "config_files/conf_default")
DEFAULT_OUTPUT = "visualizations/satellite_pass.gif"

EARTH_RADIUS_KM = 6371.0  # Earth mean radius
WINDOW_SEC = 1200  # N2YO's documented cap for the positions endpoint
SAMPLE_INTERVAL_SEC = 5  # matches main.py's polling cadence
# MAP_HALF_SPAN_DEG = 70


def fov_boundary(lab: Lab, altitude_km: float, num_points: int = 180) -> tuple:
    """
    Traces a closed dashed circle of lat/lng points marking the lab's field-of-view boundary.
    """

    elev = lab.min_elev
    nadir_angle = math.degrees(
        math.asin(
            (EARTH_RADIUS_KM / (EARTH_RADIUS_KM + altitude_km)) * math.cos(math.radians(elev))
        )
    )
    central_angle = math.radians(90 - elev - nadir_angle)  # Earth central angle, in radians

    lat1 = math.radians(lab.lat)
    lon1 = math.radians(lab.lng)

    lats, lons = [], []
    for step in range(num_points + 1):  # +1 closes the loop back to the bearing=0 point
        bearing = math.radians(step * 360 / num_points)
        lat2 = math.asin(
            math.sin(lat1) * math.cos(central_angle)
            + math.cos(lat1) * math.sin(central_angle) * math.cos(bearing)
        )
        lon2 = lon1 + math.atan2(
            math.sin(bearing) * math.sin(central_angle) * math.cos(lat1),
            math.cos(central_angle) - math.sin(lat1) * math.sin(lat2),
        )
        lats.append(math.degrees(lat2))
        lons.append(math.degrees(lon2))

    return lats, lons


def average_altitude(trajectory: list) -> float:
    """
    Averages one satellite's fetched altitude samples across the fetch window, in km.
    """

    return sum(sample["alt"] for sample in trajectory) / len(trajectory)


def frame_steps(trajectories: dict, sats: list, window_sec: int, sample_every: int) -> list:
    """
    Picks the trajectory sample indices to render, one every `sample_every` seconds.
    """

    available = min(len(trajectories[sat.norad_id]) for sat in sats)
    last_step = min(window_sec, available - 1)
    return list(range(0, last_step + 1, sample_every))


def access_strips(sats: list, trajectories: dict, intervals: dict, last_step: int) -> dict:
    """
    Cuts each satellite's ground track down to the runs that fall inside its access intervals.
    """

    strips: dict = {}
    for sat in sats:
        windows = [(i.aos_utc, i.los_utc) for i in intervals.get(sat.norad_id, [])]
        runs: list = []
        prev_in = False
        for pos in trajectories[sat.norad_id][: last_step + 1]:
            when = datetime.fromtimestamp(pos["timestamp"], timezone.utc)
            inside = any(aos <= when <= los for aos, los in windows)
            # a new run starts at each pass, or when the track wraps across the antimeridian
            if inside and (not prev_in or abs(pos["lng"] - runs[-1][0][-1]) > 180):
                runs.append(([], []))
            if inside:
                runs[-1][0].append(pos["lng"])
                runs[-1][1].append(pos["lat"])
            prev_in = inside
        strips[sat.norad_id] = runs
    return strips


def build_animation(
    sats: list,
    lab: Lab,
    trajectories: dict,
    visibilities: dict,
    steps: list,
    fovs: dict,
    strips: dict,
) -> tuple:
    """
    Builds the animation: static basemap/lab/FOV drawn once, satellite/link artists move per frame.
    """

    fig, ax = plt.subplots(subplot_kw={"projection": ccrs.PlateCarree()}, figsize=(10, 6))
    ax.set_global()  # type: ignore
    # ax.set_extent(
    #     [
    #         lab.lng - MAP_HALF_SPAN_DEG,
    #         lab.lng + MAP_HALF_SPAN_DEG,
    #         max(lab.lat - MAP_HALF_SPAN_DEG, -90),
    #         min(lab.lat + MAP_HALF_SPAN_DEG, 90),
    #     ],
    #     crs=ccrs.PlateCarree(),
    # )  # type: ignore
    ax.add_feature(cfeature.OCEAN, facecolor="#cfe8f3")  # type: ignore
    ax.add_feature(cfeature.LAND, facecolor="#f0efe9")  # type: ignore
    ax.add_feature(cfeature.COASTLINE, linewidth=0.5)  # type: ignore
    ax.add_feature(cfeature.BORDERS, linewidth=0.3, linestyle=":")  # type: ignore
    ax.set_title(
        f"Satellite passes over the station ({lab.lat:.2f}, {lab.lng:.2f}, {lab.alt_m:.0f} m)"
    )

    ax.plot(
        lab.lng,
        lab.lat,
        marker="^",
        color="black",
        markersize=9,
        zorder=1,
        transform=ccrs.PlateCarree(),
    )

    fov_bound = {
        sat.norad_id: ax.plot(
            [],
            [],
            linestyle="--",
            color=sat.color.lower(),
            linewidth=1,
            alpha=0.8,
            zorder=1,
            transform=ccrs.PlateCarree(),
        )[0]
        for sat in sats
    }

    for sat in sats:  # static access strips
        for lngs, lats in strips[sat.norad_id]:
            ax.plot(
                lngs,
                lats,
                color=sat.color.lower(),
                linewidth=1.5,
                alpha=1,
                solid_capstyle="round",
                zorder=1,
                transform=ccrs.PlateCarree(),
            )

    links = {
        sat.norad_id: ax.plot(
            [],
            [],
            linestyle="-",
            color="green",
            linewidth=1,
            alpha=0.8,
            zorder=0,
            transform=ccrs.PlateCarree(),
        )[0]
        for sat in sats
    }

    markers = {
        sat.norad_id: ax.plot(
            [],
            [],
            marker="o",
            linestyle="",
            color=sat.color.lower(),  # matplotlib named colors are lowercase-only
            markersize=7,
            zorder=3,
            label="ID:" + str(sat.norad_id),
            transform=ccrs.PlateCarree(),
        )[0]
        for sat in sats
    }
    # ax.legend(loc="lower left", fontsize=7)
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), fontsize=6, ncol=2)
    fig.subplots_adjust(right=0.82)  # reserve margin so the legend isn't clipped in the saved GIF
    time_text = ax.text(0.02, 0.96, "", transform=ax.transAxes, fontsize=9, va="top")

    def update(frame_idx: int) -> list:
        step = steps[frame_idx]
        for sat in sats:
            position = trajectories[sat.norad_id][step]
            is_visible = visibilities[sat.norad_id][step]
            markers[sat.norad_id].set_data([position["lng"]], [position["lat"]])
            if is_visible:
                links[sat.norad_id].set_data([lab.lng, position["lng"]], [lab.lat, position["lat"]])
                fov_lats, fov_lons = fovs[sat.norad_id]
                fov_bound[sat.norad_id].set_data(fov_lons, fov_lats)
            else:
                links[sat.norad_id].set_data([], [])
                fov_bound[sat.norad_id].set_data([], [])
        time_text.set_text(f"t+{step}s")
        return [*markers.values(), *links.values(), *fov_bound.values(), time_text]

    anim = FuncAnimation(fig, update, frames=len(steps), interval=200, blit=False)
    return fig, anim


def main() -> None:
    conf_file_path = (
        sys.argv[1] if len(sys.argv) > 1 else None
    ) or CONF_PATH.strip()  # conf_file path PRIORITY: 1. CLI  2. ENV_VAR
    output_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT

    sats, lab, out = load_mission_info(conf_file_path + ".yaml")

    # Async part first: access intervals (only present when Mode.Async is "both")
    # config = next((o for o in out if isinstance(o, ReportConfig)), None)
    config = out[-1] if isinstance(out[-1], ReportConfig) else None
    intervals: dict = {}
    if config:
        fetch_tle(sats, config.tle)
        for sat in sats:
            try:
                intervals[sat.norad_id] = compute_access(sat, lab, config)
            except RuntimeError as e:  # SGP4 failure, e.g. decayed satellite
                print(f"Skipping {sat.norad_id}: {e}", file=sys.stderr)

    # Sync part: live N2YO trajectories
    trajectories, visibilties = fetch_trajectory(sats, lab, sec_ahead=WINDOW_SEC)
    steps = frame_steps(trajectories, sats, WINDOW_SEC, SAMPLE_INTERVAL_SEC)
    strips = access_strips(sats, trajectories, intervals, steps[-1])
    fovs = {
        sat.norad_id: fov_boundary(lab, average_altitude(trajectories[sat.norad_id]))
        for sat in sats
    }

    fig, anim = build_animation(sats, lab, trajectories, visibilties, steps, fovs, strips)

    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    anim.save(output_path, writer="pillow", fps=5)
    plt.close(fig)

    print(f"Saved satellite pass visualization to {output_path}")


if __name__ == "__main__":
    main()
