# Relatório Técnico Comparativo Fatorial dos 4 Cenários (`As-Is`, `To-Be 1`, `To-Be 2`, `To-Be 3`)

**Projeto:** Mobilidade Urbana, Sustentabilidade e Sistemas Ciber-Físicos — Quadrilátero Central de Curitiba e Área de Intervenção (`Campina do Siqueira`, `Portão`, `Guadalupe` e Centro)  
**Simulador:** Eclipse SUMO v1.28.0 via API TraCI (Python) | **Janela simulada:** 600 s em horário de pico da tarde (17:00–19:00)

---

## 1. Desenho Experimental $2 \times 2$ (Os 4 Cenários)

Para isolar o impacto de cada frente de solução e avaliar a sinergia do conjunto:

| Cenário | Infraestrutura e Demanda (Propostas do Grupo) | Controle Semafórico (Artigos Científicos) | Arquivo de Configuração / Saída |
| :--- | :---: | :---: | :--- |
| **1. `As-Is`** (Atual) | Malha atual, 1.240 carros (incl. 40 paradas escolares) | Tempo fixo padrão | `simulation/as_is/curitiba.sumocfg` $\rightarrow$ `data/kpi_as_is.csv` |
| **2. `To-Be 1`** (Solução Grupo) | **Sim** (faixas 5 vias, carona, 3 terminais, ônibus escolar, bike) | Tempo fixo padrão | `simulation/to_be/curitiba_to_be.sumocfg` $\rightarrow$ `data/kpi_to_be_1.csv` |
| **3. `To-Be 2`** (Solução Algoritmos) | **Não** (malha e demanda atuais `As-Is`) | **Sim (`CWBEcoSyncLean`)** | `simulation/as_is/curitiba.sumocfg` (`--adaptive`) $\rightarrow$ `data/kpi_to_be_2.csv` |
| **4. `To-Be 3`** (Conjunto Integrado) | **Sim** (propostas do grupo) | **Sim (`CWBEcoSyncLean`)** | `simulation/to_be/curitiba_to_be.sumocfg` (`--scenario to_be_3`) $\rightarrow$ `data/kpi_to_be_3.csv` |

---

## 2. O que foi feito e Como foi implementado em cada cenário

### 2.1. Cenário 1 — `As-Is` (Linha de Base Calibrada)
- **Malha (`simulation/network/curitiba.net.xml`):** 21.080 arestas e 482 semáforos cobrindo de `(-49.32188, -25.49543)` a `(-49.25181, -25.41685)`.
- **Frota Real de Ônibus (`src/urbs_pipeline.py` -> `simulation/as_is/urbs_buses.rou.xml`):** 160 linhas centrais e 332 fluxos nas classes `urbs_brt`, `urbs_ligeirinho` e `urbs_convencional` (`HBEFA3/Bus`).
- **Demanda Privada e Gargalos (`src/scenario_builder.py` -> `simulation/as_is/special_as_is.rou.xml`):**
  - 1.200 carros base (`1,30 pax`), 40 carros de pais (`car_school_dropoff`, `2,00 pax`) com parada `<stop duration="35.0"/>` em frente a 6 escolas estaduais reais dos POIs da URBS, e 12 ambulâncias (`vClass="emergency"`) rumo a 4 hospitais reais.
- **Calibração GEH (`src/geh_calibration.py` -> `data/contagens_geh_as_is.csv`):** **10/10 vias aprovadas (100% com $\text{GEH} < 5,0$; máximo $1,195$)**, acima dos 85% exigidos no `Manual_Projeto.pdf`.

### 2.2. Cenário 2 — `To-Be 1` (Solução Urbana e Modal do Grupo — Isolada)
Gerado por `src/scenario_builder.py` conservando exatamente **1.640,0 passageiros de automóvel** (`data/conservacao_passageiros.csv`), mantendo os semáforos originais em tempo fixo:
- **Faixas Exclusivas / Prioritárias (`data/corredores_faixa_exclusiva.csv` e `simulation/to_be/priority_lanes.json`):** nas 5 avenidas escolhidas pelo grupo (`Rua Mariano Torres`, `Av. Pres. Getúlio Vargas`, `Av. Pres. Kennedy`, `Av. Pres. Arthur da Silva Bernardes` e `Av. Manoel Ribas`), foram ativadas **97 faixas físicas exclusivas** (`allow="bus emergency bicycle"` em vias de `>= 3` faixas sem bloqueio de conversão à direita) e **229 faixas prioritárias compartilhadas** em vias de 2 faixas/conversões.
- **Carona Compartilhada:** eleva a ocupação dos carros remanescentes de $1,30$ para $1,65\text{ pax/carro}$ (480 carros solo + 215 `car_carpool` de $3,0\text{ pax}$).
- **Park & Ride nos 3 Terminais:** 144 viagens (`187,2 pax`) encerram nos acessos de `Campina do Siqueira`, `Portão` e `Guadalupe`, absorvidas pela frota URBS (~650 ônibus/h).
- **Ônibus Escolar e Micromobilidade:** 8 rotas de `bus_escolar` eliminam os 40 bloqueios na porta das escolas; 60 viagens migram para `micro_bike` (`vClass="bicycle"`, emissão zero) nas 2.555 faixas cicloviárias existentes.
- **Redução de automóveis:** de **1.240** (`As-Is`) para **839** no total (**-32,3%**) e **695** no centro (**-44,0%**).

