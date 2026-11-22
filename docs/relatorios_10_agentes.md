# Relatórios Técnicos dos 10 Agentes Leitores (40 Artigos Analisados)

---

## Agente 1 — Lote 1: Onda Verde Clássica e Modelagem Matemática Aplicada a Curitiba

### 1. Síntese Técnica dos 4 Artigos
* **Little (1966):** Introduziu a formulação seminal em Programação Linear Inteira Mista (MILP) para maximizar a soma das larguras de banda bidirecionais ($b, \bar{b}$) em artérias. Define como variáveis de decisão as larguras de banda, os tempos de folga após o início do verde ($w_i, \bar{w}_i$), as fases relativas/offsets entre centros de vermelho ($\phi_i, \bar{\phi}_i$) e as variáveis inteiras de restrição de ciclo ($m_i = \phi_i + \bar{\phi}_i \in \mathbb{Z}$), todas expressas como frações do ciclo $C$.
* **Little, Kelson & Gartner (1981 — MAXBAND):** Expandiu o MILP (resolvido via *Branch-and-Bound*) para artérias e redes triangulares, transformando a frequência semafórica $z = 1/C$ (com $T_1 \le C \le T_2$) e as velocidades de progressão ($v_i, \bar{v}_i$) em variáveis de decisão linearizadas pela velocidade recíproca $u_i = (1/v_i)z$. Incluiu ainda o tempo de limpeza de fila ($\tau_i, \bar{\tau}_i$) e a escolha ótima da sequência de fases de conversão à esquerda.
* **Joner & Volpi (2013):** Adaptou as formulações de Little (1966) e Gartner/MAXBAND (1981) para a malha viária de Curitiba (em interlocução com a DIRETRAN). O modelo maximiza a soma ponderada das bandas $\max b_0 + \sum_{i=1}^q a_i b_i$ sujeita a 7 blocos de restrições: **(R1)** proporcionalidade em relação à artéria principal ($b_i \ge a_i b_0$); **(R2)** limites de frequência comum ($1/T_2 \le z \le 1/T_1$); **(R3)** limites de velocidade do CNT em ambos os sentidos ($z/v_{\max}^i \le u_i \le z/v_{\min}^i$); **(R4)** cabimento no ciclo ($w_{ij} + b_i + r_{ij} \le 1$ e $\bar{w}_{ij} + \bar{b}_i + \bar{r}_{ij} \le 1$); **(R5)** integridade entre semáforos adjacentes $(w_{ij_1}+\bar{w}_{ij_1}) - (w_{ij_2}+\bar{w}_{ij_2}) + d(j_1,j_2)(u_i+\bar{u}_i) + r_{ij_1} - r_{ij_2} = m(j_1,j_2) \in \mathbb{Z}$; **(R6)** fechamento geométrico de $L$ *loops* na malha fechada ($2c_l = \sum m(j_k, j_m)$, com $c_l \in \mathbb{Z}$); e **(R7)** limites de tempo de vermelho ($RMIN_{ij} \le r_{ij} \le RMAX_{ij}$) para garantir travessia segura de pedestres, idosos e deficientes. No dimensionamento para Curitiba, os autores modelaram uma rede com $q=50$ artérias, 10 semáforos por artéria ($J=500$), $L=20$ *loops* e $JJ=20$ cruzamentos com controle de vermelho, totalizando $2q + 4 + L + 3J + JJ = 1.644$ variáveis (470 inteiras) e $4q + 6 + 3J + L + JJ = 1.746$ restrições. O *offset* operacional é extraído pela mantissa: $\theta_i(1,j) = \text{mantissa}[w_{i1} - w_{ij} + \sum_{k=1}^{j-1} t(j_k, j_{k+1}) + \frac{1}{2}(r_{i1} - r_{ij})]$.
* **Gartner et al. (1991 — MULTIBAND):** Substituiu a banda uniforme ($b_i$ constante em toda a artéria) por bandas variáveis por segmento ($b_{ij}, \bar{b}_{ij}$), ponderadas na função objetivo pelo volume direcional ou pela razão volume/capacidade ($v_{ij}/c_{ij}$) de cada trecho.

