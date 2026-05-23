Choi, S. H., Lee, S. J., & Kim, T. G. (2014, May 18). Multi-fidelity modeling & simulation methodology for simulation speed up | Proceedings of the 2nd ACM SIGSIM Conference on Principles of Advanced Discrete Simulation. ACM Conferences. https://dl.acm.org/doi/10.1145/2601381.2601385

# Summary — Choi, Lee & Kim (2014): *Multi-fidelity Modeling & Simulation Methodology for Simulation Speed Up*

**Reference:** Choi, S. H., Lee, S. J., & Kim, T. G. (2014). *Multi-fidelity modeling & simulation methodology for simulation speed up*. Proceedings of the 2nd ACM SIGSIM Conference on Principles of Advanced Discrete Simulation, 139–150. ([dl.acm.org][2])

## 1. Core Motivation

The paper addresses the computational cost of **modeling-and-simulation-based analysis**, especially “what-if” analyses where many input combinations must be simulated. Running all scenarios with high-fidelity models can become prohibitively expensive. The proposed methodology therefore aims to increase simulation speed while limiting accuracy loss and preserving reuse of existing models and simulation engines. ([ResearchGate][1])

The target systems are **continuous systems** and **discrete event systems**. The paper does not propose a general surrogate modeling method, but a runtime **multi-fidelity model substitution** methodology: a high-fidelity target model is replaced by a composed multi-fidelity model that internally switches between fidelity levels. ([ResearchGate][1])

---

## 2. Main Idea

The central idea is to use the **high-fidelity model only in the important part of the simulation scenario** and to use lower-fidelity models elsewhere. The important part is called the **Interest Region**. The switching criterion is derived from an **Interest Region Variable (IRV)** and the selected region (R), which together form the **Fidelity Change Condition (FCC)**. ([ResearchGate][1])

This is conceptually close to your syssimx runtime model switching: the expensive FEM model is not active for the full simulation, but only near contact, where its additional fidelity is relevant.

---

## 3. Proposed Methodology

The paper defines a four-step methodology.

| Step                                                         | Description                                                                                                                          |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| **1. Target model selection and Interest Region definition** | Select an expensive, frequently executed target model and define the region where high fidelity is required.                         |
| **2. Low-fidelity model development**                        | Derive cheaper models from the high-fidelity target model.                                                                           |
| **3. Multi-fidelity model composition**                      | Compose a multi-fidelity model containing the internal models and a selection model.                                                 |
| **4. Selected target model substitution**                    | Replace the original target model by the composed multi-fidelity model without modifying the surrounding model or simulation engine. |

The methodology is designed explicitly to maximize **model reusability**: the multi-fidelity model has the same external input-output interface as the original target model, so the rest of the simulation model can remain unchanged. ([ResearchGate][1])

---

## 4. Target Model Selection and Interest Region

A target model should satisfy three conditions:

1. It is based on a continuous or discrete event model formalism.
2. It is executed frequently and consumes a significant share of the total simulation time.
3. Its Interest Region is smaller than the full simulation region, so lower-fidelity models can be used outside that region. ([ResearchGate][1])

The paper introduces **Execution Time Ratio (ETR)** as the ratio of the target model execution time to the total simulation time. A high ETR is important because replacing a model that contributes little to total runtime cannot yield a meaningful speedup. ([ResearchGate][1])

The **Interest Region Variable (IRV)** may be simulation time, an input variable, a state variable, or a derived variable combining inputs and states. The Interest Region (R) is then defined over this variable. ([ResearchGate][1])

---

## 5. Low-Fidelity Model Development

The paper distinguishes low-fidelity model construction for continuous and discrete event models.

### Continuous models

For continuous models, fidelity is linked to the **state transition function** and **output function**. Lower-fidelity models are obtained by simplifying these functions. The paper proposes two simplification methods:

| Method          | Meaning                                                                                   |
| --------------- | ----------------------------------------------------------------------------------------- |
| **Elimination** | Remove terms from the state-transition function that have little influence on the output. |
| **Projection**  | Fix selected variables in the state-transition function.                                  |

In the torpedo maneuver example, lower-fidelity models are created by eliminating terms from the differential equation. This reduces execution time but increases output error. ([ResearchGate][1])

### Discrete event models

