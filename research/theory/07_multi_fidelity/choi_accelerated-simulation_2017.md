Choi, S. H., Seo, K.-M., & Kim, T. G. (2017). Accelerated Simulation of Discrete Event Dynamic Systems via a Multi-Fidelity Modeling Framework. Applied Sciences, 7(10). https://doi.org/10.3390/app7101056

# Summary — Choi, Seo & Kim (2017): *Accelerated Simulation of Discrete Event Dynamic Systems via a Multi-Fidelity Modeling Framework*

**Reference:** Choi, S. H., Seo, K.-M., & Kim, T. G. (2017). *Accelerated Simulation of Discrete Event Dynamic Systems via a Multi-Fidelity Modeling Framework*. *Applied Sciences*, 7(10), 1056.

## 1. Core Motivation

The paper addresses the high computational cost of simulation-based analysis, especially when many repeated simulations are required for “what-if” studies across many input combinations. The authors propose a **multi-fidelity modeling framework** that accelerates simulations by using high-fidelity models only in important parts of a simulation scenario and lower-fidelity models elsewhere. ([mdpi.com][1])

The target systems are **discrete event dynamic systems**, i.e. systems that combine dynamic behavior with state changes triggered by discrete events. The paper argues that this structure is well suited for runtime fidelity switching because dynamic models often admit different fidelity levels, while discrete events provide natural switching points. ([mdpi.com][1])

---

## 2. Main Idea

The key idea is **condition-based switching between high- and low-fidelity models during one simulation run**.

Instead of running the high-fidelity model for the entire scenario, the simulation is divided into:

| Scenario region                    | Model choice         |
| ---------------------------------- | -------------------- |
| **Interest region**                | High-fidelity model  |
| **Marginal / non-interest region** | Lower-fidelity model |

An **interest region** is the part of the scenario where the target model output has a strong effect on the final simulation result. The high-fidelity model is used inside this region; cheaper models are used outside it. ([mdpi.com][1])

This is close to your syssimx idea: use the expensive FEM model only near contact and use cheaper pendulum models elsewhere.

---

## 3. Formal Concepts

The paper introduces three central concepts.

| Concept                             | Meaning                                                                                                                            |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| **Interest Region**                 | Region of the simulation scenario where high-fidelity accuracy is important.                                                       |
| **Interest Region Variable (IRV)**  | Input or state variable used to decide whether the system is inside the interest region.                                           |
| **Fidelity Change Condition (FCC)** | Logical condition that determines when the active fidelity level must change.                                                      |
| **Selection Model**                 | Supervisory model that routes inputs to the currently active model and activates another fidelity model when the FCC is satisfied. |

The selection model is responsible for deciding whether the current internal model remains active or whether another model should be activated. It also transfers state information so that the simulation can continue after switching. ([mdpi.com][1])

---

## 4. Proposed Framework

The framework consists of five steps:

1. **Target model selection**
   Select a frequently executed and computationally expensive submodel.

2. **Interest region definition**
   Define where high-fidelity accuracy is needed.

3. **Lower-fidelity model design**
   Derive cheaper models from the selected high-fidelity model.

4. **Multi-fidelity model composition**
   Combine the different fidelity models with a selection model.

5. **Selected target model substitution**
   Replace the original high-fidelity submodel with the composed multi-fidelity model.

The composed multi-fidelity model has the same input and output variables as the original target model. This allows the multi-fidelity model to replace the high-fidelity model without modifying the surrounding simulation model or simulation engine. ([mdpi.com][1])

---

## 5. Lower-Fidelity Model Construction

For dynamic systems, the paper proposes two methods for deriving lower-fidelity models from a high-fidelity model:

| Method          | Description                                                                                   |
| --------------- | --------------------------------------------------------------------------------------------- |
| **Elimination** | Remove terms from the state-transition function that have only minor influence on the output. |
| **Projection**  | Fix or approximate selected variables in the state-transition function.                       |

