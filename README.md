# Mobilidade Urbana, Sustentabilidade e Sistemas Ciber-Físicos (UTFPR)

Projeto multidisciplinar de **Ciências do Ambiente** — Quadrilátero Central de Curitiba (Setor Especial Estrutural) e área de intervenção (`Campina do Siqueira`, `Portão`, `Guadalupe` e Centro).

## Estrutura do Projeto (Marcos CDIO M1–M4)

- `data/` — Dados abertos da **URBS** (`2026_11_12_*.json.xz`), shapefiles SIRGAS do **IPPUC** (`data/ippuc/sirgas/`), contagens GEH (`contagens_geh_as_is.csv`), conservação de passageiros (`conservacao_passageiros.csv`), payloads IoT/MQTT (`mqtt_sample_payloads.json`), logs de KPIs (`kpi_as_is.csv`, `kpi_to_be_1.csv`, `kpi_to_be_2.csv`, `kpi_to_be_3.csv`) e comparativo consolidado (`comparativo_4_cenarios.csv`).
- `docs/` — Manual do projeto (`Manual_Projeto.pdf`), revisão de 40 artigos científicos (`docs/artigos/`), especificações arquiteturais (`solucao_arquitetural_CWB_EcoSync_4L.md`, `plano_unificado_grupo_artigos.md`) e relatório final (`comparativo_4_cenarios.md`).
- `simulation/` — Malha viária OSM (`network/curitiba.net.xml`, 21.080 arestas e 482 semáforos), cenário base (`as_is/`) e cenário proposto (`to_be/`).
- `src/` — Pipeline URBS (`urbs_pipeline.py`), construtor de cenários (`scenario_builder.py`), validação GEH (`geh_calibration.py`), controlador TraCI/MQTT (`traci_controller.py`), orquestrador dos 4 cenários (`run_all_scenarios.py`) e painel Streamlit (`dashboard.py`).

## Cenários Modelados (Experimento Fatorial 2×2)

1. **`As-Is` (Cenário Atual):** Demanda atual calibrada (1.200 carros base, 40 carros escolares com parada bloqueando faixa em 6 escolas reais, 12 ambulâncias e 332 fluxos reais URBS) com semáforos em tempo fixo.
2. **`To-Be 1` (Solução Urbana do Grupo):** Faixas exclusivas/prioritárias nas 5 avenidas (`Mariano Torres`, `Getúlio Vargas`, `Kennedy`, `Arthur Bernardes`, `Manoel Ribas`), carona compartilhada (`1,30 -> 1,65 pax/carro`), Park & Ride nos 3 terminais (`Campina do Siqueira`, `Portão`, `Guadalupe`), 8 ônibus escolares e 60 bicicletas/autopropelidos (conservando 1.640 passageiros de automóvel), ainda com semáforos fixos.
3. **`To-Be 2` (Solução Algorítmica `CWB-EcoSync-Lean`):** Controlador adaptativo OCC-MP ponderado por passageiros + filtro de parada em estação-tubo ($\beta_v$) + regras SOTL (anti-spillback, verde mínimo, anti-inanição) + Onda Verde arterial (`20,4 km/h`) + preempção para ambulâncias (EVP), aplicado sobre a malha/demanda atual (`As-Is`).
4. **`To-Be 3` (Conjunto Integrado = `To-Be 1` + `To-Be 2`):** Combina todas as intervenções urbanas/modais do grupo com o controle semafórico adaptativo e telemetria IoT/MQTT.

### Síntese dos Resultados (600 s em horário de pico)

| Indicador | `As-Is` | `To-Be 1` | `To-Be 2` | `To-Be 3` (Conjunto) |
| :--- | :---: | :---: | :---: | :---: |
| Veículos ativos (média) | 885,7 | 740,0 (-16,5%) | 862,5 (-2,6%) | **718,7 (-18,9%)** |
| Velocidade média ônibus URBS | 17,78 km/h | 18,19 km/h (+2,3%) | 22,53 km/h (+26,7%) | **22,53 km/h (+26,7%)** |
| Tempo médio ambulância (EVP) | 375,0 s | 304,5 s (-18,8%) | 298,2 s (-20,5%) | **259,0 s (-30,9%)** |
| Veículos parados em fila | 314,2 | 269,1 (-14,4%) | 222,7 (-29,1%) | **197,8 (-37,1%)** |
| Material particulado $\text{PM}_x$ | 535,57 g | 497,82 g (-7,1%) | 537,82 g (+0,4%) | **492,79 g (-8,0%)** |
| Intensidade $\text{CO}_2$ / $\text{pax}\cdot\text{km}$ | 53,16 g | 50,82 g (-4,4%) | 47,22 g (-11,2%) | **45,26 g (-14,9%)** |
| Ruído médio ($L_{eq}$) | 69,61 dB(A) | **69,06 dB(A)** | 69,83 dB(A) | 69,33 dB(A) (-0,28 dB) |

## Como executar

```bash
source .venv/bin/activate
export SUMO_HOME="$(python -c 'import sumo; print(sumo.SUMO_HOME)')"
```

### 1. Gerar os cenários `As-Is` e `To-Be`
```bash
python src/scenario_builder.py
```

### 2. Executar qualquer cenário individual (headless ou `sumo-gui`)
```bash
python src/traci_controller.py --scenario as_is --steps 600
python src/traci_controller.py --scenario to_be_1 --steps 600
python src/traci_controller.py --scenario to_be_2 --steps 600
python src/traci_controller.py --scenario to_be_3 --gui --steps 600
```

### 3. Rodar os 4 cenários e gerar a tabela comparativa
```bash
python src/run_all_scenarios.py
```

### 4. Validar calibração GEH (Marco 2)
```bash
python src/geh_calibration.py
```

### 5. Abrir o painel comparativo interativo (Streamlit)
```bash
streamlit run src/dashboard.py
```
