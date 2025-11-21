import matplotlib.pyplot as plt

def set_professional_style(latex=False, fontsize=12):
    """Configure Matplotlib for professional scientific plots."""
    
    plt.style.use('default')  # start clean

    # Basic font setup
    plt.rc('font', size=fontsize, family='serif')
    plt.rc('axes', titlesize=fontsize+2, labelsize=fontsize-2, linewidth=1.2)
    plt.rc('legend', fontsize=fontsize, frameon=True, framealpha=0.95, edgecolor='black', fancybox=True)
    plt.rc('xtick', labelsize=fontsize-2, direction='in')
    plt.rc('ytick', labelsize=fontsize-2, direction='in')


    # Tick thickness and size
    plt.rc('xtick.major', width=1.2, size=6)
    plt.rc('xtick.minor', width=1.0, size=3)
    plt.rc('ytick.major', width=1.2, size=6)
    plt.rc('ytick.minor', width=1.0, size=3)

    # Grid appearance
    plt.rc('grid', linestyle='--', linewidth=0.7, color='gray', alpha=0.6)

    # Line styles
    plt.rc('lines', linewidth=2.2)

    # Figure appearance
    plt.rc('figure', dpi=120)
    plt.rc('savefig', dpi=300, bbox='tight', format='svg')

    # Optional LaTeX rendering
    if latex:
        plt.rc('text', usetex=True)
        plt.rc('font', family='serif')
    else:
        plt.rc('text', usetex=False)

    return plt