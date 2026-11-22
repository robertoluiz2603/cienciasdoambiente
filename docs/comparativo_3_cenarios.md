# Relatório Técnico Comparativo dos 3 Cenários (`As-Is`, `To-Be 1`, `To-Be 2`)

> **Atualização (Experimento Fatorial com 4 Cenários):** Foi adicionado o cenário isolado de algoritmo (`To-Be 2`) e o cenário conjunto (`To-Be 3 = To-Be 1 + To-Be 2`). Consulte a matriz completa dos 4 cenários em [comparativo_4_cenarios.md](docs/comparativo_4_cenarios.md) e `data/comparativo_4_cenarios.csv`.

**Projeto:** Mobilidade Urbana, Sustentabilidade e Sistemas Ciber-Físicos — Quadrilátero Central de Curitiba e Área de Intervenção (`Campina do Siqueira`, `Portão`, `Guadalupe` e Centro)  
**Simulador:** Eclipse SUMO v1.28.0 via API TraCI (Python) | **Janela simulada:** 600 s em horário de pico da tarde (17:00–19:00)

---

## 1. Visão Geral dos 3 Cenários Implementados

| Cenário | O que representa | Controle Semafórico | Infraestrutura e Demanda | Arquivo de Saída |
| :--- | :--- | :--- | :--- | :--- |
| **1. `As-Is`** | Situação atual de referência | Tempo fixo padrão (`--adaptive` desligado) | 1.200 carros base (`1,30 pax`), 40 carros escolares bloqueando faixa em frente às escolas (`<stop duration="35.0"/>`), 12 ambulâncias no tráfego misto e 332 fluxos reais da URBS (`160` linhas centrais). | `data/kpi_as_is.csv` |
| **2. `To-Be 1`** | Intervenções urbanas e modais propostas pelo grupo | Tempo fixo padrão (`--adaptive` desligado) | **Conservação exata de 1.640,0 passageiros** de automóvel: faixas exclusivas/prioritárias nas 5 avenidas (`97` faixas exclusivas puras + `229` compartilhadas em conversões), carona compartilhada (`1,30 -> 1,65 pax/carro`), Park & Ride nos 3 terminais (`144` viagens), `8` ônibus escolares e `60` bicicletas/autopropelidos. | `data/kpi_to_be_1.csv` |
| **3. `To-Be 2`** | Intervenções do grupo + Algoritmos dos artigos (`CWB-EcoSync-Lean`) | **`CWBEcoSyncLean`** (`OCC-MP` + `SOTL` + `Onda Verde` + `EVP` + `MQTT`) | Mesma malha, faixas prioritárias e demanda conservada do `To-Be 1`, acrescida de controle semafórico dinâmico ponderado por passageiros, anti-spillback, onda verde arterial (`20,4 km/h`), preempção para ambulâncias e telemetria MQTT JSON. | `data/kpi_to_be_2.csv` |

---

## 2. O que foi feito e Como foi implementado em cada cenário

### 2.1. Cenário 1 — `As-Is` (Cenário Atual Calibrado)
- **Malha Viária (`simulation/network/curitiba.net.xml`):** 21.080 arestas e 482 semáforos cobrindo de `(-49.32188, -25.49543)` a `(-49.25181, -25.41685)` (Quadrilátero Central, Setor Especial Estrutural, Campina do Siqueira, Portão e Guadalupe).
- **Transporte Público Real (`src/urbs_pipeline.py` -> `simulation/as_is/urbs_buses.rou.xml`):**
  - 160 linhas centrais e 332 fluxos direcionais nas classes `urbs_brt` (24 m), `urbs_ligeirinho` (13 m) e `urbs_convencional` (12 m), todas com curva de emissão `HBEFA3/Bus`.
