# Catálogo Estruturado de 40 Artigos sobre Algoritmos de Sincronização na Mobilidade Urbana

Este catálogo organiza **40 artigos científicos verificados** em **10 Lotes de 4 artigos** (`Lote 1` a `Lote 10`), incluindo os **15 textos integrais (PDF e TXT)** armazenados em `docs/artigos/` e `docs/artigos/txt/`, além das especificações metodológicas dos demais artigos de cada lote.

---

## Lote 1 — Onda Verde Clássica e Modelagem Matemática Aplicada a Curitiba
1. **Joner, S., & Volpi, N. M. P. (2013).** *Sincronização de semáforos: modelo matemático para uma aplicação ao tráfego de Curitiba*. **HOLOS**, Ano 29, Vol. 2, pp. 3–18. DOI: `10.15628/holos.2013.1254`
   - **Arquivo de texto completo:** `docs/artigos/txt/Joner_Volpi_2013_Sincronizacao_Semaforos_Curitiba.txt`
   - **Foco técnico:** Programação Linear Inteira Mista (MILP) baseada em Little (1966) e Gartner (1981) aplicada às artérias de Curitiba, maximizando a largura de banda bidirecional com restrições de tempo de ciclo, velocidades entre trechos e conversões.
2. **Little, J. D. C. (1966).** *The Synchronization of Traffic Signals by Mixed-Integer Linear Programming*. **Operations Research**, 14(4), 568–594. DOI: `10.1287/opre.14.4.568`
   - **Foco técnico:** Formulação matemática original de sincronização por MILP para maximizar as larguras de banda ($b$ e $\bar{b}$) nos dois sentidos de uma artéria mediante variáveis inteiras de restrição de ciclo ($m_i$) e offsets ($\phi_i$).
3. **Little, J. D. C., Kelson, M. D., & Gartner, N. H. (1981).** *MAXBAND: A Program for Setting Signals on Arteries and Triangular Networks*. **Transportation Research Record**, 795, 40–46.
   - **Foco técnico:** Algoritmo MAXBAND que resolve um MILP por Branch-and-Bound permitindo otimizar simultaneamente tempo de ciclo ($C$), offsets, velocidades de progressão e ordem de fases de conversão à esquerda, incluindo tempo de limpeza de fila ($\tau$).
4. **Gartner, N. H., Assmann, S. F., Lasaga, F., & Hou, D. L. (1991).** *A multi-band approach to arterial traffic signal optimization (MULTIBAND)*. **Transportation Research Part B: Methodological**, 25(1), 55–74. DOI: `10.1016/0191-2615(91)90013-9`
   - **Foco técnico:** Substitui a banda uniforme do MAXBAND por bandas variáveis por segmento ($b_i, \bar{b}_i$), ponderadas pela razão volume/capacidade ($v_i/c_i$) ou fluxo direcional de cada trecho.

---

## Lote 2 — Extensões Modernas de Largura de Banda e Geometria de Onda Verde
5. **Friedman, M. H., Mark, B. L., & Gartner, N. H. (2025).** *Euclidean Approach to Green-Wave Theory Applied to Traffic Signal Networks*. **arXiv:2508.12146**.
   - **Arquivo de texto completo:** `docs/artigos/txt/Friedman_Mark_Gartner_2025_Euclidean_Green_Wave.txt`
   - **Foco técnico:** Teoria geométrica euclidiana para coordenação de ondas verdes em redes de semáforos.
6. **Talluri, K. K., Stang, C., & Weidl, G. (2025).** *Green Wave as an Integral Part for the Optimization of Traffic Efficiency and Safety: A Survey*. **arXiv:2507.22511**.
   - **Arquivo de texto completo:** `docs/artigos/txt/Talluri_Stang_Weidl_2025_Green_Wave_Survey.txt`
   - **Foco técnico:** Revisão abrangente da integração de ondas verdes com sistemas inteligentes de transporte (ITS), segurança viária, redução de emissões e conectividade V2X.
