from simulation import Simulation
from module import Module
import time

t0 = time.time()

# Create modules
src = Module("SRC", "signal_source.py")
lpf1 = Module("LPF1", "lowpass_filter.py", parameters={"R": (1000, "ohm"), "C": (1, "mF")}, normalise_units=True)
lpf2 = Module("LPF2", "lowpass_filter.py", parameters={"R": (1000, "ohm"), "C": (0.001, "F")})
bpf = Module("BPF", "bandpass_filter.py", parameters={"R": (1.26, "ohm"), "L": (1, "H"), "C": (0.0253, "F")}, dt=0.02)

# Create simulation
sim = Simulation(modules=[bpf, src, lpf2, lpf1], dt=0.01, t_end=2) # Module order will be determined automatically

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


# Run simulation: comment or uncomment the methods to access their functionality

#sim.run()

sim.run(monitor_results=True, monitor_config=plot_config, save_results=True, file_name="monitor_output_results")

#sim.plot_outputs(config=plot_config, save_results=True)

# sim.export_history_to_excel(step_skip=2, force_single_sheet=True)

# sim.export_history_to_excel(
#     filename="simulation_export1.xlsx",
#     outputs=[("SRC", "Uin"), ("BPF", "I")],
#     time_range=(1.2, 1.5),
# )

sim.visualise("electrical_circuit", show_edge_labels=True, show_parameters=True, show_io=True, show_dt=True)

t1 = time.time()
print(f"Execution took {t1 - t0:.4f} seconds")