### 2. Pontos Fortes e Limitações
* **Pontos Fortes:** Garantia matemática global de progressão arterial; formulação linear exata via frequência $z$ e recíproca de velocidade $u_i$; geração direta de *offsets* ($\theta_i$) de fácil programação; e proteção explícita à travessia de pedestres via limites de vermelho ($r_{ij}$).
* **Limitações em Malha Fechada (Centro de Curitiba):** Planos calculados *offline* assumem fluxo determinístico e pelotões sem dispersão. Em malhas ortogonais densas, as restrições de fechamento de ciclo ($2c_l$) engessam severamente a solução quando há múltiplos *loops*. Além disso, a banda uniforme de Joner & Volpi (2013) perde eficácia diante de variações bruscas de volume entre quadras (decorrentes de conversões), filas residuais variáveis que obstruem a cabeça do pelotão e perturbações causadas pelo embarque/desembarque ou prioridade de ônibus/BRT.

### 3. Proposta de Aproveitamento no Projeto UTFPR (Cenário *To-Be*)
Para o cenário *To-Be* do Quadrilátero Central, propõe-se acoplar **Joner & Volpi (2013) + MULTIBAND** ao `traci_controller.py`:
1. **Coordenação de Fundo (MILP + MULTIBAND via MQTT):** Definir o ciclo comum $C = 1/z$, as frações de vermelho $r_{ij} \in [RMIN_{ij}, RMAX_{ij}]$ (protegendo pedestres no centro) e os *offsets* base $\theta_i(1,j)$ usando a formulação de malha fechada ($2c_l$) de Joner & Volpi, porém ponderando cada arco $(j, j+1)$ pela razão ocupação/capacidade enviada em tempo quase-real pelos sensores indutivos no payload JSON/MQTT (abordagem MULTIBAND).
2. **Prioridade BRT Restrita à Banda e Limpeza de Fila no TraCI:** Em vez de incrementar $+5,0\text{ s}$ arbitrariamente e quebrar o ciclo comum, o `apply_adaptive_control()` deve conceder extensão/antecipação de verde ao BRT dentro da margem de folga $w_{ij}$ e dos limites $[RMIN_{ij}, RMAX_{ij}]$, retornando imediatamente ao *offset* de referência $\theta_i(1,j)$ no ciclo seguinte. Adicionalmente, o cálculo do *offset* efetivo passará a descontar o tempo de dissipação da fila residual ($\tau_{ij}$) estimado a partir de `queue_length_meters`.

---

## Agente 2 — Lote 2: Extensões Modernas de Largura de Banda e Geometria de Onda Verde

### 1. Síntese Técnica dos 4 Artigos
* **Friedman, Mark & Gartner (2025) — *Euclidean Green-Wave Theory*:** Propõem um paradigma dedutivo inspirado na geometria euclidiana para redes de vias arteriais de mão única alternada ou mão dupla topologicamente equivalentes a grades cartesianas (*RGW-roads*). A partir de quatro postulados de movimento das "setas verdes" (*green-arrows* — pelotões que nunca param, utilizam 100% da interseção, não colidem e ajustam a velocidade entre nós por $v_g = D/T_g$), demonstram que comprimentos discretos racionais ($\lambda = \alpha + \beta$, com $4/\lambda = n$) garantem progressão ininterrupta de extensão arbitrária, superando o colapso clássico após ~10 semáforos. Introduzem nós virtuais para reconciliar paridades de malha ($-1 \to +1$), setas de conversão/fluxo reduzido para demandas anisotrópicas e o dispositivo *Road-to-Traveler-Feedback-Device* (RTFD).
* **Zhang et al. (2015) — *AM-Band*:** Evoluem o MULTIBAND ao relaxar a exigência de simetria da linha central da banda verde em cada segmento arterial. Ao dividir a banda em sub-bandas assimétricas em torno da trajetória de progressão, a formulação MILP absorve a dispersão natural dos pelotões e amplia a janela efetiva de aproveitamento do verde em fluxos desbalanceados.
* **Zhang et al. (2026) — *System-Level Green-Wave with Mixed Intersection Release*:** Estendem o MILP de onda verde para redes urbanas fechadas combinando dois regimes de liberação semafórica: fases simétricas padrão NEMA e liberação por aproximação (*split phasing*). Essa liberação mista relaxa as restrições de fechamento de ciclo (*loop constraints*) da malha e maximiza a largura de banda em corredores concorrentes.
* **Talluri, Stang & Weidl (2025) — *Green Wave Survey*:** Revisam a evolução do controle de tempo fixo, atuado (MOVA) e adaptativo (SCOOT, SCATS, UTOPIA) até algoritmos inteligentes (meta-heurísticas, RL/MARL, DDPG-BAND, ES-BAND) acoplados a comunicações C-V2X (5G/IEEE 802.11p), formação de pelotões e aconselhamento de velocidade (GLOSA). Evidenciam que paradas em semáforos elevam emissões de $\text{CO}_2$ (+11,52%), $\text{CO}$ (+16,46%), $\text{HC}$ (+16,89%) e $\text{NO}_x$ (+15,72%), ao passo que ondas verdes sincronizadas reduzem $\text{CO}_2$, $\text{NO}_x$ e $\text{PM}_{10}$ em 10% a 40% e economizam até 15%–20% de combustível/energia.

