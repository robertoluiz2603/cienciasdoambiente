"""Gerador de gráficos em alta resolução (300 DPI) para apresentação e relatório final (Marco 4)."""

from __future__ import annotations

from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


OUT_DIR = Path("docs/graficos")
COMP_CSV = Path("data/comparativo_4_cenarios.csv")
GEH_CSV = Path("data/contagens_geh_as_is.csv")
URBS_HOURLY_CSV = Path("data/urbs_telemetry_hourly.csv")
PAX_CSV = Path("data/conservacao_passageiros.csv")

SCENARIO_META = [
    ("as_is", "1. As-Is (Atual)", Path("data/kpi_as_is.csv"), "#6c757d"),
    ("to_be_1", "2. To-Be 1 (Grupo)", Path("data/kpi_to_be_1.csv"), "#2b8cbe"),
    ("to_be_2", "3. To-Be 2 (Algoritmos)", Path("data/kpi_to_be_2.csv"), "#f28e2b"),
    ("to_be_3", "4. To-Be 3 (Conjunto)", Path("data/kpi_to_be_3.csv"), "#1b9e77"),
]


def setup_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "#fbfcfd",
            "axes.edgecolor": "#d0d7de",
            "axes.grid": True,
            "grid.color": "#e6ebf0",
            "grid.linestyle": "--",
            "grid.linewidth": 0.7,
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.titleweight": "bold",
            "axes.labelsize": 10,
            "legend.frameon": True,
            "legend.facecolor": "white",
            "legend.edgecolor": "#d0d7de",
        }
    )


def load_series() -> dict[str, pd.DataFrame]:
    return {key: pd.read_csv(path) for key, _, path, _ in SCENARIO_META}


def chart_01_velocidades(comp: pd.DataFrame, series: dict[str, pd.DataFrame]) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    metrics = [
        ("mean_speed_kmh", "Vel. Geral"),
        ("passenger_weighted_speed_kmh", "Vel. p/ Passageiro"),
        ("bus_mean_speed_kmh", "Ônibus URBS"),
        ("emergency_mean_speed_kmh", "Ambulâncias"),
    ]
    by_m = comp.set_index("metrica")
    x = np.arange(len(metrics))
    width = 0.2

    for i, (key, label, _, color) in enumerate(SCENARIO_META):
        vals = [float(by_m.loc[m, key]) for m, _ in metrics]
        bars = ax1.bar(x + (i - 1.5) * width, vals, width, label=label, color=color, alpha=0.92)
        for b, v in zip(bars, vals):
            ax1.text(
                b.get_x() + b.get_width() / 2,
                v + 0.5,
                f"{v:.1f}",
                ha="center",
                va="bottom",
                fontsize=7.5,
                fontweight="bold",
            )

    ax1.set_xticks(x)
    ax1.set_xticklabels([lbl for _, lbl in metrics])
    ax1.set_ylabel("Velocidade Média (km/h)")
    ax1.set_ylim(0, 36.5)
    ax1.set_title("Comparativo de Velocidades por Classe")
    ax1.legend(loc="upper left", fontsize=8.5)

    for key, label, _, color in SCENARIO_META:
        df = series[key]
        bus_s = pd.to_numeric(df["bus_mean_speed_kmh"], errors="coerce").rolling(20, min_periods=1).mean()
        ax2.plot(df["step"], bus_s, label=label, color=color, linewidth=2.2)

    ax2.set_xlabel("Tempo de Simulação (s)")
    ax2.set_ylabel("Velocidade Média dos Ônibus (km/h)")
    ax2.set_title("Evolução da Velocidade dos Ônibus URBS (Média Móvel 20 s)")
    ax2.set_ylim(10, 45)
    ax2.legend(loc="upper right", fontsize=8.5)

    fig.suptitle("Desempenho de Velocidade nos 4 Cenários (Horário de Pico — Curitiba)", fontsize=13.5, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "01_comparativo_velocidades_4_cenarios.png", dpi=300)
    plt.close(fig)


