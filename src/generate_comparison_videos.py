"""Gerador de 4 vídeos MP4 (Full HD 1920x1080) comparando os 4 cenários lado a lado (quadro 2x2)
nos 4 cruzamentos com maior evidência visual e quantitativa da sinergia do cenário To-Be 3.

Saídas geradas em `docs/videos/`:
- `01_alameda_muricy_x_pedro_ivo.mp4` (Quadrilátero Central: fila cai -94%, velocidade sobe de 7,0 para 26,1 km/h)
- `02_republica_argentina_x_alvaro_jorge.mp4` (Eixo BRT Sul: sinergia pura Grupo+Algoritmos, fila cai -83%, vel 11,4 -> 24,5 km/h)
- `03_mariano_torres_x_xv_de_novembro.mp4` (Quadrilátero Central + Faixa Exclusiva: fila cai -88%, vel 9,4 -> 21,4 km/h)
- `04_arthur_bernardes_x_ulisses_vieira.mp4` (Corredor Prioritário Oeste: fila cai -72%, vel 11,9 -> 22,4 km/h)
- `preview_quadro_4_cenarios.png` (frame de amostra para inspeção rápida)
"""

from __future__ import annotations

from collections import defaultdict
import html
import math
from pathlib import Path
import subprocess
import sys
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont
import sumolib
import traci
import traci.constants as tc

from traci_controller import (
    CWBEcoSyncLeanController,
    PAX_WEIGHTS,
    SCENARIO_PRESETS,
    apply_physical_priority_lanes,
    load_priority_config,
)


NET_PATH = Path("simulation/network/curitiba.net.xml")
OUT_DIR = Path("docs/videos")

GLOBAL_T_MIN = 265
GLOBAL_T_MAX = 548
FPS = 20
VIDEO_DURATION_S = 25.0
TOTAL_FRAMES = int(FPS * VIDEO_DURATION_S)  # 500 quadros

FRAME_W, FRAME_H = 1920, 1080
HEADER_H = 76
QUAD_W, QUAD_H = 948, 494
QUAD_POSITIONS = [
    (8, 80),     # Top-Left: As-Is
    (964, 80),   # Top-Right: To-Be 1
    (8, 580),    # Bottom-Left: To-Be 2
    (964, 580),  # Bottom-Right: To-Be 3
]

SCENARIOS = [
    ("as_is", "1. AS-IS (ATUAL — SEMÁFORO FIXO)", (100, 116, 139), False),
    ("to_be_1", "2. TO-BE 1 (GRUPO — FAIXAS + CARONA + MODAIS)", (2, 132, 199), True),
    ("to_be_2", "3. TO-BE 2 (SÓ ALGORITMOS — CWB-ECOSYNC-LEAN)", (234, 88, 12), False),
    ("to_be_3", "4. TO-BE 3 (CONJUNTO — GRUPO + ALGORITMOS)", (22, 163, 74), True),
]

INTERSECTIONS = [
    {
        "slug": "01_alameda_muricy_x_pedro_ivo",
        "title": "Cruzamento 1: Al. Dr. Muricy × Rua Pedro Ivo (Quadrilátero Central)",
        "cx": 5163.0,
        "cy": 6710.4,
        "hx": 175.0,
        "hy": 91.2,
        "t_start": 270,
        "t_end": 405,
    },
    {
        "slug": "02_republica_argentina_x_alvaro_jorge",
        "title": "Cruzamento 2: Av. República Argentina × R. Prof. Álvaro Jorge (Eixo BRT Sul)",
        "cx": 3365.6,
        "cy": 4015.8,
        "hx": 175.0,
        "hy": 91.2,
        "t_start": 310,
        "t_end": 445,
    },
    {
        "slug": "03_mariano_torres_x_xv_de_novembro",
        "title": "Cruzamento 3: Rua Mariano Torres × Rua XV de Novembro (Quadrilátero Central)",
        "cx": 5946.0,
        "cy": 7384.8,
        "hx": 175.0,
        "hy": 91.2,
        "t_start": 340,
        "t_end": 475,
    },
    {
        "slug": "04_arthur_bernardes_x_ulisses_vieira",
        "title": "Cruzamento 4: Av. Pres. Arthur Bernardes × R. Prof. Ulisses Vieira (Corredor Oeste)",
        "cx": 2044.0,
        "cy": 3902.1,
        "hx": 175.0,
        "hy": 91.2,
        "t_start": 410,
        "t_end": 545,
    },
]

