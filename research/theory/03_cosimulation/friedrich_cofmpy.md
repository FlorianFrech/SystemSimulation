Friedrich, C., Lombana, A., Fasquel, J., Schlick, C., Bennani, N., & Mendil, M. (2025). CoFMPy: A Python Framework for Rapid Prototyping of FMI-based Digital Twins (p. 128). https://doi.org/10.1109/MODELS-C68889.2025.00027

# Compact Summary: CoFMPy Paper

**Paper:** *CoFMPy: A Python Framework for Rapid Prototyping of FMI-based Digital Twins*
**Core idea:** CoFMPy is an open-source Python framework for rapid prototyping of FMI-based Digital Twins. It combines FMU co-simulation, Python/AI integration, data-stream communication, and structured storage under a coordinator-based architecture. 

---

## 1) Comparison of Existing Open-Source Tools

| Tool                   | Main Focus                               | Strengths                                                                               | Positioning vs. CoFMPy                                                                                   |
| ---------------------- | ---------------------------------------- | --------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| **INTO-CPS / Maestro** | Cyber-physical systems co-simulation     | Advanced master algorithms, hierarchical FMUs, distributed co-simulation                | More mature and comprehensive; heavier toolchain                                                         |
| **OMSimulator**        | FMI/SSP-based composite model simulation | Large-scale composite models, SSP support, algebraic loop solvers, Lua/Python scripting | Strong orchestration backend; CoFMPy can integrate such tools                                            |
| **PyFMI**              | Python-based FMU execution               | Lightweight FMU simulation, often combined with Assimulo                                | More focused on FMU execution; CoFMPy adds coordination, communication, storage, and AI workflow support |
| **CoFMPy**             | Rapid DT prototyping in Python           | Lightweight, Python-native, FMI-based, AI-friendly, extensible                          | Designed as complementary research/prototyping framework rather than a full industrial DT platform       |

**Main gap addressed:** Existing tools either provide powerful co-simulation engines or lightweight FMU execution, but CoFMPy targets a middle ground: rapid Python-based Digital Twin prototyping with FMI support, AI integration, communication with a physical twin, and structured data management. 

---

## 2) Architecture and Design of CoFMPy

CoFMPy is organized around a **Digital Twin workflow** that connects simulation models, physical-twin data streams, and stored results.

### Main architectural blocks

| Block                                  | Role                                                                             |
| -------------------------------------- | -------------------------------------------------------------------------------- |
| **Master**                             | Executes FMI-based co-simulation and manages FMU interactions                    |
| **Communication / Datastream Handler** | Handles bidirectional data exchange between Digital Twin and Physical Twin       |
| **Storage**                            | Stores simulated and observed data, model parameters, and logs                   |
| **Coordinator**                        | Central administration unit that instantiates, connects, and controls all blocks |
| **Graph Engine**                       | Builds and manages the coupling graph                                            |
| **Config Parser**                      | Reads the user-defined JSON configuration                                        |

The architecture is configuration-driven. A JSON file defines FMUs, paths, step sizes, connections, co-simulation method, and graph-related settings. The framework can then build the coupling graph, instantiate models, connect data streams, execute the simulation, and store outputs. The diagram on page 5 shows this structure explicitly: configuration files enter the parser, the coordinator controls master/storage/datastream handling, and the graph engine manages the coupling graph. 

---

## 3) Master Component for Co-Simulation

The **Master Component** is the simulation core.

### Responsibilities

* Load and execute FMUs.
* Synchronize interacting submodels.
* Manage subsystem initialization.
* Advance the simulation in time.
* Resolve algebraic loops.
* Support multiple co-simulation strategies.

### Native master algorithms

CoFMPy’s native master is built on top of **FMPy** and supports:

* **Jacobi co-simulation**
* **Gauss-Seidel co-simulation**
* **Fixed-point schemes** for algebraic loop resolution
* **Fixed-point initialization** to obtain a consistent initial state

The master uses the **coupling graph** constructed by the coordinator to detect algebraic loops automatically. CoFMPy can also integrate external orchestration backends with Python APIs, such as **Gemseo** or **OMSimulator**. 

### Python FMU proxy

A notable design element is the **Python FMU proxy**. It mimics the FMI co-simulation interface but executes native Python code. This allows quick integration of:

* AI models, e.g. PyTorch, TensorFlow, JAX
* Logical components, e.g. sums, switches
* Prototype models before formal FMU export

After validation, such Python components can be exported as FMUs using tools like **PythonFMU** or **unifmu**. 

---

## 4) Communication Block for Data Stream Management

The communication block manages data exchange between the **Digital Twin (DT)** and the **Physical Twin (PT)**.

### Default implementation