def chart_02_filas(comp: pd.DataFrame, series: dict[str, pd.DataFrame]) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    for key, label, _, color in SCENARIO_META:
        df = series[key]
        halting_s = df["halting_vehicles"].rolling(15, min_periods=1).mean()
        ax1.plot(df["step"], halting_s, label=label, color=color, linewidth=2.2)

    ax1.set_xlabel("Tempo de Simulação (s)")
    ax1.set_ylabel("Veículos Parados em Fila (veíc)")
    ax1.set_title("Evolução das Filas ao Longo da Simulação (Média Móvel 15 s)")
    ax1.legend(loc="upper left", fontsize=8.5)

    by_m = comp.set_index("metrica")
    labels = [lbl for _, lbl, _, _ in SCENARIO_META]
    colors = [clr for _, _, _, clr in SCENARIO_META]
    queue_vals = [float(by_m.loc["queue_length_m_mean", key]) for key, _, _, _ in SCENARIO_META]
    deltas = [0.0] + [float(by_m.loc["queue_length_m_mean", f"delta_{key}_pct"]) for key, _, _, _ in SCENARIO_META[1:]]

    bars = ax2.bar(labels, queue_vals, color=colors, width=0.55, alpha=0.92)
    for idx, (b, v, d) in enumerate(zip(bars, queue_vals, deltas)):
        txt = f"{v:,.0f} m".replace(",", ".") if idx == 0 else f"{v:,.0f} m\n({d:+.1f}%)".replace(",", ".")
        ax2.text(b.get_x() + b.get_width() / 2, v + 45, txt, ha="center", va="bottom", fontsize=9, fontweight="bold")

    ax2.set_ylabel("Comprimento Médio Total de Filas (m)")
    ax2.set_ylim(0, 2450)
    ax2.set_title("Redução Média de Congestionamento por Cenário")
    ax2.tick_params(axis="x", labelsize=8.5)

    fig.suptitle("Comparativo de Filas e Congestionamento (As-Is vs. Soluções Isoladas vs. Conjunto)", fontsize=13.5, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "02_evolucao_filas_4_cenarios.png", dpi=300)
    plt.close(fig)


def chart_03_emissoes(comp: pd.DataFrame, series: dict[str, pd.DataFrame]) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2))
    by_m = comp.set_index("metrica")
    labels = ["As-Is", "To-Be 1\n(Grupo)", "To-Be 2\n(Algoritmos)", "To-Be 3\n(Conjunto)"]
    colors = [clr for _, _, _, clr in SCENARIO_META]

    # Painel 1: Intensidade de Carbono (g CO2 / pax*km)
    c_vals = [float(by_m.loc["co2_g_per_pax_km", key]) for key, _, _, _ in SCENARIO_META]
    c_deltas = [0.0] + [float(by_m.loc["co2_g_per_pax_km", f"delta_{key}_pct"]) for key, _, _, _ in SCENARIO_META[1:]]
    bars1 = axes[0].bar(labels, c_vals, color=colors, width=0.58, alpha=0.92)
    for idx, (b, v, d) in enumerate(zip(bars1, c_vals, c_deltas)):
        txt = f"{v:.2f} g" if idx == 0 else f"{v:.2f} g\n({d:+.1f}%)"
        axes[0].text(b.get_x() + b.get_width() / 2, v + 1.1, txt, ha="center", va="bottom", fontsize=8.5, fontweight="bold")
    axes[0].set_ylabel("g CO2 / pax·km")
    axes[0].set_ylim(0, 64)
    axes[0].set_title("Intensidade de Carbono por Deslocamento")

    # Painel 2: Material Particulado PMx acumulado (g)
    p_vals = [float(by_m.loc["pmx_total_g", key]) for key, _, _, _ in SCENARIO_META]
    p_deltas = [0.0] + [float(by_m.loc["pmx_total_g", f"delta_{key}_pct"]) for key, _, _, _ in SCENARIO_META[1:]]
    bars2 = axes[1].bar(labels, p_vals, color=colors, width=0.58, alpha=0.92)
    for idx, (b, v, d) in enumerate(zip(bars2, p_vals, p_deltas)):
        txt = f"{v:.1f} g" if idx == 0 else f"{v:.1f} g\n({d:+.1f}%)"
        axes[1].text(b.get_x() + b.get_width() / 2, v + 10, txt, ha="center", va="bottom", fontsize=8.5, fontweight="bold")
    axes[1].set_ylabel("PMx Acumulado em 600 s (g)")
    axes[1].set_ylim(0, 640)
    axes[1].set_title("Material Particulado Total (PMx)")

    # Painel 3: Curva temporal de CO2 instantâneo
    for key, label, _, color in SCENARIO_META:
        df = series[key]
        co2_s = df["co2_g_s"].rolling(20, min_periods=1).mean()
        axes[2].plot(df["step"], co2_s, label=label, color=color, linewidth=2.0)
    axes[2].set_xlabel("Tempo de Simulação (s)")
    axes[2].set_ylabel("Emissão Instantânea de CO2 (g/s)")
    axes[2].set_title("Curva de CO2 Instantâneo (Média Móvel 20 s)")
    axes[2].legend(loc="upper left", fontsize=8)

    fig.suptitle("Impacto Ambiental Atmosférico (Modelo Cinemático HBEFA3 — SUMO)", fontsize=13.5, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "03_emissoes_hbefa3_4_cenarios.png", dpi=300)
    plt.close(fig)


