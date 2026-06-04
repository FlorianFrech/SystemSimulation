fmi_standard_blochwitz

Blochwitz, T., Otter, M., Åkesson, J., Arnold, M., Clauss, C., Elmqvist, H., Friedrich, M., Junghanns, A., Mauss, J., Neumerkel, D., Olsson, H., & Viel, A. (2012). Functional Mockup Interface 2.0: The Standard for Tool independent Exchange of Simulation Models. In *Proceedings*. [https://doi.org/10.3384/ecp12076173](https://doi.org/10.3384/ecp12076173)

**FMI 2.0 - The Standard for Tool independent Exchange of Simulation Models**

 **2 Functional Mock-up Interface**

**2.1 Main Design Ideas**

**2.1.1 FMI for Model Exchange**

- intention is that a modeling environment can generate C-code of a dynamic system model in form of an input/output block
- block can be utilized by other modeling and simulation environments
- models without solvers are described by differential, algebraic, and discrete equations with time-, state-, and step events

**2.1.2 FMI for Co-Simulation**

- intention is to couple two or more models with solvers in a co-simulation environment
- data exchange between subsystems is restricted to discrete communication points
- in the time between communication points, the subsystems are solved independently from each other by their individual solvers
- master algorithms control data exchange between subsystems and the synchronization of all slave simulation solvers
- interface allows standard and advanced master algorithms
    
    - variable communication step size
    - higher order signal extrapolation
    - error control

**2.2 Distribution**

- FMU is a standardized, tool-independent model package defined by the FMI standard
- distributed as a .fmu ZIP container that includes all the components required to simulate a model

**1\. XML Model Description**

- Contains **all exposed variables** (parameters, states, inputs, outputs).
- Includes **model structure**, data types, units, variability, dependencies.
- Allows importing tools to run the FMU **without needing the original modeling environment**.

**2\. C-Function Interface**

- Implements the **FMI API functions** for:
    
    - Model Exchange (ME): derivative evaluation, event handling, etc.
    - Co-Simulation (CS): stepping the internal solver.
- Contains **source code and/or platform-specific binaries**.
- Optional inclusion of binaries for **multiple operating systems**.

**3\. Additional Resources**

- Model icon/graphics.
- Documentation files.
- Parameter tables, lookup data.
- DLLs or other libraries needed by the model.
    

**2.3 Description Schema**

- All non-runtime information about the model is stored in an XML file named **modelDescription.xml**.
- This file **reduces overhead** because tools only load essential data and can read the XML using any programming language (C, C++, C#, Java, Python, …).
- The XML file follows a formal schema called **fmiModelDescription.xsd**.
- In **FMI 2.0**, this *single* XML file contains information for both:
    
    - **Model Exchange (ME)**
    - **Co-Simulation (CS)**
- The XML schema includes two optional elements:
    
    - **ModelExchange**
    - **CoSimulation**
- If one or both of these elements are present:
    
    - The respective **C-function APIs** must be provided in the FMU (typically as DLLs on Windows or shared objects on Linux/Mac).
- FMI 2.0 adds a new XML element:
    
    - **ModelStructure**, which exposes more detailed model structural information (e.g., dependencies between variables).

**3 Features of FMI 2.0**

**3.2 Classification of Interface Variables**

**1\. Variable Causality (what the variable *means*)**

- **parameter**
    
    - Independent value, must remain constant during simulation.
- **input**
    
    - Value provided from another model.
- **output**
    
    - Value exposed to other models.
    - Algebraic dependencies described in ModelStructure.
- **local**
    
    - Internal variable, computed from others.
    - Cannot be used externally.

**2\. Variable Variability (when the value may change)**

- **constant**
    
    - Never changes.
- **fixed**
    
    - Constant after initialization.
- **tunable** *(new in FMI 2.0)*
    
    - Can change **between externally triggered events** (due to parameter or input changes).
- **discrete**
    
    - Constant between **internal events** (time, state, step events).
- **continuous**
    
    - Can change at any time.

**3\. Meaning of “tunable”**

- Introduced to allow **interactive parameter tuning** (e.g. adjusting PID gain during simulation).
- Does **not** mean modifying parameters continuously in time.

**4\. Correct process for “tuning” a parameter during simulation**

To ensure clean, consistent state changes:

1. **Stop the simulation at an event instant  
    (typically after an integration step).**
2. **Change the tunable parameter(s).**
3. **Recompute all dependent parameters.**
4. **Resume the simulation using current variable values + new parameter values.**

**3.4 Dependency Information**

**1\. Extended Dependency Modeling**

- In **FMI 1.0**, only **output–input dependencies** could be specified (DirectDependency).
- In **FMI 2.0**, dependencies are extended to include:
    
    - Output dependencies on **state variables**
    - Derivative dependencies on **inputs**
    - Derivative dependencies on **state variables**
- All dependency information is contained inside the **ModelStructure** XML element.

**2\. Contents of ModelStructure**

ModelStructure contains **ordered lists** of:

- **Inputs**
- **Derivatives** (each linked to its state variable)
- **Outputs**

Each variable entry may include:

- stateDependencies → which state variables it depends on
- inputDependencies → which inputs it depends on
- stateFactorTypes → type of dependency per state variable
- inputFactorTypes → type of dependency per input

**3\. Types of Dependency Factors**

Dependencies may be marked as:

- **nonlinear** → nonlinear relationship
- **fixed** → linear, constant factor after initialization
- **discrete** → factor may change after events

This lets tools know **how** to treat Jacobian entries.

**4\. Why this matters**

- Helps tools:
    
    - Efficiently compute **Jacobians** (important for ODE/DAE solvers)
    - Use **sparse matrix techniques**
    - Detect **algebraic loops** between FMUs in co-simulation

[image]

[image]

**4 Examples**

**4.1 FMU as Force Element**

When we connect the FMUs:

- FMU 2 outputs phi and w → go into FMU 1 as inputs.
- FMU 1 computes torque based on these and its own states → sends torque back to FMU 2 as input.

At first glance, this looks like a **feedback loop**:

FMU2 → phi,w → FMU1 → torque → FMU2.Ba

But thanks to the ModelStructure info:

- FMU 1:
    
    - torque depends linearly on current phi and w (fixed factors).
- FMU 2:
    
    - phi and w **do not depend on the current torque** (inputDependencies="").

Therefore, at a given time step:

1. The master can compute **states in FMU 2** and then its outputs phi, w.
2. Feed these **as known inputs** into FMU 1.
3. FMU 1 computes torque.
4. torque goes back to FMU 2 as an input affecting *future* state derivatives, not the already computed phi, w at this instant.

So there is **no algebraic loop** (no “I need torque to compute phi, but I need phi to compute torque at the *same* time”). The loop is **dynamic**, not algebraic.

This allows:

- Simple explicit co-simulation schemes.
- Efficient Jacobian handling.
- The master algorithm to be confident that it does **not** need to solve a nonlinear algebraic system across the two FMUs at every step.
    

**Role of the derivative attributes**

The derivative="1" annotations (for w in both FMUs) add one more important consistency check:

- In **FMU 1**, w is declared as **the derivative of phi** (its first input).
- In **FMU 2**, w output is declared as **the derivative of phi** output.

So a coupling tool can verify:

- The w **exported by FMU 2** really is the time derivative of its phi.
- This matches exactly what **FMU 1 expects** as its second input.

If a modeler accidentally connected the wrong signal (e.g., another angle or velocity), the derivative structure could reveal inconsistencies.

**Big picture takeaway**

This example illustrates why FMI 2.0’s ModelStructure and dependency annotations are powerful:

- They make **interfaces semantically rich** (not just “some doubles”).
- They let tools:
    
    - detect **algebraic loops** or prove there are none,
    - use **sparse, structured Jacobians**,
    - ensure **derivative consistency** between connected FMUs.

In your thesis context, this is exactly the kind of metadata you want your framework to read and use when assembling hybrid systems (equation-based + FMUs + OpenSim + FEM).

If you’d like, I can help you:

- Translate this example into your own **pendulum + drive** FMUs, or
- Sketch how your SysSimX system class could use the ModelStructure info for loop detection and scheduling.

#### **2.4 FMI, FMUs, and Model Structure**

The Functional Mock-up Interface (FMI) standard provides a tool-independent standard for packaging and exchanging models as Functional Mock-up Units (FMUs). An FMU is a zip file containing:
- a modelDescription.xml (variables, units, causality, variability, dependencies),
- C functions implementing the FMI API for model exchange and co-simulation.
- binaries and additional resources.

FMUs which are exported from OpenModelica are of the FMI version 2.0 and the model description file provides the following information:
- Variable causality: input, output, parameter, calculated parameter, local, etc.
- Variable variability: continuous, discrete, constant, parameter, fixed, tunable
- Variable dependencies in the model structure section:
    - which output depends on which variables
    - which derivative depends on which variables
    - which initial unknonwn depends on which variables

**Model Structure for drive FMU:**
```xml
<ModelStructure>
    <Outputs>
      <!-- Output: torque (index 30) -->
      <Unknown 
        index="30" name="torque"
        dependencies="springDamper.phi_rel, springDamper.w_rel, alpha, omega, phi" 
        causality="(state), (state), input, input, input"
      />
    </Outputs>
</ModelStructure>
```

**Model Structure for pendulum FMU:**
```xml
<ModelStructure>
    <Outputs>
      <!-- Output: alpha (index 6) - angular acceleration -->
      <Unknown 
        index="6" name="alpha"
        dependencies="_D_outputAlias_q, torque" 
        causality="(state), input"
      />
    </Outputs>
</ModelStructure>
```

This structural information is used to
- detect algebraic loops and constraints between FMUs
- identify direct feedthrough (output depending on current input)