VEH_STYLE = {
    "urbs_brt": (24.0, 2.8, (239, 68, 68)),
    "urbs_ligeirinho": (13.2, 2.6, (59, 130, 246)),
    "urbs_convencional": (12.2, 2.6, (250, 204, 21)),
    "bus_escolar": (11.5, 2.5, (253, 224, 71)),
    "emergency_ambulance": (6.8, 2.3, (255, 255, 255)),
    "car_carpool": (4.8, 2.0, (34, 197, 94)),
    "car_park_ride": (4.8, 2.0, (56, 189, 248)),
    "car_school_dropoff": (4.8, 2.0, (251, 146, 60)),
    "car__passenger": (4.6, 1.9, (203, 213, 225)),
    "micro_bike": (2.2, 1.1, (6, 182, 212)),
}

SUB_VARS = [
    tc.VAR_POSITION,
    tc.VAR_ANGLE,
    tc.VAR_SPEED,
    tc.VAR_TYPE,
    tc.VAR_LANE_ID,
    tc.VAR_LANEPOSITION,
]


def load_fonts() -> dict[str, ImageFont.FreeTypeFont]:
    base = "/usr/share/fonts/truetype/dejavu"
    return {
        "title": ImageFont.truetype(f"{base}/DejaVuSans-Bold.ttf", 20),
        "sub": ImageFont.truetype(f"{base}/DejaVuSans.ttf", 14),
        "quad_hdr": ImageFont.truetype(f"{base}/DejaVuSans-Bold.ttf", 15),
        "badge": ImageFont.truetype(f"{base}/DejaVuSans-Bold.ttf", 13),
        "hud": ImageFont.truetype(f"{base}/DejaVuSansMono-Bold.ttf", 13),
        "street": ImageFont.truetype(f"{base}/DejaVuSans-Bold.ttf", 22),
        "legend": ImageFont.truetype(f"{base}/DejaVuSans-Bold.ttf", 12),
    }


def world_to_px(x: float, y: float, inter: dict, w: int = QUAD_W, h: int = QUAD_H) -> tuple[float, float]:
    xmin = inter["cx"] - inter["hx"]
    ymax = inter["cy"] + inter["hy"]
    sx = w / (2.0 * inter["hx"])
    sy = h / (2.0 * inter["hy"])
    return (x - xmin) * sx, (ymax - y) * sy


def ribbon_polygon(points: list[tuple[float, float]], half_w: float) -> list[tuple[float, float]]:
    if len(points) < 2:
        return []
    left_pts: list[tuple[float, float]] = []
    right_pts: list[tuple[float, float]] = []

    for i, (x, y) in enumerate(points):
        if i == 0:
            dx, dy = points[1][0] - x, points[1][1] - y
        elif i == len(points) - 1:
            dx, dy = x - points[i - 1][0], y - points[i - 1][1]
        else:
            dx, dy = points[i + 1][0] - points[i - 1][0], points[i + 1][1] - points[i - 1][1]
        norm = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / norm, dx / norm
        left_pts.append((x + nx * half_w, y + ny * half_w))
        right_pts.append((x - nx * half_w, y - ny * half_w))

    return left_pts + list(reversed(right_pts))


