# Williams & Alleyne (2014): Variable Fidelity Modeling in Closed Loop Dynamical Systems

**Reference:** Williams, M. A., & Alleyne, A. G. (2014). *Variable Fidelity Modeling in Closed Loop Dynamical Systems*. Proceedings of the ASME 2014 Dynamic Systems and Control Conference, DSCC2014-6159. 

## 1. Core Motivation

Williams and Alleyne address the use of **variable-fidelity models in closed-loop dynamical systems**. In early control-system development, designers often perform many simulation iterations. High-fidelity models can capture more system dynamics, but their computational cost makes repeated design iterations expensive. Low-fidelity models are cheaper, but they may miss relevant dynamics and can lead to controller behavior that differs from the behavior obtained with high-fidelity models. 

The paper proposes a **switched-fidelity framework** that dynamically changes the active model fidelity during simulation. The goal is to preserve the system-output and control-input behavior of a high-fidelity simulation while reducing computational cost. 

---

## 2. Fidelity and Accuracy

The paper explicitly distinguishes **fidelity** from **accuracy**.

| Term         | Meaning                                                                                             |
| ------------ | --------------------------------------------------------------------------------------------------- |
| **Fidelity** | The extent to which a model can represent the behavior or physical phenomena of the real system.    |
| **Accuracy** | The degree to which a simulation result matches a reference value, measurement, or chosen standard. |

A high-fidelity model is understood as a model that captures a larger subset of the real system dynamics. A low-fidelity model captures a smaller subset of those dynamics.

The paper formulates this concept schematically as:

$$
\dot{x}_i = f_i(x), \qquad i \in N
$$

where (N) represents the full set of real system dynamics. A high-fidelity model covers a subset (H \subset N),

$$
\dot{x}_j = f_j(x), \qquad j \in H \subset N
$$

and a low-fidelity model covers a smaller subset (\Lambda \subset H),

$$
\dot{x}_k = f_k(x), \qquad k \in \Lambda \subset H
$$

This framing is useful because it clarifies that a low-fidelity model may be adequate only in parts of the system’s dynamic operating space.

---

## 3. Main Idea of the Paper

The central idea is:

> Use the low-fidelity model when the simulated system remains inside the dynamic region that the low-fidelity model can represent sufficiently well, and switch to the high-fidelity model when the system enters a region where additional dynamics are needed.

This is runtime model switching inside a closed-loop simulation.

The paper’s conceptual figure on page 2 shows the simulation trajectory moving through the dynamic space of the system. The low-fidelity model is used while the trajectory remains inside the low-fidelity dynamic region. The high-fidelity model is activated when the trajectory leaves this region. 

---

## 4. Case Study: Closed-Loop Vapor Compression System

The paper applies the method to a **four-component vapor compression system (VCS)** modeled in Simulink with the Thermosys toolbox.

The system contains:

* compressor,
* condenser,
* evaporator,
* electronic expansion valve,
* thermal zone,
* controller.

The controller has two PI control loops:

| Controlled quantity            | Controlled by                 |
| ------------------------------ | ----------------------------- |
| Thermal zone temperature (y_1) | Compressor speed (u_1)        |
| Evaporator superheat (y_2)     | Expansion valve opening (u_2) |

The superheat is defined as:

$$
T_{\mathrm{super}}
=
T_{e,\mathrm{out}}
-
T_{e,\mathrm{sat}}
$$

The vapor compression system is a closed-loop system because the controller decisions depend on the simulated system response. Therefore, fidelity errors do not only affect outputs; they also affect the computed control inputs. 

---

## 5. Why Closed-Loop Fidelity Switching Matters

The paper shows that high- and low-fidelity models can produce different **control inputs** even when the same controller is used.

This is important because in closed-loop systems:

```text
model output error
→ different controller error signal
→ different actuator command
→ different system trajectory
```

The paper reports that the low-fidelity model produces noticeable discrepancies in the compressor speed and expansion-valve opening compared with the high-fidelity reference. In the case study, the low-fidelity model causes approximately:

* $7%$ to $10%$ difference in compressor-speed decision magnitude,
* around $20%$ difference in expansion-valve opening,
* in parts of the time history, a steady-state offset of nearly $30%$ for the second input. 

This distinguishes the paper from purely open-loop switched-fidelity methods: the fidelity level affects the **controller decisions**, not only the physical output trajectory.

---

## 6. Switching Criterion and Supervisor

The switching is controlled by a **supervisor** that analyzes exogenous signals:

* reference signal $r(t)$,
* disturbance signal $d(t)$.

These signals are known before simulation and are therefore sent first to the supervisor. The signals are delayed before entering the simulated system:

$$
z^{-n}
$$

This gives the supervisor time to activate the high-fidelity model before the transient reaches the system. It also gives time for switching transients to settle after state reinitialization. 

