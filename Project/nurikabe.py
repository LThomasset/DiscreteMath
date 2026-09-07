"""Z3-based solver of Kurodoko puzzles.

Nurikabe is played on a rectangular grid.  The objective is to shade
some squares, subject to the constraints below.

1. Some squares are shaded.
2. The shaded squares form an orthogonally-connected region.
3. The clues are never shaded.
4. Every orthogonally-connected area of unshaded cells contains
   exactly one clue, whose value is the size of the area.
5. No 2x2 region may be entirely shaded.

"""

from typing import Sequence

import argparse
import sys
import time

from z3 import (Solver, SolverFor, Bool, BoolRef, BoolVal, # type: ignore
                And, Or, Not, sat, unknown, AtMost, AtLeast,
                ModelRef, is_true, simplify)

from Project.nurikabeinputs import get_grid, check_grid, parse_command, find_clues
from Project.nurikabedisplay import print_unicode, print_matplotlib
from Project.nurikabeverify import verify

Square = tuple[int,int]

def evaluate_model(mdl: ModelRef,
                   C: Sequence[Sequence[Sequence[BoolRef]]],
                   H: Sequence[Sequence[Sequence[BoolRef]]],
                   V: Sequence[Sequence[Sequence[BoolRef]]],
                   P: Sequence[Sequence[BoolRef]],
                   R: Sequence[Sequence[BoolRef]]
                   ) -> tuple[list[list[bool]], list[list[int]], list[list[bool]], list[list[bool]]]:
    """Extract a complete solution from the solver's model."""
    nrow = len(C)
    ncol = len(C[0])
    Cbool = [[is_true(mdl.eval(C[i][j][0], model_completion=True))
              for j in range(ncol)] for i in range(nrow)]
    # Decode the H and V variables into four bits: NSEW.
    Eint = [[((8 if is_true(mdl.eval(up_right_edge(V[i][j]), model_completion=True)) else 0) +
              (4 if is_true(mdl.eval(down_left_edge(V[i][j]), model_completion=True)) else 0) +
              (2 if is_true(mdl.eval(up_right_edge(H[i][j]), model_completion=True)) else 0) +
              (1 if is_true(mdl.eval(down_left_edge(H[i][j]), model_completion=True)) else 0))
             for j in range(ncol)] for i in range(nrow)]
    Pbool = [[is_true(mdl.eval(P[i][j], model_completion=True))
              for j in range(ncol)] for i in range(nrow)]
    Rbool = [[is_true(mdl.eval(R[i][j], model_completion=True))
              for j in range(ncol)] for i in range(nrow)]
    return Cbool, Eint, Pbool, Rbool


def solve_and_print(grid: Sequence[Sequence[int]],
                    slv: Solver,
                    C: Sequence[Sequence[Sequence[BoolRef]]],
                    H: Sequence[Sequence[Sequence[BoolRef]]],
                    V: Sequence[Sequence[Sequence[BoolRef]]],
                    P: Sequence[Sequence[BoolRef]],
                    R: Sequence[Sequence[BoolRef]]) -> None:
    """Compute and print solutions."""
    # Replace the exception with your code.
    raise NotImplementedError

def absent_edge(a: Sequence[BoolRef]) -> BoolRef:
    """Return constraint for absent edge."""
    return And(Not(a[0]), Not(a[1]))

def up_right_edge(a: Sequence[BoolRef]) -> BoolRef:
    """Return constraint for edge pointing up or right."""
    return a[1]

def down_left_edge(a: Sequence[BoolRef]) -> BoolRef:
    """Return constraint for edge pointing down or left."""
    return a[0]

def legal_edge(a: Sequence[BoolRef]) -> BoolRef:
    """Return constraint preventing forbidden edge value."""
    return Or(Not(a[0]), Not(a[1]))

def add_constraints(grid: Sequence[Sequence[int]],
                    slv: Solver,
                    C: Sequence[Sequence[Sequence[BoolRef]]],
                    H: Sequence[Sequence[Sequence[BoolRef]]],
                    V: Sequence[Sequence[Sequence[BoolRef]]],
                    P: Sequence[Sequence[BoolRef]],
                    R: Sequence[Sequence[BoolRef]],
                    clues: Sequence[tuple[tuple[int,int],int]],
                    args: argparse.Namespace) -> None:
    """Encode puzzle."""
    # Replace the exception with your code.
    raise NotImplementedError

if __name__ == '__main__':

    starttime = time.process_time()

    sys.stdout.reconfigure(encoding='utf-8') # type: ignore

    args = parse_command()

    comment = '#'

    try:
        grid = get_grid(args.puzzle)
        check_grid(grid)
    except Exception as err:
        raise SystemExit(err)

    nrow = len(grid)
    ncol = len(grid[0])

    if args.drawonly:
        if args.matplotlib:
            print_matplotlib(grid, C=None, fontsize=args.fontsize)
        else:
            print_unicode(grid)
        raise SystemExit(0)

    clues = find_clues(grid)

    slv = SolverFor('QF_FD')

    # C[i][j][0] is true if Cell (i,j) is shaded.
    # C[i][j][k], k > 0 is true if Cell (i,j) is in Island k.
    C = [] # Add definition here.

    # For each arrow:
    # (false,false) means "absent."
    # (false,true)  means "pointing up or right."
    # (true,false)  means "pointing down or left."
    # (true,true)   is forbidden.

    # Horizontal edges.
    H = [] # Add definition here.
    # Vertical edges.
    V = [] # Add definition here.

    # Turn parity variables.
    P = [] # Add definition here.

    # Root variables.
    R = [] # Add definition here.

    add_constraints(grid, slv, C, H, V, P, R, clues, args)

    if args.verbose > 1:
        for a in slv.assertions():
            print(a)

    print(comment, 'Encoding time: {0:.4} s'.format(time.process_time() - starttime))

    solve_and_print(grid, slv, C, H, V, P, R)

    print(comment, 'CPU time: {0:.4} s'.format(time.process_time() - starttime))
