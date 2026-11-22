"""Painel interativo (Streamlit) comparando os 4 cenários (As-Is, To-Be 1, To-Be 2 e To-Be 3),
impacto ambiental/acústico, intervenções urbanas, IoT/MQTT, GEH e telemetria real da URBS.
"""

from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
import streamlit as st
from geh_calibration import evaluate_calibration


st.set_page_config(page_title="Curitiba Smart Mobility — 4 Cenários", layout="wide")
st.title("Quadrilátero Central de Curitiba — Comparativo Fatorial dos 4 Cenários")
st.caption(
    "As-Is (Atual) | To-Be 1 (Grupo) | To-Be 2 (Algoritmos) | To-Be 3 (Conjunto: Grupo + Algoritmos) — "
    "Dados Reais URBS/IPPUC + Simulação SUMO/TraCI"
)

COMP_CSV = Path("data/comparativo_4_cenarios.csv")
KPI_FILES = {
    "1. As-Is (Atual)": Path("data/kpi_as_is.csv"),
    "2. To-Be 1 (Grupo)": Path("data/kpi_to_be_1.csv"),
    "3. To-Be 2 (Algoritmos)": Path("data/kpi_to_be_2.csv"),
    "4. To-Be 3 (Conjunto)": Path("data/kpi_to_be_3.csv"),
}


def load_scenario_series() -> dict[str, pd.DataFrame]:
    loaded = {}
    for label, path in KPI_FILES.items():
        if path.exists():
            loaded[label] = pd.read_csv(path)
    return loaded


def build_joined_series(dfs: dict[str, pd.DataFrame], column: str) -> pd.DataFrame:
    merged = pd.DataFrame()
    for label, df in dfs.items():
        if column in df.columns:
            merged[label] = pd.to_numeric(df.set_index("step")[column], errors="coerce")
    return merged


tab_comp, tab_env, tab_group, tab_iot = st.tabs(
    [
        "1. Comparativo dos 4 Cenários",
        "2. Impacto Ambiental e Acústico",
        "3. Intervenções do Grupo & POIs",
        "4. Sensores MQTT, GEH & URBS",
    ]
)

series_dict = load_scenario_series()

with tab_comp:
    if not COMP_CSV.exists():
        st.warning("Execute `python src/run_all_scenarios.py` para gerar o comparativo dos 4 cenários.")
    else:
        comp_df = pd.read_csv(COMP_CSV)
        by_key = comp_df.set_index("metrica")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric(
            "Vel. Ponderada p/ Passageiro (To-Be 3)",
            f"{by_key.loc['passenger_weighted_speed_kmh', 'to_be_3']:.2f} km/h",
            f"{by_key.loc['passenger_weighted_speed_kmh', 'delta_to_be_3_pct']:+.1f}% vs As-Is",
        )
        c2.metric(
            "Velocidade Média Ônibus URBS (To-Be 3)",
            f"{by_key.loc['bus_mean_speed_kmh', 'to_be_3']:.2f} km/h",
            f"{by_key.loc['bus_mean_speed_kmh', 'delta_to_be_3_pct']:+.1f}% vs As-Is",
        )
        c3.metric(
            "Veículos em Fila (To-Be 3)",
            f"{by_key.loc['halting_vehicles_mean', 'to_be_3']:.1f} veíc",
            f"{by_key.loc['halting_vehicles_mean', 'delta_to_be_3_pct']:+.1f}% vs As-Is",
        )
        c4.metric(
            "Tempo Médio Ambulância EVP (To-Be 3)",
            f"{by_key.loc['amb_avg_travel_time_s', 'to_be_3']:.1f} s",
            f"{by_key.loc['amb_avg_travel_time_s', 'delta_to_be_3_pct']:+.1f}% vs As-Is",
        )

        st.subheader("Tabela Consolidada dos 4 Cenários")
        st.dataframe(
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
            ],
            use_container_width=True,
        )

        if series_dict:
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("Velocidade Ponderada por Passageiro (km/h)")
                st.line_chart(build_joined_series(series_dict, "passenger_weighted_speed_kmh"))
            with col_b:
                st.subheader("Veículos Parados em Fila")
                st.line_chart(build_joined_series(series_dict, "halting_vehicles"))

            st.subheader("Velocidade Média dos Ônibus URBS (km/h)")
            st.line_chart(build_joined_series(series_dict, "bus_mean_speed_kmh"))