CoFMPy uses **Apache Kafka** as the default communication backend.

### Functionality

* Receives sensor data from the physical twin.
* Sends control or actuation commands back to the physical twin.
* Supports low-latency, high-throughput data streaming.
* Represents message payloads as timestamp-indexed records.
* Maps streamed variables to FMU inputs and outputs through the coordinator and configuration file.
* Provides an offline mode for replaying local time-series files.

### Extensibility

The communication layer is modular. Users can implement alternative datastream backends by subclassing the base data-stream API, e.g.:

* RabbitMQ
* proprietary protocols
* other messaging systems

This makes the communication block suitable for both online DT operation and offline development/testing. 

---

## 5) Storage Component

The storage component provides persistent data management for Digital Twin workflows.

### Stored data types

* Physical-twin observation data
* Simulation outputs
* Model parameters
* Interaction logs
* Historical time-series data

### Purpose

The storage layer enables:

* long-term tracking of simulated and observed behavior,
* post-processing,
* model calibration,
* iterative improvement of the DT,
* reproducibility of experiments.

For prototyping, CoFMPy uses **local log files**, avoiding the need for cloud infrastructure or complex database setup. Advanced users can implement custom storage components. 

---

## 6) The Coordinator

The **Coordinator** is the central orchestration unit of CoFMPy.

### Main responsibilities

* Parse the JSON configuration file.
* Instantiate the master, communication, and storage components.
* Load FMUs and Python FMU proxies.
* Build the coupling graph.
* Connect FMUs according to the defined topology.
* Launch datastream services when required.
* Route data between simulation, storage, and communication blocks.
* Run co-simulation steps.
* Handle algebraic loops during simulation.
* Propagate outputs through the system.
* Log relevant variables.
* Return results after simulation completion.
* Provide dependency-graph visualization.

In practical terms, the coordinator turns a declarative JSON setup into an executable Digital Twin simulation. It is the layer that makes CoFMPy usable as a framework rather than only a collection of simulation utilities. 

---

## Key Takeaway

CoFMPy is best understood as a **Python-native orchestration framework for FMI-based Digital Twin prototyping**. Its contribution is not a new numerical solver alone, but the integration of:

* FMI/FMUs,
* co-simulation master algorithms,
* algebraic-loop handling,
* Python-native AI components,
* Kafka-based communication,
* local storage,
* configuration-driven execution,
* and dependency-graph visualization.

Its main limitation is that Python execution restricts hard real-time applicability, and fully distributed execution would require integration with higher-level orchestrators such as Maestro.

---------

# CoFmuPy — Key Features and Capabilities

> Naming note: the documentation uses **CoFmuPy**, while the paper previously cited uses **CoFMPy**. The following summary uses the documentation spelling.

## 1. Core Purpose

**CoFmuPy** is a Python library for rapid prototyping of **Digital Twins** based on the co-simulation of **Functional Mock-up Units (FMUs)**. Its main focus is the orchestration of multiple interacting FMUs, including algebraic-loop handling and data exchange between simulation components. ([irt-saint-exupery.github.io][1])

It is therefore primarily a **Python-based FMI co-simulation coordination framework**, not a general heterogeneous simulation framework for arbitrary simulation backends.

---

## 2. Key Features

### 2.1 FMI-Based Co-Simulation of FMUs

CoFmuPy builds on **FMPy** as the FMI-compliant backend and adds system-level orchestration around it. It allows users to configure and execute systems composed of multiple FMUs. ([irt-saint-exupery.github.io][1])

**Capabilities:**

* load FMUs from a JSON configuration,
* define FMU inputs, outputs, step sizes, and initialization values,
* execute coupled FMUs step-by-step or until a final simulation time,
* retrieve simulation results through the coordinator API. ([irt-saint-exupery.github.io][2])

---

### 2.2 Advanced Master Coordination

The central capability of CoFmuPy is its **master component** for coordinating multiple interacting FMUs.

**Supported coordination mechanisms:**

* **Jacobi co-simulation**
* **Gauss-Seidel co-simulation**
* iterative solution of algebraic loops
* fixed-point strategies
* optional rollback-related coordination
* automatic propagation of FMU outputs to connected FMU inputs

The master stores FMU configurations, connections, execution order, current simulation time, inputs, outputs, and results. It provides methods for initialization, input setting, stepping, result collection, and algebraic-loop solving. ([irt-saint-exupery.github.io][3])

---

### 2.3 Algebraic Loop Handling

CoFmuPy can detect and resolve cyclic dependencies between FMUs. According to the documentation, algebraic loops are solved using fixed-point strategies and can be handled with Jacobi or Gauss-Seidel schemes. ([irt-saint-exupery.github.io][1])

**Practical meaning:**