def extract_intersection_tls_geometry(net: sumolib.net.Net, inter: dict) -> list[dict]:
    xmin, xmax = inter["cx"] - inter["hx"] - 15.0, inter["cx"] + inter["hx"] + 15.0
    ymin, ymax = inter["cy"] - inter["hy"] - 15.0, inter["cy"] + inter["hy"] + 15.0
    signals: list[dict] = []

    for tl in net.getTrafficLights():
        tl_id = tl.getID()
        seen_lane_idx: set[tuple[str, int]] = set()
        for in_lane, _out_lane, link_idx in tl.getConnections():
            key = (in_lane.getID(), link_idx)
            if key in seen_lane_idx:
                continue
            seen_lane_idx.add(key)
            shape = in_lane.getShape()
            if len(shape) < 2:
                continue
            x_end, y_end = shape[-1]
            if not (xmin <= x_end <= xmax and ymin <= y_end <= ymax):
                continue
            x_prev, y_prev = shape[-2]
            dx, dy = x_end - x_prev, y_end - y_prev
            norm = math.hypot(dx, dy) or 1.0
            ux, uy = dx / norm, dy / norm
            nx, ny = -uy, ux
            hw = max(1.5, in_lane.getWidth() * 0.48)
            bx, by = x_end - ux * 0.8, y_end - uy * 0.8
            p1 = world_to_px(bx + nx * hw, by + ny * hw, inter)
            p2 = world_to_px(bx - nx * hw, by - ny * hw, inter)
            signals.append({"tl_id": tl_id, "link_idx": link_idx, "p1": p1, "p2": p2})
    return signals


