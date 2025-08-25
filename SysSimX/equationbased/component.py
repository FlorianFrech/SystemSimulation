from .expressions import Symbol

class Instance(Symbol):
    """
    A component instance in a model.
    Attribute access returns Symbols:
        - instance.variable_name
    """

    def __init__(self, type_name: str, name: str, config: str = ""):
        self.type_name = type_name
        self.name = name
        self.config = config

    def decl(self) -> str:
        """Return the Modelica declaration for this instance."""
        return f"{self.type_name} {self.name}({self.config});"

    def __getattr__(self, attr: str) -> Symbol:
        """Return a Symbol representing an attribute of the instance."""
        return Symbol(f"{self.name}.{attr}")