def chart_04_ruido(comp: pd.DataFrame, series: dict[str, pd.DataFrame]) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.3))

    for key, label, _, color in SCENARIO_META:
        df = series[key]
        leq_s = df["noise_leq_dba"].rolling(20, min_periods=1).mean()
        ax1.plot(df["step"], leq_s, label=label, color=color, linewidth=2.1)

    ax1.axhline(65.0, color="#d62728", linestyle="--", linewidth=1.8, label="Limite ABNT NBR 10151 (65 dB(A))")
    ax1.set_xlabel("Tempo de Simulação (s)")
    ax1.set_ylabel("Nível de Pressão Sonora Leq [dB(A)]")
    ax1.set_ylim(64.0, 71.5)
    ax1.set_title("Evolução do Ruído Urbano ao Longo do Pico")
    ax1.legend(loc="lower right", fontsize=8.5)

    by_m = comp.set_index("metrica")
    labels = ["As-Is", "To-Be 1\n(Grupo)", "To-Be 2\n(Algoritmos)", "To-Be 3\n(Conjunto)"]
    colors = [clr for _, _, _, clr in SCENARIO_META]
    vals = [float(by_m.loc["noise_leq_mean_dba", key]) for key, _, _, _ in SCENARIO_META]
    deltas = [0.0] + [float(by_m.loc["noise_leq_mean_dba", f"delta_{key}_pct"]) for key, _, _, _ in SCENARIO_META[1:]]

    bars = ax2.bar(labels, vals, color=colors, width=0.55, alpha=0.92)
    ax2.axhline(65.0, color="#d62728", linestyle="--", linewidth=1.8, label="Limite Diurno NBR 10151 (65 dB(A))")
    for idx, (b, v, d) in enumerate(zip(bars, vals, deltas)):
        txt = f"{v:.2f} dB" if idx == 0 else f"{v:.2f} dB\n({d:+.2f} dB)"
        ax2.text(b.get_x() + b.get_width() / 2, v + 0.12, txt, ha="center", va="bottom", fontsize=8.8, fontweight="bold")
    ax2.set_ylabel("Leq Médio [dB(A)]")
    ax2.set_ylim(64.0, 71.2)
    ax2.set_title("Nível Médio de Ruído por Cenário (FHWA/CoRTN)")
    ax2.legend(loc="upper right", fontsize=8.5)

    fig.suptitle("Avaliação Acústica Urbana vs. ABNT NBR 10151", fontsize=13.5, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "04_ruido_urbano_leq_nbr10151.png", dpi=300)
    plt.close(fig)