7. **Zhang, C., Xie, Y., Gartner, N. H., Stamatiadis, C., & Arsava, T. (2015).** *AM-Band: An Asymmetrical Multi-Band model for arterial traffic signal coordination*. **Transportation Research Part C: Emerging Technologies**. DOI: `10.1016/j.trc.2015.04.014`
   - **Foco técnico:** Relaxa a exigência de simetria da linha central de progressão do MULTIBAND, ampliando a janela efetiva de progressão em corredores com dispersão de pelotão e fluxos assimétricos.
8. **Zhang, P., Xu, S., Ji, B., Sun, C., Zhang, J., Li, W., & Ma, J. (2026).** *System-Level Optimization Model for Green-Wave Coordination Control of Urban Road Networks with Mixed Intersection Release*. **Systems** (MDPI), 14(8), 919. DOI: `10.3390/systems14080919`
   - **Foco técnico:** Modelo MILP em nível de rede urbana combinando fases simétricas NEMA e liberação por aproximação (*split phasing*) para maximizar a banda verde em malhas fechadas.

---

## Lote 3 — Auto-Organização Semafórica (SOTL) e Controle Adaptativo Clássico
9. **Gershenson, C. (2005).** *Self-Organizing Traffic Lights*. **Complex Systems**, 16(1), 29–53. DOI: `10.25088/ComplexSystems.16.1.29`
   - **Arquivo de texto completo:** `docs/artigos/txt/Gershenson_2005_Self_Organizing_Traffic_Lights.txt`
   - **Foco técnico:** Algoritmo SOTL baseado em contadores acumulados veículos×tempo ($\kappa$), tempo mínimo de fase ($u_{min}$), tamanho máximo de pelotão ($\mu$) e prevenção de bloqueio a jusante (*spillback*), gerando ondas verdes emergentes.
10. **Wei, H., Zheng, G., Gayah, V. V., & Li, Z. (2019).** *A Survey on Traffic Signal Control Methods*. **arXiv:1904.08117**.
    - **Arquivo de texto completo:** `docs/artigos/txt/Wei_Zheng_Gayah_Li_2019_Survey_Traffic_Signal_Control.txt`
    - **Foco técnico:** Taxonomia completa comparando métodos clássicos de engenharia de tráfego (Webster, MAXBAND, Actuated, SOTL, Max-Pressure) e formulações de aprendizado por reforço.
11. **Robertson, D. I., & Bretherton, R. D. (1991).** *Optimizing Networks of Traffic Signals in Real Time—The SCOOT Method*. **IEEE Transactions on Vehicular Technology**, 40(1), 11–15. DOI: `10.1109/25.69966`
    - **Foco técnico:** Perfis cíclicos de fluxo alimentados por laços indutivos a montante e três otimizadores incrementais (Split, Offset e Cycle) para minimizar paradas e atrasos na rede.
12. **Ceylan, H., & Bell, M. G. H. (2004).** *Traffic signal timing optimisation based on genetic algorithm approach, including drivers' routing*. **Transportation Research Part B: Methodological**. DOI: `10.1016/S0191-2615(03)00015-8`
    - **Foco técnico:** Otimização bi-nível por Algoritmo Genético para tempos de ciclo, splits e offsets acoplada ao equilíbrio estocástico de escolha de rotas.

---

## Lote 4 — Controle Max-Pressure Clássico e Otimização Dinâmica no SUMO/TraCI
13. **Varaiya, P. (2013).** *Max pressure control of a network of signalized intersections*. **Transportation Research Part C: Emerging Technologies**, 36, 177–195. DOI: `10.1016/j.trc.2013.08.014`
    - **Arquivo de texto completo:** `docs/artigos/txt/Varaiya_2013_Max_Pressure_Control_Network_Signalized_Intersections.txt`
    - **Foco técnico:** Controlador descentralizado Max-Pressure que calcula o peso de cada movimento $(l, m)$ pela diferença entre a fila a montante $x(l, m)$ e a fila média ponderada pelas taxas de conversão a jusante $\sum_p r(m, p) x(m, p)$, garantindo estabilidade máxima da rede.