### 2. Pontos Fortes e Limitações
* **Pontos Fortes:** A combinação de bandas assimétricas (*AM-Band*), liberação mista (*split/NEMA*) e comprimentos anisotrópicos ($\alpha \neq \beta$) destaca-se no atendimento a fluxos direcionais assimétricos típicos dos horários de pico (06:30–09:00 e 17:00–19:00). O acoplamento com recomendação de velocidade (GLOSA/RTFD) aumenta a estabilidade dos pelotões (+45%) e suaviza a cinemática veicular.
* **Limitações:** Em cruzamentos saturados ou congestionados, modelos puramente geométricos ou de largura de banda sofrem degradação severa devido a filas residuais (*queues*) e ondas de choque que impedem a passagem contínua do pelotão.

### 3. Proposta de Aproveitamento no Projeto UTFPR
1. **Progressão Assimétrica e Coordenação de Malha:** Aplicar a formulação de ondas anisotrópicas ($\alpha \neq \beta$) de Friedman et al. (2025) — ideal para a malha de vias de sentido único alternado e binários do centro de Curitiba — combinada ao relaxamento assimétrico do *AM-Band* (Zhang et al., 2015) e à liberação mista (Zhang et al., 2026) nos cruzamentos críticos.
2. **Métricas de Impacto Ambiental:** Fundamentar a avaliação ambiental com os indicadores de Talluri et al. (2025), mensurando a redução do regime "para-e-anda" (*stop-and-go*) para quantificar a mitigação esperada de 10% a 40% em $\text{CO}_2$, $\text{NO}_x$ e $\text{PM}_{10}$, a economia energética (15%–20%) e a atenuação do ruído urbano.

---

## Agente 5 — Lote 5: Max-Pressure com Prioridade ao Transporte Público e Ocupação (OCC-MP e Transit-MP)

### 1. Síntese Técnica dos 4 Artigos
* **OCC-MP (Ahmed, Liu & Gayah, 2024):** Modifica o peso $w_q(l,m)$ do Max-Pressure clássico multiplicando a diferença truncada de filas pela ocupação média de passageiros a montante $o(l,m)$, mantendo a estabilidade máxima:
  $$w(l, m) = o(l, m) \left[ x(l, m) - \sum_{n \in D(m)} x(m, n) r(m, n) \right]^+ = o(l, m) w_q(l, m)^+$$
