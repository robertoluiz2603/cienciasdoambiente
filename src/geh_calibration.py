"""Validação estatística da calibração do modelo As-Is usando o índice GEH.

Critério do projeto (Marco 2 - Desenhar):
A simulação é considerada válida quando pelo menos 85% das vias monitoradas
apresentam GEH < 5 em relação às contagens de referência de tráfego (veíc/h).
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import pandas as pd
import sumolib


NET_PATH = Path("simulation/network/curitiba.net.xml")
AS_IS_DIR = Path("simulation/as_is")
DEFAULT_GEH_CSV = Path("data/contagens_geh_as_is.csv")
LEGACY_SAMPLE_CSV = Path("data/exemplo_contagens_geh.csv")

# 10 vias monitoradas no Quadrilátero Central e nos corredores escolhidos pelo grupo
MONITORED_CORRIDORS = [
    ("Av_Pres_Kennedy", "Avenida Presidente Kennedy", 1390),
    ("Av_Mal_Floriano_Peixoto", "Avenida Marechal Floriano Peixoto", 750),
    ("Rua_Mariano_Torres", "Rua Mariano Torres", 425),
    ("Al_Dr_Muricy", "Alameda Doutor Muricy", 355),
    ("Av_Pres_Getulio_Vargas", "Avenida Presidente Getúlio Vargas", 880),
    ("Av_Arthur_Bernardes", "Avenida Presidente Arthur da Silva Bernardes", 1105),
    ("Rua_Mario_Tourinho", "Rua General Mário Tourinho", 1120),
    ("Rua_XV_de_Novembro", "Rua XV de Novembro", 175),
    ("Av_Manoel_Ribas", "Avenida Manoel Ribas", 30),
    ("Av_Republica_Argentina", "Avenida República Argentina", 955),
]


def compute_geh(simulated: float, observed: float) -> float:
    """Calcula a estatística GEH entre volume simulado (M) e observado (C)."""
    if simulated + observed == 0:
        return 0.0
    return math.sqrt((2.0 * (simulated - observed) ** 2) / (simulated + observed))


def measure_simulated_hourly_volumes(
    net_path: Path = NET_PATH,
    as_is_dir: Path = AS_IS_DIR,
    window_seconds: float = 600.0,
) -> dict[str, dict[str, float]]:
    """Extrai o fluxo horário simulado (carros + ônibus URBS) por corredor no cenário As-Is."""
    net = sumolib.net.readNet(str(net_path))
    edge_to_name = {e.getID(): e.getName() for e in net.getEdges() if not e.isSpecial() and e.getName()}
    target_names = {street for _, street, _ in MONITORED_CORRIDORS}

    car_scale = 3600.0 / window_seconds
    cars_vph = {name: 0.0 for name in target_names}
    buses_vph = {name: 0.0 for name in target_names}

    for car_file in (as_is_dir / "trips_cars.rou.xml", as_is_dir / "special_as_is.rou.xml"):
        if not car_file.exists():
            continue
        for veh in ET.parse(car_file).getroot().findall("vehicle"):
            route_el = veh.find("route")
            if route_el is None:
                continue
            seen = {edge_to_name.get(eid) for eid in route_el.get("edges", "").split()}
            for name in seen & target_names:
                cars_vph[name] += car_scale

    buses_file = as_is_dir / "urbs_buses.rou.xml"
    if buses_file.exists():
        for flow in ET.parse(buses_file).getroot().findall("flow"):
            route_el = flow.find("route")
            if route_el is None:
                continue
            vph = float(flow.get("vehsPerHour", "0.0"))
            seen = {edge_to_name.get(eid) for eid in route_el.get("edges", "").split()}
            for name in seen & target_names:
                buses_vph[name] += vph

    return {
        name: {
            "carros_sim_h": round(cars_vph[name], 1),
            "onibus_urbs_h": round(buses_vph[name], 1),
            "simulado": round(cars_vph[name] + buses_vph[name], 1),
        }
        for name in target_names
    }


def build_calibration_csv(output_csv: Path = DEFAULT_GEH_CSV) -> Path:
    """Gera a tabela das 10 vias monitoradas com volumes simulados no As-Is e referências."""
    sim_vols = measure_simulated_hourly_volumes()
    rows = []
    for via_slug, street_name, obs_ref in MONITORED_CORRIDORS:
        stats = sim_vols.get(street_name, {"carros_sim_h": 0.0, "onibus_urbs_h": 0.0, "simulado": 0.0})
        rows.append(
            {
                "via": via_slug,
                "logradouro": street_name,
                "onibus_urbs_h": stats["onibus_urbs_h"],
                "carros_sim_h": stats["carros_sim_h"],
                "observado": obs_ref,
                "simulado": stats["simulado"],
            }
        )
    df = pd.DataFrame(rows)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False)
    df[["via", "observado", "simulado"]].to_csv(LEGACY_SAMPLE_CSV, index=False)
    return output_csv


def evaluate_calibration(csv_path: Path, threshold: float = 5.0, min_pass_rate: float = 0.85) -> dict:
    """Avalia um arquivo CSV com colunas ['via', 'observado', 'simulado']."""
    df = pd.read_csv(csv_path)
    df["geh"] = df.apply(lambda r: round(compute_geh(float(r["simulado"]), float(r["observado"])), 3), axis=1)
    df["aprovado"] = df["geh"] < threshold

    total = len(df)
    passed = int(df["aprovado"].sum()) if total > 0 else 0
    pass_rate = (passed / total) if total > 0 else 0.0

    return {
        "dataframe": df,
        "total_vias": total,
        "vias_aprovadas": passed,
        "taxa_aprovacao": pass_rate,
        "modelo_valido": pass_rate >= min_pass_rate,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validação GEH - Quadrilátero Central Curitiba")
    parser.add_argument("--csv", type=Path, default=DEFAULT_GEH_CSV, help="CSV com colunas observado/simulado")
    parser.add_argument("--refresh", action="store_true", help="Recalcular volumes simulados da rede As-Is")
    args = parser.parse_args()

    if args.refresh or not args.csv.exists() or args.csv == DEFAULT_GEH_CSV:
        build_calibration_csv(DEFAULT_GEH_CSV)

    result = evaluate_calibration(args.csv)
    result["dataframe"].to_csv(args.csv, index=False)
    print(result["dataframe"].to_string(index=False))
    print(
        f"\nAprovadas: {result['vias_aprovadas']}/{result['total_vias']} "
        f"({result['taxa_aprovacao'] * 100:.1f}%) | Modelo válido (>=85%): {result['modelo_valido']}"
    )


if __name__ == "__main__":
    main()
