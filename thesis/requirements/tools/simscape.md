# Simscape

Simscape is the physical modeling technology within the MATLAB/Simulink ecosystem for building and simulating multidomain systems. It is used to model physical components such as electric drives, power electronics, hydraulic actuators, thermal systems, and other energy-based subsystems by connecting reusable components in a schematic. In contrast to pure signal-flow modeling, Simscape represents physical interactions directly through physical ports and network connections.

Within the MATLAB/Simulink environment, Simscape extends Simulink rather than replacing it. Simulink remains the surrounding simulation platform for system assembly, control logic, signal processing, and analysis, while Simscape provides the physical plant model. This makes it possible to combine physically grounded subsystem models with controllers, state machines, estimators, and test logic in one executable model.

## How Simscape Works in the MATLAB/Simulink Environment

The central difference between Simscape and standard Simulink modeling is the modeling paradigm. Simulink blocks exchange directed signals and are evaluated sequentially according to the block diagram semantics. Simscape components, by contrast, are connected through acausal physical ports. Their equations are collected into one physical network and solved simultaneously. Internally, this leads to implicit differential-algebraic equation systems rather than a simple directed signal chain.

In practice, a Simscape model inside Simulink typically consists of the following elements:

- physical component blocks from the Simscape Foundation library or add-on products,
- a `Solver Configuration` block for each physical network,
- domain-specific reference blocks where required,
- `Simulink-PS Converter` blocks for signals entering the physical network,
- `PS-Simulink Converter` blocks for quantities passed back to Simulink.

These converter blocks are necessary because Simulink and Simscape use different semantics. Simulink operates on signal lines, while Simscape operates on physical networks. Whenever a Simulink controller provides an input to a physical model, or a physical quantity is exported for control design, logging, or analysis, the corresponding interface block must be inserted.

## Typical Modeling Workflow

A common workflow is to start with `sscnew`, which creates a new Simscape-ready model with the essential infrastructure already inserted. The user then assembles the physical subsystem from existing components, parameterizes these components with MATLAB variables or expressions, and connects the plant to surrounding Simulink logic. During simulation, Simscape formulates the equations implied by the connected physical components and solves them together with the rest of the Simulink model.

This workflow is particularly useful for control development and system-level testing. A controller designed in Simulink can act on a physically consistent Simscape plant, while the resulting states and outputs can be fed back into Simulink for further processing, visualization, or validation.

## Simscape Language

The Simscape language is a dedicated textual language for defining custom physical modeling components. It is based on MATLAB syntax but adds constructs for physical domains, conserving ports, parameters, variables, and equations. It is used when the standard library does not provide a suitable component or when the user needs tighter control over the tradeoff between model fidelity and simulation speed.

With the Simscape language, users can define custom components as text files whose behavior is specified by acausal implicit equations. These components can reuse existing Simscape domain definitions so that they remain compatible with standard library blocks. It is also possible to define entirely new physical domains and assemble custom component libraries.

Custom textual components can be integrated back into Simulink by turning them into Simscape blocks, either directly through the Simscape Component block or by generating reusable custom libraries. This means that text-based physical modeling and graphical Simulink-based system assembly are tightly connected inside one environment.

## Relevance

Simscape is therefore best understood as the physical-system layer of the MATLAB/Simulink environment. Simulink provides the overall execution framework and signal-oriented system integration, while Simscape provides equation-based, acausal modeling of physical subsystems. Together, they support parameterized plant modeling, controller development, simulation-based analysis, and deployment through C code generation, including hardware-in-the-loop scenarios.
