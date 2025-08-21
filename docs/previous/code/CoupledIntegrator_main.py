import numpy as np
import matplotlib.pyplot as plt
from core.simulation import Simulation
from core.module import Module

# Create Modules
reference = Module("reference", "constant.py")

subtractor_1 = Module("subtractor_1", "subtractor.py")
subtractor_2 = Module("subtractor_2", "subtractor.py")

integrator = Module("integrator", "simple_integrator.py")

# Innstantiate the simulation
sim = Simulation(modules=[reference, subtractor_1, subtractor_2, integrator],
                 dt=0.01, t_end=10)

# Set the module connections
sim.connect("reference", "u_out", "subtractor_1", "u_in_p")
sim.connect("integrator", "y", "subtractor_1", "u_in_n")

sim.connect("subtractor_1", "u_out", "subtractor_2", "u_in_p")
sim.connect("subtractor_2", "u_out", "subtractor_2", "u_in_n")

sim.connect("subtractor_2", "u_out", "integrator", "u_in")

# Run the simulation
sim.run()

# Get and extract the results
results = sim.get_output_timeseries("integrator", "y")

t_values, x_values = zip(*results)
t_values = np.array(t_values)
x_values = np.array(x_values)

# Plot the results
plt.figure()
plt.plot(t_values, x_values, label="u_out")
plt.title("Subtractor Output")
plt.xlabel("Time (s)")
plt.ylabel("Output Value")
plt.legend()
plt.grid()
plt.show()