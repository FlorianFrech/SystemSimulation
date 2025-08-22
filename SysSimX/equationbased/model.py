from typing import Any, Optional
from .interfaces import RealInput, RealOutput
from .expressions import Expression, Literal, Symbol, BinaryOperator, FunctionCall, as_expr


class Model:
    """A class to represent a Modelica model.
    It contains inputs, outputs, constants, parameters, variables,
    initial equations, and equations of the model.
    Attributes:
        name (str): The name of the model.
        within (Any): The scope within which the model is defined.
        extends (Any): The model that this model extends.
        inputs (RealInput): The inputs of the model.
        outputs (RealOutput): The outputs of the model.
        constants (Any): The constants of the model.
        parameters (Any): The parameters of the model.
        variables (Any): The variables of the model.
        initial_equations (Any): The initial equations of the model.
        equations (Any): The equations of the model.
        modelica_code (Optional[str]): The Modelica code representation of the model.
    
    Methods:
        add_input(input: Any): Adds an input to the model.
        add_output(output: Any): Adds an output to the model.
        add_constant(constant: Any): Adds a constant to the model.
        add_parameter(parameter: Any): Adds a parameter to the model.
        add_variable(variable: Any): Adds a variable to the model.
        add_initial_equation(equation: Any): Adds an initial equation to the model.
        add_equation(equation: Any): Adds an equation to the model.
        to_mo(): Converts the model to Modelica code format.
    """
    name = None
    within: Any
    extends: Any

    inputs: RealInput
    outputs: RealOutput

    constants: Any
    parameters: Any
    variables: Any

    initial_equations: Any
    equations: Any

    modelica_code: Optional[str] = None

    def __init__(self, name: str = None, within: Any = None, extends: Any = None):
        """Initialize the model with optional name, within, and extends."""
        self.name = name
        self.within = within
        self.extends = extends
        
        self.inputs = None
        self.outputs = None
        
        self.constants = None
        self.parameters = None
        self.variables = None

        self.components = None
        
        self.initial_equations = None
        self.equations = None

    def add_input(self, input: Any) -> None:
        """Add an input to the model."""
        if self.inputs is None:
            self.inputs = {}
        self.inputs[input.name] = input

    def add_output(self, output: Any) -> None:
        """Add an output to the model."""
        if self.outputs is None:
            self.outputs = {}
        self.outputs[output.name] = output

    def add_constant(self, constant: Any) -> None:
        """Add a constant to the model."""
        if self.constants is None:
            self.constants = {}
        self.constants[constant.name] = constant

    def add_parameter(self, parameter: Any) -> None:
        """Add a parameter to the model."""
        if self.parameters is None:
            self.parameters = {}
        self.parameters[parameter.name] = parameter

    def add_variable(self, variable: Any) -> None:
        """Add a variable to the model."""
        if self.variables is None:
            self.variables = {}
        self.variables[variable.name] = variable

    def add_component(self, component: Any) -> None:
        """Add a component (sub-model) to the model."""
        if self.components is None:
            self.components = []
        self.components.append(component)

    def add_initial_equation(self, equation: Any) -> None:
        """Add an initial equation to the model."""
        if self.initial_equations is None:
            self.initial_equations = []
        self.initial_equations.append(equation)
    
    def add_equation(self, equation: Any) -> None:
        """Add an equation to the model."""
        if self.equations is None:
            self.equations = []
        self.equations.append(equation)

    def to_mo(self) -> str:
        """Convert the model to Modelica code."""
        mo_code = []
        
        if self.within:
            mo_code.append(f"within {self.within};")
        if self.extends:
            mo_code.append(f"extends {self.extends};")
        
        mo_code.append(f"model {self.name}")

        indentation = "  "  # Modelica uses 2 spaces for indentation

        # Inputs
        if self.inputs:
            for input in self.inputs.values():
                mo_code.append(indentation + input.decl())
        
        # Outputs
        if self.outputs:
            for output in self.outputs.values():
                mo_code.append(indentation + output.decl())
        
        # Constants
        if self.constants:
            for constant in self.constants.values():
                mo_code.append(indentation + constant.decl())
        
        # Components
        if self.components:
            for component in self.components:
                mo_code.append(indentation + component.decl())

        # Parameters
        if self.parameters:
            for parameter in self.parameters.values():
                mo_code.append(indentation + parameter.decl())
        
        # Variables
        if self.variables:
            for variable in self.variables.values():
                mo_code.append(indentation + variable.decl())
        
        # Initial equations
        if self.initial_equations:
            mo_code.append("initial equation")
            for eq in self.initial_equations:
                mo_code.append(indentation + eq.to_mo())
        
        # Equations
        if self.equations:
            mo_code.append("equation")
            for eq in self.equations:
                mo_code.append(indentation + eq.to_mo())
        
        # End of model
        mo_code.append("end " + self.name + ";")
        
        # Join all parts into a single string       
        self.modelica_code =  "\n".join(mo_code)

    def save(self, path: str) -> None:
        """Save the model to a file."""
        if self.modelica_code is None:
            self.to_mo()
        
        with open(path, 'w') as f:
            f.write(self.modelica_code)
        print(f"Model saved to {path}")
