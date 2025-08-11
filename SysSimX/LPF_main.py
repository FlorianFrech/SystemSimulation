from core.simulation import Simulation
from core.module import Module
import time

# Create modules
src = Module("SRC", "signal_source.py")
lpf1 = Module("LPF1", "lowpass_filter.py", parameters={"R": (1000, "ohm"), "C": (1, "mF")}, normalise_units=True)
lpf2 = Module("LPF2", "lowpass_filter.py", parameters={"R": (1000, "ohm"), "C": (0.001, "F")})
bpf = Module("BPF", "bandpass_filter.py", parameters={"R": (1.26, "ohm"), "L": (1, "H"), "C": (0.0253, "F")}, dt=0.02)

# Create simulation - Module order will be determined automatically
sim = Simulation(modules=[bpf, src, lpf2, lpf1], dt=0.01, t_end=2) 

# Define connections
sim.connect("SRC", "Uin", "LPF1", "Uin")
sim.connect("LPF1", "Uc", "LPF2", "Uin")
sim.connect("LPF2", "Uc", "BPF", "U")

# Plotting configuration
plot_config={
    "groups": [
        [("SRC", "Uin"), ("LPF1", "Uc"), ("LPF2", "Uc")], # list -> one subplot, tuple -> pair to determine output time series
        [("BPF", "I"), ("BPF", "IL")]
    ],
    "titles": ["Real-Time LPFs", "Real-Time BPF"], # titles per subgraph
    "y_labels": ["LPFs Voltages", "BPF Currents"]  # labels per subgraph
}

sim.run(monitor_results=True,
        monitor_config=plot_config,
        save_results=True,
        file_name="monitor_output_results")