The supervisor consists of:

| Component                         | Role                                                                 |
| --------------------------------- | -------------------------------------------------------------------- |
| Band-pass filter                  | Detects relevant changes in reference/disturbance signals            |
| Filter gain (K_{\mathrm{filter}}) | Sets switching sensitivity                                           |
| Dwell time (t_{\mathrm{dwell}})   | Keeps high-fidelity mode active long enough to capture the transient |

---

## 7. Band-Pass Filter and Trigger Logic

The supervisor uses a band-pass filter of the form:

$$
\frac{\omega_n^2 s}{s^2 + 2\zeta \omega_n s + \omega_n^2}
$$

where:

| Symbol     | Meaning           |
| ---------- | ----------------- |
| $\omega_n$ | natural frequency |
| $\zeta$    | damping ratio     |

The damping ratio is selected to avoid excessive overshoot:

$$
\zeta \leq 1.2
$$

The filtered signal is scaled by $K_{\mathrm{filter}}$. The logical trigger is:

$$
y_{\mathrm{logic}}
=
\begin{cases}
1, & |y_{\mathrm{filter}} K_{\mathrm{filter}}| \geq 1 \
0, & |y_{\mathrm{filter}} K_{\mathrm{filter}}| < 1
\end{cases}
$$

Thus, $K_{\mathrm{filter}}$ determines how large a reference or disturbance change must be to trigger high-fidelity mode.

---

## 8. Dwell Time

A time-based dwell rule avoids switching back immediately after a trigger. If (t_{\mathrm{switch}}) is the time at which the logic signal switches from 0 to 1, then the supervisor output is:

$$
y_{\mathrm{supervisor}}
=
\begin{cases}
1, & y_{\mathrm{logic}} = 1 \
1, & t_{\mathrm{sim}} < t_{\mathrm{dwell}} + t_{\mathrm{switch}}
\ \text{and}\ y_{\mathrm{logic}} = 0 \
0, & t_{\mathrm{sim}} \geq t_{\mathrm{dwell}} + t_{\mathrm{switch}}
\ \text{and}\ y_{\mathrm{logic}} = 0
\end{cases}
$$

If $y_{\mathrm{supervisor}}=1$, the system operates in high-fidelity mode. If $y_{\mathrm{supervisor}}=0$, it operates in low-fidelity mode.

The dwell time is chosen heuristically as a function of the system time constant:

$$
t_{\mathrm{dwell}} \approx 4\tau_{\mathrm{sys}}
$$

This allows most transient dynamics to decay before switching back to low fidelity. 

---

## 9. State Transfer Between Fidelity Levels

A central technical issue is state transfer between fidelity levels.

When switching from low to high fidelity, the high-fidelity model must be initialized from the low-fidelity model. For finite-volume heat-exchanger models, the low-fidelity states are mapped into the high-fidelity states by extracting low-fidelity zone states and linearly interpolating the states of the intermediate high-fidelity volumes.

For low-to-high switching:

$$
x_h[k] = x_l[j]
$$

where selected high-fidelity volume indices $k$ receive corresponding low-fidelity states $x_l[j]$.

For high-to-low switching:

$$
x_l[j] = x_h[k]
$$

where the inlet, middle, and exit high-fidelity volumes are extracted and used to reset the low-fidelity model.

This directly corresponds to the state-transfer problem in runtime model switching: different models may not have the same state dimension or state meaning. 

---

## 10. Output Bias Correction for Structurally Different Models

The paper also discusses the case where state mapping is not possible because the two models are structurally different, for example moving-boundary and finite-volume heat-exchanger models.

In this case, output correction can be used. After switching from high to low fidelity at time $\tau$, the low-fidelity output is biased by the difference between high- and low-fidelity outputs at the switching time:

$$
y(t)
=
y_{\mathrm{low}}(t)
+
\left[
y_{\mathrm{high}}(\tau)
-
y_{\mathrm{low}}(\tau)
\right]
$$

This keeps the low-fidelity output aligned with the high-fidelity output after switching. The bias is reset at the next high-to-low switch.

This is important for `syssimx` because heterogeneous backends such as FMU, OpenSim, and FEM may not expose equivalent state vectors. In such cases, output alignment or reduced state transfer may be more feasible than full state mapping.

---

## 11. System-Level Switched-Fidelity Logic

The switching logic is more sophisticated than a simple output switch.

The process is:

1. Both models are initially active so initial transients can settle.
2. The system starts in low-fidelity mode.
3. When the supervisor triggers, the high-fidelity model is initialized.
4. For the delay interval, the system output still comes from the low-fidelity model.
5. After the delay, the system output switches to the high-fidelity model.
6. During high-fidelity operation, the low-fidelity model continues running in standby with the same inputs.
7. After the dwell time, the system switches back to low-fidelity output.
8. Output bias correction may be applied when returning to low fidelity.