- **Demanda Privada e Gargalos Reais (`src/scenario_builder.py` -> `simulation/as_is/special_as_is.rou.xml`):**
  - 1.200 viagens base (`trips_cars.rou.xml`, `car__passenger`, ocupação $1,30\text{ pax/carro}$ = $1.560,0\text{ pax}$).
  - 40 veículos escolares (`car_school_dropoff`, $2,00\text{ pax/carro}$ = $80,0\text{ pax}$) roteados para passar em frente a **6 escolas estaduais reais** dos POIs da URBS (`EE Dom Pedro II`, `EE Inst. Educação Prof. Erasmo Pilotto`, `EE Zacarias`, `EE Gabriela Mistral`, `EE Arthur de Macedo` e `EE Dom Áttico Eusébio da Rocha`), realizando parada `<stop duration="35.0"/>` na faixa da direita para simular embarque/desembarque.
  - 12 ambulâncias (`emergency_ambulance`, `vClass="emergency"`) partindo a cada $45\text{ s}$ entre $t=10\text{ s}$ e $t=505\text{ s}$ em rotas arteriais rumo a **4 hospitais reais** (`HP Iguaçú`, `HP Muricy Ltda`, `HP Criança`, `HP Instituto de Medicina`).
- **Validação GEH (`src/geh_calibration.py`):** Mede os fluxos horários simulados nas 10 principais vias do recorte (`data/contagens_geh_as_is.csv`) contra valores de referência de calibração, atingindo **10/10 vias aprovadas (100,0% com $\text{GEH} < 5,0$; máximo $\text{GEH} = 1,195$)** — acima do critério de 85% do `Manual_Projeto.pdf`.

### 2.2. Cenário 2 — `To-Be 1` (Soluções Urbanas e Modais do Grupo)
Gerado por `src/scenario_builder.py` em `simulation/to_be/` mantendo **1.640,0 passageiros de automóvel** idênticos ao `As-Is` (`data/conservacao_passageiros.csv`):
1. **Faixas Exclusivas / Prioritárias (`data/corredores_faixa_exclusiva.csv` e `simulation/to_be/priority_lanes.json`):**
   - Aplicadas nas 5 avenidas definidas pelo grupo: **Rua Mariano Torres**, **Av. Pres. Getúlio Vargas**, **Av. Pres. Kennedy**, **Av. Pres. Arthur da Silva Bernardes** e trecho da **Av. Manoel Ribas**.
   - **Regra de engenharia segura:** Em trechos com `>= 3` faixas e sem conversão exclusiva de carros pela faixa 0 (`97` faixas ao todo), `traci.lane.setAllowed(lane_id, ["bus", "emergency", "bicycle"])` restringe fisicamente a faixa da direita a ônibus, emergência e bicicletas; em trechos de `2` faixas ou conversões obrigatórias (`229` trechos), mantém-se o compartilhamento cooperativo para não gerar bloqueio de conversões à direita.
2. **Park & Ride nos 3 Terminais (`144` viagens = `187,2 pax`):**
   - Viagens de carro com origem periférica são redirecionadas para encerrar no acesso do terminal real mais próximo (**Terminal Campina do Siqueira**, **Terminal Portão** ou **Terminal Guadalupe / Praça Guadalupe**), onde a demanda é absorvida na capacidade da frota programada da URBS (~650 ônibus/h no pico).
3. **Carona Compartilhada (`480` carros solo × `1,3` + `215` carros `car_carpool` × `3,0`):**
   - Eleva a ocupação média dos carros remanescentes de $1,30$ para $1,65\text{ pax/carro}$, reduzindo o total de automóveis em circulação de **1.240** (`As-Is`) para **839** no total (**-32,3%**) e **695** entrando na área central (**-44,0%**).
4. **Ônibus Escolar em Pontos Dedicados (`8` veículos `bus_escolar` = `123,8 pax`):**
   - Elimina as 40 paradas `<stop>` de pais na via em frente às 6 escolas e consolida as viagens em 8 rotas interligadas de ônibus escolares (`vClass="bus"`, `HBEFA3/Bus`).
5. **Micromobilidade — Ciclistas e Autopropelidos (`60` viagens `micro_bike` = `60,0 pax`):**
   - Utiliza as **2.555 faixas cicloviárias** já presentes em `curitiba.net.xml` (`vClass="bicycle"`, `emissionClass="Zero/default"`).