### 2.3. Cenário 3 — `To-Be 2` (Algoritmos de Sincronização Semafórica — Isolado)
Executa o controlador `CWBEcoSyncLeanController` (`src/traci_controller.py`) sobre a **mesma malha e demanda atual do `As-Is`**, sem faixas exclusivas nem redução de carros:
- **OCC-MP (*Occupancy-Weighted Max-Pressure*) + Filtro $\beta_v$:** pondera filas pela ocupação modal (`urbs_brt=100`, `urbs_ligeirinho=50`, `urbs_convencional=35`, `car=1,3`, `emergency=150`) e aplica $\beta_v = 0{,}2$ quando um ônibus está parado longe da linha de retenção (embarque em estação-tubo).
- **Regras de Guarda SOTL:** verde mínimo ($u_{\min}=14\text{ s}$), proteção anti-inanição e bloqueio **anti-spillback** (zera movimento quando a quadra a jusante está $>85\%$ ocupada).
- **Onda Verde Arterial:** offsets nas 5 avenidas calibrados pela velocidade real de pico da URBS ($5,66\text{ m/s} = 20,37\text{ km/h}$ às 18h).
- **Preempção de Emergência (EVP):** prioriza imediatamente ambulâncias nas aproximações respeitando o amarelo de transição.

### 2.4. Cenário 4 — `To-Be 3` (Conjunto Integrado: `To-Be 1` + `To-Be 2`)
Combina todas as intervenções viárias e modais do grupo (`To-Be 1`) com o controlador inteligente `CWBEcoSyncLean` e telemetria IoT/MQTT (`paho-mqtt` gerando o Contrato JSON em `data/mqtt_sample_payloads.json`).

---

## 3. De onde vieram os dados e referências

- **URBS (`data/urbs/2026_11_12_*.json.xz`):** 160 linhas centrais, horários programados, trajetos geográficos, telemetria GPS real (`data/urbs_telemetry_hourly.csv`: queda de $31,01\text{ km/h}$ às 04h para $20,37\text{ km/h}$ às 18h) e POIs reais (`data/pois_mapped_sumo.csv`: 3 terminais, 6 escolas e 4 hospitais).
- **IPPUC + OpenStreetMap:** shapefile `SIST_VIARIO_CLASSIFICADO.shp` + rede viária convertida no SUMO + seleção das 5 avenidas pelo grupo.
- **GEH (`data/contagens_geh_as_is.csv`):** fluxos horários de ônibus das tabelas reais da URBS + fluxos simulados de carros confrontados com contagens de referência por corredor (FHWA *Traffic Monitoring Guide*).
- **Emissões e Acústica:** modelo cinemático **HBEFA3** do SUMO ($\text{CO}_2$, $\text{NO}_x$, $\text{PM}_x$) e modelo logarítmico **FHWA/CoRTN** para $L_{eq}$ vs. limite diurno de **65 dB(A) da ABNT NBR 10151**.
- **Artigos científicos (`docs/artigos/`):** **Varaiya (2013)** (*Max-Pressure*), **Ahmed et al. (2024)** (*OCC-MP*), **Tan et al. (2025)** (*Transit-MP* / filtro $\beta_v$), **Gershenson (2005)** (*SOTL*), **Joner & Volpi (2013)** (Onda Verde em Curitiba) e **Sun et al. (2024)** (SUMO/TraCI).

---

## 4. Comparativo Real dos 4 Cenários (`data/comparativo_4_cenarios.csv`)

