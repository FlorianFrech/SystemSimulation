import matplotlib.pyplot as plt

# Text widths in inches, matching \linewidth for the thesis layout
FULL_WIDTH = 5.9
HALF_WIDTH = 2.85
SUBFIG_048 = 2.80

REFERENCE_COLOR = "#1A1A1A"

# Unified palette for §6.5.1, §6.5.2, §6.5.3 figures.
# Move to thesis/notebooks/plot_setup.py to share across notebooks.
MODEL_COLORS = {
    "FEM":     "#1f77b4",   # blue   — high-fidelity plant
    "FMU":     "#2ca02c",   # green  — rigid-body plant
    "OpenSim": "#ff7f0e",   # orange — musculoskeletal plant
}
REFERENCE_STYLE = dict(color="#d62728", linestyle="--", linewidth=1.4, alpha=0.85)
WALL_STYLE      = dict(color="0.45", linestyle=":", linewidth=1.0)
GRID_STYLE      = dict(alpha=0.4)
PANEL_LABEL_STYLE = dict(
    fontweight="bold", fontsize=10,
    bbox=dict(facecolor="white", edgecolor="none", alpha=0.9, pad=2),
)
TIMING_TOTAL_COLOR = "#2F4858"
TIMING_FEM_COLOR   = MODEL_COLORS["FEM"]

STEP_SIZE_COLORS = {
    0.02: "#7C8DA6",
    0.01: "#D58936",
    0.005: "#4F8F6B",
    0.001: "#B23A48",
}

METRIC_COLORS = {
    "e_inf": "#2F4858",
    "e_2": "#C75C2D",
}

ALGO_COLORS = {
    "Analytic": "#1A1A1A",
    "Jacobi": "#D55E00",
    "Gauss-Seidel": "#0072B2",
}

ALGO_MARKERS = {
    "Jacobi": "o",
    "Gauss-Seidel": "s",
}

ALGO_LINESTYLES = {
    "Analytic": "-",
    "Jacobi": "--",
    "Gauss-Seidel": "-.",
}

def set_professional_style(latex=True, fontsize=10, savefig_format="pdf"):
    """Configure Matplotlib for thesis-style scientific plots."""

    plt.style.use("default")

    plt.rc("font", size=fontsize, family="serif")
    plt.rc("axes", titlesize=fontsize, labelsize=fontsize, linewidth=1.0)
    plt.rc("legend", fontsize=fontsize - 1, frameon=True, framealpha=0.95,
           edgecolor="0.35", fancybox=False)
    plt.rc("xtick", labelsize=fontsize - 2, direction="in")
    plt.rc("ytick", labelsize=fontsize - 2, direction="in")

    plt.rc("xtick.major", width=1.0, size=5)
    plt.rc("xtick.minor", width=0.8, size=3)
    plt.rc("ytick.major", width=1.0, size=5)
    plt.rc("ytick.minor", width=0.8, size=3)

    plt.rc("grid", linestyle="--", linewidth=0.6, color="0.75", alpha=0.8)
    plt.rc("lines", linewidth=1.8, markersize=4.2, markeredgewidth=0.9)

    plt.rc("figure", dpi=120)
    plt.rc("savefig", dpi=300, bbox="tight", format=savefig_format)
    plt.rcParams["axes.axisbelow"] = True
    plt.rcParams["axes.spines.top"] = True
    plt.rcParams["axes.spines.right"] = True

    if latex:
        plt.rc("text", usetex=True)
        plt.rc("font", family="serif")
        plt.rc("text.latex", preamble=r"\usepackage{amsmath}\usepackage{siunitx}")
    else:
        plt.rc("text", usetex=False)

    return plt
