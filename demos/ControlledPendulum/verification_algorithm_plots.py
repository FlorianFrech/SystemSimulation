import csv
import sys
from pathlib import Path

import numpy as np
import scipy.io as io

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "docs"))  # Add docs directory

import matplotlib

matplotlib.use("Agg")  # Use non-interactive backend for plotting

from plot_setup import set_professional_style

plt = set_professional_style(fontsize=12)

# ---------------------------------------------------
# 1) Load Monolithic reference results
ref_res_simple = io.loadmat(Path(__file__).parent / "results/monolithic_simple.mat")
ref_res_complex = io.loadmat(Path(__file__).parent / "results/monolithic_complex.mat")

ref_res = {"simple": ref_res_simple, "complex": ref_res_complex}

for case in ref_res:
    for key in ref_res[case]:
        if isinstance(ref_res[case][key], np.ndarray):
            ref_res[case][key] = ref_res[case][key].flatten()

print(60 * "=")
print("1) Loaded monolithic reference results.")

# ---------------------------------------------------
# 2) Load Co-Simulation results
cs_res_dir_simple = Path(__file__).parent / "results/cs_simple/"
cs_res_dir_complex = Path(__file__).parent / "results/cs_complex/"

jacobi_dir_simple = cs_res_dir_simple / "Jacobi/"
gs_dir_simple = cs_res_dir_simple / "Gauss-Seidel/"
ijcsa_dir_simple = cs_res_dir_simple / "IJCSA/"

simple_dir = {"Jacobi": jacobi_dir_simple, "Gauss-Seidel": gs_dir_simple, "IJCSA": ijcsa_dir_simple}

jacobi_dir_complex = cs_res_dir_complex / "Jacobi/"
gs_dir_complex = cs_res_dir_complex / "Gauss-Seidel/"
ijcsa_dir_complex = cs_res_dir_complex / "IJCSA/"

complex_dir = {
    "Jacobi": jacobi_dir_complex,
    "Gauss-Seidel": gs_dir_complex,
    "IJCSA": ijcsa_dir_complex,
}

dirs = {"simple": simple_dir, "complex": complex_dir}

algorithms = ["Jacobi", "Gauss-Seidel", "IJCSA"]
dts = [0.02, 0.01, 0.005, 0.001]

cs_data = {"simple": {}, "complex": {}}

for case in ("simple", "complex"):
    for dir, alg in zip(dirs[case].values(), algorithms):
        cs_data[case][alg] = {}
        for file in dir.glob("*.csv"):
            dt_str = file.stem.split("_")[-1]
            cs_data[case][alg][dt_str] = {}
            with open(file) as f:
                reader = csv.reader(f)
                header = next(reader)
                units = next(reader)
                data = np.array([list(map(float, row)) for row in reader])
            for i, col_name in enumerate(header):
                cs_data[case][alg][dt_str][col_name] = data[:, i]

print(60 * "=")
print("2) Loaded co-simulation results.")

# ---------------------------------------------------
# 3) Define Plotting Styles
# 3.1) Common styles for all plots
algorithms.append("Monolithic")
colors = {algorithm: "" for algorithm in algorithms}
colors["Monolithic"] = "tab:red"
colors["Jacobi"] = "tab:blue"
colors["Gauss-Seidel"] = "tab:orange"
colors["IJCSA"] = "tab:green"

markers = {algorithm: "" for algorithm in algorithms}
markers["Monolithic"] = "."
markers["Jacobi"] = "o"
markers["Gauss-Seidel"] = "s"
markers["IJCSA"] = "^"

marker_size = {}
for algorithm in algorithms:
    if algorithm == "Monolithic":
        marker_size[algorithm] = 1
    else:
        marker_size[algorithm] = 4

labels = {algorithm: "" for algorithm in algorithms}
labels["Monolithic"] = r"Monolithic: DASSL (Modelica)"
labels["Jacobi"] = r"Co-Simulation: Jacobi"
labels["Gauss-Seidel"] = r"Co-Simulation: Gauss-Seidel"
labels["IJCSA"] = r"Co-Simulation: IJCSA"

styles = {}
for algorithm in algorithms:
    styles[algorithm] = {
        "color": colors[algorithm],
        "marker": markers[algorithm],
        "markersize": marker_size[algorithm],
        "label": labels[algorithm],
        "linestyle": "None",  # Only markers, no lines
    }

# 3.2) Specific styles for error convergence plots
linestyles = {algorithm: "" for algorithm in algorithms}
linestyles["Monolithic"] = "-"
linestyles["Jacobi"] = "--"
linestyles["Gauss-Seidel"] = "-."
linestyles["IJCSA"] = ":"

error_styles = {}
for algorithm in algorithms:
    error_styles[algorithm] = {
        "color": colors[algorithm],
        "marker": markers[algorithm],
        "markersize": marker_size[algorithm],
        "label": labels[algorithm],
        "linestyle": linestyles[algorithm],
    }

subtitle_style = {"fontweight": "bold", "fontsize": 14}

print(60 * "=")
print("3) Setup plotting styles.")

# ---------------------------------------------------
# 4) Trajectory Plot Function
dts = ["0.020", "0.010", "0.005", "0.001"]
titles = ["dt = 0.020 s", "dt = 0.010 s", "dt = 0.005 s", "dt = 0.001 s"]


