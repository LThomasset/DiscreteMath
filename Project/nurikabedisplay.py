"""Visualization functions for Nurikabe puzzle solver."""

from collections.abc import Sequence
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch, Rectangle
from matplotlib.path import Path

def render(i: int, j: int, grid: Sequence[Sequence[int]],
           shaded: Sequence[Sequence[bool]] | None) -> str:
    """Choose Unicode character for grid position."""
    clue = grid[i][j]
    if clue == 0:
        if shaded is None or not shaded[i][j]:
            return '\u00b7' # raised dot
        else:
            return '\u25a0' # black square
    elif clue == -1:
        return '?'
    else:
        if shaded is None or not shaded[i][j]:
            return f'{clue:X}'
        else: # will not happen in proper solutions
            # Since dingbats didn't have the 0 on black disc,
            # the Unicode character for it is not contiguous to
            # the other digits on black discs.
            if clue == 0:
                return '\u24ff' # 0 in black disc
            else:
                return chr(0x2789+clue) # clue in 

def print_unicode(grid: Sequence[Sequence[int]],
                  shaded: Sequence[Sequence[bool]] | None = None) -> None:
    """Print grid."""
    N = len(grid)
    M = len(grid[0])
    for i in range(N):
        print(' '.join([render(i, j, grid, shaded) for j in range(M)]))

def print_matplotlib(grid: Sequence[Sequence[int]],
                     C: Sequence[Sequence[bool]] | None = None,
                     E: Sequence[Sequence[int]] | None = None,
                     P: Sequence[Sequence[bool]] | None = None,
                     fontsize: int = 24,
                     dpi: int = 100) -> None:
    """Create matplotlib plot of the grid."""
    nrow = len(grid)
    ncol = len(grid[0])
    _fig, ax = plt.subplots(figsize=(ncol+1,nrow+1), dpi=dpi)

    for i in range(nrow):
        _ = ax.annotate(str(i+1), xy=(-1/2,nrow-i-1/2),
                        color='gray', fontsize=fontsize-2,
                        ha='center', va='center')
    for j in range(ncol):
        _ = ax.annotate(str(j+1), xy=(j+1/2,nrow+1/2),
                        color='gray', fontsize=fontsize-2,
                        ha='center', va='center')

    if C is not None:
        for i in range(nrow):
            for j in range(ncol):
                if C[i][j]:
                    rect = Rectangle((j,nrow-i-1),1,1, color='blue')
                    ax.add_patch(rect)

    # Draw clues.
    for i in range(nrow):
        for j in range(ncol):
            clue = grid[i][j]
            if clue != 0:
                text = '?' if clue == -1 else str(clue)
                _ = ax.annotate(text, xy=(j+1/2,nrow-i-1/2),
                                color='black', fontsize=fontsize,
                                ha='center', va='center')

    # Draw grid lines.
    for i in range(nrow+1):
        path = Path([(0,i), (ncol,i)], [Path.MOVETO, Path.LINETO])
        patch = PathPatch(path, color='black', lw=0.75)
        ax.add_patch(patch)

    for j in range(ncol+1):
        path = Path([(j,0), (j,nrow)], [Path.MOVETO, Path.LINETO])
        patch = PathPatch(path, color='black', lw=0.75)
        ax.add_patch(patch)

    # Draw spanning tree.
    if C is not None and E is not None and P is not None:
        for i in range(nrow):
            for j in range(ncol):
                if not C[i][j]:
                    arrowcolor = 'purple' if P[i][j] else 'teal'
                else:
                    arrowcolor = 'yellow' if P[i][j] else 'orange'
                if bool(E[i][j] & 8):
                    hi, hj = 0.6, 0.0
                    ax.arrow(j+0.5, nrow-i-0.3, hj, hi, width=0.08,
                             length_includes_head=True, head_width=0.16,
                             color=arrowcolor)
                if bool(E[i][j] & 4):
                    hi, hj = -0.6, 0.0
                    ax.arrow(j+0.5, nrow-i-0.7, hj, hi, width=0.08,
                             length_includes_head=True, head_width=0.16,
                             color=arrowcolor)
                if bool(E[i][j] & 2):
                    hi, hj = 0.0, 0.6
                    ax.arrow(j+0.7, nrow-i-0.5, hj, hi, width=0.08,
                             length_includes_head=True, head_width=0.16,
                             color=arrowcolor)
                if bool(E[i][j] & 1):
                    hi, hj = 0.0, -0.6
                    ax.arrow(j+0.3, nrow-i-0.5, hj, hi, width=0.08,
                             length_includes_head=True, head_width=0.16,
                             color=arrowcolor)

    # Draw grid boundary.
    path = Path([(0,0), (0,nrow), (ncol,nrow), (ncol,0), (0,0)],
                [Path.MOVETO, Path.LINETO, Path.LINETO, Path.LINETO, Path.CLOSEPOLY])
    patch = PathPatch(path, edgecolor='black', facecolor='none', lw=4)
    ax.add_patch(patch)

    ax.set_xlim(-1.1,ncol+0.1)
    ax.set_ylim(-0.1,nrow+1.1)
    ax.set_aspect('equal','box')
    ax.set_axis_off()
    plt.show()

if __name__ == '__main__':

    from nurikabeinputs import check_grid, get_grid, parse_command

    args = parse_command()

    grid = get_grid(args.puzzle)
    check_grid(grid)

    if args.matplotlib:
        print_matplotlib(grid, C=None, fontsize=args.fontsize)
    else:
        print_unicode(grid)
