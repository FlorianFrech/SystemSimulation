# Williams & Alleyne (2014): Switched-Fidelity Modeling and Optimization for Multi-Physics Dynamical Systems

**Reference:** Williams, M. A., & Alleyne, A. G. (2014). *Switched-fidelity modeling and optimization for multi-physics dynamical systems*. American Control Conference, Portland, Oregon.

## 1. Core Motivation

Williams and Alleyne address a common problem in large-scale multi-physics simulation: high-fidelity subsystem models provide better accuracy but are often too expensive to run over an entire system simulation. Low-fidelity models reduce computational cost, but they may introduce significant errors, especially during transient operating phases. The paper proposes **switched-fidelity modeling**, where the active model fidelity is changed during simulation to balance accuracy and execution speed. 

The motivating application is a **vapor compression system**. The fidelity of the evaporator model is controlled by the number of finite volumes used in the heat-exchanger discretization: more volumes yield a higher-fidelity but slower model; fewer volumes yield a lower-fidelity but faster model. 

---

## 2. Main Idea

The paper’s main idea is to avoid running the high-fidelity model during the full simulation. Instead, the simulation should use:

| Simulation phase                      | Active model        |
| ------------------------------------- | ------------------- |
| Quasi-steady or low-impact phases     | Low-fidelity model  |
| Transient or accuracy-critical phases | High-fidelity model |

The high-fidelity model is activated when incoming reference or disturbance signals indicate that a transient event is about to occur. After the transient has been captured, the system switches back to the low-fidelity model.

This differs from classical multi-fidelity surrogate modeling because the paper does not construct a surrogate correction. It instead performs **runtime switching between executable models of different fidelity**.

---

## 3. Switched-Fidelity Architecture

The proposed architecture contains:

1. **Reference/disturbance signals**
2. **A signal delay**
3. **A supervisor**
4. **A switched-fidelity system**
5. **A high/low fidelity selection signal**

The exogenous signals are first sent to a **supervisor**, which decides whether high-fidelity mode is required. The same signals are delayed before being applied to the actual system, so that the model can switch to high-fidelity mode *before* the physical transient reaches the subsystem. 

This is a **non-causal preview strategy**: the supervisor sees the input change before the simulated component receives it.

---

## 4. Switching Supervisor

The supervisor consists of three elements:

| Element                               | Function                                             |
| ------------------------------------- | ---------------------------------------------------- |
| **High-pass filter**                  | Detects relevant changes in exogenous signals        |
| **Filter gain** (K_{\mathrm{filter}}) | Sets the sensitivity of the switch trigger           |
| **Dwell time** (t_{\mathrm{dwell}})   | Keeps the high-fidelity model active after a trigger |

### 4.1 High-Pass Filter

The filter is used to detect significant changes in reference or disturbance signals. It relates the rate and magnitude of input changes to a trigger signal. The filter has the form:

$$
\frac{\omega_n^2 s}{s^2 + 2\zeta \omega_n s + \omega_n^2}
$$

The damping ratio is bounded in the paper as:

$$
0.75 \leq \zeta \leq 1.10
$$

This is intended to avoid false high-fidelity triggers caused by filter overshoot.

---

### 4.2 Filter Gain Logic

The filter output is scaled by $(K_{\mathrm{filter}})$ and compared against a threshold:

$$
y_2 =
\begin{cases}
1, & \text{if } |y_{\mathrm{filter}} K_{\mathrm{filter}}| \geq 1 \
0, & \text{if } |y_{\mathrm{filter}} K_{\mathrm{filter}}| < 1
\end{cases}
$$

A larger $(K_{\mathrm{filter}})$ makes the supervisor more sensitive. Smaller exogenous changes can then trigger high-fidelity mode. 

---

### 4.3 Dwell Time

The dwell time avoids switching immediately back to the low-fidelity model. Once a high-fidelity trigger occurs at time $(t_{\mathrm{switch}})$, high-fidelity mode is maintained until:

$$
t_{\mathrm{sim}} \geq t_{\mathrm{switch}} + t_{\mathrm{dwell}}
$$

The supervisor output is:

$$
y_3 =
\begin{cases}
1, & \text{if } y_2 = 1 \
1, & \text{if } t_{\mathrm{sim}} < t_{\mathrm{dwell}} + t_{\mathrm{switch}} \text{ and } y_2 = 0 \
0, & \text{if } t_{\mathrm{sim}} \geq t_{\mathrm{dwell}} + t_{\mathrm{switch}} \text{ and } y_2 = 0
\end{cases}
$$