def chart_05_emergencia(comp: pd.DataFrame) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.0))
    by_m = comp.set_index("metrica")
    labels = ["As-Is\n(Sem Prioridade)", "To-Be 1\n(Faixa Exclusiva)", "To-Be 2\n(Só Preempção EVP)", "To-Be 3\n(Conjunto)"]
    colors = [clr for _, _, _, clr in SCENARIO_META]

    t_vals = [float(by_m.loc["amb_avg_travel_time_s", key]) for key, _, _, _ in SCENARIO_META]
    t_deltas = [0.0] + [float(by_m.loc["amb_avg_travel_time_s", f"delta_{key}_pct"]) for key, _, _, _ in SCENARIO_META[1:]]
    bars1 = ax1.bar(labels, t_vals, color=colors, width=0.55, alpha=0.92)
    for idx, (b, v, d) in enumerate(zip(bars1, t_vals, t_deltas)):
        txt = f"{v:.1f} s" if idx == 0 else f"{v:.1f} s\n({d:+.1f}%)"
        ax1.text(b.get_x() + b.get_width() / 2, v + 7, txt, ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax1.set_ylabel("Tempo Médio de Viagem das Ambulâncias (s)")
    ax1.set_ylim(0, 445)
    ax1.set_title("Tempo de Resposta das Ambulâncias até Hospitais")

    s_vals = [float(by_m.loc["emergency_mean_speed_kmh", key]) for key, _, _, _ in SCENARIO_META]
    s_deltas = [0.0] + [float(by_m.loc["emergency_mean_speed_kmh", f"delta_{key}_pct"]) for key, _, _, _ in SCENARIO_META[1:]]
    bars2 = ax2.bar(labels, s_vals, color=colors, width=0.55, alpha=0.92)
    for idx, (b, v, d) in enumerate(zip(bars2, s_vals, s_deltas)):
        txt = f"{v:.2f} km/h" if idx == 0 else f"{v:.2f} km/h\n({d:+.1f}%)"
        ax2.text(b.get_x() + b.get_width() / 2, v + 0.7, txt, ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax2.set_ylabel("Velocidade Média em Rota (km/h)")
    ax2.set_ylim(0, 38)
    ax2.set_title("Velocidade Média das Ambulâncias em Serviço")

    fig.suptitle("Atendimento a Serviços Essenciais — Preempção de Emergência (EVP)", fontsize=13.5, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "05_emergencia_evp_ambulancias.png", dpi=300)
    plt.close(fig)


def chart_06_geh_e_urbs() -> None:
    df_urbs = pd.read_csv(URBS_HOURLY_CSV)
    df_geh = pd.read_csv(GEH_CSV)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.5, 5.5))

    # Esquerda: Telemetria URBS 24h
    ax1_twin = ax1.twinx()
    ax1_twin.bar(df_urbs["hora"], df_urbs["veiculos_unicos"], color="#cfe2f3", alpha=0.75, label="Ônibus únicos/h (URBS)")
    ax1.plot(df_urbs["hora"], df_urbs["vel_media_kmh"], color="#d95f02", marker="o", linewidth=2.3, label="Velocidade média (km/h)")
    ax1.set_zorder(ax1_twin.get_zorder() + 1)
    ax1.patch.set_visible(False)

    ax1.axvspan(6.5, 9.0, color="#fde0dd", alpha=0.35, label="Picos do Manual (06:30–09h / 17–19h)")
    ax1.axvspan(17.0, 19.0, color="#fde0dd", alpha=0.35)
    ax1.annotate("Pico 18h: 20,37 km/h\n(647 ônibus/h)", xy=(18, 20.37), xytext=(12.2, 16.5),
                 arrowprops=dict(arrowstyle="->", color="#b2182b"), fontsize=9, fontweight="bold", color="#b2182b")

    ax1.set_xlabel("Hora do Dia (Dados Reais GPS URBS)")
    ax1.set_ylabel("Velocidade Média dos Ônibus (km/h)", color="#d95f02")
    ax1_twin.set_ylabel("Ônibus Únicos Monitorados / Hora", color="#2b5c8f")
    ax1.set_xticks(range(0, 24, 2))
    ax1.set_ylim(15, 34)
    ax1_twin.set_ylim(0, 820)
    ax1.set_title("Telemetria Real URBS no Quadrilátero Central (24h)")
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax1_twin.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper right", fontsize=8)

    # Direita: Validação GEH 10 vias
    df_geh = df_geh.sort_values("geh", ascending=True)
    short_names = [s.replace("Avenida Presidente ", "Av. Pres. ").replace("Avenida ", "Av. ").replace("Alameda Doutor ", "Al. Dr. ").replace("Rua General ", "R. Gen. ") for s in df_geh["logradouro"]]
    bars = ax2.barh(short_names, df_geh["geh"], color="#1b9e77", alpha=0.9)
    ax2.axvline(5.0, color="#d62728", linestyle="--", linewidth=1.8, label="Limite de Validação (GEH < 5,0)")
    for b, v in zip(bars, df_geh["geh"]):
        ax2.text(v + 0.08, b.get_y() + b.get_height() / 2, f"{v:.3f}", va="center", fontsize=8.5, fontweight="bold")
    ax2.set_xlim(0, 5.6)
    ax2.set_xlabel("Estatística GEH (As-Is Simulado vs. Referência)")
    ax2.set_title("Calibração GEH das 10 Vias (10/10 Aprovadas = 100%)")
    ax2.legend(loc="lower right", fontsize=8.5)

    fig.suptitle("Embasamento Empírico (URBS) e Validação Estatística (GEH — Marco 2)", fontsize=13.5, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "06_validacao_geh_e_telemetria_urbs.png", dpi=300)
    plt.close(fig)


