import matplotlib
import numpy as np
import matplotlib.pyplot as plt
from core.simulation import Simulation
from core.module import Module

# Create Modules
reference = Module("reference", "constant.py")
integrator = Module("integrator", "simple_integrator.py")

# Innstantiate the simulation
sim = Simulation(modules=[reference, integrator], dt=0.01, t_end=10)

# Set the module connections
sim.connect("reference", "u_out", "integrator", "input_signal")

# Run the simulation
sim.run()

# Get and extract the results
results_y = sim.get_output_timeseries("integrator", "y")

t_values = []
y_values = []
for t, out in results_y:
    t_values.append(t)
    y_values.append(out)
t_values = np.array(t_values)
y_values = np.array(y_values)


# Plot the results
plt.figure()
plt.plot(t_values, y_values, label="y")
plt.title("Integrator Output")
plt.xlabel("Time (s)")
plt.ylabel("Output Value")
plt.grid()
plt.show()