14. **Sun, G., Qi, R., Liu, Y., & Xu, F. (2024).** *A dynamic traffic signal scheduling system based on improved greedy algorithm*. **PLOS ONE**. DOI: `10.1371/journal.pone.0298417`
    - **Arquivo de texto completo:** `docs/artigos/txt/Sun_et_al_2024_Dynamic_Traffic_Signal_SUMO_TraCI.txt`
    - **Foco técnico:** Sistema de escalonamento dinâmico de fases semafóricas baseado em algoritmo guloso aprimorado e preempção de veículos prioritários, implementado e avaliado em **SUMO via TraCI**.
15. **García-Nieto, J., Olivera, A. C., & Alba, E. (2013).** *Optimal Cycle Program of Traffic Lights With Particle Swarm Optimization*. **IEEE Transactions on Evolutionary Computation**, 17(6), 823–839. DOI: `10.1109/TEVC.2013.2260755`
    - **Foco técnico:** Otimização offline/híbrida de planos de fases semafóricas usando PSO acoplado ao simulador microscópico SUMO para reduzir tempo de viagem e emissões.
16. **He, P., Li, Q., Yuan, X., & Zhou, B. (2025).** *A Simple Framework Towards Vision-based Traffic Signal Control with Microscopic Simulation (TrafficDojo)*. **arXiv (2025)**.
    - **Foco técnico:** Integração de simulação microscópica SUMO com observação visual de câmeras para controle semafórico adaptativo e redução de emissões de $\text{CO}_2$.

---

## Lote 5 — Max-Pressure com Prioridade ao Transporte Público e Ocupação de Passageiros
17. **Ahmed, T., Liu, H., & Gayah, V. V. (2024).** *OCC-MP: A Max-Pressure framework to prioritize transit and high occupancy vehicles*. **arXiv:2406.19269** / *Transportation Research Part C*.
    - **Arquivo de texto completo:** `docs/artigos/txt/Ahmed_Liu_Gayah_2024_OCC_MP_Transit_Max_Pressure.txt`
    - **Foco técnico:** Pondera a pressão de cada movimento pela ocupação de passageiros (carros vs. ônibus/BRT), priorizando naturalmente o transporte coletivo dentro da estrutura matemática estável do Max-Pressure.
18. **Tan, C., Liu, H., Sun, D., Rinaldi, M., & van Lint, H. (2025).** *Transit-MP: Transit-Prioritized Max-Pressure Control in Sparse Connected Vehicle Environments*. **arXiv:2511.00309**.
    - **Arquivo de texto completo:** `docs/artigos/txt/Tan_et_al_2025_Transit_MP_Prioritized_Max_Pressure.txt`
    - **Foco técnico:** Formulação *Transit-MP* e *mTransit-MP* para prioridade de ônibus em controle Max-Pressure cíclico e acíclico considerando paradas de embarque/desembarque (*dwell times*) e proteção contra inanição de fases (*queue starvation*).
19. **He, Q., Head, K. L., & Ding, J. (2014).** *Multi-modal traffic signal control with priority, signal actuation and coordination*. **Transportation Research Part C: Emerging Technologies**, 46, 65–82. DOI: `10.1016/j.trc.2014.05.001`
    - **Foco técnico:** Formulação MILP multimodal (PAMSCOD) que coordena simultaneamente pelotões de carros, solicitações de prioridade de ônibus (TSP) e fases de pedestres em artérias sinalizadas.