* **Transit-MP e mTransit-MP (Tan, Liu, Sun, Rinaldi & van Lint, 2025):** Substitui o comprimento instantâneo de fila pelo tempo de viagem normalizado no link $\tau_v = \text{LTT}_v / \text{ETT}_{i,o}$ e introduz a variável binária de parada $\beta_v \in \{0,1\}$ para descontar o *dwell time* em estações ($\beta_v = 0$ enquanto o ônibus embarca passageiros), além de acumulação incremental de fila para eliminar *queue starvation*.
* **Coordenação Multimodal e Estocástica (He, Head & Ding, 2014; An et al., 2023):** O modelo MILP **PAMSCOD** (He et al., 2014) coordena simultaneamente pelotões de carros, solicitações de prioridade de ônibus (TSP) e fases de pedestres em artérias. Já **An et al. (2023)** integram incertezas estocásticas do tempo de viagem e de parada dos ônibus diretamente na otimização dos offsets arteriais.

### 2. Pontos Fortes e Limitações
O **OCC-MP** e o **Transit-MP** resolvem o conflito entre fluidez de carros e prioridade às linhas da URBS (`urbs_brt`, `urbs_ligeirinho`, `urbs_convencional`) porque arbitram fases pelo atraso/fila ponderado por passageiros a montante sem degradar o controle de *spillback* a jusante. Se duas linhas da URBS se cruzam, vence a fase com maior pressão total de passageiros; se um ônibus está parado embarcando ($\beta_v = 0$), a fase transversal é atendida, reduzindo *spillovers* em até 94,2%.

### 3. Proposta de Aproveitamento no Projeto UTFPR (`src/traci_controller.py`)
Implementar `compute_occ_transit_pressure(tl_id)`:
1. **Diferenciação de ocupação ($p_v$) por `vType` da URBS:** `urbs_brt` ($p_v = 100$), `urbs_ligeirinho` ($p_v = 50$), `urbs_convencional` ($p_v = 35$) e carros privados ($p_v = 1.5$).
2. **Filtro de parada ($\beta_v$) e tempo acumulado ($\tau_v$):** Definir $\beta_v = 0$ se o ônibus estiver parado longe da linha de retenção (estação-tubo/ponto) e calcular $\tau_v = 1.0 + \text{waiting\_time} / \text{ETT}_l$ para evitar *queue starvation*.
3. **Integração Multimodal (PAMSCOD):** Incluir pedestres aguardando travessia (`p_ped = 1.0`) na pressão de cada fase.

---

## Agente 6 — Lote 6: Prioridade Semafórica para Ônibus/BRT Integrada à Coordenação Arterial (TSP)

### 1. Síntese Técnica dos 4 Artigos
* **Li & Jin (2017):** Para conceder extensão de verde ($t_{ge} \in [5\text{ s}, 8\text{ s}]$) ou verde antecipado à fase arterial $a$ sem destruir a onda verde, o modelo mantém **fixos o ciclo comum $C$ e o *offset* relativo ao relógio mestre**, comprimindo proporcionalmente as fases não prioritárias ($m \neq a$) no mesmo ciclo (Eq. 9):
  $$g_{ge}^a = g^a + t_{ge}, \qquad g_{ge}^m = g^m \left(1 - \frac{t_{ge}}{C - L - g^a}\right), \quad \forall m \neq a$$
* **Yang et al. (2015):** Algoritmo Genético para coordenar múltiplas linhas de ônibus sobrepostas na mesma artéria minimizando o atraso ponderado por passageiros.
* **Ma et al. (2024) e Wan, Yu & Lo (2024):** Uso de trajetórias GPS de veículos-sonda (AVL de ônibus) e dependências espaço-temporais para calibrar tempos e *offsets* arteriais sob demanda estocástica.

### 2. Pontos Fortes e Limitações (Diagnóstico do `src/traci_controller.py`)
No controlador atual (`src/traci_controller.py`), aplica-se `setPhaseDuration(tl_id, remaining + 5.0)` sem compressão compensatória das fases seguintes. Isso dilata o ciclo local para $C + 5\text{ s}$ e causa **deriva de *offset* (*offset drift*)**, destruindo a onda verde nos cruzamentos seguintes.