| Indicador | Unid. | 1. `As-Is` | 2. `To-Be 1` (Grupo) | 3. `To-Be 2` (Algoritmos) | 4. `To-Be 3` (Conjunto) | $\Delta$ `To-Be 1` | $\Delta$ `To-Be 2` | $\Delta$ `To-Be 3` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Veículos Ativos (média)** | veíc | 885,7 | 740,0 | 862,5 | **718,7** | -16,45% | -2,62% | **-18,86%** |
| **Passageiros Equiv. Ativos** | pax | 18.444,0 | 18.507,3 | 17.864,8 | 17.962,3 | +0,34% | -3,14% | -2,61% |
| **Velocidade Média Geral** | km/h | 24,53 | 23,06 | **28,07** | 26,38 | -5,99% | +14,43% | **+7,54%** |
| **Vel. Ponderada p/ Passageiro** | km/h | 18,34 | 18,51 | **22,62** | 22,43 | +0,93% | +23,34% | **+22,30%** |
| **Vel. Média Ônibus URBS** | km/h | 17,78 | 18,19 | **22,53** | **22,53** | +2,31% | +26,72% | **+26,72%** |
| **Vel. Média Ambulâncias** | km/h | 26,63 | 26,23 | 30,62 | **30,98** | -1,50% | +14,98% | **+16,33%** |
| **Tempo Médio Ambulância** | s | 375,0 | 304,5 | 298,2 | **259,0** | -18,80% | -20,48% | **-30,93%** |
| **Veículos em Fila (média)** | veíc | 314,2 | 269,1 | 222,7 | **197,8** | -14,35% | -29,12% | **-37,05%** |
| **Comprimento Filas (média)** | m | 2.042,1 | 1.749,0 | 1.447,4 | **1.285,9** | -14,35% | -29,12% | **-37,03%** |
| **$\text{CO}_2$ Acumulado (600 s)** | kg | 2.962,05 | **2.872,34** | 3.155,11 | 3.013,06 | **-3,03%** | +6,52% | +1,72% |
| **$\text{NO}_x$ Acumulado (600 s)** | g | 18.992,1 | 19.313,3 | 19.743,2 | 19.897,0 | +1,69% | +3,95% | +4,76% |
| **$\text{PM}_x$ Acumulado (600 s)** | g | 535,57 | 497,82 | 537,82 | **492,79** | -7,05% | +0,42% | **-7,99%** |
| **$\text{CO}_2$ por Passageiro** | g/pax | 160,60 | **155,20** | 176,61 | 167,74 | **-3,36%** | +9,97% | +4,45% |
| **$\text{CO}_2$ por $\text{pax}\cdot\text{km}$** | g/$\text{pax}\cdot\text{km}$ | 53,16 | 50,82 | 47,22 | **45,26** | -4,40% | -11,17% | **-14,86%** |
| **Ruído Médio ($L_{eq}$)** | dB(A) | 69,61 | **69,06** | 69,83 | 69,33 | **-0,55** | +0,22 | **-0,28** |

---

## 5. Como o Conjunto (`To-Be 3`) se Comporta Frente às Soluções Isoladas

1. **`To-Be 1` isolado (só medidas urbanas) reduz emissões, mas trava a fluidez:** tira 16,45% dos veículos ativos, corta $\text{CO}_2$ (-3,03%), $\text{PM}_x$ (-7,05%) e ruído (-0,55 dB(A)), porém com semáforos ainda fixos os ônibus ganham apenas +2,31% e os carros perdem -5,99% de velocidade.
2. **`To-Be 2` isolado (só algoritmos semafóricos) dá fluidez, mas gera efeito rebote ambiental:** destrava o tráfego (+26,72% na velocidade dos ônibus, -29,12% nas filas), mas como todos os carros continuam na rua rodando mais rápido na mesma janela de 600 s, o $\text{CO}_2$ total sobe +6,52% e o ruído sobe +0,22 dB(A).
3. **`To-Be 3` (Conjunto Integrado) entrega o melhor equilíbrio técnico e ambiental:**
   - **Menor congestionamento:** reduz filas em **-37,05%** (197,8 veíc vs. 269,1 e 222,7 isolados) e veículos ativos em **-18,86%**.
   - **Melhor atendimento de emergência:** reduz o tempo de ambulância em **-30,93%** ($375,0\text{ s} \to 259,0\text{ s}$, quase 2 minutos mais rápido).
   - **Menor poluição por deslocamento e particulados:** atinge o menor $\text{PM}_x$ (**-7,99%**) e a menor intensidade de carbono por $\text{pax}\cdot\text{km}$ (**-14,86%**, de $53,16$ para $45,26\text{ g/pax}\cdot\text{km}$), mantendo redução de ruído (**-0,28 dB(A)**) e neutralizando a maior parte do rebote de $\text{CO}_2$ do algoritmo isolado.
