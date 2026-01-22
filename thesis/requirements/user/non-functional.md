# Non Functional User Requirements

| **U-ID** | **Requirement** | **Rationale** | **Priority (Shall/Should/Will Not)** |
|--------|-----------------|---------------|--------------------------------------|
| NFR_01 | The framework should provide **clear error messages and logs.** | Helps users diagnose and fix issues quickly without digging into source code. | Should |
| NFR_02 | **Documentation and examples** should help users to build and simulate models. | Improves usability and lowers learning curve for new users. | Should |
| NFR_03 | **Visual outputs for system hierarchy and live plotting** must be intuitive and easy to navigate. | Enhances understanding of system structure and simulation results. | Shall |
| NFR_04 | **Simulation performance** must be acceptable for small to medium-sized systems. | Ensures framework is usable without requiring high-end hardware. | Shall |
| NFR_05 | Must **not exceed typical desktop/notebook memory limits** for moderate use cases. | Keeps resource usage practical for most users. | Shall |
| NFR_06 | The system must **detect faulty configurations and prevent inconsistent simulations.** | Prevents invalid results and wasted computation time. | Shall |
| NFR_07 | System must work on **standard developer environments.** | Broadens usability and reduces environment-specific issues. Intercompatibility of the used packages and modules is required. | Shall |
| NFR_08 | Must **integrate with common Python simulation libraries like FMPy and OMPython.** | Facilitates interoperability with existing simulation workflows. | Should |
| NFR_09 | Must **follow good development practices** (modular design, documentation, unit tests). | Ensures maintainability and ease of contribution. | Shall |
| NFR_10 | Code and models must **comply with open-source licenses.** | Ensures legal compliance and reusability. | Shall |
| NFR_11 | Must **cite reused libraries properly.** | Gives credit to original authors and avoids legal issues. | Shall |
| NFR_12 | Must provide different functionality for **different user roles (e.g., expert vs. standard users).** | Ensures that the system meets the varying needs of its users. Experts want to customize the simulation, while standard users need simplicity and should only change basic parameters. | Shall |