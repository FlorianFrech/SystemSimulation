from typing import Any, Dict, Optional, Tuple, List
from fmpy import read_model_description, extract
from fmpy.model_description import ModelVariable, ModelDescription
from fmpy.fmi2 import FMU2Slave

from .port import RealPort, IntPort, BoolPort, StringPort
from .base import CoSimComponent
from .units import UREG, to_pint_unit

class FMUComponent(CoSimComponent):
    """
    Wrapper around an FMU to implement the CoSimComponent interface.
    """
    parameters: Dict[str, ModelVariable]
    _vars: Dict[str, ModelVariable]
    _instance: FMU2Slave

    def __init__(self, name: str, fmu_path: str, group: Optional[str] = None):
        """
        Constructor for the FMUComponent class.
            :param name: Name of the component instance.
            :param fmu_path: Path to the FMU file.
        """
        self.name = name
        self.group = group
        self.path = fmu_path
        self.inputs = {}
        self.outputs = {}
        self.parameters = None
        self._md = read_model_description(fmu_path)
        self._vars = self._md.modelVariables
        self._instance = None
        
        # Initialize input/outputs and parameters with units
        self._set_up_units()
        self.parameters = {var.name: var for var in self._md.modelVariables if var.causality == "parameter"}

        # Store value references for quick access
        self._vrs_in = {var.name: var.valueReference for var in self._md.modelVariables if var.causality == "input"}
        self._vrs_out = {var.name: var.valueReference for var in self._md.modelVariables if var.causality == "output"}
        self._vrs_param = {var.name: var.valueReference for var in self._md.modelVariables if var.causality == "parameter"}

        # Setup ports
        self._set_up_ports()

        # Set the label for visualization
        self._set_up_label()

        # Instantiate the FMU
        self._instantiate()
    
    def _set_up_ports(self):
        """
        Reads the model variables with causality "input" and "output" and initializs the Ports based on the type.
        """
        # 1) Create Input Ports
        inputs = [var for var in self._md.modelVariables if var.causality == "input"]
        for var in inputs:
            if var.type == "Real":
                self.inputs[var.name] = RealPort(name=var.name, 
                                                 value=var.start,
                                                 unit=var.unit,
                                                 description=var.description)
            if var.type == "Integer":
                self.inputs[var.name] = IntPort(name=var.name,
                                                value=var.value,
                                                description=var.description
                                                )
            # TODO: Add Boolean and String    

        # 2) Create Output Ports
        outputs = [var for var in self._md.modelVariables if var.causality == "output"]
        for var in outputs:
            if var.type == "Real":
                self.outputs[var.name] = RealPort(name=var.name, 
                                                 value=var.start,
                                                 unit=var.unit,
                                                 description=var.description)
            if var.type == "Integer":
                self.outputs[var.name] = IntPort(name=var.name,
                                                value=var.value,
                                                description=var.description
                                                )
            # TODO: Add Boolean and String
    
    def _set_up_label(self) -> None:
        """
        Create a label for visualization in the system graph.
        """
        in_str = "{ " + " | ".join(f"<{name}> {name}" for name in self.inputs.keys()) + " }"
        out_str = "{ " + " | ".join(f"<{name}> {name}" for name in self.outputs.keys()) + " }"
        if in_str == "{  }":
            in_str = ""
        if out_str == "{  }":
            out_str = ""
        if in_str and out_str:
            self.label = f"{{ {in_str} | {self.name} | {out_str} }}"
        elif in_str:
            self.label = f"{{ {in_str} | {self.name} }}"
        elif out_str:
            self.label = f"{{ {self.name} | {out_str} }}"
        else:
            self.label = f"{self.name}"
    
    def _set_up_units(self) -> None:
        """
        Convert unit strings to pint units using the global Unit Registry.
        """
        for var in self._vars:
            if hasattr(var, "unit") and var.unit:
                var.unit = to_pint_unit(var.unit)

    def _instantiate(self):
        """
        Instantiate the FMU as FMU2Slave using fmpy.
        """
        unzipdir = extract(self.path)
        self._instance = FMU2Slave(guid=self._md.guid,
                                unzipDirectory=unzipdir,
                                modelIdentifier=self._md.coSimulation.modelIdentifier,
                                instanceName=self.name)
        self._instance.instantiate()
    
    def input_ports(self) -> Dict[str, str]:
        """Return {port_name: unit_str} for inputs."""
        return {name: str(var.unit) if var.unit else "" for name, var in self.inputs.items()}

    def output_ports(self) -> Dict[str, str]:
        """Return {port_name: unit_str} for outputs."""
        return {name: str(var.unit) if var.unit else "" for name, var in self.outputs.items()}
    
    def set_parameters(self, **parameters: float) -> None:
        """
        Set the parameters of the FMU during initialization.
            :param parameters: Parameter values as keyword arguments {param_name: value}.
        """
        for name, value in parameters.items():
            if name in self.parameters:
                self.parameters[name].start = value
            else:
                raise KeyError(f"Parameter '{name}' not found in FMU '{self.name}'.")

    def initialize(self, t0: float) -> None:
        """
        Prepare the component for simulation starting at time t0.

            :param t0: Start time of the simulation.
        """
        # Standard Co-Sim Initialization
        self._instance.reset()
        self._instance.setupExperiment(startTime=t0)
        self._instance.enterInitializationMode()
        # Set start values for parameters
        for name, var in self.parameters.items():
            if var.start is not None:
                var_start = float(var.start)
                self._instance.setReal([var.valueReference], [var_start])
        self._instance.exitInitializationMode()
    
    def set_inputs(self, **signals: float) -> None:
        """
        Set the input signals for the FMU.
            :param signals: Input signals as keyword arguments {input_name: value}.
        """
        # Return early if no signals to set
        if not signals: return
        
        # Get value references and values and set them in the FMU
        vrs: List[int] = []
        vals: List[float] = []
        for k, v in signals.items():
            if k in self._vrs_in:
                vrs.append(self._vrs_in[k])
                vals.append(v)
            else:
                raise KeyError(f"Input '{k}' not found in FMU '{self.name}'.")
        self._instance.setReal(vrs, vals)

    def do_step(self, t, h) -> None:
        """
        Perform a simulation step for the FMU.
            :param t: Current communication time point.
            :param h: Communication step size.
        """
        self._instance.doStep(currentCommunicationPoint=t, communicationStepSize=h)
    
    def get_outputs(self) -> Dict[str, float]:
        """
        Return the current outputs as a dictionary {name: value}.
        """
        vrs = list(self._vrs_out.values())
        values = self._instance.getReal(vrs)
        return {name: values[i] for i, name in enumerate(self._vrs_out.keys())}
    
    def reset(self) -> None:
        """
        Reset the component to a clean state before (before initialization).
        """
        self._instance.reset()
        self._instance.terminate()
        self._instance.freeInstance()
        self._instance = None
        self._instantiate()

    def reinitialize(self, t: float, state: Optional[Dict[str, Any]] = None) -> None:
        """
        Reinitialize the component, optionally restoring a previous state.
            :param t: Time to reinitialize to.
            :param state: Optional state dictionary to restore.
        """
        self.reset()
        for name, value in (state or {}).items():
            self.parameters[name].start = value
        self.initialize(t)
    
    def set_state(self, state):
        # TODO: Implement state setting if supported by the FMU
        pass

    def get_state(self):
        # TODO: Implement state retrieval if supported by the FMU
        pass

    def free(self) -> None:
        """
        Free resources associated with the FMU component.
        """
        if self._instance:
            self._instance.terminate()
            self._instance.freeInstance()
            self._instance = None
            self._vrs_in = {}
            self._vrs_out = {}
        
        