Thus, (t_{\mathrm{dwell}}) determines how long the expensive model remains active after a detected disturbance. 

---

## 5. State Transfer Between Fidelity Levels

A key technical issue is the transition between low- and high-fidelity models.

When switching from low to high fidelity, the low-fidelity model state is used to initialize the high-fidelity model. Because the high-fidelity evaporator has more finite volumes, its internal states are initialized by **linear interpolation** from the low-fidelity states. When switching back from high to low fidelity, the low-fidelity states are reset analogously. 

The paper explicitly notes that switching introduces transient effects due to state reinitialization. Therefore, the exogenous signals are delayed by a fixed time to allow these switching transients to settle before the high-fidelity output is handed to the system. 

This is one of the most relevant points for `syssimx`: runtime model switching is not only a selection problem; it is also a **state-consistency problem**.

---

## 6. Output Selection and Error Definition

The switched-fidelity system output is selected from either the high- or low-fidelity model:

$$
y_{\mathrm{sys}} =
\begin{cases}
y_{\mathrm{high\ fidelity}}, & \text{if } y_3 = 1 \
y_{\mathrm{low\ fidelity}}, & \text{if } y_3 = 0
\end{cases}
$$

The accumulated error is measured relative to the high-fidelity model:

$$
e_{\mathrm{acc}}
=
\int_0^{t_f}
\left|
y_{\mathrm{high\ fidelity}} - y_{\mathrm{sys}}
\right|
, dt
$$

The high-fidelity model is therefore treated as the accuracy reference.

For the evaporator example, two outputs are analyzed:

* primary flow exit pressure,
* secondary flow exit temperature.

These are important because they may be used as inputs to other coupled components or systems.

---

## 7. Accuracy-Speed Tradeoff

The paper studies how $(K_{\mathrm{filter}})$ and $(t_{\mathrm{dwell}})$ affect both accumulated error and simulation runtime.

The main trends are:

| Parameter change                                            | Effect                                       |
| ----------------------------------------------------------- | -------------------------------------------- |
| Increase $(K_{\mathrm{filter}})$                              | More disturbances trigger high-fidelity mode |
| Increase $(t_{\mathrm{dwell}})$                               | High-fidelity mode remains active longer     |
| Larger $(K_{\mathrm{filter}})$, larger $(t_{\mathrm{dwell}})$   | Lower error, higher computational cost       |
| Smaller $(K_{\mathrm{filter}})$, smaller $(t_{\mathrm{dwell}})$ | Higher speed, larger error                   |

The paper finds that, for the evaporator example, $(t_{\mathrm{dwell}})$ has a stronger influence than $(K_{\mathrm{filter}})$. The reason is that capturing the full transient matters more than activating high-fidelity mode for very small disturbances. 

---

## 8. Optimization of Switching Parameters

The switching parameters are selected by solving an optimization problem that balances accuracy and computational cost.

The objective function is:

$$
J
=

\lambda
\left[
\sum_{i=1}^{n}
\gamma_i
\int_0^{t_f}
e_{\mathrm{acc},i}
, dt
\right]
+
(1-\lambda)
\frac{t_{\mathrm{real}}}{t_{\mathrm{sim}}}
$$

where:

| Symbol               | Meaning                                           |
| -------------------- | ------------------------------------------------- |
| ($\lambda$)            | weighting between accuracy and computational cost |
| ($\gamma_i$)           | scaling factor for the error of output (i)        |
| ($e_{\mathrm{acc},i}$) | accumulated error of output (i)                   |
| ($t_{\mathrm{real}}$)  | wall-clock time required for simulation           |
| ($t_{\mathrm{sim}}$)   | simulated time                                    |

For the evaporator case, the paper uses:

$$
\lambda = 0.55
$$

and considers two outputs, so $n = 2$. The optimization is performed with MATLAB `fmincon`.

The optimal parameters reported in the results section are:

$$
K_{\mathrm{filter}} = 0.26,
\qquad
t_{\mathrm{dwell}} = 80,\mathrm{s}
$$

For these values, the switched-fidelity evaporator model achieves a reported speed increase of **56%** over the isolated high-fidelity model and reduces accumulated error compared with the isolated low-fidelity model. 