with tab_env:
    if not COMP_CSV.exists():
        st.warning("Aguardando execução de `python src/run_all_scenarios.py`.")
    else:
        comp_df = pd.read_csv(COMP_CSV).set_index("metrica")
        e1, e2, e3, e4, e5 = st.columns(5)
        e1.metric(
            "CO2 Acumulado (To-Be 3)",
            f"{comp_df.loc['co2_total_kg', 'to_be_3']:.1f} kg",
            f"{comp_df.loc['co2_total_kg', 'delta_to_be_3_pct']:+.1f}% vs As-Is",
        )
        e2.metric(
            "CO2 / pax·km (To-Be 3)",
            f"{comp_df.loc['co2_g_per_pax_km', 'to_be_3']:.2f} g",
            f"{comp_df.loc['co2_g_per_pax_km', 'delta_to_be_3_pct']:+.1f}% vs As-Is",
        )
        e3.metric(
            "NOx Acumulado (To-Be 3)",
            f"{comp_df.loc['nox_total_g', 'to_be_3']:.1f} g",
            f"{comp_df.loc['nox_total_g', 'delta_to_be_3_pct']:+.1f}% vs As-Is",
        )
        e4.metric(
            "Material Particulado PMx (To-Be 3)",
            f"{comp_df.loc['pmx_total_g', 'to_be_3']:.1f} g",
            f"{comp_df.loc['pmx_total_g', 'delta_to_be_3_pct']:+.1f}% vs As-Is",
        )
        e5.metric(
            "Ruído Médio Leq (NBR 10151: 65 dB)",
            f"{comp_df.loc['noise_leq_mean_dba', 'to_be_3']:.2f} dB(A)",
            f"{comp_df.loc['noise_leq_mean_dba', 'delta_to_be_3_pct']:+.2f} dB(A) vs As-Is",
        )

        if series_dict:
            st.subheader("Emissão Instantânea de CO2 (g/s) — Modelo HBEFA3")
            st.line_chart(build_joined_series(series_dict, "co2_g_s"))

            col_n1, col_n2 = st.columns(2)
            with col_n1:
                st.subheader("Emissão Instantânea de PMx (g/s)")
                st.line_chart(build_joined_series(series_dict, "pmx_g_s"))
            with col_n2:
                st.subheader("Nível de Pressão Sonora Equivalente Leq (dB(A))")
                noise_df = build_joined_series(series_dict, "noise_leq_dba")
                noise_df["Limite ABNT NBR 10151 (65 dB(A))"] = 65.0
                st.line_chart(noise_df)

with tab_group:
    pax_path = Path("data/conservacao_passageiros.csv")
    corr_path = Path("data/corredores_faixa_exclusiva.csv")
    pois_path = Path("data/pois_mapped_sumo.csv")

    if pax_path.exists():
        st.subheader("Conservação de Passageiros entre As-Is e To-Be (Equação 2)")
        st.dataframe(pd.read_csv(pax_path), use_container_width=True)
    if corr_path.exists():
        st.subheader("Corredores de Faixa Exclusiva / Prioritária (5 Avenidas do Grupo)")
        corr_df = pd.read_csv(corr_path)
        summary_corr = (
            corr_df.groupby(["avenida", "modo_to_be"])
            .agg(trechos=("edge_id", "count"), extensao_m=("comprimento_m", "sum"))
            .reset_index()
        )
        st.dataframe(summary_corr, use_container_width=True)
    if pois_path.exists():
        st.subheader("POIs Reais da URBS Mapeados no SUMO (Terminais, Escolas e Hospitais)")
        st.dataframe(pd.read_csv(pois_path), use_container_width=True)

with tab_iot:
    geh_path = Path("data/contagens_geh_as_is.csv")
    mqtt_path = Path("data/mqtt_sample_payloads.json")
    hourly_path = Path("data/urbs_telemetry_hourly.csv")
    lines_path = Path("data/urbs_central_lines.csv")

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.subheader("Validação Estatística GEH (Cenário As-Is)")
        if geh_path.exists():
            res = evaluate_calibration(geh_path)
            st.metric(
                "Taxa de Aprovação (GEH < 5.0)",
                f"{res['vias_aprovadas']}/{res['total_vias']} ({res['taxa_aprovacao']*100:.0f}%)",
                "Aprovado (>=85%)" if res["modelo_valido"] else "Requer ajuste",
            )
            st.dataframe(res["dataframe"], use_container_width=True)
        else:
            st.info("Execute `python src/geh_calibration.py --refresh`.")

    with col_g2:
        st.subheader("Contrato JSON IoT/MQTT (`paho-mqtt`)")
        if mqtt_path.exists():
            samples = json.loads(mqtt_path.read_text(encoding="utf-8"))
            if samples:
                st.json(samples[-1])
        else:
            st.info("Execute `python src/traci_controller.py --scenario to_be_3` para capturar payloads MQTT.")

    if hourly_path.exists() and lines_path.exists():
        df_hourly = pd.read_csv(hourly_path)
        df_lines = pd.read_csv(lines_path)
        st.subheader("Telemetria Real URBS — Velocidade Média e Frota por Hora")
        st.line_chart(df_hourly.set_index("hora")[["vel_media_kmh", "vel_mediana_kmh"]])
        st.bar_chart(df_hourly.set_index("hora")[["veiculos_unicos"]])
        st.dataframe(df_lines, use_container_width=True)
