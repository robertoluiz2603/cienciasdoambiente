# Plano Unificado e Enxuto (Artigos + Propostas do Grupo) — Entrega até 26/11

**Arquitetura:** **CWB-EcoSync-Lean** (*Controle Semafórico Multimodal Ponderado por Passageiros + Onda Verde Estrutural + Intervenções Urbanas To-Be*)  
**Escopo Geográfico (`simulation/network/curitiba.net.xml`):** Malha de $21.080$ arestas e $482$ semáforos (`(-49.3219, -25.4954)` a `(-49.2518, -25.4169)`), cobrindo o Quadrilátero Central e os eixos de ligação com os Terminais **Campina do Siqueira**, **Guadalupe**, **Portão** e **Capão Raso**, com **869 POIs reais da URBS** (49 hospitais, 123 escolas públicas/particulares e 128 creches).

---

## 1. O que Fica vs. O que Foi Cortado do `CWB-EcoSync-4L` (Foco em Simplicidade e Defesa na Banca)

| Componente | Status | Justificativa Prática (Prazo 26/11 e Defesa em Banca) |
| :--- | :---: | :--- |
| **1. OCC-MP + Filtro de Parada ($\beta_v$) + Anti-Spillback SOTL** (*Varaiya 2013; Ahmed et al. 2024; Tan et al. 2025; Gershenson 2005*) | **FICA (Núcleo TraCI)** | Apenas 1 equação de pressão por fase. Diferencia BRT ($100\text{ pax}$), Ligeirinho ($50\text{ pax}$), Ônibus Convencional ($35\text{ pax}$), Ônibus Escolar ($30\text{ pax}$), Carro Carona ($3{,}0\text{ pax}$), Carro Comum ($1{,}3\text{ pax}$), Ciclista/Autopropelido ($1{,}0$) e Pedestre ($1{,}0$). Ignora ônibus parado no tubo ($\beta_v=0$) e bloqueia envio para quadra $>85\%$ cheia. |
| **2. Onda Verde Arterial nos Eixos Principais** (*Joner & Volpi 2013 - Curitiba*) | **FICA (Base Cíclica)** | Calibrada diretamente com a velocidade real da telemetria URBS no pico ($\bar{v}_{\text{real}} \approx 20{,}4\text{ km/h} = 5{,}66\text{ m/s}$ em `data/urbs_telemetry_hourly.csv`) via *offset* simples $\theta_{j,j+1} = (d_{j,j+1} / \bar{v}_{\text{real}}) \pmod C$. |
| **3. Preempção de Veículos de Emergência (EVP)** (*Sun et al. 2024*) | **FICA (Alta Prioridade)** | Detecção direta via TraCI (`vClass == "emergency"`) nas rotas ligadas aos **49 hospitais dos POIs da URBS** (ex.: Hospital Pequeno Príncipe, HP Iguaçú, HP Muricy), abrindo/estendendo o verde com segurança após o tempo mínimo. |
| **4. Propostas Físicas e Demanda *To-Be* do Grupo** (Corredores exclusivos, ciclovias/autopropelidos, carona, Park & Ride nos 3 terminais e ônibus escolar nos POIs) | **FICA (Diferencial *To-Be*)** | Modela a transformação modal mantendo **constante o número total de passageiros transportados** entre *As-Is* e *To-Be*, garantindo comparação justa de atraso por passageiro, emissões HBEFA3 e ruído $L_{eq}$. |
| **5. Contrato JSON MQTT (`paho-mqtt`) + Validação GEH + Emissões HBEFA3 e Acústica $L_{eq}$** | **FICA (Obrigatório no Manual)** | Exigência explícita das rubricas de Computação (30%), Elétrica/Automação (30%) e Mecânica (20%) do `Manual_Projeto.pdf`. |
| *MILP de fechamento de loops ($2c_l$), AM-Band e geometria euclidiana* | **CORTADO** | Exige solver externo (CPLEX/Gurobi/PuLP) e trava em malhas reais com 482 semáforos. |
| *Acoplamento Grafo-Espacial CoLight/MA2C ($\alpha_{ij}$) e Q-Learning tabular* | **CORTADO** | Adiciona hiperparâmetros difíceis de calibrar e explicar na banca; o termo de fila a jusante do Max-Pressure já acopla os cruzamentos vizinhos naturalmente. |
| *GLOSA Multi-Segmento / Recomendação de velocidade em PMV* | **CORTADO** | Não atua sobre os veículos padrão do SUMO sem reprogramar o *car-following* individual; foco mantido no controle semafórico e na infraestrutura viária. |
| *Compensação algébrica de fases (Eq. 9 Li & Jin) + Índice $\rho_b$ de headway* | **CORTADO** | Substituído pelo peso de ocupação natural do OCC-MP + guarda de verde mínimo ($u_{\min}$) e contador anti-inanição ($\varepsilon_p$). |