This design avoids including high-fidelity initialization transients in the system output. The logic tree on page 6 visualizes this sequence. 

---

## 12. Results

The case study compares:

1. pure high-fidelity simulation,
2. pure low-fidelity simulation,
3. switched-fidelity simulation.

### 12.1 Control Input Error

The RMSE of the actuator inputs is computed relative to the high-fidelity model:

$$
RMSE
====

\sqrt{
\frac{
\sum_{t=1}^{n}
(u - \hat{u})^2
}{n}
}
$$

The reported values are:

| Input                          | Low-fidelity RMSE | Switched-fidelity RMSE |
| ------------------------------ | ----------------: | ---------------------: |
| $u_1$: compressor speed        |            (54.9) |                 (6.68) |
| $u_2$: expansion valve opening |            (3.05) |                 (0.70) |

The switched-fidelity model therefore matches the high-fidelity control inputs much more closely than the low-fidelity model. The paper states that the switched-fidelity framework reduces the control-input error by over (50%) compared with the low-fidelity model. 

### 12.2 System Output Regulation

The controller regulates:

* thermal zone temperature $y_1$,
* evaporator superheat $y_2$.

The paper shows that all three configurations meet the output regulation objectives, but the actuator input histories differ. This means that the output trajectories alone may not reveal fidelity-induced controller differences. For controller development, matching control inputs can therefore be important, not only matching controlled outputs. 

### 12.3 Computational Cost

The low-fidelity model is the fastest. The high-fidelity model requires (93%) more execution time than the low-fidelity model. The switched-fidelity model requires only (32%) more time than the low-fidelity model.

Equivalently, relative to the high-fidelity model:

* low fidelity reduces computational cost by (48%),
* switched fidelity reduces computational cost by (32%).

Thus, the switched-fidelity model retains much of the computational benefit of the low-fidelity model while preserving behavior closer to the high-fidelity model. 

---

## 13. Main Conclusions

The paper concludes that variable-fidelity component models can reduce computational cost while maintaining high-fidelity-like input and output behavior in closed-loop dynamic simulations.

The main findings are:

1. **Closed-loop systems are sensitive to fidelity differences.**
   Fidelity affects not only output trajectories but also controller decisions.

2. **Runtime switching can reduce cost while preserving accuracy.**
   The switched-fidelity simulation matches high-fidelity behavior more closely than the low-fidelity simulation while reducing runtime.

3. **State transfer is essential.**
   Switching requires initialization or synchronization between models of different fidelity.

4. **Delayed exogenous signals avoid switching transients.**
   The supervisor uses previewed reference and disturbance signals, while the system receives delayed versions.

5. **The demonstrated method is still centralized and exogenous-signal based.**
   The paper identifies future work on decentralized component-level supervisors for larger systems with multiple variable-fidelity components. 

---

# Relevance for `syssimx`

## 1. Direct Relevance

This paper is directly relevant for the **runtime model-switching** part of `syssimx`.

| Williams & Alleyne concept              | `syssimx` counterpart                             |
| --------------------------------------- | ------------------------------------------------- |
| Variable-fidelity component models      | `MultiModelComponent`                             |
| High-fidelity model                     | FEM pendulum/contact model                        |
| Low-fidelity model                      | FMU/OpenSim/rigid-body model                      |
| Supervisor                              | Switching rule / mode-selection logic             |
| Reference/disturbance monitoring        | State/event/contact-based switching conditions    |
| Delayed exogenous signal                | Preview mechanism, not directly used in `syssimx` |
| State interpolation                     | State transfer between active models              |
| Output bias correction                  | Possible strategy for non-equivalent backends     |
| Closed-loop control input discrepancies | Controller behavior in controlled pendulum case   |
| Computational cost reduction            | Runtime benchmark of model switching              |

---

## 2. Strong Similarities

The paper supports several core ideas in `syssimx`:

### Runtime switching is a valid multi-fidelity strategy

The active model does not have to be fixed for the full simulation. Instead, high-fidelity models can be activated only when the system enters an accuracy-critical dynamic region.

### The switching mechanism must handle state consistency

The paper explicitly treats the mapping of low-fidelity states to high-fidelity states and vice versa. This supports the importance of state transfer in `syssimx`.

### Closed-loop systems require more than output comparison

The paper shows that low- and high-fidelity models can produce different controller input trajectories even when output regulation appears acceptable. This is relevant for the controlled pendulum system because controller behavior may change when switching between model variants.

### Computational benefit must be measured against high-fidelity and low-fidelity baselines

The paper compares all three cases: high fidelity, low fidelity, and switched fidelity. This is the right evaluation structure for `syssimx` runtime model switching.

---

## 3. Differences to `syssimx`

