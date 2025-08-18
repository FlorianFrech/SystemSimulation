import numpy as np
import matplotlib.pyplot as plt
from core.simulation import Simulation
from core.module import Module

# Create Modules
reference = Module("reference", "constant.py")
alg_int = Module("integrator", "algebraic_integrator.py")

# Innstantiate the simulation
sim = Simulation(modules=[reference, alg_int], dt=0.01, t_end=10)

# Set the module connections
sim.connect("reference", "u_out", "integrator", "u")

# Run the simulation
sim.run()

# Get and extract the results
results = sim.get_output_timeseries("integrator", "x")

t_values, x_values = zip(*results)
t_values = np.array(t_values)
x_values = np.array(x_values)

# Plot the results
plt.figure()
plt.plot(t_values, x_values, label="x")
plt.title("Integrator Output")
plt.xlabel("Time (s)")
plt.ylabel("Output Value")
plt.legend()
plt.grid()
plt.show()