For discrete event models, fidelity is linked to the **output function** and **time advance function**. The lower-fidelity model simplifies the algorithms used to compute output values or state durations. In the vehicle example, the high-fidelity model computes shortest paths using Dijkstra’s algorithm, while the low-fidelity model uses a simpler distance calculation. ([ResearchGate][1])

---

## 6. Multi-Fidelity Model Composition

The composed **Multi-Fidelity Model (MFM)** consists of:

* the original target model,
* one or more lower-fidelity models,
* a **Selection Model (SM)**,
* a coupling scheme connecting inputs, outputs, and internal models. ([ResearchGate][1])

The MFM keeps the same external inputs and outputs as the original target model. Internally, the Selection Model decides whether the currently active model should remain active or whether another fidelity level should be activated. ([ResearchGate][1])

The Selection Model has two central roles:

1. **Input bypass:** If no fidelity change is required, it forwards the input to the currently active model.
2. **Model change with state copy:** If the FCC is satisfied, it transfers the state from the current internal model to the next internal model and then forwards the input to the newly activated model. ([ResearchGate][1])

This is one of the most relevant parts for syssimx because it directly resembles the idea of a multi-model component with state synchronization.

---

## 7. Simulation Speed Evaluation

The paper defines speedup as the ratio between the execution time of the original high-fidelity model workflow and the execution time of the multi-fidelity workflow. The analysis identifies several factors that determine whether the methodology is effective:

* the execution-time share of the selected target model,
* the overhead of the Selection Model,
* the fraction of the simulation scenario spent in each fidelity level,
* the cost ratio between low- and high-fidelity models,
* the overhead caused by model exchange,
* the frequency of switching. ([ResearchGate][1])

The paper explicitly notes that frequent model exchanges reduce the benefit because they increase overhead. This point is directly relevant for interpreting syssimx runtime-switching benchmarks. ([ResearchGate][1])

---

## 8. Case Studies

## 8.1 Torpedo Tactics Simulation

The first case study applies the methodology to a **Torpedo Tactics Simulation (TTS)** model. The goal is to estimate torpedo hit rate under different scenario parameters. The target model is the torpedo maneuver model, and the Interest Region is defined by whether the torpedo has detected the target. When detection is true, maneuver accuracy has a strong influence on hit rate, so the high-fidelity model is used. ([ResearchGate][1])

The result shows that the multi-fidelity model has lower execution time than the high-fidelity model while preserving similar hit-rate behavior. The paper reports an overall simulation speedup of at least **1.21×** with **5% accuracy loss**, and the later 2017 extension reports about **1.25×** speedup for the related UUV case. ([ResearchGate][1])

## 8.2 Vehicle Allocation Simulation

The second case study applies the methodology to a **Vehicle Allocation Simulation (VAS)** model. The target model is a vehicle model whose route computation is expensive. The high-fidelity version uses Dijkstra’s algorithm, while the low-fidelity version uses a simpler distance-based approximation. ([ResearchGate][1])

The Interest Region is based on expected travel distance. The authors vary the start point of the Interest Region and select the threshold that minimizes execution time while keeping the accuracy loss within a permissible error. For a permissible error of 0.05, they select an Interest Region starting at 2000. ([ResearchGate][1])

---

## 9. Main Findings

The paper’s main contribution is not a new numerical solver but a **methodology for wrapping an existing high-fidelity model into a multi-fidelity substitute**. The key design goal is that the surrounding simulation model and simulation engine do not need to be modified. ([ResearchGate][1])

The reported results show moderate speedups with bounded accuracy loss. The benefit depends strongly on choosing a high-ETR target model, defining a meaningful Interest Region, developing sufficiently cheap and sufficiently accurate low-fidelity models, and keeping switching overhead low. ([ResearchGate][1])

---

# Relevance for syssimx

This paper is highly relevant because it is one of the closer conceptual predecessors for **runtime model switching inside one simulation run**.

## Strong Similarities

