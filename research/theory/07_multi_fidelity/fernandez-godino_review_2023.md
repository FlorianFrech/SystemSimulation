Fernández-Godino, M. G. (2023). Review of multi-fidelity models. *Advances in Computational Science and Engineering*, *1*(4), 351–400. [https://doi.org/10.3934/acse.2023015](https://doi.org/10.3934/acse.2023015)

# Summary — Fernández-Godino (2023): *Review of Multi-Fidelity Models*

**Reference:** Fernández-Godino, M. G. (2023). *Review of multi-fidelity models*. *Advances in Computational Science and Engineering*, 1(4), 351–400. The paper reviews multi-fidelity modeling methods for computational science and engineering, especially for optimization and uncertainty quantification. ([aimsciences.org][1])

---

## 1. Core Motivation

High-fidelity models provide accurate predictions but are often too expensive for repeated use in design optimization, uncertainty quantification, parameter studies, or real-time decision workflows. Low-fidelity models are cheaper but less accurate because they may use simplified physics, reduced dimensionality, coarser grids, linearization, reduced geometry complexity, or partially converged numerical solutions. 

The central idea of **multi-fidelity modeling** is to combine information from both low- and high-fidelity models to obtain predictions that are **close to high-fidelity accuracy** at **substantially reduced computational cost**. ([aimsciences.org][1])

---

## 2. Main Definitions

| Term                                         | Meaning                                                                                                                                        |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| **High-fidelity model (HFM)**                | A model that provides the required accuracy for the task, usually at high computational or experimental cost.                                  |
| **Low-fidelity model (LFM)**                 | A cheaper but less accurate model, relative to the HFM.                                                                                        |
| **Multi-fidelity model (MFM)**               | A model that combines information from multiple models with different accuracy levels.                                                         |
| **Surrogate model (SM)**                     | An algebraic or statistical approximation fitted to expensive model data.                                                                      |
| **Multi-fidelity surrogate model (MFSM)**    | A surrogate model that explicitly combines data from multiple fidelity levels.                                                                 |
| **Multi-fidelity hierarchical model (MFHM)** | A method that uses different fidelity levels according to a criterion, without necessarily constructing one explicit multi-fidelity surrogate. |

The paper emphasizes that fidelity is **relative**: a model is only high- or low-fidelity compared with another model. 

---

## 3. Sources of Fidelity Differences

The paper identifies several reasons why one model may have lower fidelity than another:

* **Dimensionality reduction**, e.g. 3D model → 2D or 1D model.
* **Grid or mesh coarsening**, e.g. coarse FEM/CFD discretization instead of fine discretization.
* **Simplified physics**, e.g. rigid-body instead of deformable-body dynamics.
* **Linearization**, e.g. linear elastic instead of nonlinear material behavior.
* **Reduced geometry complexity**, e.g. simplified CAD or idealized domain.
* **Partial convergence**, e.g. stopping an iterative solver before full convergence.
* **Simulation vs. experiment**, where experiments are often treated as the highest-fidelity reference. ([aimsciences.org][1])

For your thesis, this maps well to the distinction between a cheap rigid-body pendulum model and a more expensive FEM contact model.

---

## 4. Two Main Multi-Fidelity Strategies

## 4.1 Multi-Fidelity Surrogate Models

In **multi-fidelity surrogate modeling**, data from low- and high-fidelity models are fused into one surrogate model. The low-fidelity model provides many cheap samples, while the high-fidelity model provides fewer but more accurate correction points.

Common correction strategies include:

* **Additive correction**:
  The surrogate learns the discrepancy between low- and high-fidelity outputs.

* **Multiplicative correction**:
  The low-fidelity result is scaled to better match high-fidelity data.

* **Comprehensive correction**:
  Additive and multiplicative corrections are combined.

* **Space mapping**:
  The input or design space of the low-fidelity model is transformed so that it better aligns with high-fidelity behavior.

The paper reports that multi-fidelity surrogate models dominate much of the reviewed literature; in the preprint text, 67% of the surveyed papers are classified as MFSMs. 

---

## 4.2 Multi-Fidelity Hierarchical Models

In **multi-fidelity hierarchical modeling**, different fidelity levels are selected during the computational process according to a rule or criterion. The model does not necessarily build one explicit combined surrogate.

Typical examples include:

* using the low-fidelity model for screening,
* using the high-fidelity model only near promising regions,
* switching fidelity levels adaptively during optimization,
* using low-fidelity models for sampling or proposal generation,
* using high-fidelity evaluations to correct or validate selected results.

This category is especially relevant for your thesis because your runtime model switching is closer to a **hierarchical fidelity-management strategy** than to a classical multi-fidelity surrogate model.

---

## 5. Application Areas

The review focuses strongly on applications where repeated model evaluations are required, especially:

* design optimization,
* uncertainty quantification,
* robust design,
* aerodynamic optimization,
* structural mechanics,
* multiphysics simulation,
* simulation-based engineering design,
* scientific machine learning and neural-network-based surrogate modeling.

The paper states that optimization is the most common application area in the reviewed literature; the preprint version reports optimization in about 70% of the reviewed publications. 

---

## 6. Main Findings

The paper’s main conclusions are:

1. **Multi-fidelity modeling is useful when high-fidelity evaluations are too expensive.**
   It is most beneficial when the low-fidelity model is much cheaper and still sufficiently correlated with the high-fidelity model.

2. **Cost savings are problem-dependent.**
   A cheap low-fidelity model alone does not guarantee an efficient multi-fidelity method. The correlation between fidelities and the overhead of constructing the multi-fidelity model matter.

3. **Gaussian-process-like surrogate models have become dominant.**
   The review observes a shift from older deterministic regression-based correction methods toward probabilistic surrogate methods that can quantify uncertainty. 

4. **Reporting is often insufficient.**
   Many papers do not clearly report the computational cost, accuracy, and setup effort required to assess whether the multi-fidelity method was actually beneficial. 

5. **Standardized cost-benefit reporting is necessary.**
   The paper recommends reporting the cost ratio between low- and high-fidelity models, the cost of building the multi-fidelity model, the achieved accuracy, and the savings compared with a pure high-fidelity workflow. 

---

## 7. Important Point for Your Thesis

For your syssimx thesis, the paper is useful mainly as theoretical support for the motivation behind **runtime model switching**.

However, your approach is not a classical multi-fidelity surrogate approach. You are not primarily learning a surrogate correction between low- and high-fidelity models. Instead, you orchestrate alternative subsystem models during simulation and activate the expensive FEM model only when the system state requires it.

A good distinction would be:

| Classical multi-fidelity surrogate modeling        | syssimx runtime model switching                                               |
| -------------------------------------------------- | ----------------------------------------------------------------------------- |
| Builds a surrogate from LF/HF data                 | Switches between executable subsystem models                                  |
| Often used for optimization or UQ                  | Used during time-domain co-simulation                                         |
| Combines fidelities statistically or algebraically | Combines fidelities operationally through the master algorithm                |
| Accuracy depends on surrogate quality              | Accuracy depends on state transfer, switching criteria, and model consistency |
| Cost savings come from fewer HF evaluations        | Cost savings come from activating HF models only in relevant phases           |

---

## 8. Compact Thesis-Relevant Summary

```markdown
Fernández-Godino (2023) reviews multi-fidelity modeling as a strategy for combining models of different accuracy and computational cost. High-fidelity models provide accurate predictions but are often too expensive for repeated use, while low-fidelity models reduce cost through simplifications such as coarser discretization, reduced dimensionality, simplified physics, linearization, or partial convergence. Multi-fidelity methods aim to exploit the low cost of simplified models while retaining the accuracy of high-fidelity information.

The paper distinguishes two main families of approaches. Multi-fidelity surrogate models explicitly fuse low- and high-fidelity data into one surrogate model, for example by additive correction, multiplicative correction, comprehensive correction, space mapping, co-kriging, or Gaussian-process-based methods. Multi-fidelity hierarchical models instead use different fidelity levels according to a selection criterion, without necessarily constructing an explicit combined surrogate. The latter is closer to runtime model switching, where a computationally expensive model is activated only when its additional accuracy is required.

The review emphasizes that the benefit of multi-fidelity modeling is highly problem-dependent. Cost savings require not only a cheap low-fidelity model, but also sufficient agreement between fidelity levels and a favorable balance between modeling overhead, accuracy gain, and runtime reduction. For this reason, the paper recommends reporting cost ratios, accuracy comparisons, and the effort required to construct the multi-fidelity workflow.
```

---

## Relevance Sentence for syssimx

```latex
The runtime model-switching mechanism in \syssimx{} can be interpreted as a hierarchical multi-fidelity strategy: inexpensive subsystem models are used during phases in which their accuracy is sufficient, while a higher-fidelity FEM model is activated only near contact, where local structural behavior becomes relevant.
```

[1]: https://www.aimsciences.org/article/doi/10.3934/acse.2023015 "Review of multi-fidelity models"