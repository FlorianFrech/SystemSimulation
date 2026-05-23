# Glossary

## Terminology Rule

The thesis distinguishes between the physical/modeling world and the framework/software world.

- In the physical or theoretical sense, a **system** consists of **subsystems**.
- A **model** is the mathematical representation of a system or subsystem.
- A framework-neutral software unit that executes a subsystem model in a coupled simulation is called a **simulation unit**.
- In `syssimx`, the concrete executable representation of a subsystem model is called a **component**.
- Thus, *component* is reserved exclusively for the `syssimx` framework.  Use *simulation unit* when speaking of co-simulation participants in a tool-independent or standard-level context.

## Physical Systems and Subsystems

| Term | Definition | Preferred Usage |
|------|------------|-----------------|
| **Physical system** | A real technical or biomechanical system under study, such as a prosthesis, exoskeleton, or controlled pendulum. | Use when referring to the real-world artifact or process. |
| **System** | A set of interacting parts that together exhibit a behavior of interest. | Use as the general theoretical term unless a concrete software class is meant. |
| **Subsystem** | A constituent part of a larger system considered at the physical or conceptual level. | Use in theory chapters for parts of the overall system. |
| **Multi-domain system** | A system whose behavior involves several physical or technical domains, such as mechanics, control, electronics, or biomechanics. | Use when emphasizing cross-domain coupling. |
| **Cyber-physical system** | A system in which physical processes and computational processes interact through sensing, actuation, and feedback. | Use for the general class of systems motivating the thesis. |
| **Mechatronic system** | A cyber-physical system that combines mechanics, electronics, sensing, actuation, and control. | Use for the engineering application class addressed by the thesis. |

## Modeling and System Simulation

| Term | Definition | Preferred Usage |
|------|------------|-----------------|
| **Model** | A mathematical representation of a physical system or subsystem used for analysis or simulation. | General term for equations, state-space models, DAEs, FEM models, etc. |
| **Subsystem model** | A model that describes one subsystem of a larger system. | Use when emphasizing that the model belongs to one part of the overall system. |
| **System model** | The coupled mathematical representation of the complete system, including the relations between its subsystem models. | Use for the assembled overall model independent of software implementation. |
| **ODE (Ordinary Differential Equation)** | A differential equation in which the unknown depends on a single independent variable (time). Written in state-space form as $\dot{x} = f(x, u, t)$, $y = h(x, u, t)$. | Use when discussing continuous-time subsystem dynamics and numerical integration. |
| **DAE (Differential-Algebraic Equation)** | A mixed system of differential equations and algebraic constraints, written as $F(\dot{x}, x, z, u, t) = 0$. Arises from physical conservation laws, mechanical constraints, and acausal models. | Use when discussing constrained system formulations, Modelica-translated models, and index analysis. |
| **Simulation** | The numerical execution of a model over time in order to study its behavior. | General term for numerical time evolution. |
| **System-level simulation** | Simulation of the coupled behavior of the complete system rather than of isolated subsystems only. | Use for the thesis motivation and case-study context. |
| **Equation-based modeling** | A modeling approach in which system behavior is described through mathematical equations between variables — algebraic equations, ODEs, or DAEs. The umbrella term under which causal and acausal modeling are sub-styles. | Use as the overarching term when contrasting equation-based approaches with, for example, purely data-driven or table-lookup models. Do not treat as a synonym for acausal modeling only. |
| **Causal modeling** | A sub-style of equation-based modeling in which the computational direction is defined explicitly when the subsystem is formulated, typically through declared inputs and outputs. Example: state-space models, block diagrams, signal-flow models. | Use when the fixed input-output structure of a model matters, e.g., when discussing direct feedthrough or co-simulation coupling. |
| **Acausal modeling** | A sub-style of equation-based modeling in which subsystem behavior is stated as equations without prescribing a fixed computational direction. Computational causality is derived later by the simulation tool from the overall connected model (structural analysis, BLT decomposition). Typical in Modelica-style physical modeling. | Use for equation-based physical modeling discussions. Note: acausal models are not *executed* acausally — they are translated into a causal computation before simulation. |

## Evidence Terms