### 3. Proposta de Aproveitamento no Projeto UTFPR
1. **Calibração Espaço-Temporal com Telemetria Real (`data/urbs_telemetry_hourly.csv`):** No pico das 17h–18h, circulam **504 ônibus únicos/h** no Centro com velocidade média de **19,07 km/h** — usar esse valor real para calibrar os *offsets* base entre semáforos.
2. **TSP com Compensação de Ciclo Fixo (Eq. 9 de Li & Jin):** Ao estender a fase verde em $t_{ge}$ para passagem de ônibus prioritário, deduzir proporcionalmente $t_{ge}$ das fases não prioritárias subsequentes do mesmo ciclo, preservando o *offset* mestre da onda verde.

---

## Agente 7 — Lote 7: Aprendizado por Reforço Multiagente (MARL) e Coordenação Grafo-Espacial

### 1. Síntese Técnica dos 4 Artigos
* **PressLight (Wei et al., 2019, KDD):** Define a recompensa exatamente como o negativo da pressão da interseção ($r_t^i = -P_i$), induzindo ondas verdes arteriais emergentes.
* **CoLight (Wei et al., 2019, CIKM):** Usa *Graph Attention Networks* (GAT) para ponderar dinamicamente a influência das interseções vizinhas $j \in \mathcal{N}_i$ via pesos de atenção $\alpha_{ij}$.
* **MA2C (Chu et al., 2019, IEEE TITS):** Algoritmo *Multi-Agent Advantage Actor-Critic* descentralizado que acopla estados e recompensas dos vizinhos com fator de desconto espacial $\alpha = 0,75$.
* **eMARLIN+ (Wang et al., 2024, IEEE TITS):** Mantém a coordenação semafórica mesmo sob observabilidade parcial dos sensores locais usando histórico sequencial.

### 2. Pontos Fortes e Limitações
Redes neurais profundas (DNNs) sofrem com alto custo de treinamento e baixa explicabilidade em banca multidisciplinar. Contudo, a formulação matemática de **pressão espacialmente acoplada com desconto $\alpha$ e atenção direcional $\alpha_{ij}$** pode ser extraída analiticamente sem caixa-preta.

### 3. Proposta de Aproveitamento no Projeto UTFPR
Calcular em cada cruzamento $i$ uma **Pressão Cooperativa Espacialmente Acoplada** via tópicos MQTT dos vizinhos $j \in \mathcal{N}_i$:
$$\tilde{P}_i(p) = P_i(p) + \alpha \sum_{j \in \mathcal{N}_i} \alpha_{ij}(t) \, P_j(p)$$
onde $\alpha_{ij}(t) = \frac{\text{fluxo}_{j \to i}(t)}{\sum_{k \in \mathcal{N}_i} \text{fluxo}_{k \to i}(t)}$ pondera dinamicamente o vizinho a montante na artéria principal, antecipando a chegada de pelotões e ônibus de forma 100% explicável e estável.

---

## Agente 10 — Lote 10: Sincronização de Horários, Transferências e Regularidade no Transporte Público

### 1. Síntese Técnica dos 4 Artigos
* **Ceder, Golany & Tal (2001) e Ibarra-Rojas & Rios-Solis (2012):** Maximizam encontros sincronizados de linhas de ônibus em nós centrais dentro de janelas flexíveis $[W_{\min}, W_{\max}]$ preservando a regularidade de *headway* ($H_{\min} \le \Delta t \le H_{\max}$).
* **Huang et al. (2022), Wu et al. (2014) e Kapica, Melnikova & Naumov (2025):** Demonstram que atrasos estocásticos degradam as tabelas horárias e provocam *bus bunching* (comboio de ônibus), exigindo controle em tempo real condicional ao atraso e à ocupação.

### 2. Pontos Fortes e Limitações
Conceder prioridade semafórica cega a todo ônibus agrava o *bus bunching* (um veículo adiantado alcança o veículo da frente que parou mais tempo nos pontos). A solução sustentada pela literatura é a **Prioridade Semafórica Condicional à Regularidade/Headway**.

