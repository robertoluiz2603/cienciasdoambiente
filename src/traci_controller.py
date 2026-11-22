"""Controlador semafórico adaptativo CWB-EcoSync-Lean e coletor de KPIs via TraCI/SUMO.

Funcionalidades:
- Suporta os 3 cenários do projeto (`as_is`, `to_be_1`, `to_be_2`) ou configuração customizada via CLI.
- Aplica faixas exclusivas/prioritárias nos corredores das 5 avenidas (`simulation/to_be/priority_lanes.json`).
- Executa o algoritmo `CWBEcoSyncLean` (`To-Be 2`):
  1. OCC-MP (Max-Pressure ponderado por passageiros) + filtro de parada em estação-tubo (`beta_v`).
  2. Regras de guarda SOTL: verde mínimo (`u_min`), anti-spillback (`occ_jusante > 85%`) e anti-inanição.
  3. Onda Verde arterial calibrada pela velocidade real da telemetria URBS (`20.4 km/h = 5.66 m/s`).
  4. Preempção de Veículos de Emergência (EVP) para ambulâncias (`vClass="emergency"`).
- Calcula emissões cinemáticas HBEFA3 (`CO2`, `NOx`, `PMx`) e ruído urbano `L_eq` (FHWA/CoRTN vs. NBR 10151).
- Publica amostras do Contrato JSON de Integração via MQTT (`paho-mqtt`) e salva `data/mqtt_sample_payloads.json`.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
import traci
import traci.constants as tc

try:
    import paho.mqtt.client as mqtt
except ImportError:  # pragma: no cover
    mqtt = None


DEFAULT_CONFIG = Path("simulation/as_is/curitiba.sumocfg")
DEFAULT_KPI_LOG = Path("data/kpi_log.csv")
PRIORITY_JSON = Path("simulation/to_be/priority_lanes.json")
MQTT_SAMPLES_OUT = Path("data/mqtt_sample_payloads.json")

SCENARIO_PRESETS = {
    "as_is": {
        "config": Path("simulation/as_is/curitiba.sumocfg"),
        "priority_lanes": False,
        "adaptive": False,
        "out": Path("data/kpi_as_is.csv"),
    },
    "to_be_1": {
        "config": Path("simulation/to_be/curitiba_to_be.sumocfg"),
        "priority_lanes": True,
        "adaptive": False,
        "out": Path("data/kpi_to_be_1.csv"),
    },
    "to_be_2": {
        "config": Path("simulation/as_is/curitiba.sumocfg"),
        "priority_lanes": False,
        "adaptive": True,
        "out": Path("data/kpi_to_be_2.csv"),
    },
    "to_be_3": {
        "config": Path("simulation/to_be/curitiba_to_be.sumocfg"),
        "priority_lanes": True,
        "adaptive": True,
        "out": Path("data/kpi_to_be_3.csv"),
    },
}

# Pesos de ocupação média por tipo de veículo (Equação 3 - OCC-MP)
PAX_WEIGHTS = {
    "urbs_brt": 100.0,
    "urbs_ligeirinho": 50.0,
    "urbs_convencional": 35.0,
    "bus_escolar": 30.0,
    "car_carpool": 3.0,
    "car_school_dropoff": 2.0,
    "car__passenger": 1.3,
    "car_park_ride": 1.3,
    "micro_bike": 1.0,
    "emergency_ambulance": 150.0,
}

BUS_TYPES = {"urbs_brt", "urbs_ligeirinho", "urbs_convencional", "bus_escolar"}
CAR_TYPES = {"car_carpool", "car_school_dropoff", "car__passenger", "car_park_ride"}
CORRIDOR_SPEED_MPS = 5.66  # 20.37 km/h medido na telemetria real URBS (17h-18h)
VEHICLE_SUB_VARS = [
    tc.VAR_SPEED,
    tc.VAR_TYPE,
    tc.VAR_LANE_ID,
    tc.VAR_LANEPOSITION,
    tc.VAR_CO2EMISSION,
    tc.VAR_NOXEMISSION,
    tc.VAR_PMXEMISSION,
]


class MqttTelemetryPublisher:
    """Publicador MQTT resiliente para o Contrato JSON de Integração (com fallback offline)."""

    def __init__(self, host: str = "localhost", port: int = 1883) -> None:
        self.client = None
        self.connected = False
        self.samples: list[dict] = []
        if mqtt is None:
            return
        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="curitiba_sumo_traci")
            client.connect(host, port, keepalive=15)
            client.loop_start()
            self.client = client
            self.connected = True
        except Exception:
            self.connected = False

    def publish(self, tl_id: str, payload: dict) -> None:
        self.samples.append(payload)
        if self.connected and self.client is not None:
            topic = f"curitiba/smartmobility/{tl_id}/telemetry"
            try:
                self.client.publish(topic, json.dumps(payload, ensure_ascii=False), qos=0)
            except Exception:
                self.connected = False

    def close(self, output_path: Path = MQTT_SAMPLES_OUT) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(self.samples, indent=2, ensure_ascii=False), encoding="utf-8")
        if self.client is not None:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except Exception:
                pass


def load_priority_config() -> dict:
    """Carrega a configuração das faixas exclusivas e corredores das 5 avenidas."""
    if not PRIORITY_JSON.exists():
        return {"pure_exclusive_lanes": [], "cooperative_lanes": [], "corridor_edges": []}
    return json.loads(PRIORITY_JSON.read_text(encoding="utf-8"))


def apply_physical_priority_lanes(priority_cfg: dict) -> int:
    """Aplica permissão exclusiva (ônibus, emergência, bicicleta) nas faixas seguras das 5 avenidas."""
    applied = 0
    for lane_id in priority_cfg.get("pure_exclusive_lanes", []):
        try:
            traci.lane.setAllowed(lane_id, ["bus", "emergency", "bicycle"])
            applied += 1
        except traci.TraCIException:
            continue
    return applied


def build_integration_payload(tl_id: str, lane_ids: list[str], lane_metrics: dict[str, dict]) -> dict:
    """Constrói payload JSON conforme o Contrato de Dados de Integração do Manual."""
    sensors = []
    total_queue_m = 0.0
    total_co2_gs = 0.0

    for lane_id in lane_ids:
        metrics = lane_metrics.get(lane_id)
        if metrics:
            count = metrics["count"]
            halting = metrics["halting"]
            mean_speed_kmh = (metrics["speed_sum"] / count) * 3.6 if count > 0 else 40.0
            co2_gs = metrics["co2_mg_s"] / 1000.0
            occupied = count > 0
        else:
            occupancy = traci.lane.getLastStepOccupancy(lane_id)
            mean_speed_kmh = traci.lane.getLastStepMeanSpeed(lane_id) * 3.6
            halting = traci.lane.getLastStepHaltingNumber(lane_id)
            co2_gs = traci.lane.getCO2Emission(lane_id) / 1000.0
            occupied = occupancy > 0.05

        total_queue_m += halting * 6.5
        total_co2_gs += co2_gs
        sensors.append(
            {
                "sensor_id": f"sensor_indutivo_{lane_id}",
                "state": "occupied" if occupied else "free",
                "vehicle_speed_kmh": round(mean_speed_kmh, 2),
            }
        )

    return {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "intersection_id": tl_id,
        "sensors": sensors,
        "instantaneous_metrics": {
            "queue_length_meters": round(total_queue_m, 2),
            "co2_grams_per_second": round(total_co2_gs, 3),
        },
    }


class CWBEcoSyncLeanController:
    """Controlador semafórico OCC-MP + SOTL + Onda Verde Arterial + Preempção de Emergência (EVP)."""

    def __init__(self, tl_ids: list[str], priority_cfg: dict) -> None:
        self.tl_ids = tl_ids
        self.corridor_edge_set = set(priority_cfg.get("corridor_edges", []))
        self.lane_lengths: dict[str, float] = {}
        self.tl_topology: dict[str, dict] = {}
        self.phase_elapsed: dict[str, int] = {tl: 0 for tl in tl_ids}
        self.last_phase_idx: dict[str, int] = {}
        self.starvation: dict[str, dict[int, int]] = {}
        self.corridor_tls: list[str] = []

        self._init_topology()
        self._apply_initial_green_wave_offsets()

    def _get_lane_length(self, lane_id: str) -> float:
        length = self.lane_lengths.get(lane_id)
        if length is None:
            try:
                length = max(1.0, traci.lane.getLength(lane_id))
            except traci.TraCIException:
                length = 50.0
            self.lane_lengths[lane_id] = length
        return length

    def _init_topology(self) -> None:
        for tl_id in self.tl_ids:
            links = traci.trafficlight.getControlledLinks(tl_id)
            defs = traci.trafficlight.getCompleteRedYellowGreenDefinition(tl_id)
            if not defs or not defs[0].phases:
                continue

            phases = defs[0].phases
            green_phases: dict[int, dict] = {}
            in_lanes_all: set[str] = set()
            is_corridor_tl = False

            for p_idx, ph in enumerate(phases):
                state = ph.state
                # Ignora fases puramente amarelas/vermelhas de transição
                if not any(ch in ("G", "g") for ch in state) or ("y" in state.lower()):
                    continue

                movements: list[tuple[str, str]] = []
                in_set: set[str] = set()
                corridor_hits = 0

                for sig_idx, ch in enumerate(state):
                    if ch not in ("G", "g") or sig_idx >= len(links):
                        continue
                    for link in links[sig_idx]:
                        in_lane, out_lane = link[0], link[1]
                        if not in_lane:
                            continue
                        in_set.add(in_lane)
                        in_lanes_all.add(in_lane)
                        self._get_lane_length(in_lane)
                        if out_lane:
                            self._get_lane_length(out_lane)
                        movements.append((in_lane, out_lane))
                        edge_id = in_lane.rsplit("_", 1)[0]
                        if edge_id in self.corridor_edge_set:
                            corridor_hits += 1
                            is_corridor_tl = True

                if in_set:
                    green_phases[p_idx] = {
                        "in_lanes": in_set,
                        "movements": movements,
                        "corridor_hits": corridor_hits,
                    }

            if len(green_phases) >= 1:
                cycle = sum(p.duration for p in phases)
                corridor_phase = max(green_phases, key=lambda pid: green_phases[pid]["corridor_hits"])
                self.tl_topology[tl_id] = {
                    "num_phases": len(phases),
                    "cycle": max(30.0, cycle),
                    "green_phases": green_phases,
                    "all_in_lanes": in_lanes_all,
                    "corridor_phase": corridor_phase,
                    "is_corridor": is_corridor_tl,
                }
                self.starvation[tl_id] = {pid: 0 for pid in green_phases}
                self.last_phase_idx[tl_id] = traci.trafficlight.getPhase(tl_id)
                if is_corridor_tl:
                    self.corridor_tls.append(tl_id)

    def _apply_initial_green_wave_offsets(self) -> None:
        """Aplica offset progressivo de Onda Verde nos semáforos dos 5 corredores principais."""
        coords: list[tuple[float, float, str]] = []
        for tl_id in self.corridor_tls:
            in_lanes = sorted(self.tl_topology[tl_id]["all_in_lanes"])
            if not in_lanes:
                continue
            try:
                shape = traci.lane.getShape(in_lanes[0])
                x, y = shape[-1]
                coords.append((x, y, tl_id))
            except traci.TraCIException:
                continue

        if not coords:
            return

        # Ordena ao longo do eixo principal sudoeste-nordeste e aplica offset pela velocidade real (5.66 m/s)
        coords.sort(key=lambda item: item[0] + item[1])
        x0, y0, _ = coords[0]
        for x, y, tl_id in coords:
            topo = self.tl_topology[tl_id]
            cycle = topo["cycle"]
            dist = math.hypot(x - x0, y - y0)
            offset = (dist / CORRIDOR_SPEED_MPS) % cycle
            topo["wave_offset"] = offset
            # Posiciona fase inicial proporcional ao offset para formar onda verde desde t=0
            if offset < cycle * 0.5:
                try:
                    traci.trafficlight.setPhase(tl_id, topo["corridor_phase"])
                    traci.trafficlight.setPhaseDuration(tl_id, max(12.0, (cycle * 0.45) - offset * 0.3))
                except traci.TraCIException:
                    pass

    def step(
        self,
        sim_time: float,
        lane_pressure: dict[str, float],
        lane_occ_len: dict[str, float],
        emergency_lanes: set[str],
    ) -> None:
        """Executa 1 ciclo de decisão OCC-MP + SOTL + EVP + Onda Verde."""
        run_mp = int(sim_time) % 2 == 0

        for tl_id, topo in self.tl_topology.items():
            curr_phase = traci.trafficlight.getPhase(tl_id)
            if curr_phase != self.last_phase_idx.get(tl_id):
                self.phase_elapsed[tl_id] = 0
                self.last_phase_idx[tl_id] = curr_phase
            else:
                self.phase_elapsed[tl_id] += 1

            green_phases = topo["green_phases"]
            for pid in green_phases:
                if pid == curr_phase:
                    self.starvation[tl_id][pid] = 0
                else:
                    self.starvation[tl_id][pid] += 1

            # Só atua se houver veículos ativos nas aproximações ou ambulância presente
            active_here = any(lane in lane_pressure for lane in topo["all_in_lanes"])
            if not active_here:
                continue

            # Ignora semáforo durante transição amarela
            if curr_phase not in green_phases:
                continue

            remaining = traci.trafficlight.getNextSwitch(tl_id) - sim_time
            elapsed = self.phase_elapsed[tl_id]

            # 1. Preempção de Veículos de Emergência (EVP)
            evp_lanes = topo["all_in_lanes"] & emergency_lanes
            if evp_lanes:
                if evp_lanes & green_phases[curr_phase]["in_lanes"]:
                    if remaining < 6.0 and elapsed < 65.0:
                        traci.trafficlight.setPhaseDuration(tl_id, remaining + 6.0)
                    continue
                if elapsed >= 5 and len(green_phases) > 1:
                    # Encerra fase atual suavemente para o SUMO passar pelo amarelo até a fase da ambulância
                    traci.trafficlight.setPhaseDuration(tl_id, 0.0)
                    continue

            if not run_mp:
                continue

            # 2. OCC-MP + Filtro Beta + Anti-Spillback SOTL + Anti-Inanição + Bônus Onda Verde
            cycle = topo["cycle"]
            wave_offset = topo.get("wave_offset", 0.0)
            in_wave_window = ((sim_time - wave_offset) % cycle) < (cycle * 0.45)

            scores: dict[int, float] = {}
            for pid, pinfo in green_phases.items():
                pressure = 0.0
                seen_moves: set[tuple[str, str]] = set()
                for in_lane, out_lane in pinfo["movements"]:
                    if (in_lane, out_lane) in seen_moves:
                        continue
                    seen_moves.add((in_lane, out_lane))

                    up_p = lane_pressure.get(in_lane, 0.0)
                    if up_p <= 0.0:
                        continue

                    down_occ_ratio = 0.0
                    down_p = 0.0
                    if out_lane:
                        down_p = lane_pressure.get(out_lane, 0.0)
                        down_occ_ratio = lane_occ_len.get(out_lane, 0.0) / self._get_lane_length(out_lane)

                    # Regra 6 SOTL (Gershenson, 2005): bloqueia envio para quadra > 85% ocupada
                    spill_guard = 0.0 if down_occ_ratio > 0.85 else 1.0
                    pressure += spill_guard * max(0.0, up_p - 0.5 * down_p)

                starv_bonus = 0.5 * self.starvation[tl_id][pid]
                wave_bonus = 18.0 if (in_wave_window and pid == topo["corridor_phase"] and pinfo["corridor_hits"] > 0) else 0.0
                scores[pid] = pressure + starv_bonus + wave_bonus

            best_pid = max(scores, key=lambda pid: scores[pid])
            curr_score = scores[curr_phase]

            if best_pid == curr_phase:
                if remaining <= 3.0 and elapsed < 55 and curr_score > 5.0:
                    traci.trafficlight.setPhaseDuration(tl_id, remaining + 6.0)
            elif len(green_phases) > 1 and elapsed >= 14 and scores[best_pid] > 1.50 * max(curr_score, 1.0):
                traci.trafficlight.setPhaseDuration(tl_id, 0.0)


def run_simulation(
    config_path: Path,
    gui: bool,
    max_steps: int,
    adaptive: bool,
    priority_lanes: bool,
    kpi_log: Path,
    enable_mqtt: bool = True,
) -> dict:
    """Executa a simulação SUMO via TraCI, grava os KPIs e retorna resumo agregado."""
    if not config_path.exists():
        print(f"Arquivo de configuração não encontrado: {config_path}", file=sys.stderr)
        sys.exit(1)

    binary_name = "sumo-gui" if gui else "sumo"
    venv_bin = Path(sys.executable).parent / binary_name
    sumo_binary = str(venv_bin) if venv_bin.exists() else binary_name
    traci.start([sumo_binary, "-c", str(config_path), "--no-step-log", "true"])

    priority_cfg = load_priority_config()
    if priority_lanes:
        n_applied = apply_physical_priority_lanes(priority_cfg)
        print(f"Faixas prioritárias aplicadas: {n_applied} faixas exclusivas")

    tl_ids = list(traci.trafficlight.getIDList())
    controller = CWBEcoSyncLeanController(tl_ids, priority_cfg) if adaptive else None
    mqtt_pub = MqttTelemetryPublisher() if enable_mqtt else None

    # Escolhe um semáforo de corredor movimentado para telemetria JSON do contrato
    sample_tl = None
    corridor_edges = set(priority_cfg.get("corridor_edges", []))
    for tl_id in tl_ids:
        lanes = list(dict.fromkeys(traci.trafficlight.getControlledLanes(tl_id)))
        if any(ln.rsplit("_", 1)[0] in corridor_edges for ln in lanes):
            sample_tl = tl_id
            sample_lanes = lanes[:3]
            break
    if sample_tl is None and tl_ids:
        sample_tl = tl_ids[0]
        sample_lanes = list(dict.fromkeys(traci.trafficlight.getControlledLanes(sample_tl)))[:3]

    kpi_log.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "step",
        "active_vehicles",
        "active_passengers",
        "pax_km_step",
        "mean_speed_kmh",
        "bus_mean_speed_kmh",
        "emergency_mean_speed_kmh",
        "passenger_weighted_speed_kmh",
        "halting_vehicles",
        "queue_length_m",
        "co2_g_s",
        "nox_g_s",
        "pmx_g_s",
        "noise_leq_dba",
    ]

    lane_length_cache: dict[str, float] = {}
    amb_depart: dict[str, float] = {}
    amb_travel_times: list[float] = []

    try:
        with kpi_log.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()

            for step in range(max_steps):
                if traci.simulation.getMinExpectedNumber() <= 0:
                    break

                traci.simulationStep()
                sim_time = traci.simulation.getTime()

                # Inscreve apenas veículos recém-inseridos (reduz em ~10x o overhead IPC)
                for veh_id in traci.simulation.getDepartedIDList():
                    traci.vehicle.subscribe(veh_id, VEHICLE_SUB_VARS)
                    if veh_id.startswith("amb_"):
                        amb_depart[veh_id] = sim_time

                for veh_id in traci.simulation.getArrivedIDList():
                    if veh_id in amb_depart:
                        amb_travel_times.append(sim_time - amb_depart.pop(veh_id))

                sub_results = traci.vehicle.getAllSubscriptionResults()

                # Acumuladores de passo único
                n_veh = 0
                total_pax = 0.0
                speed_sum_mps = 0.0
                pax_speed_sum_mps = 0.0
                bus_speeds_kmh: list[float] = []
                emg_speeds_kmh: list[float] = []
                halting = 0
                n_cars = 0
                n_buses = 0
                co2_mg_s = 0.0
                nox_mg_s = 0.0
                pmx_mg_s = 0.0

                lane_pressure: dict[str, float] = defaultdict(float)
                lane_occ_len: dict[str, float] = defaultdict(float)
                lane_metrics: dict[str, dict] = {}
                emergency_lanes: set[str] = set()

                for veh_id, data in sub_results.items():
                    spd = data[tc.VAR_SPEED]
                    vtype = data[tc.VAR_TYPE]
                    lane_id = data[tc.VAR_LANE_ID]
                    lane_pos = data[tc.VAR_LANEPOSITION]
                    v_co2 = data[tc.VAR_CO2EMISSION]
                    v_nox = data[tc.VAR_NOXEMISSION]
                    v_pmx = data[tc.VAR_PMXEMISSION]

                    # Ignora veículo em teleporte (SUMO retorna INVALID_DOUBLE_VALUE = -1073741824.0)
                    if not lane_id or spd < 0.0 or v_co2 < 0.0:
                        continue

                    n_veh += 1
                    v_nox = max(0.0, v_nox)
                    v_pmx = max(0.0, v_pmx)
                    p_v = PAX_WEIGHTS.get(vtype, 1.3)
                    spd_kmh = spd * 3.6
                    speed_sum_mps += spd
                    pax_speed_sum_mps += p_v * spd
                    total_pax += p_v

                    co2_mg_s += v_co2
                    nox_mg_s += v_nox
                    pmx_mg_s += v_pmx

                    is_halting = spd < 0.1
                    if is_halting:
                        halting += 1

                    if vtype in BUS_TYPES:
                        n_buses += 1
                        bus_speeds_kmh.append(spd_kmh)
                        veh_len = 24.0 if vtype == "urbs_brt" else 13.0
                    elif vtype == "emergency_ambulance":
                        emg_speeds_kmh.append(spd_kmh)
                        emergency_lanes.add(lane_id)
                        veh_len = 6.5
                    elif vtype in CAR_TYPES:
                        n_cars += 1
                        veh_len = 5.0
                    else:
                        veh_len = 2.5

                    # Filtro beta_v (Tan et al., 2025): ignora ônibus parado longe da retenção do semáforo
                    beta_v = 1.0
                    if lane_id:
                        if vtype in BUS_TYPES and is_halting:
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

                        if lane_id in lane_metrics:
                            lm = lane_metrics[lane_id]
                            lm["count"] += 1
                            lm["speed_sum"] += spd
                            lm["co2_mg_s"] += v_co2
                            if is_halting:
                                lm["halting"] += 1
                        else:
                            lane_metrics[lane_id] = {
                                "count": 1,
                                "speed_sum": spd,
                                "co2_mg_s": v_co2,
                                "halting": 1 if is_halting else 0,
                            }

                if controller is not None:
                    controller.step(sim_time, lane_pressure, lane_occ_len, emergency_lanes)

                mean_speed_kmh = (speed_sum_mps / n_veh) * 3.6 if n_veh > 0 else 0.0
                pax_speed_kmh = (pax_speed_sum_mps / total_pax) * 3.6 if total_pax > 0 else 0.0
                bus_mean_kmh = sum(bus_speeds_kmh) / len(bus_speeds_kmh) if bus_speeds_kmh else ""
                emg_mean_kmh = sum(emg_speeds_kmh) / len(emg_speeds_kmh) if emg_speeds_kmh else ""

                # Modelo acústico FHWA/CoRTN por corredor monitorado (~30 pontos arteriais) em dB(A) (Equação 5)
                acoustic_load = max(1.0, (n_cars + 8.0 * n_buses + 3.5 * halting) / 30.0)
                noise_dba = 49.0 + 10.0 * math.log10(acoustic_load) + 10.0 * math.log10(max(mean_speed_kmh, 12.0) / 30.0)

                row = {
                    "step": step,
                    "active_vehicles": n_veh,
                    "active_passengers": round(total_pax, 1),
                    "pax_km_step": round(pax_speed_sum_mps / 1000.0, 3),
                    "mean_speed_kmh": round(mean_speed_kmh, 2),
                    "bus_mean_speed_kmh": round(bus_mean_kmh, 2) if isinstance(bus_mean_kmh, float) else "",
                    "emergency_mean_speed_kmh": round(emg_mean_kmh, 2) if isinstance(emg_mean_kmh, float) else "",
                    "passenger_weighted_speed_kmh": round(pax_speed_kmh, 2),
                    "halting_vehicles": halting,
                    "queue_length_m": round(halting * 6.5, 1),
                    "co2_g_s": round(co2_mg_s / 1000.0, 3),
                    "nox_g_s": round(nox_mg_s / 1000.0, 4),
                    "pmx_g_s": round(pmx_mg_s / 1000.0, 4),
                    "noise_leq_dba": round(noise_dba, 2),
                }
                writer.writerow(row)

                if step % 60 == 0 and sample_tl:
                    payload = build_integration_payload(sample_tl, sample_lanes, lane_metrics)
                    if mqtt_pub is not None:
                        mqtt_pub.publish(sample_tl, payload)
                    if step % 180 == 0:
                        print(
                            f"[Passo {step}] Veic={n_veh} | Pax={total_pax:.0f} | "
                            f"Vel={mean_speed_kmh:.1f} km/h | Bus={row['bus_mean_speed_kmh']} | "
                            f"CO2={row['co2_g_s']:.1f} g/s | Ruído={row['noise_leq_dba']:.1f} dB(A)"
                        )
    finally:
        if mqtt_pub is not None:
            mqtt_pub.close()
        traci.close()

    return {
        "ambulances_completed": len(amb_travel_times),
        "amb_avg_travel_time_s": round(sum(amb_travel_times) / len(amb_travel_times), 2) if amb_travel_times else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Controlador TraCI/SUMO - Quadrilátero Central Curitiba")
    parser.add_argument(
        "--scenario",
        choices=["as_is", "to_be_1", "to_be_2", "to_be_3"],
        default=None,
        help="Preset do cenário (sobrescreve config, priority-lanes, adaptive e out)",
    )
    parser.add_argument("-c", "--config", type=Path, default=DEFAULT_CONFIG, help="Caminho para o arquivo .sumocfg")
    parser.add_argument("--gui", action="store_true", help="Abrir interface gráfica (sumo-gui)")
    parser.add_argument("--steps", type=int, default=600, help="Número máximo de passos (segundos)")
    parser.add_argument("--adaptive", action="store_true", help="Ativar algoritmo CWB-EcoSync-Lean")
    parser.add_argument("--priority-lanes", action="store_true", help="Ativar faixas exclusivas das 5 avenidas")
    parser.add_argument("--out", type=Path, default=DEFAULT_KPI_LOG, help="Arquivo CSV de saída para KPIs")
    args = parser.parse_args()

    config = args.config
    priority_lanes = args.priority_lanes
    adaptive = args.adaptive
    out_path = args.out

    if args.scenario:
        preset = SCENARIO_PRESETS[args.scenario]
        config = preset["config"]
        priority_lanes = preset["priority_lanes"]
        adaptive = preset["adaptive"]
        out_path = preset["out"]

    summary = run_simulation(
        config_path=config,
        gui=args.gui,
        max_steps=args.steps,
        adaptive=adaptive,
        priority_lanes=priority_lanes,
        kpi_log=out_path,
    )
    print(f"Simulação finalizada -> {out_path} | Resumo EVP={summary}")


if __name__ == "__main__":
    main()
