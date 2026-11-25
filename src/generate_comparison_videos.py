"""Gerador de 4 vídeos MP4 (Full HD 1920x1080) comparando os 4 cenários lado a lado (quadro 2x2)
em 4 cruzamentos estratégicos de Curitiba a partir das simulações reais no SUMO/TraCI.

Saídas geradas em `docs/videos/`:
- `01_kennedy_x_republica_argentina.mp4`
- `02_mariano_torres_x_xv_de_novembro.mp4`
- `03_mariano_torres_x_sete_setembro.mp4`
- `04_agua_verde_x_ciclovia_castro.mp4`
- `preview_quadro_4_cenarios.png` (frame de amostra para inspeção rápida)
"""

from __future__ import annotations

from collections import defaultdict
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

# Janela temporal de pico consolidado gravada no vídeo: t = 340s até t = 490s (150s de simulação -> 25s a 20 FPS)
T_START = 340
T_END = 490
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
    ("to_be_2", "3. TO-BE 2 (ALGORITMOS — CWB-ECOSYNC-LEAN)", (234, 88, 12), False),
    ("to_be_3", "4. TO-BE 3 (CONJUNTO — GRUPO + ALGORITMOS)", (22, 163, 74), True),
]

INTERSECTIONS = [
    {
        "slug": "01_kennedy_x_republica_argentina",
        "title": "Cruzamento 1: Av. Pres. Kennedy × Av. República Argentina (Portão / BRT Sul)",
        "cx": 3100.0,
        "cy": 2045.0,
        "hx": 195.0,
        "hy": 101.6,
    },
    {
        "slug": "02_mariano_torres_x_xv_de_novembro",
        "title": "Cruzamento 2: Rua Mariano Torres × Rua XV de Novembro (Quadrilátero Central)",
        "cx": 5935.0,
        "cy": 7415.0,
        "hx": 175.0,
        "hy": 91.2,
    },
    {
        "slug": "03_mariano_torres_x_sete_setembro",
        "title": "Cruzamento 3: Rua Mariano Torres × Av. Sete de Setembro (Centro / Guadalupe)",
        "cx": 6272.0,
        "cy": 6558.0,
        "hx": 160.0,
        "hy": 83.4,
    },
    {
        "slug": "04_agua_verde_x_ciclovia_castro",
        "title": "Cruzamento 4: Av. Água Verde × Ciclovia do Água Verde / R. Silveira Neto",
        "cx": 4585.0,
        "cy": 4565.0,
        "hx": 175.0,
        "hy": 91.2,
    },
]

# Estilo visual (dimensões em metros e cor RGB) por tipo veicular
VEH_STYLE = {
    "urbs_brt": (24.0, 2.8, (239, 68, 68)),             # Vermelho BRT Biarticulado
    "urbs_ligeirinho": (13.2, 2.6, (59, 130, 246)),     # Azul Ligeirinho
    "urbs_convencional": (12.2, 2.6, (250, 204, 21)),   # Amarelo Convencional
    "bus_escolar": (11.5, 2.5, (253, 224, 71)),         # Amarelo Escolar
    "emergency_ambulance": (6.8, 2.3, (255, 255, 255)), # Branco Emergência
    "car_carpool": (4.8, 2.0, (34, 197, 94)),           # Verde Carona
    "car_park_ride": (4.8, 2.0, (56, 189, 248)),        # Azul-claro Park & Ride
    "car_school_dropoff": (4.8, 2.0, (251, 146, 60)),   # Laranja Embarque Escolar
    "car__passenger": (4.6, 1.9, (203, 213, 225)),      # Cinza-claro Automóvel Solo
    "micro_bike": (2.2, 1.1, (6, 182, 212)),            # Ciano Ciclista / Autopropelido
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
        "hud": ImageFont.truetype(f"{base}/DejaVuSansMono-Bold.ttf", 13),
        "street": ImageFont.truetype(f"{base}/DejaVuSans-Bold.ttf", 22),  # usado em 2x supersampling
        "legend": ImageFont.truetype(f"{base}/DejaVuSans-Bold.ttf", 12),
    }


def world_to_px(x: float, y: float, inter: dict, w: int = QUAD_W, h: int = QUAD_H) -> tuple[float, float]:
    xmin = inter["cx"] - inter["hx"]
    ymax = inter["cy"] + inter["hy"]
    sx = w / (2.0 * inter["hx"])
    sy = h / (2.0 * inter["hy"])
    return (x - xmin) * sx, (ymax - y) * sy


