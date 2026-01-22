from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fmpy import extract, read_model_description
from fmpy.fmi2 import FMU2Slave
from fmpy.model_description import (
    ModelDescription,
    ModelVariable,
)  # ScalarVariable is ModelVariable in newer fmpy versions

from ..core.base import CoSimComponent
from ..core.port import PortSpec, PortType
from ..utilities.units import QuantityClass, to_pint_unit, ureg


# ----------------------------------------------------------------------------
# FMU Component Class
# ----------------------------------------------------------------------------
class FMUComponent(CoSimComponent):
    """
    FMU Co-Simulation Wrapper implementing the CoSimComponent interface.

    Supports:

    - FMI 2.0 CS-FMUs
    - REAL/INT/BOOL/STRING input and output ports
    - Units for REAL ports
    """

    # State of all FMU variables
    state: dict[str, Any]

    _md: ModelDescription
    _md_vars: dict[str, ModelVariable]
    _instance: FMU2Slave | None
    _unzipdir: str | None

    # Direct Feedthrough for output dependencies
    direct_feedthrough: dict[str, set[str]]

    # Cached value references per base type and causality
    _vrs_in_real: dict[str, int]
    _vrs_in_int: dict[str, int]
    _vrs_in_bool: dict[str, int]
    _vrs_in_str: dict[str, int]
    _vrs_in_bytes: dict[str, int]

    _vrs_out_real: dict[str, int]
    _vrs_out_int: dict[str, int]
    _vrs_out_bool: dict[str, int]
    _vrs_out_str: dict[str, int]
    _vrs_out_bytes: dict[str, int]

    def __init__(self, name: str, fmu_path: str, group: str | None = None):
        super().__init__(name=name, group=group)
        self._path = str(Path(fmu_path).resolve())
        self._md = read_model_description(self._path)
        self._md_vars = {var.name: var for var in self._md.modelVariables}
        if not self._md.coSimulation:
            raise RuntimeError(f"FMU '{fmu_path}' is not a Co-Simulation FMU.")
        if self._md.fmiVersion != "2.0":
            raise NotImplementedError(
                f"FMU '{fmu_path}' has unsupported FMI version '{self._md.fmiVersion}'. Only FMI 2.0 is supported."
            )
        self._instance = None
        self._unzipdir = None

        # Port specification containers
        self.input_specs: dict[str, PortSpec] = {}
        self.output_specs: dict[str, PortSpec] = {}
        self.direct_feedthrough = {}
        self._detect_direct_feedthrough()
        self._analyze_model_structure()

        # Build port specifications from model description (Real, Int, Bool, Str, Bytes)
        self._build_port_specs()

        # Cache value references map
        self._vrs_in_real = {}
        self._vrs_in_int = {}
        self._vrs_in_bool = {}
        self._vrs_in_str = {}
        self._vrs_out_real = {}
        self._vrs_out_int = {}
        self._vrs_out_bool = {}
        self._vrs_out_str = {}
        self._build_value_reference_map()

        # Parameters dictionary
        self.parameters: dict[str, ModelVariable] = {
            var.name: var
            for var in self._md.modelVariables
            if var.causality == "parameter"
            or var.causality == "calculatedParameter"
            or var.causality == "structuralParameter"
        }

    # ----------------------------------------------------------------------------
    # Build helper for port specifications and value reference maps
    # ----------------------------------------------------------------------------
    def _build_port_specs(self) -> None:
        for var in self._md.modelVariables:
            if var.causality not in ("input", "output"):
                continue
            direction: Literal["in", "out"] = "in" if var.causality == "input" else "out"
            port_type = _port_type_from_var(var)
            if port_type is None:
                continue
            unit = None
            if port_type == PortType.REAL and var.unit:
                unit = str(to_pint_unit(var.unit)) if var.unit else None

            spec = PortSpec(
                name=var.name,
                type=port_type,
                direction=direction,
                unit=unit,
                description=var.description,
            )
            if direction == "in":
                self.input_specs.update({var.name: spec})
            else:
                self.output_specs.update({var.name: spec})

    def _build_value_reference_map(self) -> None:
        for var in self._md.modelVariables:
            causality = var.causality
            if causality not in ("input", "output"):
                continue
            port_type = _port_type_from_var(var)
            value_reference = var.valueReference
            if causality == "input":
                if port_type == PortType.REAL:
                    self._vrs_in_real[var.name] = value_reference
                elif port_type == PortType.INT:
                    self._vrs_in_int[var.name] = value_reference
                elif port_type == PortType.BOOL:
                    self._vrs_in_bool[var.name] = value_reference
                elif port_type == PortType.STRING:
                    self._vrs_in_str[var.name] = value_reference

            elif causality == "output":
                if port_type == PortType.REAL:
                    self._vrs_out_real[var.name] = value_reference
                elif port_type == PortType.INT:
                    self._vrs_out_int[var.name] = value_reference
                elif port_type == PortType.BOOL:
                    self._vrs_out_bool[var.name] = value_reference
                elif port_type == PortType.STRING:
                    self._vrs_out_str[var.name] = value_reference

    def _analyze_model_structure(self) -> None:
        for output in self._md.outputs:
            out_var = output.variable.name
            deps = []
            for dep in output.dependencies:
                deps.append(dep.name)
            self.model_structure["outputs"][out_var] = deps

        for derivative in self._md.derivatives:
            der_var = derivative.variable.name
            deps = []
            for dep in derivative.dependencies:
                deps.append(dep.name)
            self.model_structure["derivatives"][der_var] = deps

        for init_unknown in self._md.initialUnknowns:
            init_var = init_unknown.variable.name
            deps = []
            for dep in init_unknown.dependencies:
                deps.append(dep.name)
            self.model_structure["initialUnknowns"][init_var] = deps

    def _detect_direct_feedthrough(self) -> None:
        for unknown in self._md.outputs:
            self.direct_feedthrough[unknown.variable.name] = set()
            for dep in unknown.dependencies:
                if dep.causality == "input":
                    self.direct_feedthrough[unknown.variable.name].add(dep.name)

    def _require_instance(self) -> FMU2Slave:
        """Return FMU instance or raise if not initialized."""
        if self._instance is None:
            raise RuntimeError(f"{self.name}: FMU instance not initialized")
        return self._instance

    # ----------------------------------------------------------------------------
    # Initialization
    # ----------------------------------------------------------------------------
    def _initialize_component(self, t0: float) -> None:
        """
        FMU-specific initialization (called by base-class).
        """
        self._initialize_ports_from_specs()
        self._unzipdir = extract(self._path)
        self._instance = FMU2Slave(
            instanceName=self.name,
            guid=self._md.guid,
            unzipDirectory=self._unzipdir,
            modelIdentifier=self._md.coSimulation.modelIdentifier,
        )
        self._instance.instantiate()
        self._instance.setupExperiment(startTime=t0)
        self._instance.enterInitializationMode()
        self._apply_parameters_starts()
        self._apply_input_starts()
        self._instance.exitInitializationMode()

    # ----------------------------------------------------------------------------
    # Initialization helpers
    # ----------------------------------------------------------------------------
    def _apply_parameters_starts(self) -> None:
        instance = self._require_instance()
        # batch parameters by base type
        real_vrs: list[int] = []
        real_vals: list[float] = []
        int_vrs: list[int] = []
        int_vals: list[int] = []
        bool_vrs: list[int] = []
        bool_vals: list[int] = []
        str_vrs: list[int] = []
        str_vals: list[str] = []

        for name, param in self.parameters.items():
            if param.start is None:
                continue
            if param._python_type is float:
                real_vrs.append(param.valueReference)
                real_vals.append(float(param.start))
            elif param._python_type is int:
                int_vrs.append(param.valueReference)
                int_vals.append(int(param.start))
            elif param._python_type is bool:
                bool_vrs.append(param.valueReference)
                bool_vals.append(1 if bool(param.start) else 0)
            elif param._python_type is str:
                str_vrs.append(param.valueReference)
                str_vals.append(str(param.start))

        if real_vrs:
            instance.setReal(real_vrs, real_vals)
        if int_vrs:
            instance.setInteger(int_vrs, int_vals)
        if bool_vrs:
            instance.setBoolean(bool_vrs, bool_vals)
        if str_vrs:
            instance.setString(str_vrs, str_vals)

    def _apply_input_starts(self) -> None:
        # If PortStates contain initial values (via specs or pre-set), push them into the FMU
        init_vals = {
            name: in_port.get()
            for name, in_port in self.inputs.items()
            if in_port.get() is not None
        }
        if init_vals:
            self.set_inputs(init_vals, t=None)

    # ----------------------------------------------------------------------------
    # Parameter and Initial Condition Handling
    # ----------------------------------------------------------------------------
    def set_parameters(self, **parameters) -> None:
        for name, val in parameters.items():
            var = self.parameters.get(name)
            if not var:
                raise KeyError(f"{self.name}: Unknown parameter '{name}'")
            var.start = val

    def get_parameters(self, *names: str) -> dict[str, Any]:
        if not names:
            return self.parameters.copy()

        result = {}
        for name in names:
            if name not in self.parameters:
                raise KeyError(
                    f"Unknown parameter '{name}' for component '{self.name}'. "
                    f"Available parameters: {list(self.parameters.keys())}"
                )
            result[name] = self.parameters[name]
        return result

    # ----------------------------------------------------------------------------
    # Input/output methods
    # ----------------------------------------------------------------------------
    def set_inputs(self, signals: dict[str, Any], t: float | None = None) -> None:
        if not signals:
            return
        instance = self._require_instance()

        # Set inputs by batch per type
        real_vrs: list[int] = []
        real_vals: list[float] = []
        int_vrs: list[int] = []
        int_vals: list[int] = []
        bool_vrs: list[int] = []
        bool_vals: list[int] = []
        str_vrs: list[int] = []
        str_vals: list[str] = []

        for name, val in signals.items():
            if name not in self.inputs:
                raise KeyError(f"{self.name}: Unknown input '{name}")
            port_state = self.inputs[name]
            port_state.set(value=val, t=t)
            spec = port_state.spec
            vr_map = _in_vr_map_for_type(self, spec.type)
            if name not in vr_map:
                continue
            vr = vr_map[name]

            # Convert to raw value
            if spec.type == PortType.REAL:
                q = port_state.get(as_unit=spec.unit)
                if q is None:
                    raise ValueError(f"{self.name}: REAL input '{name}' has no value")
                mag = float(q.magnitude) if isinstance(q, QuantityClass) else float(q)
                real_vrs.append(vr)
                real_vals.append(mag)
            elif spec.type == PortType.INT:
                if type(port_state.value) is not int:
                    raise TypeError(f"{self.name}: INT input '{name}' must be int")
                int_vrs.append(vr)
                int_vals.append(port_state.value)
            elif spec.type == PortType.BOOL:
                if not isinstance(port_state.value, bool):
                    raise TypeError(f"{self.name}: BOOL input '{name}' must be bool")
                bool_vrs.append(vr)
                bool_vals.append(1 if port_state.value else 0)
            elif spec.type == PortType.STRING:
                if not isinstance(port_state.value, str):
                    raise TypeError(f"{self.name}: STRING input '{name}' must be str")
                str_vrs.append(vr)
                str_vals.append(port_state.value)

        # Set the values by batch
        if real_vrs:
            instance.setReal(real_vrs, real_vals)
        if int_vrs:
            instance.setInteger(int_vrs, int_vals)
        if bool_vrs:
            instance.setBoolean(bool_vrs, bool_vals)
        if str_vrs:
            instance.setString(str_vrs, str_vals)

        # Evaluation of direct feedthrough outputs
        # self._do_step_internal(0.0, 0.0)
        self._update_output_states(t=None)

    def get_outputs(self) -> dict[str, Any]:
        return {
            name: out_port.get()
            for name, out_port in self.outputs.items()
            if out_port.get() is not None
        }

    def _update_output_states(
        self, t: float | None = None, event_names: list[str] | None = None
    ) -> None:
        instance = self._require_instance()
        # For each base type, batch get and set into PortStates as Quantities (REAL) or raw types
        if self._vrs_out_real:
            vrs = list(self._vrs_out_real.values())
            vals = instance.getReal(vrs)
            for name, val in zip(self._vrs_out_real.keys(), vals):
                spec = self.output_specs[name]
                q = (val * ureg(spec.unit)) if spec.unit else val
                self.outputs[name].set(q, t=t)

        if self._vrs_out_int:
            vrs = list(self._vrs_out_int.values())
            vals = instance.getInteger(vrs)
            for name, val in zip(self._vrs_out_int.keys(), vals):
                self.outputs[name].set(int(val), t=t)

        if self._vrs_out_bool:
            vrs = list(self._vrs_out_bool.values())
            vals = instance.getBoolean(vrs)
            for name, val in zip(self._vrs_out_bool.keys(), vals):
                self.outputs[name].set(bool(val), t=t)

        if self._vrs_out_str:
            vrs = list(self._vrs_out_str.values())
            vals = instance.getString(vrs)
            for name, val in zip(self._vrs_out_str.keys(), vals):
                self.outputs[name].set(str(val), t=t)

    # ----------------------------------------------------------------------------
    # Time stepping method
    # ----------------------------------------------------------------------------
    def _do_step_internal(self, t: float, dt: float) -> None:
        """
        Perform a single time step in the FMU.
        """
        self._require_instance().doStep(currentCommunicationPoint=t, communicationStepSize=dt)

    # ----------------------------------------------------------------------------
    # State methods for setting and getting simulation state
    # ----------------------------------------------------------------------------
    def set_state(self, state: dict[str, Any], t: float) -> None:
        instance = self._require_instance()
        instance.instantiate()
        instance.setupExperiment(startTime=t)
        instance.enterInitializationMode()

        params = {}
        inputs = {}
        for var_name, attr in state.items():
            if var_name in self.parameters:
                params[var_name] = attr["value"]
            if var_name in self.inputs:
                inputs[var_name] = attr["value"]

        self.set_parameters(**params)
        self._apply_parameters_starts()
        self.set_inputs(inputs, t=t)

        instance.exitInitializationMode()

        self._update_output_states(t)

    def get_state(self):
        """
        Return all FMU variables as a dictionary.
        1. Get all model variable names with variability not 'fixed'.
        2. For each variable, determine its type (REAL, INT, BOOL, STRING), causality, variability and unit.
        3. Use the appropriate get method from the FMU instance to retrieve the value based on its type.
        4. Store the variable name and its attributes and retrieved value in a dictionary.
        5. Return the dictionary containing all variable names and their attributes with values.
        """
        instance = self._require_instance()
        state = {}
        for var in self._md.modelVariables:
            if var.variability == "fixed" or var.causality == "local":
                continue
            name = var.name
            state[name] = {}
            state[name]["unit"] = var.unit
            vr = var.valueReference
            if var.type == "Real":
                val = instance.getReal([vr])[0]
                # if unit:
                #     val = val * ureg(unit)
                state[name]["value"] = val
            elif var.type == "Integer":
                val = instance.getInteger([vr])[0]
                state[name]["value"] = val
            elif var.type == "Boolean":
                val = instance.getBoolean([vr])[0]
                state[name]["value"] = bool(val)
            elif var.type == "String":
                val = instance.getString([vr])[0]
                state[name]["value"] = val
        self.state = state
        return self.state

    # ----------------------------------------------------------------------------
    # Evaluate outputs without time step for direct feedthrough
    # ----------------------------------------------------------------------------
    def evaluate_outputs(self, inputs: dict[str, Any], t: float | None = None) -> dict[str, Any]:
        # 1) Apply inputs without touching histories
        self.set_inputs(inputs, t=None)

        # 2) Do a zero-time step to update outputs
        step_time = self.t if t is None else t
        self._do_step_internal(t=step_time, dt=0.0)

        # 3) Read outputs
        self._update_output_states(t=None)

        # 4) Return outputs as raw values (Quantities converted to magnitudes)
        outputs = self.get_outputs()
        for key, value in outputs.items():
            value = value.magnitude if isinstance(value, QuantityClass) else value
            outputs[key] = value
        return outputs

    # ----------------------------------------------------------------------------
    # Reset method
    # ----------------------------------------------------------------------------
    def reset(self) -> None:
        """
        Reset the FMU component, releasing the FMU instance.
        After reset(), the component can be re-initialized by calling initialize().
        This properly terminates the FMU and frees resources.
        """
        if self._instance is not None:
            try:
                self._instance.terminate()
                self._instance.freeInstance()
            except Exception:
                pass  # Ignore errors during cleanup
            finally:
                self._instance = None

        # Clear runtime state (including _is_initialized via super)
        super().reset()
        self.inputs.clear()
        self.outputs.clear()

    def soft_reset(self, t0: float = 0.0) -> None:
        """
        Soft reset the FMU to initial state without releasing the instance.
        This uses FMI's reset() to return to post-instantiate state, then
        re-initializes. Useful for repeated simulations without FMU reload overhead.
        Args:
            t0: New start time for the simulation.
        """
        if self._instance is None:
            raise RuntimeError(f"{self.name}: Cannot soft_reset - FMU not initialized")

        # FMI reset() returns to Instantiated state
        self._instance.reset()

        # Must go through full initialization sequence
        self._instance.setupExperiment(startTime=t0)
        self._instance.enterInitializationMode()
        self._apply_parameters_starts()
        self._apply_input_starts()
        self._instance.exitInitializationMode()

        # Clear and update state
        self.history.clear()
        self.t = t0
        self._update_output_states(t=t0)
        self._record_outputs(t0)


# ----------------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------------
def _port_type_from_var(var: ModelVariable) -> PortType:
    if var._python_type is float:
        return PortType.REAL
    elif var._python_type is int:
        return PortType.INT
    elif var._python_type is bool:
        return PortType.BOOL
    elif var._python_type is str:
        return PortType.STRING
    else:
        raise NotImplementedError(
            f"Unsupported variable type '{var._python_type}' for variable '{var.name}'."
        )


def _in_vr_map_for_type(comp: FMUComponent, pt: PortType) -> dict[str, int]:
    return (
        comp._vrs_in_real
        if pt == PortType.REAL
        else comp._vrs_in_int
        if pt == PortType.INT
        else comp._vrs_in_bool
        if pt == PortType.BOOL
        else comp._vrs_in_str
    )
