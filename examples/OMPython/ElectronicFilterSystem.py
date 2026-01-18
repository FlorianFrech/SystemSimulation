"""
FilterSystemModel Simulation using OMPython
"""

from pathlib import Path

import matplotlib.pyplot as plt
from OMPython import ModelicaSystem


def simulate_filter_system():
    """
    Simulate the FilterSystemModel using OMPython
    """

    # Define paths
    filter_system_path = Path("/home/flo/repos/SystemSimulation/examples/Modelica/FilterSystem")
    package_path = filter_system_path / "package.mo"

    print("Loading FilterSystem package from:", package_path)
    print("Simulation equivalent to LPF_main.py")
    print("=" * 50)

    try:
        # Load the FilterSystemModel from the FilterSystem package
        model_system = ModelicaSystem(str(package_path), "FilterSystem.FilterSystemModel")

        print("Model loaded successfully")

        # Build the model
        print("Building model...")
        model_system.buildModel()
        print("Model built successfully")

        # Get model information
        print("\nModel Information:")
        print("-" * 30)
        outputs = model_system.getOutputs()
        inputs = model_system.getInputs()
        parameters = model_system.getParameters()
        continuous = model_system.getContinuous()

        print(f"Outputs:    {outputs}")
        print(f"Inputs:     {inputs}")
        print(f"Parameters: {parameters}")
        print(f"Continuous: {continuous}")

        # Set simulation parameters (matching Python simulation: dt=0.01, t_end=2)
        print("\nSetting simulation options...")
        simulation_options = ["startTime=0.0", "stopTime=10.0", "stepSize=0.01", "tolerance=1e-6"]

        model_system.setSimulationOptions(simulation_options)
        current_options = model_system.getSimulationOptions()
        print(f"Simulation options: {current_options}")

        # Run simulation
        print("\nRunning simulation...")
        model_system.simulate()
        print("Simulation completed successfully")

        # Get results (matching the monitoring variables from FilterSystemModel)
        print("\nExtracting results...")
        time_vals, src_voltage = model_system.getSolutions(["time", "src_voltage"])
        _, lpf1_voltage = model_system.getSolutions(["time", "lpf1_voltage"])
        _, lpf2_voltage = model_system.getSolutions(["time", "lpf2_voltage"])
        _, bpf_current = model_system.getSolutions(["time", "bpf_current"])
        _, bpf_inductor_current = model_system.getSolutions(["time", "bpf_inductor_current"])

        print(f"Results extracted: {len(time_vals)} time points")

        # Create plots (replicating Python plot_config)
        plot_results(
            time_vals, src_voltage, lpf1_voltage, lpf2_voltage, bpf_current, bpf_inductor_current
        )

        return {
            "time": time_vals,
            "src_voltage": src_voltage,
            "lpf1_voltage": lpf1_voltage,
            "lpf2_voltage": lpf2_voltage,
            "bpf_current": bpf_current,
            "bpf_inductor_current": bpf_inductor_current,
        }

    except Exception as e:
        print(f"Error during simulation: {e}")
        return None


def plot_results(
    time_vals, src_voltage, lpf1_voltage, lpf2_voltage, bpf_current, bpf_inductor_current
):
    # Create figure with subplots (matching Python plot_config groups)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

    # Group 1: Real-Time LPFs (voltages)
    ax1.plot(time_vals, src_voltage, label="SRC.Uin", linewidth=2, color="blue")
    ax1.plot(time_vals, lpf1_voltage, label="LPF1.Uc", linewidth=2, color="orange")
    ax1.plot(time_vals, lpf2_voltage, label="LPF2.Uc", linewidth=2, color="green")

    ax1.set_title("Real-Time LPFs", fontsize=14, fontweight="bold")
    ax1.set_ylabel("LPFs Voltages [V]", fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    # Group 2: Real-Time BPF (currents)
    ax2.plot(time_vals, bpf_current, label="BPF.I (Total)", linewidth=2, color="red")
    ax2.plot(
        time_vals, bpf_inductor_current, label="BPF.IL (Inductor)", linewidth=2, color="purple"
    )

    ax2.set_title("Real-Time BPF", fontsize=14, fontweight="bold")
    ax2.set_ylabel("BPF Currents [A]", fontsize=12)
    ax2.set_xlabel("Time [s]", fontsize=12)
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    plt.suptitle(
        "FilterSystemModel Simulation Results (OMPython)", fontsize=16, fontweight="bold", y=0.98
    )

    # Save the plot
    plt.savefig(
        "/home/flo/repos/SystemSimulation/examples/OMPython/filter_system_results.png",
        dpi=300,
        bbox_inches="tight",
    )
    print("Plot saved as 'filter_system_results.png'")

    plt.show()


if __name__ == "__main__":
    print("FilterSystemModel OMPython Simulation")
    print("=" * 50)

    # Run the simulation
    results = simulate_filter_system()

    print("\n" + "=" * 50)
    print("Simulation completed!")
