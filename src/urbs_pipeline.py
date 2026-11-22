"""Pipeline de dados abertos da URBS para o SUMO e Painel de Analytics.

Consome os arquivos `.json.xz` da URBS em `data/urbs/` para:
1. Calcular estatísticas reais de telemetria GPS dos ônibus dentro do Quadrilátero Central.
2. Mapear os itinerários (`shapeLinha`) e horários de pico (`tabelaLinha`) das linhas
   que cruzam o Centro de Curitiba para a malha do SUMO (`simulation/network/curitiba.net.xml`).
3. Gerar o arquivo de rotas reais `simulation/as_is/urbs_buses.rou.xml` com tipagem BRT/Expresso.
"""

from collections import defaultdict
from datetime import datetime
import json
import lzma
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import pandas as pd
import sumolib


# Limites da Área de Intervenção completa (Campina do Siqueira, Portão, Kennedy, Floriano, Centro)
BBOX = (-49.312, -25.480, -49.258, -25.424)  # (west, south, east, north)

URBS_DIR = Path("data/urbs")
NET_PATH = Path("simulation/network/curitiba.net.xml")
OUT_ROUTES = Path("simulation/as_is/urbs_buses.rou.xml")
OUT_TELEMETRY_HOURLY = Path("data/urbs_telemetry_hourly.csv")
OUT_CENTRAL_LINES = Path("data/urbs_central_lines.csv")


def parse_coord(value: str) -> float:
    """Converte string com vírgula decimal ('-25,4305') para float."""
    return float(value.strip().replace(",", "."))