The authors apply these ideas to a UUV maneuvering model, where the high-fidelity model computes six-degree-of-freedom motion. Lower-fidelity models are obtained by simplifying the differential equations. ([mdpi.com][1])

For discrete-event systems, the lower-fidelity model can simplify event behavior or time-advance logic. In the UTV case study, the high-fidelity model computes shortest paths with Dijkstra’s algorithm, whereas the low-fidelity model approximates travel distance using Euclidean distance. ([mdpi.com][1])

---

## 6. Selection Model and Runtime Switching

The **selection model** acts as a supervisor around the internal models of different fidelities.

Its responsibilities are:

* receive external inputs,
* forward inputs to the currently active model,
* monitor the fidelity change condition,
* receive and store state information from the active model,
* activate another model when the fidelity level must change,
* pass the copied state and input to the newly activated model.

For dynamic-system models, the selection model is specified in a DTSS-like form. For discrete-event systems, it is specified in DEVS and includes explicit activation and stop events. ([mdpi.com][1])

This is highly relevant to syssimx because it resembles the idea of a **multi-model component** that selects one active internal model while preserving the external interface.

---

## 7. Application Case Studies

## 7.1 UUV Case Study

The first case study simulates an **unmanned underwater vehicle (UUV)** that tracks and attacks a target. The target model for fidelity switching is the maneuver submodel, because it has high computational cost and is executed continuously. The interest region is defined using a Boolean detection variable: after the UUV detects the target, accurate maneuvering becomes important. ([mdpi.com][1])

The multi-fidelity model uses the high-fidelity maneuver model when the target has been detected and a lower-fidelity maneuver model otherwise. The reported result is a speedup of about **1.25×** without significant loss of the success-rate accuracy. ([mdpi.com][1])

## 7.2 UTV Case Study

The second case study simulates **urban transportation vehicles (UTVs)**. The goal is to evaluate passenger waiting time and vehicle utilization. The expensive target model is the UTV routing model, because it repeatedly computes shortest paths. ([mdpi.com][1])

The high-fidelity model uses Dijkstra’s algorithm, while the low-fidelity model uses Euclidean distance. The interest region is defined by the expected travel distance. A threshold is selected experimentally by balancing execution time against accuracy loss. With a permitted accuracy loss below 5%, the selected distance threshold is 2000. ([mdpi.com][1])

The reported speedup is about **1.21×**. The speedup is lower than in the UUV case because the UTV model switches fidelity more frequently, and switching introduces overhead. ([mdpi.com][1])

---

## 8. Main Findings

The paper reports that the proposed framework accelerates the two case studies by about **1.25×** and **1.21×**, respectively, with no significant accuracy loss. The authors also emphasize that the multi-fidelity model can replace the original target model while reusing the surrounding models and simulation engine. ([mdpi.com][1])

A central conclusion is that performance depends on:

* selecting a target model that consumes a large share of execution time,
* defining meaningful interest regions,
* developing sufficiently accurate lower-fidelity models,
* minimizing the overhead of the selection function,
* avoiding excessive model switching frequency. ([mdpi.com][1])

The paper also states that formalizing the derivation of lower-fidelity models remains future work. The framework is the main contribution; the transformation methods are only partly formalized. ([mdpi.com][1])

---

# Relevance for syssimx

This paper is more directly relevant to your thesis than classical multi-fidelity surrogate papers because it deals with **runtime fidelity switching inside a simulation scenario**.

## Strong Similarities

| Choi et al. concept             | syssimx counterpart                                                       |
| ------------------------------- | ------------------------------------------------------------------------- |
| High-fidelity model             | FEM pendulum/contact model                                                |
| Lower-fidelity model            | FMU/OpenSim/rigid-body pendulum model                                     |
| Interest region                 | Contact-near region                                                       |
| Interest region variable        | Distance to wall / contact indicator / gap function                       |
| Fidelity change condition       | Runtime switching criterion                                               |
| Selection model                 | `MultiModelComponent` / active-model selection                            |
| Target model substitution       | Replace one subsystem by a multi-model subsystem with same external ports |
| State transfer during switching | Synchronization of angle, angular velocity, and model state               |

