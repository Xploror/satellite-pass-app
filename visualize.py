import math
import os
import sys

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

from lib.config import load_mission_info
from lib.providers.n2yo import fetch_trajectory
from lib.systems import Lab

CONF_PATH = os.getenv("CONFIG_FILENAME", "config_files/conf_default")
DEFAULT_OUTPUT = "visualizations/satellite_pass.gif"

EARTH_RADIUS_KM = 6371.0  # Earth mean radius
WINDOW_SEC = 200  # N2YO's documented cap for the positions endpoint
SAMPLE_INTERVAL_SEC = 10  # matches main.py's real polling cadence


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


def average_altitude(trajectories: dict, sats: list) -> float:
    """
    Averages each tracked satellite's first fetched altitude sample, in km.
    """

    first_samples = [trajectories[sat.norad_id][0]["alt"] for sat in sats]
    return sum(first_samples) / len(first_samples)


def frame_steps(trajectories: dict, sats: list, window_sec: int, sample_every: int) -> list:
    """
    Picks the trajectory sample indices to render, one every `sample_every` seconds.
    """

    available = min(len(trajectories[sat.norad_id]) for sat in sats)
    last_step = min(window_sec, available - 1)
    return list(range(0, last_step + 1, sample_every))


def build_animation(sats: list, lab: Lab, trajectories: dict, steps: list, fov: tuple) -> tuple:
    """
    Builds the animation: static basemap/lab/FOV drawn once, satellite markers updated per frame.
    """

    fov_lats, fov_lons = fov

    fig, ax = plt.subplots(figsize=(10, 6), subplot_kw={"projection": ccrs.PlateCarree()})
    ax.set_global()
    ax.add_feature(cfeature.OCEAN, facecolor="#cfe8f3")
    ax.add_feature(cfeature.LAND, facecolor="#f0efe9")
    ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
    ax.add_feature(cfeature.BORDERS, linewidth=0.3, linestyle=":")
    ax.set_title(f"Satellite passes over the station ({lab.lat:.2f}, {lab.lng:.2f})")

    ax.plot(lab.lng, lab.lat, marker="^", color="black", markersize=9, transform=ccrs.PlateCarree())
    ax.plot(
        fov_lons,
        fov_lats,
        linestyle="--",
        color="black",
        linewidth=1,
        transform=ccrs.PlateCarree(),
    )

    markers = {
        sat.norad_id: ax.plot(
            [],
            [],
            marker="o",
            linestyle="",
            color=sat.color.lower(),  # matplotlib named colors are lowercase-only
            markersize=7,
            label=sat.name,
            transform=ccrs.PlateCarree(),
        )[0]
        for sat in sats
    }
    ax.legend(loc="lower left", fontsize=7)
    time_text = ax.text(0.02, 0.96, "", transform=ax.transAxes, fontsize=9, va="top")

    def update(frame_idx: int) -> list:
        step = steps[frame_idx]
        for sat in sats:
            position = trajectories[sat.norad_id][step]
            markers[sat.norad_id].set_data([position["lng"]], [position["lat"]])
        time_text.set_text(f"t+{step}s")
        return [*markers.values(), time_text]

    anim = FuncAnimation(fig, update, frames=len(steps), interval=200, blit=False)
    return fig, anim


def main() -> None:
    conf_file_path = (
        sys.argv[1] if len(sys.argv) > 1 else None
    ) or CONF_PATH.strip()  # conf_file path PRIORITY: 1. CLI  2. ENV_VAR
    output_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT

    sats, lab, _out_type = load_mission_info(conf_file_path + ".yaml")

    trajectories = fetch_trajectory(sats, lab, sec_ahead=WINDOW_SEC)
    steps = frame_steps(trajectories, sats, WINDOW_SEC, SAMPLE_INTERVAL_SEC)
    fov = fov_boundary(lab, average_altitude(trajectories, sats))

    fig, anim = build_animation(sats, lab, trajectories, steps, fov)

    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    anim.save(output_path, writer="pillow", fps=5)
    plt.close(fig)

    print(f"Saved satellite pass visualization to {output_path}")


if __name__ == "__main__":
    main()