The abstract reports a speed increase of **64%** from the high-fidelity baseline, with accumulated error reductions of **69%** for secondary flow exit temperature and **76%** for primary flow exit pressure compared with the low-fidelity baseline. 

---

## 9. Main Results

The main reported results are:

| Quantity                                   |                         Reported result |
| ------------------------------------------ | --------------------------------------: |
| Optimal $K_{\mathrm{filter}}$              |                                  $0.26$ |
| Optimal $t_{\mathrm{dwell}}$               |                         $80,\mathrm{s}$ |
| Speed increase in detailed results section |       (56%) over high-fidelity baseline |
| Speed increase in abstract                 |       (64%) over high-fidelity baseline |
| Pressure accumulated-error reduction       | (76%) relative to low-fidelity baseline |
| Temperature accumulated-error reduction    | (69%) relative to low-fidelity baseline |

The key result is not only that switching improves speed, but that it can simultaneously improve accuracy relative to a pure low-fidelity model.

---

## 10. Limitations and Future Work

The authors explicitly state that the presented method is demonstrated for a **single component**. Extension to larger system-level simulations with interconnected components and multiple time scales is identified as future work. 

The main limitation is that switching is based only on **exogenous signals**. Because these signals are delayed before reaching the system, the method cannot directly trigger fidelity changes based on endogenous signals exchanged between interconnected subsystems. The authors identify the analysis of endogenous inter-subsystem signals as necessary future work. 

This limitation is central for your thesis because `syssimx` operates at system level, where switching can be triggered by simulation states, contact indicators, event indicators, or coupling variables.

---

# Relevance for `syssimx`

## 1. Direct Relevance

Williams and Alleyne are highly relevant for the **runtime model switching** part of `syssimx`.

| Williams & Alleyne concept                   | `syssimx` counterpart                                     |
| -------------------------------------------- | --------------------------------------------------------- |
| High-fidelity evaporator model               | FEM pendulum/contact model                                |
| Low-fidelity evaporator model                | FMU/OpenSim/rigid-body pendulum model                     |
| Switched-fidelity component                  | `MultiModelComponent`                                     |
| Supervisor                                   | Switching logic / mode-selection logic                    |
| (K_{\mathrm{filter}})                        | Switching sensitivity threshold                           |
| (t_{\mathrm{dwell}})                         | Minimum active duration / hysteresis-like switching guard |
| Exogenous preview signal                     | Reference signal or known external command                |
| State interpolation between fidelities       | State transfer between active models                      |
| Accumulated error vs. high-fidelity baseline | Error against FEM or monolithic reference                 |
| Speed-accuracy optimization                  | Evaluation of runtime reduction vs. state/output error    |

---

## 2. Strong Similarities to `syssimx`

The paper supports several design ideas that also appear in `syssimx`:

1. **Fidelity should change during simulation, not only before simulation.**
   This directly supports runtime model switching.

2. **High-fidelity models should be active only when their accuracy matters.**
   In `syssimx`, the FEM model is activated near contact rather than during the full pendulum trajectory.

3. **State transfer is central.**
   Switching is only meaningful if the target model can be initialized consistently from the previous active model.

4. **Switching causes transients.**
   Williams and Alleyne explicitly account for switching transients by delaying exogenous signals. In `syssimx`, this motivates measuring state-transfer error and checking continuity at switching points.

5. **The switching rule affects both accuracy and computational cost.**
   This supports evaluating switching criteria quantitatively instead of treating them as arbitrary thresholds.

---

## 3. Key Differences to `syssimx`

| Aspect                   | Williams & Alleyne (2014)                                                                     | `syssimx` |
| ------------------------ | --------------------------------------------------------------------------------------------- | --------- |
| Scope                    | Single switched component                                                                     |           |
| System level             | Future work                                                                                   |           |
| Switching trigger        | Exogenous preview signals                                                                     |           |
| `syssimx` trigger        | Endogenous state/event/contact conditions possible                                            |           |
| Model family             | Same physical component with different discretization levels                                  |           |
| `syssimx` model family   | Different simulation backends: FMU, OpenSim, FEM                                              |           |
| State transfer           | Interpolation between finite-volume states                                                    |           |
| `syssimx` state transfer | Tool-specific reconstruction of angle, velocity, and internal state                           |           |
| Coupling                 | Not focused on heterogeneous co-simulation                                                    |           |
| `syssimx` coupling       | System-level co-simulation with master algorithms                                             |           |
| Events                   | Not formulated as hybrid event handling                                                       |           |
| `syssimx` events         | Event indicators, rollback, bisection localization, event propagation                         |           |
| Optimization             | Optimizes switching parameters                                                                |           |
| `syssimx`                | Demonstrates runtime switching and measures runtime/accuracy; optimization can be future work |           |