| Choi et al. (2014)           | syssimx                                                                        |
| ---------------------------- | ------------------------------------------------------------------------------ |
| High-fidelity target model   | FEM pendulum/contact model                                                     |
| Low-fidelity models          | FMU/OpenSim/rigid-body pendulum models                                         |
| Interest Region              | Contact-near simulation phase                                                  |
| Interest Region Variable     | Gap, distance to wall, contact indicator, angle condition                      |
| Fidelity Change Condition    | Runtime switching condition                                                    |
| Selection Model              | `MultiModelComponent` / active-model selection logic                           |
| Model change with state copy | State synchronization between active models                                    |
| Target model substitution    | Multi-model component exposes same external ports as individual pendulum model |
| Goal                         | Runtime reduction with acceptable accuracy loss                                |

## Main Differences

| Aspect                 | Choi et al. (2014)                                                                         | syssimx |
| ---------------------- | ------------------------------------------------------------------------------------------ | ------- |
| Simulation domain      | Continuous and discrete event systems                                                      |         |
| Formalism              | Continuous model formalism and DEVS-style discrete event modeling                          |         |
| Tool integration       | Assumes reusable existing models in one simulation setting                                 |         |
| syssimx extension      | Heterogeneous co-simulation with FMUs, OpenSim, and FEM/NGSolve                            |         |
| Event handling         | Fidelity switching based on Interest Region / FCC                                          |         |
| syssimx event handling | Hybrid event indicators, rollback, bisection-based event localization, event propagation   |         |
| State transfer         | State copy between internal models                                                         |         |
| syssimx state transfer | Tool-specific state reconstruction and synchronization                                     |         |
| Main contribution      | Multi-fidelity M&S methodology for simulation speedup                                      |         |
| syssimx contribution   | Framework architecture for heterogeneous hybrid co-simulation with runtime model switching |         |

The paper provides a strong conceptual basis for your runtime-switching idea, but it does not solve the tool-coupling problem addressed by syssimx: integrating FMUs, OpenSim, and FEM models under one co-simulation interface.

---

## Compact Thesis-Ready Summary

```markdown
Choi, Lee, and Kim (2014) propose a multi-fidelity modeling and simulation methodology for accelerating simulation-based analyses. Their method targets scenarios in which a high-fidelity submodel is executed frequently and contributes a large share of the total simulation time. Instead of using this high-fidelity model throughout the entire simulation, the method defines an Interest Region in which high-fidelity accuracy is required and uses lower-fidelity models outside that region.

The methodology consists of four steps: target model selection and Interest Region definition, low-fidelity model development, multi-fidelity model composition, and substitution of the selected target model. The composed multi-fidelity model contains several internal models of different fidelity and a Selection Model. This Selection Model evaluates a Fidelity Change Condition derived from the Interest Region Variable and switches between internal models during simulation. If a model change is required, it copies the state from the current model to the newly activated model so that the simulation can continue.

The paper demonstrates the methodology on a torpedo tactics simulation and a vehicle allocation simulation. The reported results show that simulation speed can be increased with limited accuracy loss, provided that the selected target model has a high execution-time ratio, the low-fidelity model is sufficiently cheap, the Interest Region is chosen appropriately, and switching overhead remains small.

For this thesis, the paper is relevant because it provides a direct conceptual precedent for runtime model switching. The multi-model component in \syssimx{} follows a similar principle: a high-fidelity FEM model is activated only in the contact-relevant region, while cheaper models are used elsewhere. In contrast to Choi et al., \syssimx{} applies this idea to heterogeneous hybrid co-simulation, where alternative subsystem models may originate from different tools and require explicit state synchronization across FMU, OpenSim, and FEM backends.
```

## Possible Thesis Sentence

```latex
The runtime model-switching mechanism in \syssimx{} is conceptually related to the multi-fidelity M\&S methodology of Choi et al., in which a high-fidelity target model is replaced by a composed multi-fidelity model that switches between internal models according to a fidelity change condition. While their approach focuses on preserving model reusability and simulation speedup within continuous and discrete event systems, \syssimx{} extends the idea to heterogeneous hybrid co-simulation by coordinating tool-specific models from FMI, OpenSim, and FEM backends through a common component interface.
```

[1]: https://www.researchgate.net/publication/266658864_Multi-fidelity_modeling_simulation_methodology_for_simulation_speed_up "(PDF) Multi-fidelity modeling & simulation methodology for simulation speed up"
[2]: https://dl.acm.org/doi/10.1145/2601381.2601385?utm_source=chatgpt.com "Multi-fidelity modeling & simulation methodology for ..."