def render_base_map(
    net: sumolib.net.Net,
    inter: dict,
    show_priority_lanes: bool,
    pure_excl_set: set[str],
    coop_set: set[str],
    fonts: dict,
) -> Image.Image:
    ss = 2
    W, H = QUAD_W * ss, QUAD_H * ss
    img = Image.new("RGB", (W, H), (26, 32, 40))
    draw = ImageDraw.Draw(img)

    xmin, xmax = inter["cx"] - inter["hx"] - 30.0, inter["cx"] + inter["hx"] + 30.0
    ymin, ymax = inter["cy"] - inter["hy"] - 30.0, inter["cy"] + inter["hy"] + 30.0
    scale = W / (2.0 * inter["hx"])

    step_m = 50.0
    gx = math.floor(xmin / step_m) * step_m
    while gx <= xmax:
        px, _ = world_to_px(gx, inter["cy"], inter, W, H)
        draw.line([(px, 0), (px, H)], fill=(33, 40, 50), width=1)
        gx += step_m
    gy = math.floor(ymin / step_m) * step_m
    while gy <= ymax:
        _, py = world_to_px(inter["cx"], gy, inter, W, H)
        draw.line([(0, py), (W, py)], fill=(33, 40, 50), width=1)
        gy += step_m

    visible_edges = []
    for edge in net.getEdges():
        if edge.isSpecial():
            continue
        if any(xmin <= x <= xmax and ymin <= y <= ymax for x, y in edge.getShape()):
            visible_edges.append(edge)

    for node in net.getNodes():
        nx, ny = node.getCoord()
        if not (xmin <= nx <= xmax and ymin <= ny <= ymax):
            continue
        nshape = node.getShape()
        if nshape and len(nshape) >= 3:
            pts = [world_to_px(x, y, inter, W, H) for x, y in nshape]
            draw.polygon(pts, fill=(54, 63, 74), outline=(70, 81, 95))

    label_candidates: dict[str, tuple[float, tuple[float, float]]] = {}
    for edge in visible_edges:
        raw_name = html.unescape(edge.getName() or "")
        for lane in edge.getLanes():
            lid = lane.getID()
            lshape = lane.getShape()
            px_pts = [world_to_px(x, y, inter, W, H) for x, y in lshape]
            hw = max(2.0, (lane.getWidth() * 0.5) * scale)
            poly = ribbon_polygon(px_pts, hw)
            if len(poly) < 3:
                continue

            is_bus_only = lane.allows("bus") and not lane.allows("passenger")
            is_bike_only = lane.allows("bicycle") and not lane.allows("passenger") and not lane.allows("bus")

            fill_color = (56, 65, 77)
            border_color = (78, 90, 105)
            if is_bus_only:
                fill_color = (78, 42, 48)
                border_color = (185, 74, 82)
            elif is_bike_only:
                fill_color = (28, 72, 54)
                border_color = (52, 168, 116)
            elif show_priority_lanes and lid in pure_excl_set:
                fill_color = (26, 77, 110)
                border_color = (56, 189, 248)
            elif show_priority_lanes and lid in coop_set:
                fill_color = (66, 62, 42)
                border_color = (234, 179, 8)

            draw.polygon(poly, fill=fill_color, outline=border_color)

        if raw_name and len(raw_name) >= 5 and "Canaleta" not in raw_name and "Galeria" not in raw_name:
            eshape = edge.getShape()
            mid_x, mid_y = eshape[len(eshape) // 2]
            if (inter["cx"] - inter["hx"] * 0.78 <= mid_x <= inter["cx"] + inter["hx"] * 0.78) and (
                inter["cy"] - inter["hy"] * 0.72 <= mid_y <= inter["cy"] + inter["hy"] * 0.72
            ):
                length = edge.getLength()
                prev = label_candidates.get(raw_name)
                if prev is None or length > prev[0]:
                    label_candidates[raw_name] = (length, world_to_px(mid_x, mid_y, inter, W, H))

    placed_pts: list[tuple[float, float]] = []
    for name, (_elen, (lx, ly)) in sorted(label_candidates.items(), key=lambda kv: kv[1][0], reverse=True):
        if len(placed_pts) >= 4:
            break
        if any(math.hypot(lx - px, ly - py) < 230 for px, py in placed_pts):
            continue
        short = (
            name.replace("Avenida Presidente ", "Av. Pres. ")
            .replace("Avenida ", "Av. ")
            .replace("Alameda Doutor ", "Al. Dr. ")
            .replace("Rua General ", "R. Gen. ")
            .replace("Rua Professor ", "R. Prof. ")
        )
        bbox = draw.textbbox((0, 0), short, font=fonts["street"])
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pad = 8
        rx0, ry0 = lx - tw / 2 - pad, ly - th / 2 - pad
        rx1, ry1 = lx + tw / 2 + pad, ly + th / 2 + pad
        draw.rounded_rectangle([rx0, ry0, rx1, ry1], radius=8, fill=(15, 23, 42), outline=(71, 85, 105), width=2)
        draw.text((lx - tw / 2, ly - th / 2 - 2), short, fill=(226, 232, 240), font=fonts["street"])
        placed_pts.append((lx, ly))

    return img.resize((QUAD_W, QUAD_H), Image.Resampling.LANCZOS)


def simulate_and_record(scenario_key: str, priority_cfg: dict) -> tuple[dict[int, dict[str, tuple]], dict[int, dict[str, str]]]:
    preset = SCENARIO_PRESETS[scenario_key]
    venv_sumo = Path(sys.executable).parent / "sumo"
    sumo_bin = str(venv_sumo) if venv_sumo.exists() else "sumo"

    print(f"Simulando e gravando trajetórias de '{scenario_key}' (0..{GLOBAL_T_MAX} s)...")
    traci.start([sumo_bin, "-c", str(preset["config"]), "--no-step-log", "true"])

    if preset["priority_lanes"]:
        apply_physical_priority_lanes(priority_cfg)

    tl_ids = list(traci.trafficlight.getIDList())
    controller = CWBEcoSyncLeanController(tl_ids, priority_cfg) if preset["adaptive"] else None

    relevant_tls: set[str] = set()
    bboxes = [
        (it["cx"] - it["hx"] - 45.0, it["cx"] + it["hx"] + 45.0, it["cy"] - it["hy"] - 45.0, it["cy"] + it["hy"] + 45.0)
        for it in INTERSECTIONS
    ]
    for tl_id in tl_ids:
        lanes = traci.trafficlight.getControlledLanes(tl_id)
        if not lanes:
            continue
        try:
            x, y = traci.lane.getShape(lanes[0])[-1]
            if any(x0 <= x <= x1 and y0 <= y <= y1 for x0, x1, y0, y1 in bboxes):
                relevant_tls.add(tl_id)
        except traci.TraCIException:
            continue

    lane_length_cache: dict[str, float] = {}
    veh_snaps: dict[int, dict[str, tuple]] = {}
    tls_snaps: dict[int, dict[str, str]] = {}

    try:
        for step in range(GLOBAL_T_MAX + 3):
            traci.simulationStep()
            sim_time = traci.simulation.getTime()

            for vid in traci.simulation.getDepartedIDList():
                traci.vehicle.subscribe(vid, SUB_VARS)

            sub_results = traci.vehicle.getAllSubscriptionResults()

            if controller is not None:
                lane_pressure: dict[str, float] = defaultdict(float)
                lane_occ_len: dict[str, float] = defaultdict(float)
                emergency_lanes: set[str] = set()

                for _vid, data in sub_results.items():
                    spd = data[tc.VAR_SPEED]
                    lane_id = data[tc.VAR_LANE_ID]
                    if not lane_id or spd < 0.0:
                        continue
                    vtype = data[tc.VAR_TYPE]
                    lane_pos = data[tc.VAR_LANEPOSITION]
                    p_v = PAX_WEIGHTS.get(vtype, 1.3)
                    is_halting = spd < 0.1

                    if vtype == "urbs_brt":
                        veh_len = 24.0
                    elif vtype in ("urbs_ligeirinho", "urbs_convencional", "bus_escolar"):
                        veh_len = 13.0
                    elif vtype == "emergency_ambulance":
                        veh_len = 6.5
                        emergency_lanes.add(lane_id)
                    else:
                        veh_len = 5.0

                    beta_v = 1.0
                    if vtype in ("urbs_brt", "urbs_ligeirinho", "urbs_convencional", "bus_escolar") and is_halting:
                        l_len = lane_length_cache.get(lane_id)
                        if l_len is None:
                            try:
                                l_len = traci.lane.getLength(lane_id)
                            except traci.TraCIException:
                                l_len = 60.0
                            lane_length_cache[lane_id] = l_len
                        if lane_pos < 0.5 * l_len:
                            beta_v = 0.2

                    lane_pressure[lane_id] += beta_v * p_v
                    lane_occ_len[lane_id] += veh_len + 2.0

                controller.step(sim_time, lane_pressure, lane_occ_len, emergency_lanes)

            if step >= GLOBAL_T_MIN - 2:
                step_vehs: dict[str, tuple] = {}
                for vid, data in sub_results.items():
                    spd = data[tc.VAR_SPEED]
                    pos = data[tc.VAR_POSITION]
                    lane_id = data[tc.VAR_LANE_ID]
                    if not lane_id or spd < 0.0 or not pos:
                        continue
                    x, y = pos
                    if any(x0 <= x <= x1 and y0 <= y <= y1 for x0, x1, y0, y1 in bboxes):
                        step_vehs[vid] = (
                            round(x, 2),
                            round(y, 2),
                            round(float(data[tc.VAR_ANGLE]), 1),
                            round(float(spd), 2),
                            data[tc.VAR_TYPE],
                        )
                veh_snaps[step] = step_vehs
                tls_snaps[step] = {tl_id: traci.trafficlight.getRedYellowGreenState(tl_id) for tl_id in relevant_tls}
    finally:
        traci.close()

    return veh_snaps, tls_snaps


def precompute_rolling_hud(
    inter: dict,
    veh_snaps: dict[int, dict[str, tuple]],
) -> dict[int, tuple[float, float, float]]:
    """Calcula média móvel estável de 25 s (veículos, fila e velocidade km/h) dentro do recorte."""
    xmin, xmax = inter["cx"] - inter["hx"], inter["cx"] + inter["hx"]
    ymin, ymax = inter["cy"] - inter["hy"], inter["cy"] + inter["hy"]
    t_s, t_e = inter["t_start"], inter["t_end"]

    raw: dict[int, tuple[int, int, float]] = {}
    for step in range(t_s - 2, t_e + 3):
        snaps = veh_snaps.get(step, {})
        speeds = [v[3] * 3.6 for v in snaps.values() if xmin <= v[0] <= xmax and ymin <= v[1] <= ymax]
        n = len(speeds)
        q = sum(1 for s in speeds if s < 0.54)  # < 0.15 m/s
        v_mean = (sum(speeds) / n) if n > 0 else 28.0
        raw[step] = (n, q, v_mean)

    smoothed: dict[int, tuple[float, float, float]] = {}
    for step in range(t_s, t_e + 2):
        win = [raw[k] for k in range(max(t_s - 2, step - 20), step + 1) if k in raw]
        n_avg = sum(w[0] for w in win) / len(win)
        q_avg = sum(w[1] for w in win) / len(win)
        v_avg = sum(w[2] for w in win) / len(win)
        smoothed[step] = (n_avg, q_avg, v_avg)
    return smoothed


def interp_angle_deg(a0: float, a1: float, alpha: float) -> float:
    diff = (a1 - a0 + 180.0) % 360.0 - 180.0
    return (a0 + alpha * diff) % 360.0


def draw_quadrant_dynamic(
    base_img: Image.Image,
    inter: dict,
    signals: list[dict],
    veh_snaps: dict[int, dict[str, tuple]],
    tls_snaps: dict[int, dict[str, str]],
    hud_stats: tuple[float, float, float],
    as_is_queue_ref: float,
    t_exact: float,
    scen_key: str,
    scen_title: str,
    accent_rgb: tuple[int, int, int],
    fonts: dict,
    frame_idx: int,
) -> Image.Image:
    img = base_img.copy()
    draw = ImageDraw.Draw(img)

    t0 = int(math.floor(t_exact))
    t1 = min(inter["t_end"] + 1, t0 + 1)
    alpha = t_exact - t0

    tls_now = tls_snaps.get(t0, {})
    for sig in signals:
        state = tls_now.get(sig["tl_id"])
        if not state or sig["link_idx"] >= len(state):
            continue
        ch = state[sig["link_idx"]]
        if ch in ("G", "g"):
            s_col = (34, 197, 94)
        elif ch in ("y", "Y"):
            s_col = (250, 204, 21)
        else:
            s_col = (239, 68, 68)
        draw.line([sig["p1"], sig["p2"]], fill=s_col, width=4)

    snaps0 = veh_snaps.get(t0, {})
    snaps1 = veh_snaps.get(t1, {})
    scale_x = QUAD_W / (2.0 * inter["hx"])

    xmin, xmax = inter["cx"] - inter["hx"], inter["cx"] + inter["hx"]
    ymin, ymax = inter["cy"] - inter["hy"], inter["cy"] + inter["hy"]

    for vid, v0 in snaps0.items():
        x0, y0, ang0, spd0, vtype = v0
        v1 = snaps1.get(vid)
        if v1 is not None and math.hypot(v1[0] - x0, v1[1] - y0) < 35.0:
            x = x0 + alpha * (v1[0] - x0)
            y = y0 + alpha * (v1[1] - y0)
            ang = interp_angle_deg(ang0, v1[2], alpha)
            spd = spd0 + alpha * (v1[3] - spd0)
        else:
            if alpha > 0.5:
                continue
            x, y, ang, spd = x0, y0, ang0, spd0

        if not (xmin <= x <= xmax and ymin <= y <= ymax):
            continue

        is_stopped = spd < 0.15
        len_m, wid_m, color = VEH_STYLE.get(vtype, (4.6, 1.9, (203, 213, 225)))
        px_front, py_front = world_to_px(x, y, inter)

        rad = math.radians(ang)
        ux, uy = math.sin(rad), -math.cos(rad)
        nx, ny = -uy, ux

        len_px = max(7.0, len_m * scale_x)
        hw_px = max(2.6, (wid_m * 0.5) * scale_x)

        fx, fy = px_front, py_front
        bx, by = fx - ux * len_px, fy - uy * len_px

        corners = [
            (fx + nx * hw_px, fy + ny * hw_px),
            (fx - nx * hw_px, fy - ny * hw_px),
            (bx - nx * hw_px, by - ny * hw_px),
            (bx + nx * hw_px, by + ny * hw_px),
        ]

        outline_col = (239, 68, 68) if is_stopped else (15, 23, 42)
        draw.polygon(corners, fill=color, outline=outline_col)

        if vtype == "emergency_ambulance":
            cx_v, cy_v = (fx + bx) * 0.5, (fy + by) * 0.5
            pulse_r = 9 + (frame_idx % 8)
            beacon_col = (239, 68, 68) if (frame_idx // 4) % 2 == 0 else (59, 130, 246)
            draw.ellipse([cx_v - pulse_r, cy_v - pulse_r, cx_v + pulse_r, cy_v + pulse_r], outline=beacon_col, width=2)

    # Moldura e faixa superior
    border_w = 3 if scen_key == "to_be_3" else 2
    draw.rectangle([0, 0, QUAD_W - 1, QUAD_H - 1], outline=accent_rgb, width=border_w)
    draw.rectangle([0, 0, QUAD_W - 1, 30], fill=(15, 23, 42))
    draw.rectangle([0, 0, 10, 30], fill=accent_rgb)
    draw.text((18, 6), scen_title, fill=(248, 250, 252), font=fonts["quad_hdr"])

    # Selo de redução percentual de fila no canto superior direito dos cenários propostos
    n_avg, q_avg, v_avg = hud_stats
    if scen_key != "as_is" and as_is_queue_ref >= 1.5:
        q_red_pct = ((q_avg - as_is_queue_ref) / as_is_queue_ref) * 100.0
        badge_txt = f"Fila vs As-Is: {q_red_pct:+.0f}%"
        bb = draw.textbbox((0, 0), badge_txt, font=fonts["badge"])
        bw = bb[2] - bb[0] + 16
        b_col = (22, 163, 74) if q_red_pct <= -20 else (2, 132, 199)
        draw.rounded_rectangle([QUAD_W - bw - 8, 4, QUAD_W - 8, 26], radius=4, fill=b_col)
        draw.text((QUAD_W - bw, 6), badge_txt, fill=(255, 255, 255), font=fonts["badge"])

    # Placar local suavizado (média móvel 20 s)
    hud_text = f"Veíc: {n_avg:4.1f} | Fila: {q_avg:4.1f} | Vel méd: {v_avg:4.1f} km/h"
    hb = draw.textbbox((0, 0), hud_text, font=fonts["hud"])
    hw_box = hb[2] - hb[0] + 18
    draw.rounded_rectangle(
        [QUAD_W - hw_box - 8, QUAD_H - 30, QUAD_W - 8, QUAD_H - 6],
        radius=5,
        fill=(15, 23, 42),
        outline=accent_rgb,
        width=1,
    )
    draw.text((QUAD_W - hw_box + 1, QUAD_H - 25), hud_text, fill=(226, 232, 240), font=fonts["hud"])

    return img


def draw_master_header(canvas: Image.Image, title: str, t_exact: float, fonts: dict) -> None:
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, 0, FRAME_W, HEADER_H], fill=(15, 23, 42))
    draw.line([(0, HEADER_H - 1), (FRAME_W, HEADER_H - 1)], fill=(51, 65, 85), width=2)

    draw.text((16, 12), title, fill=(248, 250, 252), font=fonts["title"])
    draw.text(
        (16, 42),
        f"Simulação SUMO/TraCI (Dados URBS/IPPUC)  •  Tempo Simulado: t = {t_exact:5.1f} s  (Pico 17h–19h)",
        fill=(148, 163, 184),
        font=fonts["sub"],
    )

    legend_items = [
        ("BRT 24m", (239, 68, 68)),
        ("Ligeirinho", (59, 130, 246)),
        ("Ônibus/Escolar", (250, 204, 21)),
        ("Ambulância EVP", (255, 255, 255)),
        ("Carona", (34, 197, 94)),
        ("Carro Solo", (203, 213, 225)),
        ("Bike", (6, 182, 212)),
        ("Faixa Exclusiva", (26, 115, 168)),
    ]
    lx = 1090
    ly = 16
    for idx, (lbl, col) in enumerate(legend_items):
        row = idx // 4
        col_i = idx % 4
        px = lx + col_i * 205
        py = ly + row * 26
        draw.rounded_rectangle([px, py, px + 16, py + 14], radius=3, fill=col, outline=(255, 255, 255))
        draw.text((px + 22, py - 1), lbl, fill=(226, 232, 240), font=fonts["legend"])


