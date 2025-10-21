from __future__ import annotations
from typing import Any, Dict, Optional, Tuple, List
from pathlib import Path

from fmpy import read_model_description, extract
from fmpy.model_description import ScalarVariable, ModelDescription # ScalarVariable is ModelVariable in newer fmpy versions
from fmpy.fmi2 import FMU2Slave

from .base import CoSimComponent
from .port import PortSpec, PortState, PortType
from ..utilities.units import ureg, Quantity, to_pint_unit

class FMUComponent(CoSimComponent):
    """
    FMU Co-Simulation Wrapper implementing the CoSimComponent interface.
    Supports:
        - FMI 2.0 CS-FMUs
        - REAL/INT/BOOL/STRING input and output ports
        - Units for REAL ports
    """

    _md: ModelDescription
    _instance: Optional[FMU2Slave]
    _unzipdir: Optional[str]

    # Cached value references per base type and causality
    _vrs_in_real: Dict[str, int]
    _vrs_in_int: Dict[str, int]
    _vrs_in_bool: Dict[str, int]
    _vrs_in_str: Dict[str, int]
    _vrs_in_bytes: Dict[str, int]

    _vrs_out_real: Dict[str, int]
    _vrs_out_int: Dict[str, int]
    _vrs_out_bool: Dict[str, int]
    _vrs_out_str: Dict[str, int]
    _vrs_out_bytes: Dict[str, int]

    def __init__(self, name: str, fmu_path: str, group: Optional[str] = None):
        super().__init__(name=name, group=group)
        self._path = str(Path(fmu_path).resolve())
        self._md = read_model_description(self._path)
        if not self._md.coSimulation:
            raise RuntimeError(f"FMU '{fmu_path}' is not a Co-Simulation FMU.")
        if self._md.fmiVersion != "2.0":
            raise NotImplementedError(f"FMU '{fmu_path}' has unsupported FMI version '{self._md.fmiVersion}'. Only FMI 2.0 is supported.")
        self._instance = None
        self._unzipdir = None

        # Port specification containers
        self.input_specs: Dict[str, PortSpec] = {}
        self.output_specs: Dict[str, PortSpec] = {}

        # Build port specifications from model description (Real, Int, Bool, Str, Bytes)
        self._build_port_specs()

        # Cache value references map
        self._vrs_in_real = {}; self._vrs_in_int = {}; self._vrs_in_bool = {}; self._vrs_in_str = {}
        self._vrs_out_real = {}; self._vrs_out_int = {}; self._vrs_out_bool = {}; self._vrs_out_str = {}
        self._build_value_reference_map()

        # Parameters dictionary
        self.parameters: Dict[str, ScalarVariable] = {
            var.name: var for var in self._md.modelVariables if var.causality == "parameter"
        }

    # -------------------------------------------------------------------------------
    # Build Port Specifications
    def _build_port_specs(self) -> None:
        for var in self._md.modelVariables:
            if var.causality not in ("input", "output"):
                continue
            direction = "in" if var.causality == "input" else "out"           
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
                unit= unit,
                description=var.description
            )
            if direction == "in":
                self.input_specs[var.name] = spec
            else:
                self.output_specs[var.name] = spec
    
    def _build_value_reference_map(self) -> None:
        for var in self._md.modelVariables:
            causality = var.causality
            if causality not in ("input", "output"):
                continue
            port_type = _port_type_from_var(var)
            value_reference = var.valueReference
            if causality == "input":
                if   port_type == PortType.REAL:   self._vrs_in_real[var.name] = value_reference
                elif port_type == PortType.INT:    self._vrs_in_int[var.name]  = value_reference
                elif port_type == PortType.BOOL:   self._vrs_in_bool[var.name] = value_reference
                elif port_type == PortType.STRING: self._vrs_in_str[var.name]  = value_reference

            elif causality == "output":
                if   port_type == PortType.REAL:   self._vrs_out_real[var.name] = value_reference
                elif port_type == PortType.INT:    self._vrs_out_int[var.name]  = value_reference
                elif port_type == PortType.BOOL:   self._vrs_out_bool[var.name] = value_reference
                elif port_type == PortType.STRING: self._vrs_out_str[var.name]  = value_reference

    # -------------------------------------------------------------------------------
    # Lifecycle
    def initialize(self, t0: float) -> None:
        # Create Port States
        self.inputs = {name: PortState(spec=spec) for name, spec in self.input_specs.items()}
        self.outputs = {name: PortState(spec=spec) for name, spec in self.output_specs.items()}

        # Unzip and instantiate FMU
        self._unzipdir = extract(self._path)
        self._instance = FMU2Slave(instanceName=self.name,
                                   guid=self._md.guid,
                                   unzipDirectory=self._unzipdir,
                                   modelIdentifier=self._md.coSimulation.modelIdentifier)
        self._instance.instantiate()
        self._instance.setupExperiment(startTime=t0)
        self._instance.enterInitializationMode()

        # Apply parameters
        self._apply_parameters_starts()

        # Apply initial input starts if present in specs/PortStates
        self._apply_input_starts()

        self._instance.exitInitializationMode()

        # Initialize output PortStates with current FMU values (t0)
        self._update_output_states(t0)

    def set_parameters(self, **parameters) -> None:
        for name, val in parameters.items():
            var = self.parameters.get(name)
            if not var:
                raise KeyError(f"{self.name}: Unknown parameter '{name}'")
            var.start = val

    def set_inputs(self, signals: Dict[str, Any], t:Optional[float]) -> None:
        if not signals: return
        assert self._instance is not None

        # Set inputs by batch per type
        real_vrs: List[int] = []; real_vals: List[float] = []
        int_vrs: List[int] = []; int_vals: List[int] = []
        bool_vrs: List[int] = []; bool_vals: List[int] = []
        str_vrs: List[int] = []; str_vals: List[str] = []

        for name, val in signals.items():
            if name not in self.inputs:
                raise KeyError(f"{self.name}: Unknown input '{name}")
            port_state = self.inputs[name]
            port_state.set(value=val, t=t)
            spec = port_state.spec
            vr_map = _in_vr_map_for_type(self, spec.type)
            if name not in vr_map:
                raise KeyError(f"{self.name}: '{name}' is not an FMU input")
            vr = vr_map[name]
            
            # Convert to raw value
            if spec.type == PortType.REAL:
                q = port_state.get(as_unit=spec.unit)
                mag = float(q.magnitude) if isinstance(q, Quantity) else float(q)
                real_vrs.append(vr); real_vals.append(mag)
            elif spec.type == PortType.INT:
                if type(port_state.value) is not int:
                    raise TypeError(f"{self.name}: INT input '{name}' must be int")
                int_vrs.append(vr); int_vals.append(port_state.value)
            elif spec.type == PortType.BOOL:
                if not isinstance(port_state.value, bool):
                    raise TypeError(f"{self.name}: BOOL input '{name}' must be bool")
                bool_vrs.append(vr); bool_vals.append(1 if port_state.value else 0)
            elif spec.type == PortType.STRING:
                if not isinstance(port_state.value, str):
                    raise TypeError(f"{self.name}: STRING input '{name}' must be str")
                str_vrs.append(vr); str_vals.append(port_state.value)

        # Set the values by batch    
        if real_vrs:  self._instance.setReal(real_vrs, real_vals)
        if int_vrs:   self._instance.setInteger(int_vrs, int_vals)
        if bool_vrs:  self._instance.setBoolean(bool_vrs, bool_vals)
        if str_vrs:   self._instance.setString(str_vrs, str_vals)

    def do_step(self, t: float, dt: float) -> Dict[str, Any]:
        assert self._instance is not None
        self._instance.doStep(currentCommunicationPoint=t, communicationStepSize=dt)
        self._update_output_states(t+dt)
        return self.get_outputs()

    def get_outputs(self) -> Dict[str, Any]:
        return {name: out_port.get() for name, out_port in self.outputs.items() if out_port.get() is not None}
    
    def set_state(self, state):
        # TODO: Implement method
        pass

    def get_state(self):
        # TODO: Implement method
        pass

    def reset(self):
        if self._instance is not None:
            try:
                self._instance.reset()
            finally:
                self._instance = None

    # --------------------------------------------------------------
    # Helpers
    def _apply_parameters_starts(self) -> None:
        assert self._instance is not None
        # batch parameters by base type
        real_vrs: List[int] = []; real_vals: List[float] = []
        int_vrs: List[int] = []; int_vals: List[int] = []
        bool_vrs: List[int] = []; bool_vals: List[int] = []
        str_vrs: List[int] = []; str_vals: List[str] = []

        for name, param in self.parameters.items():
            if param.start is None:
                continue
            if param._python_type == float:
                real_vrs.append(param.valueReference); real_vals.append(float(param.start))
            elif param._python_type == int:
                int_vrs.append(param.valueReference); int_vals.append(int(param.start))
            elif param._python_type == bool:
                bool_vrs.append(param.valueReference); bool_vals.append(1 if bool(param.start) else 0)
            elif param._python_type == str:
                str_vrs.append(param.valueReference); str_vals.append(str(param.start))

        if real_vrs: self._instance.setReal(real_vrs, real_vals)
        if int_vrs: self._instance.setInteger(int_vrs, int_vals)
        if bool_vrs: self._instance.setBoolean(bool_vrs, bool_vals)
        if str_vrs: self._instance.setString(str_vrs, str_vals)
    
    def _apply_input_starts(self) -> None:
        # If PortStates contain initial values (via specs or pre-set), push them into the FMU
        init_vals = {name: in_port.get() for name, in_port in self.inputs.items() if in_port.get() is not None}
        if init_vals:
            self.set_inputs(init_vals, t=None)
    
    def _update_output_states(self, t: float) -> None:
            assert self._instance is not None

            # For each base type, batch get and set into PortStates as Quantities (REAL) or raw types
            if self._vrs_out_real:
                vrs = list(self._vrs_out_real.values())
                vals = self._instance.getReal(vrs)
                for name, val in zip(self._vrs_out_real.keys(), vals):
                    spec = self.output_specs[name]
                    q = (val * ureg(spec.unit)) if spec.unit else val
                    self.outputs[name].set(q, t=t)

            if self._vrs_out_int:
                vrs = list(self._vrs_out_int.values())
                vals = self._instance.getInteger(vrs)
                for name, val in zip(self._vrs_out_int.keys(), vals):
                    self.outputs[name].set(int(val), t=t)

            if self._vrs_out_bool:
                vrs = list(self._vrs_out_bool.values())
                vals = self._instance.getBoolean(vrs)
                for name, val in zip(self._vrs_out_bool.keys(), vals):
                    self.outputs[name].set(bool(val), t=t)

            if self._vrs_out_str:
                vrs = list(self._vrs_out_str.values())
                vals = self._instance.getString(vrs)
                for name, val in zip(self._vrs_out_str.keys(), vals):
                    self.outputs[name].set(str(val), t=t)

# --------------------------------------------------------------
# Helpers
def _port_type_from_var(var: ModelVariable) -> PortType:
    if   var._python_type == float: return PortType.REAL
    elif var._python_type == int:   return PortType.INT
    elif var._python_type == bool:  return PortType.BOOL
    elif var._python_type == str:   return PortType.STRING
    else:
        raise NotImplementedError(f"Unsupported variable type '{var._python_type}' for variable '{var.name}'.")
    
def _in_vr_map_for_type(comp: FMUComponent, pt: PortType) -> Dict[str, int]:
    return (
        comp._vrs_in_real if pt == PortType.REAL   else
        comp._vrs_in_int  if pt == PortType.INT    else
        comp._vrs_in_bool if pt == PortType.BOOL   else
        comp._vrs_in_str  
    )