6. **Ambulâncias idênticas (`amb_0`..`amb_11`):** Mesmas 12 rotas e horários de partida do `As-Is`.

### 2.3. Cenário 3 — `To-Be 2` (Intervenções do Grupo + Algoritmos `CWB-EcoSync-Lean` e IoT/MQTT)
Implementado na classe `CWBEcoSyncLeanController` de `src/traci_controller.py` sobre o cenário `To-Be 1`:
1. **OCC-MP (*Occupancy-Weighted Max-Pressure*) + Filtro de Parada ($\beta_v$):**
   - Pondera a fila de entrada de cada fase pelo número estimado de passageiros (`urbs_brt=100`, `urbs_ligeirinho=50`, `urbs_convencional=35`, `bus_escolar=30`, `car_carpool=3.0`, `car__passenger=1.3`, `micro_bike=1.0`, `emergency_ambulance=150`).
   - Aplica $\beta_v = 0{,}2$ quando um ônibus está parado na primeira metade da faixa (`lane_pos < 0,5 * L`), evitando desperdício de tempo verde durante embarque em estação-tubo ou ponto.
2. **Regras de Guarda SOTL:**
   - **Anti-Spillback ($\omega_{\text{spill}}$):** Zera o peso de movimentos cuja via receptora a jusante esteja com ocupação $> 85\%$, evitando travar cruzamentos (*gridlock*).
   - **Verde Mínimo ($u_{\min} = 14\text{ s}$) e Anti-Inanição ($\varepsilon_{i,p}$):** Impede oscilações bruscas que aumentam o "para-e-anda" e garante atendimento periódico às transversais.
3. **Onda Verde Arterial:**
   - Inicializa os *offsets* dos semáforos nos 5 corredores pela velocidade real medida na telemetria URBS ($\bar{v}_{\text{real}} = 5{,}66\text{ m/s} = 20{,}37\text{ km/h}$ às 18h) e concede bônus de pressão dentro da janela da onda verde.
4. **Preempção de Veículos de Emergência (EVP):**
   - Detecta `emergency_ambulance` nas aproximações: estende o verde se a via já estiver aberta ou encurta a fase conflitante (respeitando $u_{\min} = 5\text{ s}$ e passando pelo amarelo de segurança) para liberar o cruzamento.
5. **Telemetria IoT/MQTT (`paho-mqtt`):**
   - Publica a cada 60 passos o payload no Contrato JSON do `Manual_Projeto.pdf` (`timestamp`, `intersection_id`, `sensors`, `instantaneous_metrics`) no tópico `curitiba/smartmobility/<tl_id>/telemetry` e grava as amostras em `data/mqtt_sample_payloads.json`.

---

## 3. De onde vieram os dados, parâmetros e equações (Rastreabilidade)

