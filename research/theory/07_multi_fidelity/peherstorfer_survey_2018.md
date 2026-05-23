Peherstorfer, B., Willcox, K., & Gunzburger, M. (2018). Survey of Multifidelity Methods in Uncertainty Propagation, Inference, and Optimization. SIAM Review, 60(3), 550–591. https://doi.org/10.1137/16M1082469

# Summary — Peherstorfer, Willcox & Gunzburger (2018): *Survey of Multifidelity Methods in Uncertainty Propagation, Inference, and Optimization*

**Reference:** Peherstorfer, B., Willcox, K., & Gunzburger, M. (2018). *Survey of Multifidelity Methods in Uncertainty Propagation, Inference, and Optimization*. *SIAM Review*, 60(3), 550–591. The paper surveys multifidelity methods that combine high-fidelity and low-fidelity model evaluations to accelerate outer-loop tasks such as uncertainty propagation, statistical inference, and optimization. ([kiwi.oden.utexas.edu][1])

---

## 1. Core Motivation

The paper starts from the observation that many computational science and engineering problems have access to multiple models of the same system. These models differ in **accuracy** and **computational cost**. A high-fidelity model provides the accuracy required for the application, but repeated evaluations are often too expensive. Low-fidelity models are cheaper but less accurate. ([kiwi.oden.utexas.edu][1])

The central idea is that low-fidelity models can be used to reduce computational cost, while the high-fidelity model remains “in the loop” to preserve accuracy, convergence, or statistical guarantees. This is a key distinction from simply replacing the high-fidelity model by a reduced or simplified model. ([kiwi.oden.utexas.edu][1])

---

## 2. Basic Definition of Multifidelity Modeling

The paper represents a model as an input-output map

```text
f : Z -> Y
```

where the input describes system parameters or environmental conditions and the output contains the quantity of interest. A high-fidelity model is denoted as `f_hi`, while one or more low-fidelity models are denoted as `f_lo`. The low-fidelity models approximate the same output quantity as the high-fidelity model but with lower cost and lower accuracy. ([kiwi.oden.utexas.edu][1])

A multifidelity method therefore does not merely use “many models”; it uses multiple models of the **same input-output relationship** in a structured way.

---

## 3. Types of Low-Fidelity Models

The paper distinguishes three main types of low-fidelity models.

| Type                        | Description                                                                                              | Examples                                                                                                     |
| --------------------------- | -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| **Simplified models**       | Derived by simplifying the physics, numerical method, geometry, or solver tolerance.                     | Coarse-grid PDE models, linearized models, early stopping of iterative solvers, simplified turbulence models |
| **Projection-based models** | Reduced-order models derived by projecting the governing equations onto a low-dimensional subspace.      | Proper orthogonal decomposition, reduced basis methods, Krylov subspace models, dynamic mode decomposition   |
| **Data-fit models**         | Surrogates fitted from input-output data, often usable even when the high-fidelity model is a black box. | Polynomial interpolation, sparse grids, radial basis functions, kriging, support vector machines             |

This classification is important because the appropriate multifidelity strategy depends strongly on how the low-fidelity model was generated and how well it correlates with the high-fidelity model. ([kiwi.oden.utexas.edu][1])

---

## 4. Three Model-Management Strategies

A central contribution of the paper is the classification of multifidelity methods into three **model-management strategies**: **adaptation**, **fusion**, and **filtering**. Model management defines when different models are evaluated and how their outputs are combined. ([kiwi.oden.utexas.edu][1])

### 4.1 Adaptation

In adaptation-based methods, the low-fidelity model is corrected or improved using information from the high-fidelity model during the computation.

Typical examples:

* additive correction,
* multiplicative correction,
* Gaussian-process correction,
* adaptive reduced-order models,
* efficient global optimization with adaptive kriging models.

The goal is to make the low-fidelity model progressively more accurate in the region relevant to the outer-loop task. ([kiwi.oden.utexas.edu][1])

---

### 4.2 Fusion

In fusion-based methods, outputs from low- and high-fidelity models are combined statistically or algebraically.

Typical examples:

* control variates,
* multifidelity Monte Carlo,
* Bayesian regression,
* cokriging,
* multilevel or multifidelity stochastic collocation.

A central idea is that a large number of cheap low-fidelity evaluations can reduce variance, while a smaller number of high-fidelity evaluations anchors the estimator to the desired high-fidelity quantity. ([kiwi.oden.utexas.edu][1])

The paper emphasizes that efficiency depends on both the **cost ratio** and the **correlation** between fidelity levels. A cheap low-fidelity model is not automatically useful; it must be sufficiently correlated with the high-fidelity model. ([kiwi.oden.utexas.edu][1])

---

### 4.3 Filtering

In filtering-based methods, the low-fidelity model is evaluated first and decides whether a high-fidelity evaluation is necessary.

Typical examples:

* two-stage MCMC,
* multifidelity importance sampling,
* low-fidelity screening before high-fidelity evaluation,
* greedy selection of points for high-fidelity stochastic collocation.

This strategy is closest to the intuition of “only use the expensive model when needed.” ([kiwi.oden.utexas.edu][1])

---

## 5. Main Application Areas

The paper focuses on three outer-loop applications.

| Application                 | Multifidelity role                                                                                                                                          |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Uncertainty propagation** | Estimate statistics of high-fidelity model outputs more cheaply, often using Monte Carlo, control variates, importance sampling, or stochastic collocation. |
| **Statistical inference**   | Reduce the cost of Bayesian inverse problems and MCMC by using low-fidelity models to pre-screen or approximate expensive likelihood evaluations.           |
| **Optimization**            | Use low-fidelity models to accelerate the search while retaining convergence or optimality with respect to the high-fidelity model.                         |

These are called **outer-loop** applications because they require many repeated model evaluations. ([kiwi.oden.utexas.edu][1])

---

## 6. Uncertainty Propagation

In uncertainty propagation, uncertain inputs are modeled as random variables, and the goal is to estimate statistics of the high-fidelity output, such as mean or variance. A plain Monte Carlo estimator may require many high-fidelity evaluations, making it expensive. ([kiwi.oden.utexas.edu][1])

Multifidelity uncertainty propagation reduces cost by shifting many evaluations to low-fidelity models while using enough high-fidelity evaluations to retain unbiasedness or accuracy. Important methods include:

* multifidelity Monte Carlo,
* control variates,
* importance sampling,
* stochastic collocation,
* multilevel or multifidelity stochastic collocation.

A key technical point is that the benefit depends on the interaction between all models, their costs, and their correlations, not only on one low-fidelity model in isolation. ([kiwi.oden.utexas.edu][1])

---

## 7. Statistical Inference

In Bayesian inference, unknown inputs are treated as random variables and inferred from noisy observations. Evaluating the likelihood often requires evaluating the high-fidelity model, which makes MCMC expensive. ([kiwi.oden.utexas.edu][1])

The paper reviews multifidelity inference methods such as:

* two-stage MCMC,
* delayed-acceptance MCMC,
* adaptive low-fidelity models during MCMC,
* Bayesian approximate error models.

In two-stage MCMC, a candidate sample is first tested using the low-fidelity model. Only candidates that pass this cheap first stage are evaluated with the high-fidelity model. ([kiwi.oden.utexas.edu][1])

The paper also discusses modeling the discrepancy between low- and high-fidelity models explicitly, for example by writing the observation model as a low-fidelity prediction plus a model-error term. ([kiwi.oden.utexas.edu][1])

---

## 8. Optimization

In optimization, repeated model evaluations are required to find an input that minimizes or maximizes an objective. If the objective is evaluated through a high-fidelity model, optimization can become computationally prohibitive. ([kiwi.oden.utexas.edu][1])

The paper distinguishes:

* **global multifidelity optimization**, where low-fidelity models help explore the full design space,
* **local multifidelity optimization**, where low-fidelity models are corrected inside a local trust-region framework,
* **optimization under uncertainty**, where each optimization iteration may itself contain an uncertainty-quantification loop.