### 3. Proposta de Aproveitamento no Projeto UTFPR
Com base em `data/urbs_central_lines.csv` (ex.: linha `250 Ligeirão Norte/Sul` com 69,0 part./h e *headway* alvo $H^* = 52\text{ s}$; `203` com 63,0 part./h e $H^* = 57\text{ s}$; `303` com 49,5 part./h e $H^* = 73\text{ s}$):
1. Calcular o índice de irregularidade $\rho_b = H_{\text{atual}} / H^*$ ou verificar se a velocidade instantânea do ônibus está abaixo de `vel_media_real_kmh`;
2. Ativar prioridade semafórica apenas para coletivos atrasados ($\rho_b > 1{,}10$ ou velocidade reduzida), suprimindo a prioridade para veículos adiantados ($\rho_b < 0{,}90$) para eliminar o *bus bunching* no Quadrilátero Central.

---

## Agente 3 — Lote 3: Auto-Organização Semafórica (SOTL) e Controle Adaptativo Clássico

### 1. Síntese Técnica dos 4 Artigos
* **Gershenson (2005 — *Self-Organizing Traffic Lights*, SOTL):** Governa cada interseção localmente por 6 regras operacionais a cada passo $\Delta t$:
  1. **Tempo mínimo de fase ($u_{min}$):** Nenhuma fase verde é interrompida enquanto $\phi_i < u_{min}$.
  2. **Acumulador espaço-temporal ($\kappa_i$):** Nas fases vermelhas, acumula $\kappa_i \mathrel{+}= \text{veículos} \cdot \Delta t$ (com pesos prioritários $w_j$ por classe veicular).
  3. **Integridade/corte de pelotão a curta distância ($e$ / $\omega$):** Mantém o verde se houver veículos prestes a cruzar a uma distância curta $e$ da linha de retenção.
  4. **Tamanho máximo de pelotão ($\mu$):** Desativa a restrição de manutenção de pelotão caso o pelotão exceda $\mu$ veículos.
  5. **Limiar de comutação ($\theta$):** Satisfeito $\phi_i \ge u_{min}$ e liberada a condição de pelotão, se $\kappa_i \ge \theta$, comuta a fase e zera $\kappa_i = 0$.
  6. **Bloqueio a jusante ($\omega_{\text{spillback}}$):** Inibe a concessão de verde se a via receptora a jusante estiver obstruída (*spillback*).
* **Wei, Zheng, Gayah & Li (2019), Robertson & Bretherton (1991 — SCOOT) e Ceylan & Bell (2004 — GA):** Estabelecem a taxonomia de controle cíclico (Webster, MAXBAND, SCOOT, GA) versus controle atuado/auto-organizado (SOTL, Max-Pressure).

### 2. Pontos Fortes e Limitações
O SOTL induz ondas verdes emergentes por estigmergia sem otimização central pesada, mapeando diretamente para laços indutivos e MQTT.

### 3. Proposta de Aproveitamento no Projeto UTFPR
Usar as regras de integridade de pelotão ($u_{min}, e, \mu$) e prevenção de *spillback* ($\omega$) em conjunto com os dados de ocupação do payload JSON MQTT.

---

## Agente 4 — Lote 4: Controle Max-Pressure Clássico e Otimização Dinâmica no SUMO/TraCI

### 1. Síntese Técnica dos 4 Artigos
* **Varaiya (2013 — *Max-Pressure Control*):** Define o peso de cada movimento $(l, m)$ como a diferença entre a fila a montante e a fila média ponderada nos links a jusante:
  $$w(l, m)(X) = x(l, m) - \sum_{p \in \text{Out}_m} r(m, p)x(m, p)$$
  e a pressão da fase $P(S_n)(X_n) = \sum_{(l, m) \in S_n} c(l, m) w(l, m)(X_n)$. Pelo Teorema 2 (função de Lyapunov quadrática estocástica), garante **estabilidade máxima da rede** usando apenas filas locais adjacentes, sem necessitar da matriz Origem-Destino global. No Teorema 5, introduz filas ponderadas $w_Q(l,m)$ normalizadas pela capacidade da quadra ($Q(l,m) = 1/x_{\max}(l,m)$).