The most useful conceptual link is this: **the expensive model does not need to be active over the entire simulation scenario**. It should be active only where its additional fidelity affects the relevant outputs.

---

## Main Differences to syssimx

| Aspect             | Choi et al. (2017)                                 | syssimx                                                                                 |
| ------------------ | -------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Target formalism   | DTSS and DEVS                                      | Heterogeneous co-simulation components                                                  |
| Model types        | Formal discrete-time / discrete-event models       | FMUs, OpenSim models, FEM/NGSolve models, Python components                             |
| Switching trigger  | Interest region / FCC                              | Event indicators, contact conditions, switching criteria                                |
| State transfer     | Formal state copying between internal models       | Tool-specific state synchronization between heterogeneous models                        |
| Simulation focus   | Discrete event dynamic systems                     | Hybrid co-simulation with continuous dynamics, algebraic loops, and heterogeneous tools |
| Main goal          | Simulation speedup with small accuracy loss        | Heterogeneous hybrid co-simulation and runtime model switching                          |
| Case studies       | UUV and urban transportation                       | Controlled pendulum with wall contact                                                   |
| Backend assumption | Same simulation formalism and engine can be reused | Different tools and solvers must be orchestrated                                        |

The paper does not address FMI, OpenSim, FEM solvers, algebraic-loop handling in co-simulation, or zero-crossing-based event localization across heterogeneous components. Its model-switching logic is conceptually close, but its technical setting is different.

---

## Compact Thesis-Ready Summary

```markdown
Choi, Seo, and Kim (2017) propose a multi-fidelity modeling framework for accelerating simulations of discrete event dynamic systems. Their central idea is to replace an expensive high-fidelity submodel by a composed multi-fidelity model that contains several internal models of different fidelity and a selection model. The selection model monitors a fidelity change condition derived from an interest region and activates the high-fidelity model only in parts of the simulation scenario where its accuracy has a strong influence on the final simulation result. Lower-fidelity models are used in marginal regions to reduce computational cost.

The framework consists of five steps: selecting a computationally expensive target model, defining the interest region, designing lower-fidelity models, composing the multi-fidelity model, and substituting the original target model. Lower-fidelity dynamic models are obtained through simplifications such as elimination of less relevant terms or projection of selected variables. The composed multi-fidelity model preserves the same external input-output interface as the original target model, allowing it to replace the original model without modifying the surrounding simulation model or simulation engine.

The paper demonstrates the method on an unmanned underwater vehicle simulation and an urban transportation vehicle simulation. The reported speedups are approximately 1.25 and 1.21, respectively, with no significant loss of accuracy. The results also show that excessive switching frequency can reduce the benefit because model exchange introduces overhead.

For the present thesis, the paper is relevant because it provides a direct conceptual precedent for runtime fidelity switching within a single simulation scenario. The runtime model switching implemented in \syssimx{} follows a similar principle: a cheap model is used during phases in which it is sufficiently accurate, while the expensive FEM model is activated only near contact. In contrast to Choi et al., \syssimx{} applies this idea to heterogeneous hybrid co-simulation, where the alternative models may come from different simulation tools such as FMI-based Modelica models, OpenSim models, and FEM/NGSolve models.
```

## Possible Thesis Sentence

```latex
The runtime model-switching mechanism in \syssimx{} follows the same general principle as the interest-region-based multi-fidelity framework of Choi et al.: high-fidelity models are activated only in those parts of a simulation scenario where their additional accuracy is relevant, while lower-fidelity models are used in marginal regions to reduce computational cost. In contrast to their DTSS/DEVS-based framework for discrete event dynamic systems, \syssimx{} applies this principle to heterogeneous hybrid co-simulation with tool-specific subsystem models and state synchronization across different simulation backends.
```

[1]: https://www.mdpi.com/2076-3417/7/10/1056 "Accelerated Simulation of Discrete Event Dynamic Systems via a Multi-Fidelity Modeling Framework"