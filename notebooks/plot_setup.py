import matplotlib.pyplot as plt

# Text widths in inches, matching \linewidth for the thesis layout
FULL_WIDTH = 5.9
HALF_WIDTH = 2.85
SUBFIG_048 = 2.80

REFERENCE_COLOR = "#1A1A1A"

# Unified palette for §6.5.1, §6.5.2, §6.5.3 figures.
# Move to thesis/notebooks/plot_setup.py to share across notebooks.
# Okabe-Ito: distinguishable in print, in greyscale, and under the common
# forms of colour vision deficiency. The previous tab10 blue/green/orange trio
# collapsed to near-identical greys and was hard to separate for deuteranopes,
# which matters here because the model identity *is* the message.
# Okabe-Ito by role, so a figure asks for a role and never for a hex code.
# The list is closed. A figure that needs a colour this does not define needs a
# decision recorded in the paper repository's figure_style.md first.
SERIES_COLORS = {
    "primary":    "#0072B2",   # blue
    "secondary":  "#009E73",   # bluish green
    "tertiary":   "#E69F00",   # orange
    "deviation":  "#D55E00",   # vermillion, for error and residual series
    "quaternary": "#CC79A7",   # reddish purple
    "quinary":    "#56B4E9",   # sky blue
}
# Okabe-Ito yellow #F0E442 is deliberately absent. It fails on white in print.

MODEL_COLORS = {
    "FEM":     "#0072B2",   # blue          — deformable, high-fidelity plant
    "FMU":     "#009E73",   # bluish green  — rigid-body plant
    "OpenSim": "#E69F00",   # orange        — multibody plant
}
# The reference is an underlay, not a competitor: a neutral grey rail that the
# coloured co-simulation sits on, so "follows closely" reads as coincidence
# rather than as two lines fighting for attention.
REFERENCE_STYLE = dict(color="0.62", linestyle="-", linewidth=2.6,
                       solid_capstyle="round", zorder=1)
WALL_STYLE      = dict(color="0.45", linestyle=":", linewidth=1.0)
GRID_STYLE      = dict(alpha=0.4)
# A handover is a rule, not data: it marks where something happened without
# competing with the curve it annotates.
HANDOVER_STYLE  = dict(color="0.45", linestyle="--", linewidth=0.8)
# Deviation, error and residual series. Okabe-Ito vermillion, which is distinct
# from every model colour in both hue and luminance.
DEVIATION_COLOR = "#D55E00"
# The band that marks where the expensive model was active. Neutral grey, not a
# model colour, because the trajectory drawn over it already carries colour and
# a grey fill is unambiguous in greyscale.
ACTIVE_BAND_COLOR = "0.45"
# Background fills below 0.10 vanish in print; above 0.15 they compete with the
# data. Only one state is ever shaded, so the band reads in greyscale
# (figure_style.md section 3).
MODE_BAND_ALPHA = 0.12
PANEL_LABEL_STYLE = dict(
    fontweight="bold", fontsize=10,
    bbox=dict(facecolor="white", edgecolor="none", alpha=0.9, pad=2),
)
TIMING_TOTAL_COLOR = SERIES_COLORS["primary"]
TIMING_FEM_COLOR   = MODEL_COLORS["FEM"]

# Macro step is an ordered quantity, so the sequence runs cool to warm as the
# step coarsens. All four are Okabe-Ito.
STEP_SIZE_COLORS = {
    0.02: SERIES_COLORS["quinary"],
    0.01: SERIES_COLORS["primary"],
    0.005: SERIES_COLORS["tertiary"],
    0.001: SERIES_COLORS["deviation"],
}

METRIC_COLORS = {
    "e_inf": SERIES_COLORS["primary"],
    "e_2": SERIES_COLORS["deviation"],
}

ALGO_COLORS = {
    "Analytic": REFERENCE_COLOR,
    "Jacobi": SERIES_COLORS["deviation"],
    "Gauss-Seidel": SERIES_COLORS["primary"],
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

def legend_above(target, handles=None, ncol=3, **kwargs):
    """Place one legend above the figure, centred and unframed.

    Every manuscript figure carries exactly one legend, and it goes above the
    plotting area rather than into a corner of it. A legend inside the axes
    moves whenever the data does, covers the curve it explains on the next
    run, and forces a reader who has found one legend to look for a second.

    Pass the ``Figure`` for a multi-panel figure and the ``Axes`` for a single
    panel. ``handles`` is optional and lets a caller order the entries, which
    matters because Matplotlib fills a multi-column legend column by column.
    """
    options = dict(loc="lower center", frameon=False, fontsize=8, ncol=ncol,
                   handlelength=2.0, columnspacing=1.5, borderaxespad=0.0)
    options.update(kwargs)
    is_figure = isinstance(target, plt.Figure)
    options.setdefault("bbox_to_anchor", (0.5, 1.0) if is_figure else (0.5, 1.02))
    if handles is not None:
        return target.legend(handles=handles, **options)
    return target.legend(**options)


def panel_labels(axes, labels=None, y=0.94, va="top"):
    """Letter each panel in the upper left, bold, over a white box.

    The box is what keeps the letter readable where a dense curve runs through
    the corner. Pass ``y`` and ``va`` for a panel too short to hold a label at
    the top, such as an annotation strip.
    """
    letters = labels if labels is not None else [f"({c})" for c in "abcdefgh"]
    for label, ax in zip(letters, axes):
        ax.text(0.012, y, label, transform=ax.transAxes, ha="left", va=va,
                **PANEL_LABEL_STYLE)


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
