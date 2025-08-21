from .expressions import Expression

# Equantion wrapper
class Equation:
    """A class to represent an equation in the model.
    It contains a left-hand side (lhs) and a right-hand side (rhs) expression.
    
    Attributes:
        lhs (Expression): The left-hand side expression of the equation.
        rhs (Expression): The right-hand side expression of the equation.

    Methods:
        to_mo(): Converts the equation to Modelica code format.
    """
    def __init__(self, lhs: Expression, rhs: Expression):
        self.lhs, self.rhs = lhs, rhs
    
    def to_mo(self):
        """Convert the equation to Modelica code format."""
        if not isinstance(self.lhs, Expression) or not isinstance(self.rhs, Expression):
            raise TypeError("Both lhs and rhs must be instances of Expression.")
        # Convert lhs and rhs to Modelica code
        # Assuming Expression class has a to_mo() method
        if not hasattr(self.lhs, 'to_mo') or not hasattr(self.rhs, 'to_mo'):
            raise AttributeError("Both lhs and rhs must have a to_mo() method.")
        # Return the formatted equation string
        return f"{self.lhs.to_mo()} = {self.rhs.to_mo()};"