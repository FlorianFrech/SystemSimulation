Petridis, K., & Clauß, C. (2015). *Test of Basic Co-Simulation Algorithms Using FMI*. 865–872. [https://doi.org/10.3384/ecp15118865](https://doi.org/10.3384/ecp15118865)

# Introduction

- Co-SImulation as the commonly used method for complete system simulation, two types:
    
    - Direct coupling between tools
    - Export and import of the simulation model into the other tool
- Algorithms used for coupling are strongly coupled with the interface
- FMI was developed as an interface standard which allows the exchange and co-simulation of models
    
    - Allows the use of different coupling algorithms within the same interface
    - Coupling algorithm are not part of the standard

**Coupling Cases**

- Simulator specific model with one imported FMU
- Simulator specific model with more than one imported FMU
- Software in the Loop platform with control algorithms and one or more FMU plant models

**Types of Coupling**

- Coupling in one direction or with feedback (cycle)
- Analog coupling quantities (displacement, force) or discrete coupling quantities (sensor or actor signals)

**Simulation Model Properties**

- Algebraic system without solver
- Differential or Differential-Algebraic Equation including solver (based on constant or variable step size) or without solver  
    
- **Gauss-Jacobi method:**
    
    - simulators can operate in parallel, since all simulators access the same vectors of coupling variables
- **Gauss-Seidel method:**
    
    - needs an a priori defined calling sequence $r$ of the simulators
    - Each simulator uses the results of the already called simulators
    - One iteration step is finished if all simulators have been called
- **Calling sequence $r$** us defined by analyzing the input and output variables of SUs (same as analyzing the connection graph)
    
    - Sequence shall be chosen such that as many as possible input coupling variables are updated before the simulation of each SU
- **Gauss-Seidel with one iteration** is a special case where there are no SUs with direct feed-through, each SU takes input values only which are computed before called simulators
- FMI is designed to exchanges values at certain time points (communication points)
- Simulation of an SU within a communication interval is performed by FMI doStep function
- Gauss-Jacobi and Newton-Rhapson methods need repeated simulations of communication intervals
    
    - FMUState must be stored with GetFMUState and used again SetFMUState
- Methods must be chosen depending on the simulation of the properties of the simulation task and the restrictions of the FMUs to be coupled
- Master should offer many coupling algorithms to be able to choose the best suitable one for a special task