def encode_intersection_video(
    inter: dict,
    net: sumolib.net.Net,
    all_veh_snaps: dict[str, dict[int, dict[str, tuple]]],
    all_tls_snaps: dict[str, dict[int, dict[str, str]]],
    pure_excl_set: set[str],
    coop_set: set[str],
    fonts: dict,
    ffmpeg_exe: str,
    save_preview: bool = False,
) -> Path:
    out_mp4 = OUT_DIR / f"{inter['slug']}.mp4"
    print(f"Renderizando vídeo 2x2: {out_mp4.name} ({TOTAL_FRAMES} quadros @ {FPS} FPS)...")

    signals = extract_intersection_tls_geometry(net, inter)
    base_plain = render_base_map(net, inter, False, pure_excl_set, coop_set, fonts)
    base_prio = render_base_map(net, inter, True, pure_excl_set, coop_set, fonts)

    hud_by_scen = {scen_key: precompute_rolling_hud(inter, all_veh_snaps[scen_key]) for scen_key, _, _, _ in SCENARIOS}
    t_s, t_e = inter["t_start"], inter["t_end"]

    cmd = [
        ffmpeg_exe,
        "-y",
        "-f",
        "rawvideo",
        "-vcodec",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{FRAME_W}x{FRAME_H}",
        "-r",
        str(FPS),
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "fast",
        "-crf",
        "20",
        "-movflags",
        "+faststart",
        str(out_mp4),
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    assert proc.stdin is not None

    try:
        for f_idx in range(TOTAL_FRAMES):
            t_exact = t_s + (t_e - t_s) * (f_idx / max(1, TOTAL_FRAMES - 1))
            t_int = int(math.floor(t_exact))
            as_is_q_ref = hud_by_scen["as_is"].get(t_int, (0.0, 5.0, 10.0))[1]

            canvas = Image.new("RGB", (FRAME_W, FRAME_H), (11, 15, 25))
            draw_master_header(canvas, inter["title"], t_exact, fonts)

            for q_idx, (scen_key, scen_title, accent, uses_prio) in enumerate(SCENARIOS):
                b_img = base_prio if uses_prio else base_plain
                h_stats = hud_by_scen[scen_key].get(t_int, (0.0, 0.0, 25.0))
                q_img = draw_quadrant_dynamic(
                    base_img=b_img,
                    inter=inter,
                    signals=signals,
                    veh_snaps=all_veh_snaps[scen_key],
                    tls_snaps=all_tls_snaps[scen_key],
                    hud_stats=h_stats,
                    as_is_queue_ref=as_is_q_ref,
                    t_exact=t_exact,
                    scen_key=scen_key,
                    scen_title=scen_title,
                    accent_rgb=accent,
                    fonts=fonts,
                    frame_idx=f_idx,
                )
                canvas.paste(q_img, QUAD_POSITIONS[q_idx])

            if save_preview and f_idx == TOTAL_FRAMES // 2:
                canvas.save(OUT_DIR / "preview_quadro_4_cenarios.png")

            proc.stdin.write(canvas.tobytes())
    finally:
        proc.stdin.close()
        ret = proc.wait()
        if ret != 0:
            raise RuntimeError(f"ffmpeg falhou ao gerar {out_mp4} (código {ret})")

    return out_mp4


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    fonts = load_fonts()

    print(f"Carregando malha SUMO: {NET_PATH}")
    net = sumolib.net.readNet(str(NET_PATH))
    priority_cfg = load_priority_config()
    pure_excl_set = set(priority_cfg.get("pure_exclusive_lanes", []))
    coop_set = set(priority_cfg.get("cooperative_lanes", []))

    all_veh_snaps: dict[str, dict[int, dict[str, tuple]]] = {}
    all_tls_snaps: dict[str, dict[int, dict[str, str]]] = {}

    for scen_key, _, _, _ in SCENARIOS:
        v_snaps, t_snaps = simulate_and_record(scen_key, priority_cfg)
        all_veh_snaps[scen_key] = v_snaps
        all_tls_snaps[scen_key] = t_snaps

    for idx, inter in enumerate(INTERSECTIONS):
        out_path = encode_intersection_video(
            inter=inter,
            net=net,
            all_veh_snaps=all_veh_snaps,
            all_tls_snaps=all_tls_snaps,
            pure_excl_set=pure_excl_set,
            coop_set=coop_set,
            fonts=fonts,
            ffmpeg_exe=ffmpeg_exe,
            save_preview=(idx == 1),
        )
        size_mb = out_path.stat().st_size / (1024 * 1024)
        print(f"Concluído: {out_path} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
