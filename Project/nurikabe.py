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

from nurikabeinputs import get_grid, check_grid, parse_command, find_clues
from nurikabedisplay import print_unicode, print_matplotlib
from nurikabeverify import verify

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
    # ---------------Temporary for oct 7 deadline -------------------
    if not V:
        return Cbool, [], [], []
    # ---------------Temporary for oct 7 deadline -------------------
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
    solution_count = 0
    while slv.check() == sat:
        mdl = slv.model()
        Cbool, Eint, Pbool, Rbool = evaluate_model(mdl, C, H, V, P, R)
        if args.matplotlib:
            print_matplotlib(grid, Cbool, fontsize=args.fontsize)
        else:
            print_unicode(grid, Cbool)
        solution_count += 1
        if args.solutions is not None and solution_count ==args.solutions:
            break
    # blocking clause
    blocking_clause = []
    for i in range(len(C)):
        for j in range(len(C[0])):
            if Cbool[i][j]:
                # if shaded, make it not shaded next time
                blocking_clause.append(Not(C[i][j][0]))
            else:
                # if not shaded, make it shaded next time
                blocking_clause.append(C[i][j][0])
    slv.add(Or(*blocking_clause))
    print(comment, 'Number of solutions found: {0}'.format(solution_count))

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
    # if it is a clue, then it cannot be shaded (in a stream), so C[i][j][0] must be false
    for (i, j), clue in clues:
        slv.add(Not(C[i][j][0]))

    # no 2x2 region may be entirely shaded
    nrow = len(grid)
    ncol = len(grid[0])
    for i in range(nrow -1):
        for j in range(ncol - 1):
            # at most 3 of the 4 cells can be shaded
            slv.add(AtMost(C[i][j][0], C[i+1][j][0], C[i][j+1][0], C[i+1][j+1][0], 3)) 

    # mutual exclusivity of stream (shading) vs island
    for i in range(nrow):
        for j in range(ncol):
            # at most one of the options can be true
            slv.add(AtMost(*C[i][j], 1)) # note: * is not a pointer, it's an unpackaging operator that takes the C list and runs all possible combinations of C into AtMost
            # every cell must be a stream or an island
            slv.add(AtLeast(*C[i][j], 1))

    # each clue belongs to only one island, and the size of the island must match the clue
    for k, ((i, j), clue) in enumerate(clues, start=1): # enumerate = iterates list while keeping track of the index
        # the clue belongs to island k
        slv.add(C[i][j][k])
        # only applies to clues that arent "?" (represented by -1)
        if clue != -1:
            # island size must match the clue
            island_cells = [C[x][y][k] for x in range(nrow) for y in range(ncol)]
            slv.add(AtMost(*island_cells, clue))
            slv.add(AtLeast(*island_cells, clue))

    # no distinct islands can touch each other orthogonally
    for k in range(1, len(clues) + 1):
        for i in range(nrow):
            for j in range(ncol):
                # check neighbors
                if i > 0:
                    slv.add(Or(Not(C[i][j][k]), C[i-1][j][k], C[i-1][j][0]))
                if i < nrow - 1:
                    slv.add(Or(Not(C[i][j][k]), C[i+1][j][k], C[i+1][j][0]))
                if j > 0:
                    slv.add(Or(Not(C[i][j][k]), C[i][j-1][k], C[i][j-1][0]))
                if j < ncol - 1:
                    slv.add(Or(Not(C[i][j][k]), C[i][j+1][k], C[i][j+1][0]))


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
    # for k in range clues + 1 (if 5 clues, then range generates 0-5 so there are 6 options for k) and j represents column and i represents row
    C = [[[Bool(f'c_{i}_{j}_{k}') for k in range(len(clues) + 1)] 
         for j in range(ncol)] 
         for i in range(nrow)] 

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