---

## 2. As 5 Equações Essenciais para a Apresentação em Banca

Toda a equipe (Computação, Elétrica/Automação e Mecânica) só precisa dominar estas **5 equações**:

### Equação 1 — Calibração Estatística do Cenário *As-Is* (Índice GEH — Marco 2)
$$\text{GEH}_k = \sqrt{\frac{2 (M_k - C_k)^2}{M_k + C_k}} < 5{,}0 \quad \text{em } \ge 85\% \text{ das vias monitoradas}$$
* **Parâmetros:** $M_k$ = volume horário simulado no SUMO (veíc/h); $C_k$ = volume horário real observado (contagens IPPUC/URBS).
* **Onde está no código:** `src/geh_calibration.py`.

### Equação 2 — Conservação de Passageiros e Redução de Carros no Cenário *To-Be* (Propostas do Grupo)
$$N_{\text{pax, total}} = N_{\text{car}}^{\text{As-Is}} \cdot o_{\text{car}}^{\text{As-Is}} + N_{\text{bus, pax}}^{\text{As-Is}} = \text{constante}$$
$$N_{\text{car}}^{\text{To-Be}} = \frac{(1 - \alpha_{\text{P\&R}} - \alpha_{\text{escolar}} - \alpha_{\text{micro}}) \cdot N_{\text{car}}^{\text{As-Is}} \cdot o_{\text{car}}^{\text{As-Is}}}{o_{\text{car}}^{\text{To-Be}}}$$
* **Parâmetros defensáveis:**
  * $o_{\text{car}}^{\text{As-Is}} = 1{,}30\text{ pax/carro}$ (ocupação média basal) $\rightarrow$ $o_{\text{car}}^{\text{To-Be}} = 1{,}65\text{ pax/carro}$ (incentivo à **carona compartilhada**);
  * $\alpha_{\text{P\&R}} = 12\%$ das viagens periferia$\rightarrow$centro interceptadas nos **3 Terminais (Campina do Siqueira, Portão e Guadalupe)** via *Park & Ride* + último quilômetro em ônibus/autopropelidos;
  * $\alpha_{\text{escolar}} = 5\%$ das viagens no pico substituídas por **ônibus escolares** atendendo as escolas mapeadas em `data/urbs/2026_11_12_pois.json.xz` (eliminando filas de embarque em fila dupla `<stop>` na via);
  * $\alpha_{\text{micro}} = 3\%$ migradas para **ciclistas e autopropelidos** em faixas exclusivas.

### Equação 3 — Pressão Multimodal Ponderada por Passageiros com Anti-Spillback (OCC-MP + SOTL — Marco 3)
$$P_i(p, t) = \sum_{(l, m) \in p} \omega_{\text{spill}}(m, t) \cdot \left[ \sum_{v \in \mathcal{V}_l(t)} \beta_v(t) \cdot p_v - \sum_{v \in \mathcal{V}_m(t)} p_v \right]^+ + \eta_{\text{starv}} \, \varepsilon_{i,p}(t)$$
* **Parâmetros:**
  * $p_v$: ocupação por veículo (`urbs_brt` = $100$, `urbs_ligeirinho` = $50$, `urbs_convencional` = $35$, `bus_escolar` = $30$, `car_carpool` = $3{,}0$, `passenger` = $1{,}3$, `bicycle`/`pedestrian` = $1{,}0$);
  * $\beta_v(t) \in \{0, 1\}$: vale $0$ se o ônibus está parado embarcando em ponto/estação-tubo longe do semáforo, e $1$ quando está em aproximação ou na fila do semáforo (*Tan et al., 2025*);
  * $\omega_{\text{spill}}(m, t) \in \{0, 1\}$: vale $0$ se a quadra receptora a jusante $m$ estiver com ocupação $> 85\%$ (*Regra 6 de Gershenson, 2005*), evitando travar o cruzamento (*gridlock*);
  * $\varepsilon_{i,p}(t)$: tempo (em segundos) que a fase $p$ está no vermelho ($\eta_{\text{starv}} = 0{,}5$), garantindo que nenhuma rua secundária ou travessia de pedestres sofra inanição (*Sun et al., 2024*).
