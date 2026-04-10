Cremona, F., Lohstroh, M., Broman, D., Lee, E. A., Masin, M., & Tripakis, S. (2019). Hybrid co-simulation: It’s about time. Software & Systems Modeling, 18(3), 1655–1679. https://doi.org/10.1007/s10270-017-0633-6

**Summary**

**1 Motivation and & Problem Statement**

- CPS combine discrete and continuous dynamics
- Existing simulation tools struggle with hybrid behaviors
    
    - Modelica struggles with discrete behavior
    - DE tools simulate continuous dynamics inefficiently
- FMI 2.0 enables tool-coupling via co-simulations, but lacks robust time modeling for hybrid systems

**2 Core Issue: Inadequate Time Representation**

- FMI 2.0 uses floating-point numers for time
    
    - prone to quantization errors
    - cannot guarantee simultaneity of events
    - cause inconsistencies in simulation involving discrete-time vents and intantaneous transitions

**3 Paper Contribution: Hybrid Co-Simulation with improved Time Semantics**

- Introduces a new model of time for FMI based co-simulation: based on superdense time and integer representation
- Supports both continuous-time and discrete-event behavior
- enables instantaneous reactions and zero-time venets
- ensures causality and simultaneity across cyber and physical components

**4 Introduced Key Concepts**

1. **Superdense time**

- Events can carry time stamp (simulation time: int t, microstep index: int n)
- enables representing multiple discrete events at the same simulation time
- eliminates floating point ambiguities in detecting simultaneity or causality

1. **Integer Time Representation**

- using 64-bit unsigned integer with configurable resolution
- guarantees exact arithmetic and deterministic ordering of events
- time resolution is model specific and negotiable between FMUs and the master

1. **Resolution Negotiation**

- FMUs declare their preferred time resolution
- Master algorithm computes a common compatible resolution
    
    - via minimum resolution / greatest common divisor
- Allows mixing FMUs operating on different time scales

1. **FMU Categorization**

- 0A/0B: lagacy FMUs with/without zero-step support
- 1-4: varying support for resolution negotiation
-  Wrappers are used to abstract FMU-specific time models and interface with the master

1. **Wrapper-Based Architecture**

- Master delegates time and signal translation to wrapper layers
- all wrappers expose a uniform interface using integer time
- ensures modularity and compatibility across legacy and new FMUs

1. **Time conversion & quantization**

- Carfully handles conversion between:
    
    - FP time to / from integer timeIn
    - Different integer time resolutions
- Ceiling/flooring rounding strategies to ensure causality and avoid Zeno effects
- Quantization still exists but is bounded and controlled

**Relevant Concepts:**

<table><tbody><tr><td><p><strong>Modeling &amp; Co-Simulation Concepts</strong></p></td><td><ul><li><ul><li>Time as core abstarction: essential for orchestrating between continuous and possible discrete or event dirven models</li><li>Heterogeneous time resolution and models: critical when integrating components with different numerical solvers, sampling rates, or event bahavior</li><li>Superdense time: necessary for instantaneous events (sensor triggers or contact events)</li><li>Integer-based time modeling: to avoid FP rounding errors that affect synchrony in co-simulation</li></ul></li></ul></td></tr><tr><td><p><strong>Framework Design Aspects</strong></p></td><td><ul><li><ul><li>FMU categorization: enables to define interface behavior in the framework depending on FMU capabilities</li><li>Wrappers for time abstraction: important pattern to implement for supporting FMUs with different time models</li><li>Time conversion and quantization: for exchanging data between continuous simulators and discrete ones</li></ul></li></ul></td></tr></tbody></table>