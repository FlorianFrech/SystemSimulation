from .expressions import Symbol

class RealInput(Symbol):
    def __init__(self, name: str, unit: str):
        super().__init__(name)
        self.unit = unit

    def decl(self) -> str:
        return f"Modelica.Blocks.Interfaces.RealInput {self.name}(unit=\"{self.unit}\");"
    
class RealOutput(Symbol):
    def __init__(self, name: str, unit: str):
        super().__init__(name)
        self.unit = unit

    def decl(self) -> str:
        return f"Modelica.Blocks.Interfaces.RealOutput {self.name}(unit=\"{self.unit}\");"