A major theme is balancing **exploitation** of the current low-fidelity model with **exploration** through high-fidelity evaluations that improve or validate the low-fidelity approximation. ([kiwi.oden.utexas.edu][1])

---

## 9. Main Findings and Outlook

The paper concludes that multifidelity methods have become important across computational science and engineering, especially for expensive outer-loop tasks. Optimization had already used multifidelity ideas for decades, while uncertainty quantification offered substantial further opportunities because Monte Carlo and MCMC methods require many repeated evaluations. ([kiwi.oden.utexas.edu][1])

The authors also identify open challenges:

* Most methods treat the high-fidelity model as the “truth,” although it is still only an approximation.
* Relationships between models may be richer than a simple linear fidelity hierarchy.
* Multifidelity methods should be extended beyond computational models to include experimental data, expert opinion, lookup tables, and other information sources.
* Model management should decide not only which source to evaluate, but also where in the input space to evaluate it. ([kiwi.oden.utexas.edu][1])

---

# Relevance for syssimx

For your thesis, this paper is useful as a conceptual foundation for **model management across different fidelity levels**.

However, the paper mainly studies multifidelity methods for **outer-loop applications** such as uncertainty propagation, inference, and optimization. Your syssimx runtime model switching is different: it happens **inside a time-domain co-simulation**, where the active subsystem model changes during simulation according to system state or event conditions.

## Thesis-Relevant Interpretation

| Peherstorfer et al. concept | Relation to syssimx                                                    |
| --------------------------- | ---------------------------------------------------------------------- |
| High-fidelity model         | FEM contact model                                                      |
| Low-fidelity model          | Rigid-body / FMU / OpenSim pendulum model                              |
| Model management            | Runtime switching logic in `MultiModelComponent`                       |
| Filtering strategy          | Activate FEM only when contact-relevant conditions are detected        |
| Cost-accuracy tradeoff      | Use cheap model during free motion and expensive model near contact    |
| High-fidelity kept in loop  | FEM is not replaced globally; it is selectively activated where needed |

Your method is closest to a **filtering-based multifidelity strategy**, but adapted from an outer-loop setting to **state-dependent runtime model switching in co-simulation**.

---

## Compact Thesis-Ready Summary

```markdown
Peherstorfer, Willcox, and Gunzburger (2018) survey multifidelity methods that combine high- and low-fidelity model evaluations to reduce the cost of outer-loop tasks such as uncertainty propagation, statistical inference, and optimization. The key principle is that low-fidelity models are used to accelerate the computation, while the high-fidelity model remains in the loop to preserve accuracy, convergence, or statistical guarantees.

The paper classifies low-fidelity models into simplified models, projection-based reduced models, and data-fit surrogate models. It further distinguishes three model-management strategies: adaptation, fusion, and filtering. Adaptation improves a low-fidelity model using high-fidelity information; fusion combines outputs from several fidelity levels, for example through control variates or cokriging; filtering uses low-fidelity evaluations to decide when expensive high-fidelity evaluations are required.

For the present thesis, the filtering perspective is particularly relevant. Runtime model switching in \syssimx{} can be interpreted as a time-domain variant of multifidelity model management: inexpensive models are used during phases in which their accuracy is sufficient, while the expensive FEM model is activated only near contact, where additional local structural fidelity is required. Unlike the methods surveyed by Peherstorfer et al., this strategy is not used for an outer-loop optimization or uncertainty-propagation task, but inside a heterogeneous hybrid co-simulation workflow.
```

## Possible Thesis Sentence

```latex
The runtime model-switching mechanism implemented in \syssimx{} follows the general multifidelity principle of using inexpensive low-fidelity models whenever possible while keeping a high-fidelity model available for phases in which additional accuracy is required. In contrast to classical multifidelity methods for uncertainty propagation, inference, or optimization, the switching in \syssimx{} is performed inside the time-domain co-simulation loop rather than in an outer-loop sampling or optimization procedure.
```

[1]: https://kiwi.oden.utexas.edu/papers/multi-fidelity-survey-peherstorfer-willcox-gunzburger.pdf "Survey of Multifidelity Methods in Uncertainty Propagation, Inference, and Optimization"