| Aspect                  | Williams & Alleyne (2014)                                | `syssimx` |
| ----------------------- | -------------------------------------------------------- | --------- |
| Model type              | Same component family with different fidelity            |           |
| `syssimx` model type    | Heterogeneous FMU, OpenSim, FEM, Python components       |           |
| Simulation environment  | Simulink / Thermosys                                     |           |
| `syssimx` environment   | Python framework                                         |           |
| Switching trigger       | Exogenous preview signals                                |           |
| `syssimx` trigger       | Endogenous state, contact, or event conditions           |           |
| Supervisor              | Centralized system-level supervisor                      |           |
| `syssimx` switching     | Component-level `MultiModelComponent`                    |           |
| State mapping           | Finite-volume interpolation or output bias               |           |
| `syssimx` state mapping | Tool-specific state extraction and reinitialization      |           |
| Hybrid events           | Not formalized as event detection/localization           |           |
| `syssimx` hybrid logic  | Event indicators, rollback, bisection event localization |           |
| Co-simulation           | Not the main focus                                       |           |
| `syssimx` focus         | Heterogeneous hybrid co-simulation                       |           |

---

## 4. Why This Paper Is Useful for the Thesis

This paper is useful because it extends switched-fidelity modeling from isolated components to a **closed-loop dynamic system**. It provides a strong argument that fidelity switching is relevant not only for computational speed but also for preserving controller behavior.

For `syssimx`, the key transferable ideas are:

* runtime model switching can preserve high-fidelity behavior at reduced cost,
* model switching requires explicit state transfer or output alignment,
* closed-loop simulations should compare controller inputs, not only controlled outputs,
* switching rules need hysteresis or dwell-time-like mechanisms to avoid excessive switching,
* multi-fidelity evaluation should report both accuracy/error and computational cost.

---

# Compact Thesis-Ready Summary

Williams and Alleyne (2014) propose a variable-fidelity modeling framework for closed-loop dynamical systems. The motivation is that high-fidelity models are valuable for control-system development because they capture more system dynamics, but their computational cost makes repeated simulation and controller validation expensive. Low-fidelity models reduce computational effort but may miss relevant dynamics, leading to different controller decisions. The paper therefore introduces a switched-fidelity approach that changes the active model fidelity during simulation to approximate high-fidelity behavior with reduced computational cost. 

The method is demonstrated on a four-component vapor compression system with a PI-controlled thermal zone and evaporator superheat. The variable-fidelity components are the evaporator and condenser. A supervisor monitors known reference and disturbance signals, which are delayed before entering the simulated system. This non-causal preview allows the supervisor to activate the high-fidelity model before the transient reaches the system and gives switching transients time to decay. The supervisor uses a band-pass filter, a gain (K_{\mathrm{filter}}), and a dwell time (t_{\mathrm{dwell}}). State transfer between fidelity levels is performed by mapping low-fidelity finite-volume states to high-fidelity states through interpolation and by extracting selected high-fidelity states when switching back. For structurally different models, the paper proposes output bias correction instead of full state mapping. 

The case study compares pure high-fidelity, pure low-fidelity, and switched-fidelity simulations. The low-fidelity model produces noticeable differences in the controller inputs compared with the high-fidelity model. The switched-fidelity framework reduces the RMSE of the compressor-speed input from (54.9) to (6.68) and the RMSE of the expansion-valve input from (3.05) to (0.70), both measured relative to the high-fidelity simulation. Computationally, the high-fidelity model requires (93%) more execution time than the low-fidelity model, whereas the switched-fidelity model requires only (32%) more than the low-fidelity model. Relative to the high-fidelity baseline, the switched-fidelity framework reduces computational cost by (32%). 

For this thesis, the paper is relevant because it provides a direct precedent for runtime model switching in closed-loop dynamic simulations. The `MultiModelComponent` in `syssimx` follows the same general principle: a high-fidelity model is activated only during phases where its additional accuracy is required, while cheaper models are used elsewhere. In contrast to Williams and Alleyne, `syssimx` applies this principle to heterogeneous hybrid co-simulation. The alternative models may originate from different tools, such as FMI-based Modelica models, OpenSim models, and FEM/NGSolve models, and switching can be triggered by endogenous state or event conditions such as contact rather than only by previewed exogenous reference and disturbance signals.

# Possible Thesis Sentence

```latex
Williams and Alleyne demonstrate that variable-fidelity modeling can preserve high-fidelity-like behavior in closed-loop dynamic simulations while reducing computational cost. Their work motivates the runtime model-switching mechanism in \syssimx{}, especially the need for explicit state transfer and the comparison of both system outputs and controller inputs. Whereas their approach uses a centralized supervisor based on delayed exogenous reference and disturbance signals, \syssimx{} extends the concept to heterogeneous hybrid co-simulation with tool-specific FMU, OpenSim, and FEM backends and switching based on endogenous state or event conditions.
```