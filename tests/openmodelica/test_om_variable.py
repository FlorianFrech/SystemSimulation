import pytest

from SysSimX.adapters.openmodelica.om_variable import *

def test_variable():
    # State variable
    phi = Variable(name="phi",
                   vtype=BaseType.REAL,
                   variability=Variability.CONTINUOUS,
                   start=0,
                   min=0,
                   max=100,
                   unit="rad",
                   fixed=True)
    print("Output:")
    print(phi.to_modelica_decl())
    # Parameter
    resistance = Variable(name="R",
                          vtype=BaseType.REAL,
                          variability=Variability.PARAMETER, 
                          value=1000,
                          unit="ohm")
    print("\nOutput:")
    print(resistance.to_modelica_decl())

    x = Variable(name="x",
                 vtype=BaseType.INTEGER,
                 variability=Variability.CONSTANT,
                 value=42)
    print("\nOutput:")
    print(x.to_modelica_decl())