* tightly coupled FMU networks can be simulated without manually breaking all feedback paths,
* cyclic FMU dependencies are treated at the master level,
* the user can configure whether the loop solution should be iterative.

---

### 2.4 Explicit Data Exchange and Synchronization

CoFmuPy provides explicit control over data routing between:

* FMU → FMU,
* external data source → FMU,
* FMU → external data sink.

The JSON configuration supports connections between FMUs, from external data sources to FMUs, and from FMUs to sinks such as files or Kafka streams. ([irt-saint-exupery.github.io][4])

Supported external data sources include:

* literal time-value definitions,
* CSV files,
* Kafka streams,
* custom data stream handlers. ([irt-saint-exupery.github.io][5])

---

### 2.5 Data Stream Handling

CoFmuPy includes a **data stream handler module** that abstracts live or recorded input streams for Digital Twin prototypes. It allows switching between CSV, Kafka, and local in-memory streams through a common API. ([irt-saint-exupery.github.io][6])

**Capabilities:**

* unified API for time-based data retrieval,
* alias mapping between internal FMU variables and external stream variables,
* interpolation of stream values,
* dynamic handler creation via factory method,
* extensibility through custom handler subclasses. ([irt-saint-exupery.github.io][6])

This is especially relevant for Digital Twin scenarios where measured physical-twin data must be injected into the simulation.

---

### 2.6 Kafka-Based Communication

CoFmuPy supports Kafka streams as both input sources and output sinks.

**Use cases:**

* receive physical-twin measurements,
* feed sensor data into FMUs,
* publish FMU outputs to external consumers,
* connect simulation workflows to external monitoring or control systems.

Kafka data can be configured directly in the JSON file by specifying the broker URI, consumer group, topic, variable name, and interpolation behavior. ([irt-saint-exupery.github.io][5])

---

### 2.7 Declarative JSON Configuration

A CoFmuPy simulation is defined through a structured **JSON configuration file**. The configuration contains three main sections:

1. **FMUs**
   Defines FMU IDs, paths, step sizes, initialization values, and optional metadata.

2. **Connections**
   Defines the connection graph between FMUs and external data sources/sinks.

3. **Global settings**
   Defines settings such as the co-simulation method, iterative loop solving, edge separator, and root path. ([irt-saint-exupery.github.io][4])

This makes experiments reproducible and easy to modify without changing the Python source code.

---

### 2.8 Python and AI Component Integration

CoFmuPy supports the integration of Python-based components, including machine-learning or control-logic components, directly into the co-simulation loop without immediate FMU export. The documentation frames this as enabling AI framework integration while keeping the overall workflow FMI-oriented. ([irt-saint-exupery.github.io][1])

**Practical use:**

* prototype ML discrepancy models,
* test Python control logic,
* integrate AI components before packaging them as FMUs.

---

### 2.9 Graph Visualization and GUI Direction

CoFmuPy provides graph-based visualization of the simulated system through its graph engine. The getting-started guide shows that the coordinator can visualize the connection graph after loading a JSON configuration. ([irt-saint-exupery.github.io][2])

A graphical user interface is announced as under development. Planned GUI capabilities include drag-and-drop system construction, FMU interconnection, remote interface configuration, algorithm selection, and co-simulation control. ([irt-saint-exupery.github.io][1])

---

## 3. Summary Table

| Capability                                            | CoFmuPy Support                                   |
| ----------------------------------------------------- | ------------------------------------------------- |
| FMU execution                                         | Yes, via FMPy                                     |
| FMI-based co-simulation                               | Yes                                               |
| Multiple coupled FMUs                                 | Yes                                               |
| Jacobi / Gauss-Seidel coordination                    | Yes                                               |
| Algebraic-loop handling                               | Yes, fixed-point based                            |
| JSON-based configuration                              | Yes                                               |
| External data sources                                 | Literal values, CSV, Kafka, custom handlers       |
| External data sinks                                   | CSV and Kafka                                     |
| Kafka communication                                   | Yes                                               |
| Python / AI components                                | Yes, through Python proxy-style integration       |
| Graph visualization                                   | Yes                                               |
| GUI                                                   | Announced / under development                     |
| Native OpenSim backend                                | Not a core capability                             |
| Native FEM backend                                    | Not a core capability                             |
| Hybrid event handling with zero-crossing localization | Not presented as a central documented capability  |
| Multi-fidelity runtime switching                      | Not presented as a central documented capability  |
| General component abstraction beyond FMUs             | Limited compared with a general wrapper framework |

---

# Relevance for syssimx Backend Decision

## Why CoFmuPy Is Relevant

CoFmuPy is clearly relevant as a **state-of-the-art open-source FMI co-simulation framework**. It covers several aspects that overlap with syssimx:

