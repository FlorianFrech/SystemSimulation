from typing import Dict, List
from fmpy import read_model_description, extract, instantiate_fmu
from fmpy.fmi2 import FMU2Slave

class FMUComponent():
    """
    Wrapper around an FMU to implement the CoSimComponent interface.
    """
    def __init__(self, name: str, fmu_path: str,
                 inputs: Dict[str, str], outputs: Dict[str, str]):
        """
        Constructor for the FMUComponent class.
            :param name: Name of the component instance.
            :param fmu_path: Path to the FMU file.
            :param inputs: Mapping of input signal names to FMU variable names.
            :param outputs: Mapping of output signal names to FMU variable names.
        """
        self.name = name
        self._path = fmu_path
        self._inputs_map = inputs
        self._outputs_map = outputs
        self._inst = None
        self._vrs_in: Dict[str, int] = {}
        self._vrs_out: Dict[str, int] = {}
    
    def initialize(self, t0: float) -> None:
        """
        Prepare the component for simulation starting at time t0.
            :param t0: Start time of the simulation.
        """
        md = read_model_description(self._path)
        unzipdir = extract(self._path)
        self._inst = FMU2Slave(guid=md.guid,
                                unzipDirectory=unzipdir,
                                modelIdentifier=md.coSimulation.modelIdentifier,
                                instanceName=self.name)
        self._inst.instantiate()

        # Map variable names to value references
        name2var = {var.name: var.valueReference for var in md.modelVariables}
        self._vrs_in = {k: name2var[nm] for k, nm in self._inputs_map.items()}
        self._vrs_out = {k: name2var[nm] for k, nm in self._outputs_map.items()}

        # Standard Co-Sim Initialization
        self._inst.reset()
        self._inst.setupExperiment(startTime=t0)
        self._inst.enterInitializationMode()
        self._inst.exitInitializationMode()

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
        self._inst.setReal(vrs, vals)

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
        self._inst.setReal(vrs, vals)

    def step(self, t: float, h: float) -> None:
        """
        Perform a simulation step for the FMU.
            :param t: Current communication time point.
            :param h: Communication step size.
        """
        self._inst.doStep(currentCommunicationPoint=t, communicationStepSize=h)
    
    def get_outputs(self) -> Dict[str, float]:
        """
        Return the current outputs as a dictionary {name: value}.
        """
        vrs = list(self._vrs_out.values())
        vals = self._inst.getReal(vrs)
        return {k: vals[i] for i, k in enumerate(self._vrs_out.keys())}
    
    def reset(self) -> None:
        """
        Reset the FMU component, releasing resources.
        """
        if self._inst:
            self._inst.terminate()
            self._inst.freeInstance()
            self._inst = None
            self._vrs_in = {}
            self._vrs_out = {}