| Term | Definition | Preferred Usage |
|------|------------|-----------------|
| **Verification** | A check that an implemented mechanism, numerical result, or simulation configuration behaves consistently with a specified reference, analytical result, or implementation contract. | Use for feature-level checks in Chapter 5 and for numerical comparisons against model-based references. Verification does not imply physical truth. |
| **Validation** | An evaluation that the combined workflow is suitable for the intended thesis use case and satisfies the mandatory user-facing requirements in the controlled-pendulum scenario. | Use for the case-study workflow as a whole. State explicitly when validation is workflow validation rather than experimental physical validation. |
| **Benchmark** | A measurement of computational cost or runtime behavior for a fixed scenario and configuration. | Use for performance results such as wall-clock time, speedup, call counts, and active simulated time. A benchmark is not correctness evidence on its own. |

## Hybrid Terms

| Term | Definition | Preferred Usage |
|------|------------|-----------------|
| **Hybrid system** | A system that combines continuous-time dynamics with discrete changes of state, mode, or behavior. | Use in the theoretical discussion of continuous-discrete interaction. |
| **Discrete event** | An instantaneous change or trigger that causes a change in system state, mode, or equations. | Use for contact, switching, controller actions, and sampled behavior. |
| **Mode change** | A discrete transition from one system regime or equation set to another. | Use in hybrid modeling and event-handling discussions. |
| **Event handling** | The processing of a discrete event, including detection, state update, and continuation of the simulation. | Use in hybrid-system and hybrid co-simulation contexts. |
| **Event source** | A component that emits a discrete event through an event indicator. The emitting end of an event connection. | Use for the component that produces an event in `syssimx` event routing. |
| **Event listener** | A component that receives a routed event and updates its state in response. The receiving end of an event connection. | Use consistently for this role. Do not use *event receiver* or *event target* for the component. |
| **Event localization** | The numerical determination of the physical time at which an event occurs within a simulation step. | Use when discussing rollback, bisection, or root-finding. |
| **Rollback** | The restoration of a previously stored simulation state in order to repeat part of a computation, for example during event localization. | Use in hybrid simulation and iterative co-simulation contexts. |
| **Superdense time** | A time representation of the form $(t, \nu)$, where $t$ is the real-valued physical time and $\nu \in \mathbb{N}$ is a micro-instant index. Superdense time allows multiple logically simultaneous events at the same physical instant to be ordered without advancing the clock, enabling consistent event handling at communication points. | Use when discussing event ordering, zero-crossing handling, and hybrid co-simulation algorithms that must distinguish multiple events at the same time $t$. |

## Co-Simulation Terms

| Term | Definition | Preferred Usage |
|------|------------|-----------------|
| **Co-simulation** | A simulation approach in which multiple subsystem models are executed by separate solvers and exchange data at discrete communication points. | Use for the general method, not for a specific implementation. |
| **Hybrid co-simulation** | A co-simulation approach that supports hybrid systems, i.e., coupled subsystem models that include discrete events, mode changes, or discontinuities. Requires mechanisms for event detection, event localization, and consistent state update across simulation units. | Use when the co-simulation method must explicitly handle discrete events or mode switches, as opposed to purely continuous co-simulation. |
| **Simulation unit** | A framework-neutral term for an executable software entity that encapsulates a subsystem model and participates in a coupled simulation by exchanging data at communication points. | Use as the neutral, tool-independent term in theory chapters and standard-level discussions. Do not use *component* in this context — *component* is reserved for `syssimx`. |
| **Communication point** | A discrete time instant at which coupled simulation units exchange data. | Use in co-simulation algorithm descriptions. |
| **Master algorithm** | The algorithm that orchestrates the coupled execution of simulation units in a co-simulation, controlling time advancement and data exchange. Not to be confused with the FMI master role, which is a specific realization of this concept under the FMI Co-Simulation standard. | Use as the preferred orchestration term throughout the thesis. |
| **Macro step size** | The communication interval between two communication points in co-simulation. | Use for the system-level co-simulation step. |
| **Micro step size** | The internal integration step size used by an individual subsystem solver between communication points. | Use for component-internal stepping. |
| **Direct feedthrough** | A structural property of a simulation unit in which the current output depends directly on the current input without integration. | Use in structural analysis and algebraic-loop discussions. |
| **Algebraic loop** | A closed instantaneous dependency between coupled variables or simulation units that requires simultaneous resolution. | Use in continuous-time and co-simulation discussions. |
| **Execution order** | The order in which simulation units are evaluated or advanced during co-simulation. | Use for graph-based orchestration and stepping schemes. |
| **FMI Co-Simulation mode** | An FMI operating mode in which the FMU provides its own internal solver and advances its state autonomously between communication points. The importing environment (master algorithm) controls time stepping and data exchange but does not supply the solver. Contrast with FMI Model Exchange. | Use when discussing FMU-based co-simulation setups. |
| **FMI Model Exchange mode** | An FMI operating mode in which the importing environment provides the numerical solver for the model equations. | Use only in the FMI context when contrasting with Co-Simulation mode. |
| **Functional Mock-up Interface (FMI)** | A standardized interface for packaging and executing simulation models across tools. | Use for the general interoperability standard. |
| **Functional Mock-up Unit (FMU)** | A packaged simulation model conforming to the FMI standard. | Use for FMI-based model artifacts. |