20. **An, L., Bai, X., et al. (2023).** *Stochastic-priority-integrated signal coordination considering connected bus operation uncertainties*. **Transportmetrica B: Transport Dynamics**. DOI: `10.1080/21680566.2023.2297152`
    - **Foco técnico:** Coordenação semafórica arterial integrada à prioridade de ônibus considerando incertezas estocásticas no tempo de viagem e parada dos coletivos.

---

## Lote 6 — Prioridade Semafórica para Ônibus/BRT Integrada à Coordenação Arterial (TSP)
21. **Li, R., & Jin, P. J. (2017).** *Transit signal priority optimization for urban traffic network considering arterial coordinated signal control*. **Advances in Mechanical Engineering**, 9(8). DOI: `10.1177/1687814017700594`
    - **Arquivo de texto completo:** `docs/artigos/txt/Li_Jin_2017_Transit_Signal_Priority_Arterial_Coordinated_Signal_Control.txt`
    - **Foco técnico:** Otimização de extensão de verde (*green extension*) e verde antecipado (*early green*) para ônibus mantendo o ciclo comum e o offset de coordenação arterial para não romper a onda verde geral.
22. **Yang, Z., Wang, W., Chen, S., & Ding, H. (2015).** *Genetic Algorithm for Multiple Bus Line Coordination on Urban Arterial*. **Computational Intelligence and Neuroscience**. DOI: `10.1155/2015/868521`
    - **Foco técnico:** Otimização por Algoritmo Genético para coordenar semáforos em corredores com múltiplas linhas de ônibus sobrepostas, minimizando o atraso ponderado por passageiros.
23. **Ma, W., Li, X., Yu, C., Su, Z., & Liu, S. (2024).** *Arterial Signal Timing Based on Probe Vehicle Trajectories Under Cyclic Stochastic Demand*. **IEEE Transactions on Intelligent Transportation Systems**. DOI: `10.1109/TITS.2024.3408803`
    - **Foco técnico:** Estimação e otimização de tempos e offsets arteriais usando trajetórias GPS de veículos-sonda (como telemetria de ônibus) sob demanda cíclica estocástica.
24. **Wan, L., Yu, C., & Lo, H. K. (2024).** *Traffic Signal Coordination Under Stochastic Demands and Turning Ratios Considering Spatial-Temporal Dependencies*. **IEEE Transactions on Intelligent Transportation Systems**, 25(11), 18236–18251. DOI: `10.1109/TITS.2024.3453495`
    - **Foco técnico:** Modelo de coordenação semafórica que incorpora correlações espaço-temporais de chegada de pelotões e incertezas nas taxas de conversão entre interseções.

---

## Lote 7 — Aprendizado por Reforço Multiagente (MARL) e Coordenação Grafo-Espacial
25. **Wei, H., Xu, N., Zhang, H., Zheng, G., Zang, X., Chen, C., Zhang, W., Zhu, Y., Xu, K., & Li, Z. J. (2019).** *CoLight: Learning Network-level Cooperation for Traffic Signal Control*. **Proceedings of CIKM '19**. DOI: `10.1145/3357384.3357902`
    - **Arquivo de texto completo:** `docs/artigos/txt/Wei_et_al_2019_CoLight_MARL.txt`
    - **Foco técnico:** Redes de Atenção em Grafos (*Graph Attention Networks* - GAT) para ponderar dinamicamente a influência das interseções vizinhas na decisão de fase de cada semáforo.
26. **Chu, T., Wang, J., Xu, L., & Li, Z. (2019).** *Multi-Agent Deep Reinforcement Learning for Large-scale Traffic Signal Control*. **arXiv:1903.04527** / IEEE TITS.
    - **Arquivo de texto completo:** `docs/artigos/txt/Chu_et_al_2019_MARL_Traffic_Signal_Control.txt`
    - **Foco técnico:** Arquitetura MA2C (Multi-Agent Advantage Actor-Critic) totalmente descentralizada com desconto espacial de estados e recompensas das interseções adjacentes.