def ribbon_polygon(points: list[tuple[float, float]], half_w: float) -> list[tuple[float, float]]:
    """Constrói polígono de faixa com largura `2 * half_w` ao redor de uma polilinha."""
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
    """Extrai segmentos de linha de retenção de cada sinal semafórico visível no recorte."""
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
            # Recua 0.8m da ponta para ficar exatamente na linha de parada
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
    """Pré-renderiza o mapa viário estático com supersampling 2x para nitidez máxima."""
    ss = 2
    W, H = QUAD_W * ss, QUAD_H * ss
    img = Image.new("RGB", (W, H), (26, 32, 40))
    draw = ImageDraw.Draw(img)

    xmin, xmax = inter["cx"] - inter["hx"] - 30.0, inter["cx"] + inter["hx"] + 30.0
    ymin, ymax = inter["cy"] - inter["hy"] - 30.0, inter["cy"] + inter["hy"] + 30.0
    scale = W / (2.0 * inter["hx"])

    # Grade urbana sutil de fundo (a cada 50m)
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

    # 1. Polígonos das interseções (asfalto contínuo)
    for node in net.getNodes():
        nx, ny = node.getCoord()
        if not (xmin <= nx <= xmax and ymin <= ny <= ymax):
            continue
        nshape = node.getShape()
        if nshape and len(nshape) >= 3:
            pts = [world_to_px(x, y, inter, W, H) for x, y in nshape]
            draw.polygon(pts, fill=(54, 63, 74), outline=(70, 81, 95))

    # 2. Faixas de rolamento, canaletas BRT, ciclovias e faixas exclusivas To-Be
    label_candidates: dict[str, tuple[float, tuple[float, float]]] = {}
    for edge in visible_edges:
        name = edge.getName()
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
                fill_color = (78, 42, 48)  # Canaleta BRT estrutural
                border_color = (185, 74, 82)
            elif is_bike_only:
                fill_color = (28, 72, 54)
                border_color = (52, 168, 116)
            elif show_priority_lanes and lid in pure_excl_set:
                fill_color = (26, 77, 110)  # Faixa exclusiva física (To-Be 1 / To-Be 3)
                border_color = (56, 189, 248)
            elif show_priority_lanes and lid in coop_set:
                fill_color = (66, 62, 42)   # Faixa prioritária compartilhada
                border_color = (234, 179, 8)

            draw.polygon(poly, fill=fill_color, outline=border_color)

        # Guarda melhor ponto para rótulo da via (omite rótulo redundante de canaleta no meio do cruzamento)
        if name and len(name) >= 5 and "Canaleta" not in name:
            eshape = edge.getShape()
            mid_x, mid_y = eshape[len(eshape) // 2]
            if (inter["cx"] - inter["hx"] * 0.78 <= mid_x <= inter["cx"] + inter["hx"] * 0.78) and (
                inter["cy"] - inter["hy"] * 0.72 <= mid_y <= inter["cy"] + inter["hy"] * 0.72
            ):
                length = edge.getLength()
                prev = label_candidates.get(name)
                if prev is None or length > prev[0]:
                    label_candidates[name] = (length, world_to_px(mid_x, mid_y, inter, W, H))

    # 3. Rótulos enxutos das principais vias visíveis (até 4 nomes sem colisão)
    placed_pts: list[tuple[float, float]] = []
    for name, (_elen, (lx, ly)) in sorted(label_candidates.items(), key=lambda kv: kv[1][0], reverse=True):
        if len(placed_pts) >= 4:
            break
        if any(math.hypot(lx - px, ly - py) < 230 for px, py in placed_pts):
            continue
        short = (
            name.replace("Avenida Presidente ", "Av. Pres. ")
            .replace("Avenida ", "Av. ")
            .replace("Rua General ", "R. Gen. ")
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
    """Executa 1 cenário no SUMO até T_END+2 e grava trajetórias e estados semafóricos nas 4 janelas."""
    preset = SCENARIO_PRESETS[scenario_key]
    venv_sumo = Path(sys.executable).parent / "sumo"
    sumo_bin = str(venv_sumo) if venv_sumo.exists() else "sumo"

    print(f"Simulando e gravando trajetórias de '{scenario_key}' (0..{T_END} s)...")
    traci.start([sumo_bin, "-c", str(preset["config"]), "--no-step-log", "true"])

    if preset["priority_lanes"]:
        apply_physical_priority_lanes(priority_cfg)

    tl_ids = list(traci.trafficlight.getIDList())
    controller = CWBEcoSyncLeanController(tl_ids, priority_cfg) if preset["adaptive"] else None

    # Pré-filtra apenas os TLS relevantes às 4 câmeras para economizar memória e IPC
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
        for step in range(T_END + 3):
            traci.simulationStep()
            sim_time = traci.simulation.getTime()

            for vid in traci.simulation.getDepartedIDList():
                traci.vehicle.subscribe(vid, SUB_VARS)

            sub_results = traci.vehicle.getAllSubscriptionResults()

            # Alimenta o controlador caso adaptativo (idêntico ao traci_controller.py)
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

            if step >= T_START - 1:
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


def interp_angle_deg(a0: float, a1: float, alpha: float) -> float:
    diff = (a1 - a0 + 180.0) % 360.0 - 180.0
    return (a0 + alpha * diff) % 360.0


def draw_quadrant_dynamic(
    base_img: Image.Image,
    inter: dict,
    signals: list[dict],
    veh_snaps: dict[int, dict[str, tuple]],
    tls_snaps: dict[int, dict[str, str]],
    t_exact: float,
    scen_title: str,
    accent_rgb: tuple[int, int, int],
    fonts: dict,
    frame_idx: int,
) -> Image.Image:
    """Desenha semáforos, veículos interpolados e HUD local sobre o mapa base do quadrante."""
    img = base_img.copy()
    draw = ImageDraw.Draw(img)

    t0 = int(math.floor(t_exact))
    t1 = min(T_END + 1, t0 + 1)
    alpha = t_exact - t0

    # 1. Barras dos semáforos (Verde / Amarelo / Vermelho)
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

    # 2. Veículos orientados e interpolados
    snaps0 = veh_snaps.get(t0, {})
    snaps1 = veh_snaps.get(t1, {})
    scale_x = QUAD_W / (2.0 * inter["hx"])

    xmin, xmax = inter["cx"] - inter["hx"], inter["cx"] + inter["hx"]
    ymin, ymax = inter["cy"] - inter["hy"], inter["cy"] + inter["hy"]

    local_count = 0
    local_halting = 0
    local_speed_sum = 0.0

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

        local_count += 1
        local_speed_sum += spd * 3.6
        is_stopped = spd < 0.15
        if is_stopped:
            local_halting += 1

        len_m, wid_m, color = VEH_STYLE.get(vtype, (4.6, 1.9, (203, 213, 225)))
        px_front, py_front = world_to_px(x, y, inter)

        # Em coordenadas de mundo SUMO: 0° = Norte (+y), 90° = Leste (+x).
        # Em tela: +x para direita, +y para baixo -> vetor frente em pixels = (sin(rad), -cos(rad))
        rad = math.radians(ang)
        ux, uy = math.sin(rad), -math.cos(rad)
        nx, ny = -uy, ux

        len_px = max(6.5, len_m * scale_x)
        hw_px = max(2.4, (wid_m * 0.5) * scale_x)

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

        # Destaque especial para ambulância (halo pulsante vermelho/azul)
        if vtype == "emergency_ambulance":
            cx_v, cy_v = (fx + bx) * 0.5, (fy + by) * 0.5
            pulse_r = 9 + (frame_idx % 8)
            beacon_col = (239, 68, 68) if (frame_idx // 4) % 2 == 0 else (59, 130, 246)
            draw.ellipse([cx_v - pulse_r, cy_v - pulse_r, cx_v + pulse_r, cy_v + pulse_r], outline=beacon_col, width=2)

    # 3. Moldura do quadrante + Faixa de título superior + HUD local inferior
    draw.rectangle([0, 0, QUAD_W - 1, QUAD_H - 1], outline=accent_rgb, width=2)
    draw.rectangle([0, 0, QUAD_W - 1, 28], fill=(15, 23, 42))
    draw.rectangle([0, 0, 8, 28], fill=accent_rgb)
    draw.text((16, 5), scen_title, fill=(248, 250, 252), font=fonts["quad_hdr"])

    mean_spd = (local_speed_sum / local_count) if local_count > 0 else 0.0
    hud_text = f"Veíc: {local_count:2d} | Fila: {local_halting:2d} | Vel: {mean_spd:4.1f} km/h"
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

    # Legenda compacta à direita
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
    """Renderiza e codifica em MP4 H.264 o vídeo comparativo 2x2 de um cruzamento."""
    out_mp4 = OUT_DIR / f"{inter['slug']}.mp4"
    print(f"Renderizando vídeo 2x2: {out_mp4.name} ({TOTAL_FRAMES} quadros @ {FPS} FPS)...")

    signals = extract_intersection_tls_geometry(net, inter)
    base_plain = render_base_map(net, inter, False, pure_excl_set, coop_set, fonts)
    base_prio = render_base_map(net, inter, True, pure_excl_set, coop_set, fonts)

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
            t_exact = T_START + (T_END - T_START) * (f_idx / max(1, TOTAL_FRAMES - 1))
            canvas = Image.new("RGB", (FRAME_W, FRAME_H), (11, 15, 25))
            draw_master_header(canvas, inter["title"], t_exact, fonts)

            for q_idx, (scen_key, scen_title, accent, uses_prio) in enumerate(SCENARIOS):
                b_img = base_prio if uses_prio else base_plain
                q_img = draw_quadrant_dynamic(
                    base_img=b_img,
                    inter=inter,
                    signals=signals,
                    veh_snaps=all_veh_snaps[scen_key],
                    tls_snaps=all_tls_snaps[scen_key],
                    t_exact=t_exact,
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
            save_preview=(idx == 0),
        )
        size_mb = out_path.stat().st_size / (1024 * 1024)
        print(f"Concluído: {out_path} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