## SysSimX Terms

| Term | Definition | Preferred Usage |
|------|------------|-----------------|
| **Component** | In `syssimx`, an executable simulation unit that encapsulates a subsystem model and exposes a common interface for coupled simulation. The `syssimx`-specific realization of what is called a *simulation unit* at the framework-neutral level. | Use in framework chapters instead of *simulation unit* or *subsystem* when referring to `syssimx` software objects. |
| **CoSimComponent** | The abstract base class in `syssimx` that defines the common interface for all co-simulation components. | Use only for the concrete framework abstraction. |
| **FMUComponent** | A concrete `syssimx` component that wraps an FMU and adapts it to the `CoSimComponent` interface. | Use only for the specific wrapper implementation. |
| **Port** | In `syssimx`, a typed, unit-aware interface point on a component through which values are exchanged with other components. Ports are classified as input or output ports and carry physical unit information managed by Pint. | Use when describing the coupling interface of a component, both in architecture and in connection descriptions. |
| **System (`syssimx`)** | The `syssimx` object that assembles interconnected components into a complete co-simulation model and runs the master algorithm. | Use for the concrete framework object, ideally written as `\texttt{System}` in the thesis. |
| **MultiComponent** | A `syssimx` abstraction that groups multiple components representing the same physical subsystem at different fidelity levels and supports runtime switching between them during simulation. The concrete class is `MultiComponent` (`syssimx/core/multi_comp.py`); `MasterPendulum` is the case-study subclass. | Use when discussing multi-fidelity or model-switching scenarios, such as switching between a rigid-body FMU, a musculoskeletal OpenSim model, and a FEM model of the same pendulum. |
| **Connection** | A directed relation that transfers values from an output port of one component to an input port of another component. | Use in framework and architecture chapters. |

## Recommended Usage Notes

- **Subsystem** (physical/theoretical) → **simulation unit** (framework-neutral software) → **component** (SysSimX concrete realization). These three terms form a strict hierarchy and must not be used interchangeably.
- **Component** is exclusively a `syssimx` term. When speaking about co-simulation participants in a tool-neutral or FMI-standard context, use **simulation unit**.
- **System** (lowercase, theoretical) denotes the coupled physical or mathematical entity. **`System`** (the `syssimx` class) is the software object. Distinguish carefully in prose, e.g., write *"the `\texttt{System}` object assembles the simulation units into a system model"*.
- **Equation-based modeling** is the umbrella term. **Causal** and **acausal** are its sub-styles, classified by treatment of computational direction — not independent categories at the same level.
- **Acausal models are not executed acausally.** They are translated into a causal computation (via structural analysis and BLT decomposition) before simulation. Make this explicit if the chapter discusses Modelica or DAE-based models.
- **Master algorithm** refers to the orchestration algorithm. When discussing the FMI standard specifically, clarify the context to avoid confusion with the FMI master role.

## Canonical Thesis Sentence

> In the theoretical discussion, the term *subsystem* denotes a constituent part of the modeled system. In a tool-neutral co-simulation context, the executable software unit that encapsulates a subsystem model is called a *simulation unit*. In `syssimx`, the concrete realization of this concept is called a *component* and is implemented through the `CoSimComponent` interface.