27. **Wei, H., Chen, C., Zheng, G., Wu, K., Gayah, V., Xu, K., & Li, Z. J. (2019).** *PressLight: Learning Max Pressure Control to Coordinate Traffic Signals in Arterial Network*. **Proceedings of KDD '19**. DOI: `10.1145/3292500.3330949`
    - **Foco técnico:** Conecta a teoria de controle (Max-Pressure de Varaiya) ao Deep RL, definindo a recompensa exatamente como o negativo da pressão da interseção para alcançar coordenação arterial sem comunicação explícita pesada.
28. **Wang, X., Taitler, A., Smirnov, I., Sanner, S., & Abdulhai, B. (2024).** *eMARLIN+: Addressing Partial Observability to Promote Traffic Signal Coordination by Leveraging Historical Information*. **IEEE Transactions on Intelligent Transportation Systems**, 25(12), 21380–21392. DOI: `10.1109/TITS.2024.3462951`
    - **Foco técnico:** Aprendizado por reforço multiagente recorrente capaz de manter a sincronização entre cruzamentos mesmo quando sensores locais fornecem observabilidade parcial.

---

## Lote 8 — Q-Learning de Velocidade/Offset e Sincronização Veículo-Infraestrutura (GLOSA)
29. **Yuan, T., & Ioannou, P. A. (2024).** *Traffic Signal Control and Speed Offset Coordination Using Q-Learning for Arterial Road Networks*. **arXiv:2404.06382**.
    - **Arquivo de texto completo:** `docs/artigos/txt/Yuan_Ioannou_2024_TSC_Speed_Offset_QLearning.txt`
    - **Foco técnico:** Coordenação conjunta de tempos semafóricos e offsets de velocidade em corredores arteriais usando Q-Learning tabular/estruturado para reduzir paradas e filas.
30. **Seredynski, M., Khadraoui, D., et al. (2013).** *Comparison of Single- and Multi-Segment GLOSA Approaches*. **2013 16th International IEEE Conference on Intelligent Transportation Systems (ITSC)**. DOI: `10.1109/ITSC.2013.6728552`
    - **Foco técnico:** Demonstra que o aconselhamento ótimo de velocidade em múltiplos segmentos sincronizados (*Multi-Segment GLOSA*) supera o GLOSA de interseção isolada na redução de paradas e consumo de combustível.
31. **Kopp, M., Erdmann, C., et al. (2013).** *Combining Adaptive Junction Control with Simultaneous Green-Light-Optimal-Speed-Advisory*. **2013 IEEE WiVeC**. DOI: `10.1109/WIVEC.2013.6698230`
    - **Foco técnico:** Integra controle semafórico adaptativo com GLOSA, utilizando previsões de mudança de fase para evitar conflito entre a adaptação do semáforo e a recomendação de velocidade enviada via V2I/MQTT.
32. **Bhattacharyya, K., Laharotte, P.-A., Burianne, A., & El Faouzi, N.-E. (2022).** *Assessing Connected Vehicle's Response to Green Light Optimal Speed Advisory From Field Operational Test and Scaling Up*. **IEEE Transactions on Intelligent Transportation Systems**, 24(6). DOI: `10.1109/TITS.2022.3187532`
    - **Foco técnico:** Avaliação empírica e em simulação do impacto da taxa de penetração e adesão a recomendações de velocidade na suavização do tráfego e redução de emissões.

---

## Lote 9 — Veículos Inteligentes, Sensores IoT, Eficiência Energética e Redução de Emissões
33. **Tomar, I., Sreedevi, I., & Pandey, N. (2022).** *State-of-Art Review of Traffic Light Synchronization for Intelligent Vehicles: Current Status, Challenges, and Emerging Trends*. **Electronics** (MDPI), 11(3), 465. DOI: `10.3390/electronics11030465`
    - **Arquivo de texto completo:** `docs/artigos/txt/Tomar_et_al_2022_Traffic_Light_Synchronization_Intelligent_Vehicles_Review.txt`
    - **Foco técnico:** Revisão detalhada sobre arquiteturas de sensoriamento (laços indutivos, câmeras, V2I/IoT), algoritmos de sincronização semafórica, priorização de veículos e métricas ambientais.