def chart_07_conservacao_modal() -> None:
    df = pd.read_csv(PAX_CSV)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.2))

    # Esquerda: Frota de automóveis + modais substitutos
    as_is_cars = int(df[df["cenario"] == "As-Is"]["veiculos"].sum())
    to_be_cars = int(df[(df["cenario"] == "To-Be") & (df["modal"].str.startswith("Automóvel"))]["veiculos"].sum())
    to_be_center_cars = int(
        df[(df["cenario"] == "To-Be") & (df["modal"].isin(["Automóvel individual remanescente (car__passenger)", "Automóvel em carona compartilhada (car_carpool)"]))]["veiculos"].sum()
    )

    cats = ["As-Is\n(Total no Mapa)", "To-Be\n(Total incl. Park & Ride)", "To-Be\n(Circulando no Centro)"]
    vals = [as_is_cars, to_be_cars, to_be_center_cars]
    colors = ["#6c757d", "#2b8cbe", "#1b9e77"]
    bars = ax1.bar(cats, vals, color=colors, width=0.52, alpha=0.92)
    notes = ["1.240 carros", "839 carros\n(-32,3%)", "695 carros\n(-44,0%)"]
    for b, v, note in zip(bars, vals, notes):
        ax1.text(b.get_x() + b.get_width() / 2, v + 25, note, ha="center", va="bottom", fontsize=9.5, fontweight="bold")
    ax1.set_ylim(0, 1480)
    ax1.set_ylabel("Número de Automóveis Gerados (600 s)")
    ax1.set_title("Redução da Frota de Automóveis no Cenário To-Be")

    # Direita: Conservação exata de 1.640 passageiros por modal
    as_is_df = df[df["cenario"] == "As-Is"]
    to_be_df = df[df["cenario"] == "To-Be"]

    bottom = 0.0
    as_colors = ["#8c96c6", "#fd8d3c"]
    for (_, row), clr in zip(as_is_df.iterrows(), as_colors):
        val = float(row["passageiros_totais"])
        ax2.bar("As-Is\n(1.640,0 pax)", val, bottom=bottom, width=0.45, color=clr, label=row["modal"].split(" (")[0])
        ax2.text(0, bottom + val / 2, f"{val:.0f} pax", ha="center", va="center", color="white", fontweight="bold", fontsize=9)
        bottom += val

    bottom = 0.0
    tb_colors = ["#4eb3d3", "#1b9e77", "#386cb0", "#17becf", "#ffd92f"]
    for (_, row), clr in zip(to_be_df.iterrows(), tb_colors):
        val = float(row["passageiros_totais"])
        ax2.bar("To-Be\n(1.640,0 pax)", val, bottom=bottom, width=0.45, color=clr, label=row["modal"].split(" (")[0])
        if val >= 75:
            ax2.text(1, bottom + val / 2, f"{val:.0f} pax", ha="center", va="center", color="black" if clr == "#ffd92f" else "white", fontweight="bold", fontsize=8.5)
        bottom += val

    ax2.set_ylim(0, 2450)
    ax2.set_ylabel("Total de Passageiros Transportados (pax)")
    ax2.set_title("Conservação Exata de Demanda (1.640,0 Passageiros)")
    ax2.legend(loc="upper center", ncol=2, fontsize=7.5)

    fig.suptitle("Equidade Metodológica — Menos Carros na Via para o Mesmo Total de Pessoas", fontsize=13.5, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "07_conservacao_passageiros_modais.png", dpi=300)
    plt.close(fig)


def main() -> None:
    setup_style()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    comp = pd.read_csv(COMP_CSV)
    series = load_series()

    chart_01_velocidades(comp, series)
    chart_02_filas(comp, series)
    chart_03_emissoes(comp, series)
    chart_04_ruido(comp, series)
    chart_05_emergencia(comp)
    chart_06_geh_e_urbs()
    chart_07_conservacao_modal()

    generated = sorted(OUT_DIR.glob("*.png"))
    print(f"{len(generated)} gráficos gerados em {OUT_DIR}:")
    for p in generated:
        print(f" - {p}")


if __name__ == "__main__":
    main()