---

## 4. Relation to the `syssimx` Contribution

The paper is useful because it provides a direct precedent for the claim that runtime model switching can improve the cost-accuracy tradeoff in dynamic simulation. However, `syssimx` extends the idea in several ways:

1. **From component-level to system-level orchestration**
   Williams and Alleyne switch fidelity inside one component. `syssimx` embeds model switching into a heterogeneous co-simulation framework.

2. **From exogenous preview to endogenous events**
   The paper relies on known future input signals and delays. `syssimx` can use state-dependent switching criteria such as contact indicators.

3. **From same-model discretization to heterogeneous backends**
   Williams and Alleyne switch between models of the same evaporator with different finite-volume resolutions. `syssimx` switches between models implemented through different tools and abstractions.

4. **From signal-based switching to hybrid co-simulation**
   `syssimx` connects switching to event handling, rollback, and state synchronization across components.

---

# Compact Thesis-Ready Summary

Williams and Alleyne (2014) propose a switched-fidelity modeling approach for multi-physics dynamical systems. Their motivation is that high-fidelity subsystem models improve accuracy but are too expensive for full system simulations, while low-fidelity models reduce computational cost at the expense of accuracy. The proposed method dynamically changes the active component model during simulation to achieve a better balance between speed and accuracy. The method is demonstrated on a finite-volume evaporator model in a vapor compression system, where fidelity is varied through the number of finite volumes. 

The switching architecture uses a supervisor that analyzes exogenous reference or disturbance signals. These signals are delayed before entering the simulated system so that the supervisor can switch to high-fidelity mode before the transient reaches the component. The supervisor consists of a high-pass filter, a sensitivity gain (K_{\mathrm{filter}}), and a dwell time (t_{\mathrm{dwell}}). The filter detects relevant input changes, (K_{\mathrm{filter}}) determines which disturbance magnitudes trigger high-fidelity mode, and (t_{\mathrm{dwell}}) keeps the high-fidelity model active long enough to capture the transient response. 

The paper evaluates the tradeoff between accumulated output error and computational cost. Accumulated error is computed relative to the high-fidelity model, while computational cost is measured using the ratio of real simulation time to simulated time. An optimization problem is formulated to select (K_{\mathrm{filter}}) and (t_{\mathrm{dwell}}). For the evaporator example, the optimized parameters are (K_{\mathrm{filter}} = 0.26) and (t_{\mathrm{dwell}} = 80,\mathrm{s}). With these values, the switched-fidelity model achieves a reported speed increase of (56%) over the isolated high-fidelity model and reduces accumulated error compared with the isolated low-fidelity model. The abstract reports a (64%) speed increase, a (69%) accumulated-error reduction for secondary flow exit temperature, and a (76%) reduction for primary flow exit pressure. 

For this thesis, the paper is relevant because it provides a direct conceptual precedent for runtime model switching. The `MultiModelComponent` in `syssimx` follows the same general principle: a high-fidelity model is activated only during phases where its additional accuracy is required, while cheaper models are used elsewhere. In contrast to Williams and Alleyne, `syssimx` applies this idea at the level of heterogeneous hybrid co-simulation. The active models may come from different simulation tools, such as FMI-based Modelica models, OpenSim models, and FEM/NGSolve models, and switching can be triggered by endogenous simulation states or events rather than only by delayed exogenous input signals.

# Possible Thesis Sentence

```latex
Williams and Alleyne propose switched-fidelity modeling as a runtime strategy for balancing simulation speed and accuracy by activating a high-fidelity component model only during transient phases detected from exogenous signals. This supports the motivation for the runtime model-switching mechanism in \syssimx{}, while the present framework extends the idea from a single switched component to heterogeneous hybrid co-simulation with tool-specific FMU, OpenSim, and FEM backends, endogenous event-based switching, and explicit state transfer between alternative subsystem models.
```