* Python-based framework design,
* FMU orchestration,
* master algorithms,
* algebraic-loop handling,
* graph-based system representation,
* JSON-based reproducibility,
* external data streams for Digital Twin workflows.

It is therefore a useful comparison tool in the thesis, especially in the **state-of-the-art / gap analysis** section.

---

## Why CoFmuPy Was Not an Appropriate Backend for syssimx

For syssimx, the central thesis contribution is not only FMU orchestration. The framework targets a broader problem: **hybrid heterogeneous system simulation** with interchangeable components from Modelica/FMUs, OpenSim, and FEM/NGSolve, plus event handling and multi-model switching.

CoFmuPy would not be the ideal backend because its documented core abstraction is still centered on **FMU-based Digital Twin co-simulation**.

### Main reasons

| Requirement of syssimx                              |     CoFmuPy Fit | Reason                                                                          |
| --------------------------------------------------- | --------------: | ------------------------------------------------------------------------------- |
| Integrate Modelica via FMI                          |          Strong | CoFmuPy is FMI/FMUs focused                                                     |
| Integrate OpenSim components                        |            Weak | Not a documented core backend                                                   |
| Integrate FEM/NGSolve components                    |            Weak | Not a documented core backend                                                   |
| Use arbitrary Python component wrappers             |         Partial | Python/AI components are supported, but the framework remains FMU-centered      |
| Hybrid event detection and localization             |  Weak / unclear | Not the central documented focus                                                |
| Zero-crossing detection with rollback and bisection |  Weak / unclear | Not described as a core framework capability                                    |
| Event chains and superdense-time handling           |            Weak | Not documented as a main feature                                                |
| Runtime multi-model switching                       |            Weak | Not documented as a main feature                                                |
| General component interface for heterogeneous tools |  Weak / partial | CoFmuPy focuses on FMUs and data streams                                        |
| Thesis-specific algorithm development               | Weak as backend | A backend would hide or constrain the implementation of the thesis contribution |

---

## Compact Thesis Argument

```markdown
CoFmuPy is a Python-based framework for rapid prototyping of FMI-based Digital Twins. 
It provides a high-level coordinator for FMU co-simulation, master algorithms based on 
Jacobi and Gauss-Seidel schemes, fixed-point handling of algebraic loops, JSON-based 
system configuration, data-stream integration via CSV and Kafka, result storage, graph 
visualization, and the possibility to integrate Python or AI components into the 
co-simulation loop.

However, CoFmuPy is primarily designed around FMI-based co-simulation of FMUs and 
Digital Twin data-stream management. The scope of syssimx is broader: it aims to 
orchestrate heterogeneous simulation backends, including Modelica/FMUs, OpenSim, and 
FEM/NGSolve components, through a common component interface. In addition, syssimx 
implements thesis-specific mechanisms for hybrid co-simulation, including event 
indicators, zero-crossing detection, rollback-based bisection for event localization, 
event propagation, event chains, simultaneous-event handling, and runtime switching 
between model fidelities.

For this reason, CoFmuPy was considered relevant as an open-source FMI co-simulation 
tool, but not selected as the backend for syssimx. Using it as the core backend would 
have constrained the framework to an FMU-centric architecture and would not have 
provided the required flexibility for integrating non-FMU tools and implementing the 
hybrid co-simulation mechanisms that form part of the thesis contribution.
```

---

## Short Evaluation Statement

```markdown
CoFmuPy is well suited for FMI-centered Digital Twin prototyping with FMU coordination, 
algebraic-loop handling, Kafka/CSV data streams, and reproducible JSON configuration. 
It was not chosen as the backend for syssimx because syssimx requires a more general 
heterogeneous component architecture, explicit support for OpenSim and FEM backends, 
hybrid event handling, rollback-based event localization, and multi-fidelity runtime 
switching beyond the documented FMU-centric scope of CoFmuPy.
```

[1]: https://irt-saint-exupery.github.io/CoFmuPy/ "CoFmuPy"
[2]: https://irt-saint-exupery.github.io/CoFmuPy/getting_started/ "Getting started - CoFmuPy"
[3]: https://irt-saint-exupery.github.io/CoFmuPy/api/master/ "Master - CoFmuPy"
[4]: https://irt-saint-exupery.github.io/CoFmuPy/user_guide/configuration_file/ "Configuration file - CoFmuPy"
[5]: https://irt-saint-exupery.github.io/CoFmuPy/user_guide/data_sources/ "Managing data sources - CoFmuPy"
[6]: https://irt-saint-exupery.github.io/CoFmuPy/user_guide/advanced/stream_handler_module/ "Data Stream Handler Module - CoFmuPy"