| Elemento | Origem / Fonte Real no Projeto |
| :--- | :--- |
| **Geometria viária e 482 semáforos** | OpenStreetMap convertido via `netconvert` (`simulation/network/curitiba.net.xml`) + classificação viária do **IPPUC** (`data/ippuc/sirgas/SIST_VIARIO_CLASSIFICADO.shp`). |
| **160 linhas, itinerários, horários e velocidade real dos ônibus** | **Dados Abertos da URBS** (`data/urbs/2026_11_12_linhas.json.xz`, `shapeLinha.json.xz`, `tabelaLinha.json.xz`, `veiculos.json.xz`), processados em `data/urbs_telemetry_hourly.csv` e `data/urbs_central_lines.csv` (comprovando queda de $31,01\text{ km/h}$ às 04h para $20,37\text{ km/h}$ às 18h). |
| **Terminais, escolas e hospitais reais** | **URBS POIs** (`data/urbs/2026_11_12_pois.json.xz`), mapeados para arestas conectadas em `data/pois_mapped_sumo.csv`. |
| **As 5 avenidas de faixas prioritárias** | Levantamento urbano do integrante de Arquitetura do grupo (`Mariano Torres`, `Getúlio Vargas`, `Kennedy`, `Arthur Bernardes`, `Manoel Ribas`), auditado por faixa em `data/corredores_faixa_exclusiva.csv`. |
| **Contagens de validação GEH** | Fluxos de ônibus direto das tabelas reais da URBS + fluxos horários simulados do `As-Is` confrontados com referências de calibração por corredor em `data/contagens_geh_as_is.csv` (FHWA *Traffic Monitoring Guide*, critério $\text{GEH} < 5{,}0$ em $\ge 85\%$ das vias). |
| **Algoritmo semafórico (`CWB-EcoSync-Lean`)** | Artigos em `docs/artigos/`: **Varaiya (2013)** (*Max-Pressure*), **Ahmed, Liu & Gayah (2024)** (*OCC-MP*), **Tan et al. (2025)** (*Transit-MP* / filtro $\beta_v$), **Gershenson (2005)** (*SOTL* / anti-spillback), **Joner & Volpi (2013)** (Onda Verde em Curitiba) e **Sun et al. (2024)** (escalonamento e preempção no SUMO/TraCI). |
| **Emissões atmosféricas** | Modelo cinemático nativo do SUMO **HBEFA3** (`HBEFA3/PC_G_EU4` para carros, `HBEFA3/LDV_D_EU4` para ambulâncias e `HBEFA3/Bus` para ônibus). |
| **Ruído urbano ($L_{eq}$)** | Modelo logarítmico baseado em **FHWA / CoRTN** ponderando fluxo de leves, pesados ($E_{\text{bus}} = 8$) e veículos em parada/arrancada (`halting_vehicles`) por corredor monitorado, comparado ao limite diurno de **$65\text{ dB(A)}$ da ABNT NBR 10151** (áreas mistas/centrais). |

---

## 4. Resultados Reais Obtidos (`data/comparativo_3_cenarios.csv`)

Resultados medidos nas execuções completas de 600 passos via `python src/run_all_scenarios.py`:

| Indicador | Unidade | 1. `As-Is` | 2. `To-Be 1` (Grupo) | 3. `To-Be 2` (Grupo + Algoritmos) | $\Delta$ `To-Be 1` vs `As-Is` | $\Delta$ `To-Be 2` vs `As-Is` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Veículos Ativos (média)** | veíc | 885,70 | 740,00 | 718,70 | **-16,45%** | **-18,86%** |
| **Passageiros Equivalentes Ativos (média)** | pax | 18.444,00 | 18.507,30 | 17.962,30 | +0,34% | -2,61% |
| **Velocidade Média Geral** | km/h | 24,53 | 23,06 | **26,38** | -5,99% | **+7,54%** |
| **Velocidade Média Ponderada por Passageiro** | km/h | 18,34 | 18,51 | **22,43** | +0,93% | **+22,30%** |
| **Velocidade Média dos Ônibus URBS** | km/h | 17,78 | 18,19 | **22,53** | +2,31% | **+26,72%** |
| **Velocidade Média das Ambulâncias (EVP)** | km/h | 26,63 | 26,23 | **30,98** | -1,50% | **+16,33%** |
| **Tempo Médio de Viagem Ambulância** | s | 375,00 | 304,50 | **259,00** | -18,80% | **-30,93%** |
| **Veículos Parados em Fila (média)** | veíc | 314,20 | 269,10 | **197,80** | -14,35% | **-37,05%** |
| **Comprimento Total de Filas (média)** | m | 2.042,10 | 1.749,00 | **1.285,90** | -14,35% | **-37,03%** |
| **Emissão Acumulada de $\text{CO}_2$ (600 s)** | kg | 2.962,05 | **2.872,34** | 3.013,06 | **-3,03%** | +1,72% |
| **Emissão Acumulada de $\text{NO}_x$ (600 s)** | g | 18.992,10 | 19.313,30 | 19.897,00 | +1,69% | +4,76% |
| **Emissão Acumulada de $\text{PM}_x$ (600 s)** | g | 535,57 | 497,82 | **492,79** | -7,05% | **-7,99%** |
| **Emissão de $\text{CO}_2$ por Passageiro** | g/pax | 160,60 | **155,20** | 167,74 | **-3,36%** | +4,45% |
| **Intensidade de Carbono ($\text{CO}_2$ por $\text{pax}\cdot\text{km}$)** | g/$\text{pax}\cdot\text{km}$ | 53,16 | 50,82 | **45,26** | -4,40% | **-14,86%** |
| **Ruído Urbano Médio ($L_{eq}$ FHWA/CoRTN)** | dB(A) | 69,61 | **69,06** | 69,33 | **-0,55 dB(A)** | **-0,28 dB(A)** |

