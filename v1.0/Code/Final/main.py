from simulation import Simulation
from module import Module


# Create modules
mod1 = Module("", ".py", parameters={"": (0.0, "")})

# Create simulation
sim = Simulation(modules=[], dt=0.01, t_end=2)      # Module order will be determined automatically based on connections

# Define connections
sim.connect("", "", "", "")


# Run simulation

sim.run()