34. **Simchon, L., Ben-Idan, I., & Oren, Y. (2020).** *Real-Time Implementation of GLOSA for Electric Vehicles*. **Vehicles** (MDPI), 2(1), 35–54. DOI: `10.3390/vehicles2010003`
    - **Foco técnico:** Modelagem cinemática de desaceleração/aceleração suave para eliminar ciclos "para-e-anda" (*stop-and-go*) antes de semáforos, reduzindo consumo energético e ruído de frenagem/arrancada.
35. **Zhang, Z., et al. (2020).** *GLOSA System Designed for Electric Vehicles Considering Queuing Effect and Driver's Speed Tracking Error*. **IEEE Access**, 8, 208796–208808. DOI: `10.1109/ACCESS.2020.3037105`
    - **Foco técnico:** Incorpora o tempo de dissipação da fila parada no semáforo ($\tau_{queue}$) ao cálculo do offset/janela verde efetiva para que os veículos em aproximação não colidam com a cauda da fila.
36. **Gao, L., et al. (2024).** *Traffic Signal Coordination and Optimization for Urban Arterials with Emission Reduction Target*. **IET Intelligent Transport Systems**.
    - **Foco técnico:** Otimização bi-objetivo de coordenação semafórica arterial (atraso + emissões cinemáticas de $\text{CO}_2$, $\text{NO}_x$ e PM) validada por co-simulação SUMO-TraCI.

---

## Lote 10 — Sincronização de Horários, Transferências e Regularidade no Transporte Público
37. **Kapica, D., Melnikova, Y., & Naumov, V. (2025).** *Synchronization in Public Transportation: A Review of Challenges and Techniques*. **Future Transportation** (MDPI), 5(1), 6. DOI: `10.3390/futuretransp5010006`
    - **Arquivo de texto completo:** `docs/artigos/txt/Kapica_et_al_2025_Synchronization_Public_Transportation_Review.txt`
    - **Foco técnico:** Revisão sistemática de modelos de sincronização no transporte público, métodos de controle em tempo real (*holding*, *speed adjustment*, prioridade semafórica condicional) para evitar *bus bunching* (comboio de ônibus) e manter a regularidade dos *headways*.
38. **Ceder, A., Golany, B., & Tal, O. (2001).** *Creating bus timetables with maximal synchronization*. **Transportation Research Part A: Policy and Practice**, 35(10), 913–928.
    - **Foco técnico:** Modelo MIP para maximizar encontros sincronizados de linhas de ônibus em nós de transferência sob restrições de *headway* mínimo e máximo.
39. **Ibarra-Rojas, O. J., & Rios-Solis, Y. A. (2012).** *Synchronization of bus timetabling*. **Transportation Research Part B: Methodological**, 46(5), 599–614. DOI: `10.1016/j.trb.2012.01.006`
    - **Foco técnico:** Janelas flexíveis de sincronização entre linhas de transporte coletivo que se cruzam no centro urbano, otimizadas por busca local iterada (ILS).
40. **Huang, K., Wu, J., Sun, H., Chen, X., & Zhou, Z. (2022).** *Timetable synchronization optimization in a subway–bus network*. **Physica A**, 608, 128273. DOI: `10.1016/j.physa.2022.128273` (em conjunto com **Wu et al., 2014**, DOI: `10.1016/j.trc.2014.11.001`)
    - **Foco técnico:** Sincronização multimodal em redes de alta capacidade e linhas alimentadoras, considerando capacidade dos veículos, equidade no tempo de espera e dados reais de operação.