def create_trajectory_plot(case: str, monolithic_signal: str, cs_signal: str, y_label: str):
    fig, axs = plt.subplots(2, 2, figsize=(12, 10), constrained_layout=False)
    fig.suptitle(
        f"Trajectory Comparison for {monolithic_signal}\nCase: {case.capitalize()}",
        **subtitle_style,
        y=1.05,
    )

    gs = cs_data[case]["Gauss-Seidel"]
    ijcsa = cs_data[case]["IJCSA"]
    jacobi = cs_data[case]["Jacobi"]

    ref_data = ref_res[case]
    t_ref = ref_data["time"]

    for ax, dt, title in zip(axs.flat, dts, titles):
        t = gs[dt]["time"]  # or ds['Jacobi'][dt]['time'], they share the grid
        ax.set_title(f"{monolithic_signal} - {title}", **subtitle_style)

        # reference
        ax.plot(t_ref, ref_data[monolithic_signal], **styles["Monolithic"])

        # co-sim algorithms
        ax.plot(t, jacobi[dt][cs_signal], **styles["Jacobi"])
        ax.plot(t, gs[dt][cs_signal], **styles["Gauss-Seidel"])
        ax.plot(t, ijcsa[dt][cs_signal], **styles["IJCSA"])

        ax.set_xlabel(r"Time $t$ (s)")
        ax.set_ylabel(y_label)
        ax.minorticks_on()
        ax.grid(True, which="major")
        ax.grid(True, which="minor", alpha=0.3)

    # Add one common legend centered above all subplots
    handles, labels = axs[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, fontsize=12, bbox_to_anchor=(0.5, 1.0))

    fig.subplots_adjust(top=0.9)

    plt.subplots_adjust(hspace=0.25, wspace=0.25)

    # plt.tight_layout()
    figures_dir = Path(__file__).parent / f"figures/cs_alg_verification/{case}/all/"
    plt.savefig(figures_dir / f"{monolithic_signal.replace('.', '_')}.svg", bbox_inches="tight")
    plt.savefig(figures_dir / f"{monolithic_signal.replace('.', '_')}.pdf", bbox_inches="tight")


# ---------------------------------------------------
# 5) Error Convergence Plot Function
def create_error_convergence_plot(case: str, monolithic_signal: str, cs_signal: str):
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_title(
        f"Error Convergence for {monolithic_signal}\nCase: {case.capitalize()}", **subtitle_style
    )

    ref_data = ref_res[case]
    t_ref = ref_data["time"]
    y_ref = ref_data[monolithic_signal]

    errors_dict = {algorithm: [] for algorithm in algorithms[:-1]}  # Exclude Monolithic
    for algorithm in algorithms[:-1]:  # Exclude Monolithic
        errors = []
        dt_values = []
        for dt in dts:
            t_cs = cs_data[case][algorithm][dt]["time"]
            y_cs = cs_data[case][algorithm][dt][cs_signal]

            # Interpolate reference solution to co-simulation time points
            y_ref_interp = np.interp(t_cs, t_ref, y_ref)

            # Compute L2 norm of the error
            error = np.sqrt(np.mean((y_cs - y_ref_interp) ** 2))
            errors.append(error)
            dt_values.append(float(dt))
        errors_dict[algorithm] = errors
        ax.plot(dt_values, errors, **error_styles[algorithm])

    h_values = np.array(dt_values)
    ref_line = h_values
    ref_line_2nd = h_values**2
    ax.loglog(
        h_values,
        ref_line * (errors_dict["Jacobi"][0] / ref_line[0]),
        "k--",
        label=r"$O(\Delta t)$",
        linewidth=2,
    )
    ax.loglog(
        h_values,
        ref_line_2nd * (errors_dict["Jacobi"][0] / ref_line_2nd[0]),
        "k:",
        label=r"$O(\Delta t^2)$",
        linewidth=2,
    )

    ax.invert_xaxis()
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"Time Step Size $\Delta t$ (s)")
    ax.set_ylabel(r"Relative Error $\frac{||x_{ref} - x_{cs}||_2}{||x_{ref}||_2}$")
    ax.minorticks_on()
    ax.grid(True, which="major")
    ax.grid(True, which="minor", alpha=0.3)

    # Add legend
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles, labels, fontsize=12)

    plt.tight_layout()
    figures_dir = Path(__file__).parent / f"figures/cs_alg_verification/{case}/convergence/"
    plt.savefig(
        figures_dir / f"error_convergence_{cs_signal.replace('.', '_')}.svg", bbox_inches="tight"
    )
    plt.savefig(
        figures_dir / f"error_convergence_{cs_signal.replace('.', '_')}.pdf", bbox_inches="tight"
    )
    plt.close(fig)


# ---------------------------------------------------
# 6) Create Plots

signals = [
    ("reference.q_ref", "ref.q_ref", r"Angular Position $\theta_{ref}$ (rad)"),
    ("sensor_ref.U_q", "sensor_ref.U_q", r"Voltage $U_q$ (V)"),
    ("sensor_state.U_q", "sensor_state.U_q", r"Voltage $U_q$ (V)"),
    ("pid.u", "pid.u", r"Control Output $u$"),
    ("drive.torque", "drive.torque", r"Torque $\tau$ (Nm)"),
    ("pendulum.q", "pendulum.q", r"Pendulum Angle $\theta$ (rad)"),
    ("pendulum.omega", "pendulum.omega", r"Pendulum Angular Velocity $\omega$ (rad/s)"),
    ("pendulum.alpha", "pendulum.alpha", r"Pendulum Angular Acceleration $\alpha$ (rad/s$^2$)"),
]

print(60 * "=")
print("4) Generating plots...")

for case in ("simple", "complex"):
    for monolithic_signal, cs_signal, y_label in signals:
        print(f"   - Generating plots for case '{case}', signal '{monolithic_signal}'...")
        if case == "complex" and monolithic_signal == "drive.torque":
            cs_signal = "drive_coupled.torque"
        create_trajectory_plot(case, monolithic_signal, cs_signal, y_label)
        create_error_convergence_plot(case, monolithic_signal, cs_signal)

print(60 * "=")
print("5) Generated all trajectory and error convergence plots.")
