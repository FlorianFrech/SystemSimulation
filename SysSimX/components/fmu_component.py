from typing import Dict, List
from fmpy import read_model_description, extract, instantiate_fmu
from fmpy.fmi2 import FMU2Slave
from tabulate import tabulate

class FMUComponent():
    """
    Wrapper around an FMU to implement the CoSimComponent interface.
    """
    def __init__(self, name: str, fmu_path: str):
        """
        Constructor for the FMUComponent class.
            :param name: Name of the component instance.
            :param fmu_path: Path to the FMU file.
            :param inputs: Mapping of input signal names to FMU variable names.
            :param outputs: Mapping of output signal names to FMU variable names.
        """
        self.name = name
        self.path = fmu_path
        self.inputs = None
        self.outputs = None
        self.parameters = None
        self._md = read_model_description(fmu_path)
        self._vars = self._md.modelVariables
        self._instance = None
        
        # Initialize input/outputs
        self.inputs = {var.name: var for var in self._md.modelVariables if var.causality == "input"}
        self.outputs = {var.name: var for var in self._md.modelVariables if var.causality == "output"}
        self.parameters = {var.name: var for var in self._md.modelVariables if var.causality == "parameter"}
        self._instantiate()

    def _instantiate(self):
        unzipdir = extract(self.path)
        self._instance = FMU2Slave(guid=self._md.guid,
                                unzipDirectory=unzipdir,
                                modelIdentifier=self._md.coSimulation.modelIdentifier,
                                instanceName=self.name)
        self._instance.instantiate()


    def initialize(self, t0: float) -> None:
        """
        Prepare the component for simulation starting at time t0.
            :param t0: Start time of the simulation.
        """
        self._vrs_in = {name: var.valueReference for name, var in self.inputs.items()}
        self._vrs_out = {name: var.valueReference for name, var in self.outputs.items()}

        # Standard Co-Sim Initialization
        self._instance.reset()
        self._instance.setupExperiment(startTime=t0)
        self._instance.enterInitializationMode()
        for name, var in self.parameters.items():
            if var.start is not None:
                var_start = float(var.start)
                self._instance.setReal([var.valueReference], [var_start])
        self._instance.exitInitializationMode()

    def set_parameters(self, **parameters: float) -> None:
        """
        Set the parameters of the FMU during initialization.
            :param parameters: Parameters as keyword arguments {name: value}.
        """
        if not parameters: return
        vrs: List[int] = []
        vals: List[float] = []
        for k, v in parameters.items():
            vrs.append(self._vrs_in[k])
            vals.append(v)
        self._instance.setReal(vrs, vals)

    def set_inputs(self, **signals: float) -> None:
        """
        Set the input signals for the FMU.
            :param signals: Input signals as keyword arguments {name: value}.
        """
        if not signals: return
        vrs: List[int] = []
        vals: List[float] = []
        for k, v in signals.items():
            vrs.append(self._vrs_in[k])
            vals.append(v)
        self._instance.setReal(vrs, vals)

    def step(self, t: float, h: float) -> None:
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
        vals = self._instance.getReal(vrs)
        return {k: vals[i] for i, k in enumerate(self._vrs_out.keys())}
    
    def reset(self) -> None:
        """
        Reset the FMU component, releasing resources.
        """
        if self._instance:
            self._instance.terminate()
            self._instance.freeInstance()
            self._instance = None
            self._vrs_in = {}
            self._vrs_out = {}

    def _model_info(self) -> str:
        """
        Return a formatted string with information about the FMU model.
        """
        info = f"FMU Name: {self.name}\n"
        info += f"FMU Path: {self.path}\n"
        info += f"FMU Description: {self._md.description}\n"    
        return info

    def _variable_info(self) -> str:
        """
        Return a formatted string with information about the FMU variables.
        """
        headers = ["Name", "Type", "Start", "Unit", "Causality", "Variability"]
        table = []
        for var in self._md.modelVariables:
            row = [var.name, var.type, var.start, var.unit, var.causality, var.variability]
            if var.causality != "local":
                table.append(row)
        return tabulate(table, headers, tablefmt="github")
    
    def __str__(self) -> str:
        return self._model_info() + "\n" + self._variable_info() + "\n"
    
    def reinitialize(self, t: float, **signals) -> None:
        """
        Re-initialize the FMU component at time t0.
            :param t0: Start time of the simulation.
        """
        self.reset()
        if 'q_state' in signals:
            self.parameters['q0'].start = signals['q_state']
        if 'omega_state' in signals:
            self.parameters['omega0'].start = signals['omega_state']
        self._instantiate()
        self.initialize(t)