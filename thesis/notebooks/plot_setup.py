import matplotlib.pyplot as plt

# Text widths in inches, matching \linewidth for the thesis layout
FULL_WIDTH = 5.9
HALF_WIDTH = 2.85
SUBFIG_048 = 2.80

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
