"""Orquestrador dos 4 cenários (As-Is, To-Be 1, To-Be 2 e To-Be 3) e comparativo consolidado."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import pandas as pd
from traci_controller import SCENARIO_PRESETS, run_simulation


SUMMARY_4_CSV = Path("data/comparativo_4_cenarios.csv")
SUMMARY_3_CSV = Path("data/comparativo_3_cenarios.csv")
AMBIENT_KPI_COPY = Path("data/kpi_log.csv")
EVP_SUMMARY_JSON = Path("data/evp_summary.json")


def summarize_kpi_csv(csv_path: Path, evp_info: dict) -> dict:
    """Extrai métricas consolidadas de um arquivo KPI por passo."""
    df = pd.read_csv(csv_path)
    total_co2_kg = float(df["co2_g_s"].sum()) / 1000.0
    total_nox_g = float(df["nox_g_s"].sum())
    total_pmx_g = float(df["pmx_g_s"].sum())
    mean_pax = float(df["active_passengers"].mean())

    co2_g_per_pax = (float(df["co2_g_s"].sum()) / mean_pax) if mean_pax > 0 else 0.0
    total_pax_km = float(df["pax_km_step"].sum()) if "pax_km_step" in df.columns else 0.0
    co2_g_per_pax_km = (float(df["co2_g_s"].sum()) / total_pax_km) if total_pax_km > 0 else 0.0

    bus_series = pd.to_numeric(df["bus_mean_speed_kmh"], errors="coerce").dropna()
    emg_series = pd.to_numeric(df["emergency_mean_speed_kmh"], errors="coerce").dropna()

    return {
        "active_vehicles_mean": round(float(df["active_vehicles"].mean()), 1),
        "active_passengers_mean": round(mean_pax, 1),
        "mean_speed_kmh": round(float(df["mean_speed_kmh"].mean()), 2),
        "passenger_weighted_speed_kmh": round(float(df["passenger_weighted_speed_kmh"].mean()), 2),
        "bus_mean_speed_kmh": round(float(bus_series.mean()), 2) if not bus_series.empty else 0.0,
        "emergency_mean_speed_kmh": round(float(emg_series.mean()), 2) if not emg_series.empty else 0.0,
        "ambulances_completed": evp_info.get("ambulances_completed", 0),
        "amb_avg_travel_time_s": evp_info.get("amb_avg_travel_time_s") or 0.0,
        "halting_vehicles_mean": round(float(df["halting_vehicles"].mean()), 1),
        "queue_length_m_mean": round(float(df["queue_length_m"].mean()), 1),
        "co2_total_kg": round(total_co2_kg, 2),
        "nox_total_g": round(total_nox_g, 1),
        "pmx_total_g": round(total_pmx_g, 2),
        "co2_g_per_pax": round(co2_g_per_pax, 2),
        "co2_g_per_pax_km": round(co2_g_per_pax_km, 2),
        "noise_leq_mean_dba": round(float(df["noise_leq_dba"].mean()), 2),
    }


def pct_delta(new_val: float, base_val: float) -> float:
    if base_val == 0:
        return 0.0
    return round(((new_val - base_val) / base_val) * 100.0, 2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Executa e compara os 4 cenários no SUMO")
    parser.add_argument("--steps", type=int, default=600, help="Passos por simulação (segundos)")
    parser.add_argument(
        "--summarize-only",
        action="store_true",
        help="Reprocessa os KPIs já gravados em data/kpi_*.csv sem reexecutar o SUMO",
    )
    args = parser.parse_args()

    labels = {
        "as_is": "1. As-Is (Cenário Atual)",
        "to_be_1": "2. To-Be 1 (Solução Grupo: Faixas/Carona/Terminais/Escolas)",
        "to_be_2": "3. To-Be 2 (Solução Algoritmos: CWB-EcoSync-Lean Isolado)",
        "to_be_3": "4. To-Be 3 (Conjunto: Grupo + CWB-EcoSync-Lean)",
    }

    evp_results: dict[str, dict] = {}
    if args.summarize_only and EVP_SUMMARY_JSON.exists():
        evp_results = json.loads(EVP_SUMMARY_JSON.read_text(encoding="utf-8"))

    results: dict[str, dict] = {}
    for key in ("as_is", "to_be_1", "to_be_2", "to_be_3"):
        preset = SCENARIO_PRESETS[key]
        if not args.summarize_only:
            print(f"\n=== Executando {labels[key]} ===")
            evp_info = run_simulation(
                config_path=preset["config"],
                gui=False,
                max_steps=args.steps,
                adaptive=preset["adaptive"],
                priority_lanes=preset["priority_lanes"],
                kpi_log=preset["out"],
                enable_mqtt=(key == "to_be_3"),
            )
            evp_results[key] = evp_info
        else:
            evp_info = evp_results.get(key, {})
        results[key] = summarize_kpi_csv(preset["out"], evp_info)

    shutil.copyfile(SCENARIO_PRESETS["to_be_3"]["out"], AMBIENT_KPI_COPY)
    EVP_SUMMARY_JSON.write_text(json.dumps(evp_results, indent=2), encoding="utf-8")

    metric_specs = [
        ("active_vehicles_mean", "Veículos Ativos (média)", "veíc"),
        ("active_passengers_mean", "Passageiros Equivalentes Ativos (média)", "pax"),
        ("mean_speed_kmh", "Velocidade Média Geral", "km/h"),
        ("passenger_weighted_speed_kmh", "Velocidade Média Ponderada por Passageiro", "km/h"),
        ("bus_mean_speed_kmh", "Velocidade Média dos Ônibus URBS", "km/h"),
        ("emergency_mean_speed_kmh", "Velocidade Média das Ambulâncias (EVP)", "km/h"),
        ("amb_avg_travel_time_s", "Tempo Médio de Viagem Ambulância", "s"),
        ("halting_vehicles_mean", "Veículos Parados em Fila (média)", "veíc"),
        ("queue_length_m_mean", "Comprimento Total de Filas (média)", "m"),
        ("co2_total_kg", "Emissão Acumulada de CO2", "kg"),
        ("nox_total_g", "Emissão Acumulada de NOx", "g"),
        ("pmx_total_g", "Emissão Acumulada de PMx", "g"),
        ("co2_g_per_pax", "Emissão de CO2 por Passageiro", "g/pax"),
        ("co2_g_per_pax_km", "Intensidade de Carbono (CO2 por pax·km)", "g/pax·km"),
        ("noise_leq_mean_dba", "Ruído Urbano Médio (Leq FHWA/CoRTN)", "dB(A)"),
    ]

    rows = []
    for col, label, unit in metric_specs:
        v0 = results["as_is"][col]
        v1 = results["to_be_1"][col]
        v2 = results["to_be_2"][col]
        v3 = results["to_be_3"][col]
        rows.append(
            {
                "metrica": col,
                "indicador": label,
                "unidade": unit,
                "as_is": v0,
                "to_be_1": v1,
                "to_be_2": v2,
                "to_be_3": v3,
                "delta_to_be_1_pct": round(v1 - v0, 2) if unit == "dB(A)" else pct_delta(v1, v0),
                "delta_to_be_2_pct": round(v2 - v0, 2) if unit == "dB(A)" else pct_delta(v2, v0),
                "delta_to_be_3_pct": round(v3 - v0, 2) if unit == "dB(A)" else pct_delta(v3, v0),
            }
        )

    comp_df = pd.DataFrame(rows)
    SUMMARY_4_CSV.parent.mkdir(parents=True, exist_ok=True)
    comp_df.to_csv(SUMMARY_4_CSV, index=False)
    comp_df.to_csv(SUMMARY_3_CSV, index=False)

    print("\n=== COMPARATIVO FINAL DOS 4 CENÁRIOS ===")
    print(
        comp_df[
            [
                "indicador",
                "unidade",
                "as_is",
                "to_be_1",
                "to_be_2",
                "to_be_3",
                "delta_to_be_1_pct",
                "delta_to_be_2_pct",
                "delta_to_be_3_pct",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