def inside_bbox(lon: float, lat: float, bbox: tuple[float, float, float, float] = BBOX) -> bool:
    """Verifica se a coordenada (lon, lat) está dentro do retângulo envolvente."""
    west, south, east, north = bbox
    return west <= lon <= east and south <= lat <= north


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distância geodésica aproximada em metros entre dois pontos WGS84."""
    r = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2.0 * r * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def find_urbs_file(suffix: str) -> Path:
    """Localiza o arquivo mais recente em `data/urbs/` para o sufixo dado."""
    matches = sorted(URBS_DIR.glob(f"*_{suffix}.json.xz"))
    if not matches:
        raise FileNotFoundError(f"Arquivo *_{suffix}.json.xz não encontrado em {URBS_DIR}")
    return matches[-1]


def load_json_xz(path: Path) -> list[dict]:
    """Lê arquivo JSON padrão compactado com XZ."""
    with lzma.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def process_telemetry(veiculos_path: Path, lines_meta: dict[str, dict]) -> tuple[pd.DataFrame, dict[str, dict]]:
    """Extrai velocidades reais e contagem de ônibus por hora dentro do Quadrilátero Central."""
    pings_by_veh: dict[str, list[tuple[datetime, float, float, str]]] = defaultdict(list)

    with lzma.open(veiculos_path, "rt", encoding="utf-8") as f:
        for raw_line in f:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            rec = json.loads(raw_line)
            lat = parse_coord(rec["LAT"])
            lon = parse_coord(rec["LON"])
            if not inside_bbox(lon, lat):
                continue
            dt = datetime.strptime(rec["DTHR"], "%d/%m/%Y %H:%M:%S")
            pings_by_veh[rec["VEIC"]].append((dt, lat, lon, rec["COD_LINHA"]))

    hourly_speeds: dict[int, list[float]] = defaultdict(list)
    hourly_vehs: dict[int, set[str]] = defaultdict(set)
    line_speeds: dict[str, list[float]] = defaultdict(list)
    line_vehs: dict[str, set[str]] = defaultdict(set)

    for veh_id, points in pings_by_veh.items():
        points.sort(key=lambda item: item[0])
        for idx, (dt, lat, lon, cod) in enumerate(points):
            hourly_vehs[dt.hour].add(veh_id)
            line_vehs[cod].add(veh_id)
            if idx == 0:
                continue
            prev_dt, prev_lat, prev_lon, _ = points[idx - 1]
            dt_sec = (dt - prev_dt).total_seconds()
            if 5.0 <= dt_sec <= 120.0:
                dist_m = haversine_meters(prev_lat, prev_lon, lat, lon)
                speed_kmh = (dist_m / dt_sec) * 3.6
                if 0.0 <= speed_kmh <= 85.0:
                    hourly_speeds[dt.hour].append(speed_kmh)
                    line_speeds[cod].append(speed_kmh)

    hourly_rows = []
    for hour in range(24):
        speeds = hourly_speeds.get(hour, [])
        if not speeds and not hourly_vehs.get(hour):
            continue
        s_series = pd.Series(speeds) if speeds else pd.Series([0.0])
        hourly_rows.append(
            {
                "hora": hour,
                "veiculos_unicos": len(hourly_vehs[hour]),
                "amostras_velocidade": len(speeds),
                "vel_media_kmh": round(float(s_series.mean()), 2),
                "vel_mediana_kmh": round(float(s_series.median()), 2),
            }
        )

    line_stats = {}
    for cod, vehs in line_vehs.items():
        speeds = line_speeds.get(cod, [])
        meta = lines_meta.get(cod, {})
        line_stats[cod] = {
            "cod": cod,
            "nome": meta.get("NOME", "DESCONHECIDA"),
            "categoria": meta.get("CATEGORIA_SERVICO", "OUTRA"),
            "veiculos_reais_dia": len(vehs),
            "vel_media_real_kmh": round(sum(speeds) / len(speeds), 2) if speeds else 0.0,
        }

    return pd.DataFrame(hourly_rows), line_stats


def compute_peak_departures(tabela_rows: list[dict]) -> dict[str, float]:
    """Calcula partidas/hora no pico da tarde (17:00-19:00) em dia útil (DIA='1')."""
    counts: dict[str, int] = defaultdict(int)
    for row in tabela_rows:
        if row.get("DIA") != "1":
            continue
        hora = row.get("HORA", "")
        if "17:00" <= hora <= "19:00":
            counts[row["COD"]] += 1
    # Janela de 2 horas -> dividir por 2 para obter partidas/hora totais da linha
    return {cod: count / 2.0 for cod, count in counts.items()}


def map_shape_to_sumo_edges(net: sumolib.net.Net, coords: list[tuple[float, float]]) -> list[str]:
    """Converte uma sequência de (lon, lat) em uma rota contínua e válida de edges no SUMO."""
    # Amostra a cada ~2 pontos para reduzir ruído de GPS mantendo fidelidade
    sampled = coords[::2] if len(coords) > 10 else coords
    matched: list = []

    for lon, lat in sampled:
        if not inside_bbox(lon, lat):
            continue
        x, y = net.convertLonLat2XY(lon, lat)
        candidates = net.getNeighboringEdges(x, y, r=45.0)
        bus_candidates = [(edge, dist) for edge, dist in candidates if edge.allows("bus")]
        if not bus_candidates:
            continue
        bus_candidates.sort(key=lambda item: item[1])
        best_edge = bus_candidates[0][0]
        if not matched or matched[-1].getID() != best_edge.getID():
            # Evita vai-e-vem imediato entre duas pistas opostas próximas
            if len(matched) >= 2 and matched[-2].getID() == best_edge.getID():
                continue
            matched.append(best_edge)

    if len(matched) < 2:
        return []

    # Conecta trechos com caminho mínimo permitido para ônibus e escolhe o maior segmento contínuo
    segments: list[list[str]] = [[matched[0].getID()]]
    for next_edge in matched[1:]:
        prev_edge_id = segments[-1][-1]
        if prev_edge_id == next_edge.getID():
            continue
        prev_edge = net.getEdge(prev_edge_id)
        path, _ = net.getShortestPath(prev_edge, next_edge, vClass="bus", maxCost=1200.0)
        if path and len(path) <= 25:
            for edge in path[1:]:
                if segments[-1][-1] != edge.getID():
                    segments[-1].append(edge.getID())
        else:
            segments.append([next_edge.getID()])

    best_segment = max(segments, key=len)
    return best_segment if len(best_segment) >= 4 else []


def vtype_for_category(category: str) -> str:
    """Seleciona o tipo de veículo SUMO conforme a categoria URBS."""
    cat_upper = category.upper()
    if "EXPRESSO" in cat_upper or "LIGEIRÃO" in cat_upper:
        return "urbs_brt"
    if "LINHA DIRETA" in cat_upper:
        return "urbs_ligeirinho"
    return "urbs_convencional"


def build_bus_routes(
    net: sumolib.net.Net,
    shapes_rows: list[dict],
    lines_meta: dict[str, dict],
    peak_vph: dict[str, float],
    line_stats: dict[str, dict],
) -> tuple[int, list[dict]]:
    """Gera o arquivo XML de rotas reais de ônibus/BRT no SUMO."""
    grouped_shapes: dict[tuple[str, str], list[tuple[float, float]]] = defaultdict(list)
    for row in shapes_rows:
        lon = parse_coord(row["LON"])
        lat = parse_coord(row["LAT"])
        grouped_shapes[(row["COD"], row["SHP"])].append((lon, lat))

    # Filtra apenas shapes que entram no Quadrilátero Central
    central_shapes: dict[str, list[tuple[str, list[str]]]] = defaultdict(list)
    for (cod, shp_id), coords in grouped_shapes.items():
        if not any(inside_bbox(lon, lat) for lon, lat in coords):
            continue
        edges = map_shape_to_sumo_edges(net, coords)
        if edges:
            central_shapes[cod].append((shp_id, edges))

    root = ET.Element(
        "routes",
        {
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:noNamespaceSchemaLocation": "http://sumo.dlr.de/xsd/routes_file.xsd",
        },
    )

    ET.SubElement(
        root,
        "vType",
        {
            "id": "urbs_brt",
            "vClass": "bus",
            "length": "24.0",
            "maxSpeed": "16.67",
            "color": "0.9,0.1,0.1",
            "emissionClass": "HBEFA3/Bus",
        },
    )
    ET.SubElement(
        root,
        "vType",
        {
            "id": "urbs_ligeirinho",
            "vClass": "bus",
            "length": "13.0",
            "maxSpeed": "16.67",
            "color": "0.1,0.5,0.95",
            "emissionClass": "HBEFA3/Bus",
        },
    )
    ET.SubElement(
        root,
        "vType",
        {
            "id": "urbs_convencional",
            "vClass": "bus",
            "length": "12.0",
            "maxSpeed": "15.0",
            "color": "1.0,0.75,0.0",
            "emissionClass": "HBEFA3/Bus",
        },
    )

    total_flows = 0
    summary_rows = []

    for cod, shp_list in sorted(central_shapes.items()):
        meta = lines_meta.get(cod, {})
        category = meta.get("CATEGORIA_SERVICO", "CONVENCIONAL")
        vtype = vtype_for_category(category)
        total_vph = peak_vph.get(cod, 2.0)
        # Divide partidas totais entre os sentidos/shapes válidos encontrados
        vph_per_shp = max(1.0, round(total_vph / len(shp_list), 2))

        for shp_id, edges in shp_list:
            flow_id = f"urbs_{cod}_{shp_id}"
            flow_el = ET.SubElement(
                root,
                "flow",
                {
                    "id": flow_id,
                    "type": vtype,
                    "begin": "0",
                    "end": "3600",
                    "vehsPerHour": f"{vph_per_shp:.2f}",
                    "departLane": "best",
                    "departSpeed": "max",
                },
            )
            ET.SubElement(flow_el, "route", {"edges": " ".join(edges)})
            total_flows += 1

        stats = line_stats.get(cod, {})
        summary_rows.append(
            {
                "cod": cod,
                "nome": meta.get("NOME", ""),
                "categoria": category,
                "shapes_mapeados": len(shp_list),
                "partidas_pico_hora": round(total_vph, 2),
                "veiculos_reais_dia": stats.get("veiculos_reais_dia", 0),
                "vel_media_real_kmh": stats.get("vel_media_real_kmh", 0.0),
            }
        )

    OUT_ROUTES.parent.mkdir(parents=True, exist_ok=True)
    tree = ET.ElementTree(root)
    ET.indent(tree, space="    ")
    tree.write(OUT_ROUTES, encoding="utf-8", xml_declaration=True)
    return total_flows, summary_rows


def main() -> None:
    linhas_path = find_urbs_file("linhas")
    shapes_path = find_urbs_file("shapeLinha")
    tabela_path = find_urbs_file("tabelaLinha")
    veiculos_path = find_urbs_file("veiculos")

    print("Lendo dados da URBS...")
    linhas_rows = load_json_xz(linhas_path)
    lines_meta = {row["COD"]: row for row in linhas_rows}
    shapes_rows = load_json_xz(shapes_path)
    tabela_rows = load_json_xz(tabela_path)

    print("Processando telemetria GPS real (veiculos)...")
    hourly_df, line_stats = process_telemetry(veiculos_path, lines_meta)
    OUT_TELEMETRY_HOURLY.parent.mkdir(parents=True, exist_ok=True)
    hourly_df.to_csv(OUT_TELEMETRY_HOURLY, index=False)

    print("Calculando partidas no horário de pico (17:00-19:00) e mapeando rotas no SUMO...")
    peak_vph = compute_peak_departures(tabela_rows)
    net = sumolib.net.readNet(str(NET_PATH))
    total_flows, summary_rows = build_bus_routes(net, shapes_rows, lines_meta, peak_vph, line_stats)

    summary_df = pd.DataFrame(summary_rows).sort_values(by="partidas_pico_hora", ascending=False)
    summary_df.to_csv(OUT_CENTRAL_LINES, index=False)

    print(f"Concluído! {len(summary_df)} linhas centrais e {total_flows} fluxos gravados em {OUT_ROUTES}")
    print(f"Resumo de telemetria salvo em {OUT_TELEMETRY_HOURLY} e {OUT_CENTRAL_LINES}")


if __name__ == "__main__":
    main()