* **Regra de Preempção de Emergência (EVP):** Se houver qualquer veículo com `vClass == "emergency"` na faixa $l \in p$, $P_i(p, t) = +\infty$ (abre/mantém verde imediatamente respeitando apenas o tempo mínimo de segurança $u_{\min} = 8\text{ s}$).

### Equação 4 — Offset de Onda Verde Arterial Calibrado por Telemetria URBS (*Joner & Volpi, 2013*)
$$\theta_{j \to j+1} = \left( \frac{d_{j, j+1}}{\bar{v}_{\text{corredor}}} - \frac{L_{q, j+1}}{v_{\text{dissip}}} \right) \pmod{C}$$
* **Parâmetros:** $d_{j,j+1}$ = distância entre semáforos consecutivos no corredor; $\bar{v}_{\text{corredor}} = 20{,}4\text{ km/h}$ ($5{,}66\text{ m/s}$, extraído de `data/urbs_telemetry_hourly.csv`); $L_{q,j+1}$ = `queue_length_meters` do payload JSON MQTT; $v_{\text{dissip}} = 5{,}0\text{ m/s}$.

### Equação 5 — Emissões Cinemáticas (HBEFA3) e Nível de Pressão Sonora Equivalente ($L_{eq}$ — Mecânica, Marco 4)
$$E_{\text{pol}} = \sum_{t} \sum_{v} \dot{e}_{\text{HBEFA3}}\big(v_v(t), a_v(t), \text{vType}_v\big) \Delta t, \qquad L_{eq}(t) = L_0 + 10 \log_{10}\!\left( Q_{\text{leves}}(t) + 10 \, Q_{\text{pesados}}(t) + 4 \, N_{\text{halting}}(t) \right) + 20 \log_{10}\!\left(\frac{\max(\bar{v}(t), 10)}{v_{\text{ref}}}\right)$$
* **Parâmetros:** $\dot{e}_{\text{HBEFA3}}$ coletado nativamente pelo SUMO/TraCI ($\text{CO}_2$, $\text{NO}_x$, $\text{PM}_x$ em $\text{g/s}$); $E_{\text{bus}} = 10$ (1 ônibus pesado equivale acusticamente a 10 carros segundo FHWA/CoRTN); $N_{\text{halting}}$ penaliza o ruído de frenagem e arrancada nos semáforos, confrontado com a **ABNT NBR 10151** ($65\text{ dB(A)}$ diurno em áreas mistas/centrais).

---

## 3. Plano de Implementação Passo a Passo (`src/` e `simulation/`)

### Passo 1 — Extração de POIs Reais e Construção dos Cenários *As-Is* vs. *To-Be* (`src/scenario_builder.py` + `simulation/`)
1. **Ler `data/urbs/2026_11_12_pois.json.xz` e mapear na malha `curitiba.net.xml`:**
   * **Terminais (Park & Ride + Autopropelidos):** Terminal Campina do Siqueira, Terminal Portão e Terminal Guadalupe/Capão Raso;
   * **Escolas (Ônibus Escolar vs. Parada na Via):** Selecionar escolas reais no Quadrilátero/entorno (ex.: *Colégio Estadual do Paraná*, *Inst. Educação Erasmo Pilotto*, *EE Zacarias*, *EM Professor Brandão*);
   * **Hospitais (Rotas de Emergência EVP):** Mapear hospitais reais (ex.: *Hospital Pequeno Príncipe*, *HP Iguaçú*, *HP Muricy*) como origem/destino de ambulâncias (`vClass="emergency"`).
2. **Gerar `simulation/as_is/` (Cenário Atual de Referência):**
   * Carros com baixa ocupação ($1{,}3\text{ pax/carro}$), paradas rápidas de embarque escolar (`<stop>` obstruindo faixa em frente às escolas), ônibus reais da URBS (`urbs_buses.rou.xml`), ambulâncias presas no tráfego misto e semáforos em tempo fixo original (`--adaptive` desligado), gerando `data/kpi_as_is.csv`.