* **Sun, Qi, Liu & Xu (2024 — *PLOS ONE*, SUMO/TraCI):** Escalonamento dinâmico em malha fechada com contador de inanição ($\varepsilon_n = \varepsilon_{n-1} + 1$) e preempção no SUMO/TraCI, reduzindo o tempo de espera em 32,1%, combustível em 17,48% e emissões em 18,46%.
* **García-Nieto et al. (2013) & He et al. (2025):** Otimização *simulation-in-the-loop* no SUMO focada em tempo de viagem e emissões de $\text{CO}_2$.

### 2. Pontos Fortes e Limitações
Estabilidade matemática comprovada em malhas fechadas como o Quadrilátero Central de Curitiba e mitigação nativa de *spillback*, exigindo apenas o contador anti-inanição ($\varepsilon_n$) e pesos modais.

### 3. Proposta de Aproveitamento no Projeto UTFPR
Mapear ligações $(l,m)$ via `traci.trafficlight.getControlledLinks(tl_id)`, normalizar filas pelo comprimento da quadra ($1/L_{\max}$) e somar o termo anti-inanição $\alpha \varepsilon_n(S_n)$.

---

## Agente 8 — Lote 8: Q-Learning de Velocidade/Offset e Sincronização Veículo-Infraestrutura (GLOSA)

### 1. Síntese Técnica dos 4 Artigos
* **Yuan & Ioannou (2024):** Acoplam controle semafórico (TSC) e coordenação dinâmica de *offset* de velocidade (DSO) via Q-Learning tabular, reduzindo paradas em até 49%, filas em 55% e emissões de $\text{CO}_2$ em 10–12%.
* **Seredynski et al. (2013), Kopp et al. (2013) e Bhattacharyya et al. (2022):** Demonstram que o **Multi-Segment GLOSA** integrado ao controle adaptativo calcula a velocidade recomendada $v_{rec} = \text{clip}\left(\frac{d}{\Delta t_{chegada\_verde}}, v_{min}, v_{max}\right)$ considerando o tempo de limpeza da fila ($\tau_{fila}$), suavizando a condução de todo o pelotão.

### 2. Proposta de Aproveitamento no Projeto UTFPR
Calcular a cada passo no TraCI o *offset* dinâmico $T_o = \left(\frac{L}{\bar{v}_{real}} + \tau_{fila}\right) \pmod{T_c}$ e a velocidade ótima de onda verde $v_{opt\_kmh} = \text{clip}\left(3{,}6 \cdot \frac{L}{\Delta t_{verde\_inicio} + \tau_{fila}}, 25{,}0, 50{,}0\right)$, publicando no MQTT e exibindo como Painel de Mensagem Variável (PMV) no dashboard **Streamlit**.

---

## Agente 9 — Lote 9: Veículos Inteligentes, Sensores IoT, Eficiência Energética e Redução de Emissões

### 1. Síntese Técnica dos 4 Artigos
* **Tomar, Sreedevi & Pandey (2022):** Revisam arquiteturas de sensoriamento IoT e V2I em Nível I (interseções adjacentes) e Nível II (malha).
* **Zhang et al. (2020):** Incorporam o tempo de dissipação da fila parada ($\tau_{queue} = L_{queue} / v_{shockwave}$) ao cálculo do *offset* e da janela verde efetiva.
* **Simchon et al. (2020) e Gao et al. (2024):** Comprovam via HBEFA/PHEMlight no SUMO-TraCI que eliminar ciclos *stop-and-go* corta os picos transientes de $\text{CO}_2$, $\text{NO}_x$, $\text{PM}_x$ e o ruído de frenagem/arrancada.

### 2. Proposta de Aproveitamento no Projeto UTFPR
1. Integrar a taxa de emissão instantânea `co2_grams_per_second` ($\dot{E}_{\text{CO}_2,i}$) e `queue_length_meters` do contrato JSON MQTT na função de avaliação da fase:
   $$J_p(t) = \sum_{i \in p} \left( w_q \cdot \texttt{queue\_length\_meters}_i(t) + w_e \cdot \texttt{co2\_grams\_per\_second}_i(t) \right)$$
2. Parametrizar a atenuação de ruído urbano ($\Delta L_{eq}$ nos modelos FHWA/CoRTN) em função da redução de veículos parados (`halting_vehicles`) e picos de aceleração/emissão.