---

## 5. Interpretação Técnica dos Resultados (para Defesa na Banca)

1. **Por que o `To-Be 1` sozinho já ajuda, mas não basta para destravar o transporte coletivo?**
   - As faixas exclusivas, caronas, terminais e pontos escolares reduzem as filas em **-14,35%**, cortam os veículos ativos em **-16,45%** e reduzem o $\text{CO}_2$ total em **-3,03%** e o $\text{PM}_x$ em **-7,05%**. Contudo, com os semáforos ainda em **tempo fixo**, os ônibus continuam presos nos cruzamentos transversais (velocidade sobe apenas de $17,78$ para $18,19\text{ km/h}$, $+2,31\%$), e o estreitamento da faixa de carros em corredores de 3 faixas reduz levemente a velocidade média dos automóveis ($-5,99\%$).
2. **Qual é o salto do `To-Be 2` (algoritmos de sincronização semafórica sobre o `To-Be 1`)?**
   - Quando o `CWBEcoSyncLean` atua ponderando os semáforos pelo número de passageiros e aplicando onda verde + anti-spillback + EVP:
     - As **filas caem $-37,05\%$** (de $2.042,1\text{ m}$ para $1.285,9\text{ m}$);
     - A **velocidade dos ônibus URBS salta $+26,72\%$** ($17,78 \to 22,53\text{ km/h}$, superando o patamar real medido no pico das 17h–18h);
     - A **velocidade ponderada por passageiro sobe $+22,30\%$** ($18,34 \to 22,43\text{ km/h}$);
     - O **tempo médio de viagem das ambulâncias cai $-30,93\%$** ($375,0\text{ s} \to 259,0\text{ s}$, ganho de quase 2 minutos);
     - As **emissões de material particulado ($\text{PM}_x$) caem $-7,99\%$** e a **intensidade de carbono por passageiro-quilômetro ($\text{g CO}_2/\text{pax}\cdot\text{km}$) cai $-14,86\%$** ($53,16 \to 45,26\text{ g/pax}\cdot\text{km}$).
3. **Por que o $\text{CO}_2$ acumulado na janela fixa de 600 s sobe $+1,72\%$ no `To-Be 2` enquanto o $\text{CO}_2/\text{pax}\cdot\text{km}$ cai $-14,86\%$?**
   - Trata-se de um efeito físico clássico do modelo cinemático **HBEFA3**: em janela de tempo fixa ($600\text{ s}$), ao eliminar $-37\%$ das filas, os veículos (especialmente ônibus pesados a diesel `HBEFA3/Bus`) passam muito mais tempo **rodando e acelerando** ($+26,7\%$ mais rápido) em vez de parados em marcha lenta, percorrendo uma distância total muito maior dentro dos mesmos 10 minutos. Quando normalizado pelo serviço prestado (**$\text{pax}\cdot\text{km}$ transportados**), cada deslocamento real emite **$-14,86\%$ menos $\text{CO}_2$**.
4. **Ruído Urbano vs. ABNT NBR 10151:**
   - Todos os cenários ficam acima do limite diurno de $65\text{ dB(A)}$ em áreas mistas/centrais devido à alta carga de ônibus pesados na malha central, mas as intervenções reduzem a pressão sonora equivalente em **$-0,55\text{ dB(A)}$ (`To-Be 1`)** e **$-0,28\text{ dB(A)}$ (`To-Be 2`)**, o que equivale a ~6% a 12% de redução na energia acústica irradiada pelos ciclos de parada e arrancada.