3. **Gerar `simulation/to_be/` (Cenário Proposto pelo Consórcio):**
   * **Conservação exata de passageiros:** Reduzir o número de carros circulando no centro pela migração para **carona compartilhada** (`car_carpool`), **Park & Ride nos 3 terminais** (viagens periferia$\rightarrow$terminal + reforço proporcional de frequência nas linhas da URBS terminal$\rightarrow$centro), **rotas de ônibus escolar** (`bus_escolar` com `<busStop>` dedicado sem bloquear a via) e fluxos de **ciclistas/autopropelidos** (`vClass="bicycle"`) e **pedestres no Calçadão da XV**.
   * **Prioridade viária física:** Configurar faixas exclusivas/prioritárias de ônibus/emergência e ciclovias nos corredores principais de 2+ faixas do cenário *To-Be*.

### Passo 2 — Refatoração Enxuta do Controlador + MQTT (`src/traci_controller.py`)
1. Implementar o controlador **`CWBEcoSyncLean`**:
   * **Preempção de Emergência (EVP):** Prioridade imediata para `vClass == "emergency"`;
   * **OCC-MP + Filtro de Tubo ($\beta_v$) + Anti-Spillback SOTL + Anti-Inanição ($\varepsilon_p$):** Seleção/extensão de fase limpa baseada na Equação 3, lendo `vType` e ocupação de passageiros;
   * **Onda Verde Arterial:** Ajuste dos *offsets* nos corredores principais conforme a Equação 4.
2. **Integração Ciberfísica MQTT (`paho-mqtt`):**
   * Publicar a cada ciclo o Contrato JSON exato do Manual (`timestamp`, `intersection_id`, `sensors`, `instantaneous_metrics`) no broker MQTT local (com *fallback* automático caso o broker `localhost:1883` não esteja aberto, para nunca travar a execução).
3. **Coleta Completa de KPIs (`data/kpi_as_is.csv` e `data/kpi_to_be.csv`):**
   * Gravar a cada passo: veículos ativos, **passageiros equivalentes ativos**, velocidade média geral, velocidade média dos ônibus URBS, **tempo de viagem das ambulâncias (EVP)**, veículos em fila (`halting_vehicles`), emissões ($\text{CO}_2$, $\text{NO}_x$, $\text{PM}_x$ em $\text{g/s}$) e **ruído estimado $L_{eq}$ em $\text{dB(A)}$**.

### Passo 3 — Validação GEH Real (`src/geh_calibration.py`)
* Conectar `src/geh_calibration.py` aos fluxos simulados no *As-Is* versus contagens de referência das principais vias do Quadrilátero Central (Av. Mal. Floriano Peixoto, Rua Mariano Torres, Al. Dr. Muricy, Av. Pres. Kennedy, Av. Mário Tourinho, etc.), comprovando $\text{GEH} < 5{,}0$ em $\ge 85\%$ das vias.

### Passo 4 — Dashboard Comparativo *As-Is* vs. *To-Be* (`src/dashboard.py`)
* Atualizar o painel **Streamlit** com 4 abas alinhadas às rubricas da banca:
  1. **Comparativo Geral *As-Is* vs. *To-Be* (Computação):** Velocidade média, redução de filas, atraso ponderado por passageiro e ganho de resposta de veículos de emergência (EVP);
  2. **Impacto Ambiental e Acústico (Mecânica):** Redução percentual acumulada de $\text{CO}_2$, $\text{NO}_x$ e $\text{PM}_x$ (HBEFA3) e curva de atenuação de ruído $L_{eq}$ $[\text{dB(A)}]$ vs. limite da ABNT NBR 10151;
  3. **Telemetria Ciberfísica MQTT & Calibração GEH (Elétrica/Automação):** Visualizador ao vivo do payload JSON do contrato de integração e tabela de aprovação $\text{GEH} < 5$;
  4. **Transporte Público URBS e Intervenções do Grupo:** Desempenho das linhas centrais, impacto do *Park & Ride* nos terminais, carona compartilhada, ônibus escolar e micromobilidade.
