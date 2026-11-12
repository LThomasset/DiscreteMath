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
    solution_count = 0
    while slv.check() == sat:
        mdl = slv.model()
        Cbool, Eint, Pbool, Rbool = evaluate_model(mdl, C, H, V, P, R)

        #verify valid solution
        errors = verify(grid, Cbool)
        if errors:
            for er in errors:
                print(comment, er)
        # displays solution: -m, -a, -f, -D
        if args.matplotlib:
            if args.annotate: # -a, "to request that the displayed solution include also the values of the p variables.
                #Eint = which direction the square's arrows are facing, Pbool = Parity values
                print_matplotlib(grid, Cbool, Eint, Pbool, fontsize=args.fontsize, dpi = args.dpi)
            else:
                print_matplotlib(grid, Cbool, fontsize=args.fontsize, dpi=args.dpi)
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

    # -r statistics
    if args.report:
        print(slv.statistics())

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

    # parity constraints
    # iterate through every square as if it were a "middle square"
    for i in range(nrow):
        for j in range (ncol):
            #check incoming directions (up, down, left, right)
            # incoming from below i+1, j
            if i < nrow-1:
                if j < ncol-1:
                    # took Incoming And Outgoing --> Parity and (with demorgan's law) turned it into OR(Not(incoming), Not(outgoing), Parity)
                    # "Either there is NOT an incoming arrow here, OR there is NOT an outgoing arrow here, OR the parity rule holds."
                    # outgoing right from ij, up then right --> flip parity
                    slv.add(Or(Not(up_right_edge(V[i+1][j])), # Not(incoming)
                               Not(up_right_edge(H[i][j])), #Not(outgoing)
                               P[i][j]!=P[i+1][j])) #parity
                if i>0:
                    #outgoing up from ij, straight up --> keep parity
                    slv.add(Or(Not(up_right_edge(V[i+1][j])),
                                Not(up_right_edge(V[i][j])),
                                P[i][j]==P[i+1][j]))
                if j>0:
                    #outgoing left from ij, up then left --> keep parity
                    slv.add(Or(Not(up_right_edge(V[i+1][j])),
                                Not(down_left_edge(H[i][j])),
                                P[i][j]==P[i+1][j]))
            # incoming from left
            if j > 0:
                if i > 0:
                    # outgoing up from ij, right then up --> flip parity
                    slv.add(Or(Not(up_right_edge(H[i][j-1])),
                                Not(up_right_edge(V[i][j])),
                                P[i][j]!=P[i][j-1]))
                if i < nrow-1:
                    # outgoing down from ij, right then down --> keep parity
                    slv.add(Or(Not(up_right_edge(H[i][j-1])),
                                Not(down_left_edge(V[i][j])),
                                P[i][j]==P[i][j-1]))
                if j < ncol-1:
                    # outgoing right from ij, straight right --> keep parity
                    slv.add(Or(Not(up_right_edge(H[i][j-1])),
                                Not(up_right_edge(H[i][j])),
                                P[i][j]==P[i][j-1]))
            # incoming from above
            if i > 0:
                if i < nrow-1:
                    # outgoing down from ij, straight down --> keep parity
                    slv.add(Or(Not(down_left_edge(V[i-1][j])),
                               Not(down_left_edge(V[i][j])),
                               P[i][j]==P[i-1][j]))
                if j < ncol-1:
                    # outgoing right from ij, down then right --> keep parity
                    slv.add(Or(Not(down_left_edge(V[i-1][j])),
                                Not(up_right_edge(H[i][j])),
                                P[i][j]==P[i-1][j]))
                if j > 0:
                    # outgoing left from ij, down then left --> keep parity
                    slv.add(Or(Not(down_left_edge(V[i-1][j])),
                                Not(down_left_edge(H[i][j])),
                                P[i][j]==P[i-1][j]))
            # incoming from right
            if j < ncol-1:
                if i < nrow-1:
                    # outgoing down from ij, left then down --> keep parity
                    slv.add(Or(Not(down_left_edge(H[i][j+1])),
                               Not(down_left_edge(V[i][j])),
                               P[i][j]==P[i][j+1]))
                if j > 0:
                    # outgoing left from ij, straight left --> keep parity
                    slv.add(Or(Not(down_left_edge(H[i][j+1])),
                                Not(down_left_edge(H[i][j])),
                                P[i][j]==P[i][j+1]))
                if i > 0:
                    # outgoing up from ij, left the up --> keep parity
                    slv.add(Or(Not(down_left_edge(H[i][j+1])),
                                Not(up_right_edge(V[i][j])),
                                P[i][j]==P[i][j+1]))


    # root constraints
    # if a square is the stream root, it must be shaded
    for i in range(nrow):
        for j in range(ncol):
            # either square (i,j) is not the stream root or square (i,j) is shaded
            slv.add(Or(Not(R[i][j]), C[i][j][0]))
    #at most, only one square in the grid can be the stream root
    #turns 2d grid into 1d list of all R[i][j]
    all_roots = [R[i][j] for i in range(nrow) for j in range(ncol)]
    slv.add(AtMost(*all_roots, 1)) # at most 1 stream root
    slv.add(AtLeast(*all_roots, 1)) # at least 1 stream root 

    for i in range(nrow):
        for j in range(ncol):
            #every edge must be legal, there cannot be (True, True)
            slv.add(legal_edge(H[i][j]))
            slv.add(legal_edge(V[i][j]))
            #every square that's not a root must have one outgoing arrow
            if grid[i][j] != 0: #clue squares are roots & have no outgoing arrows
                slv.add(absent_edge(H[i][j]))
                slv.add(absent_edge(V[i][j]))
            if grid[i][j] ==0: #either is root or has arrow (if has arrow, either H or V is not absent)
                slv.add(Or(R[i][j], absent_edge(V[i][j])!= absent_edge(H[i][j])))
                slv.add(Or(Not(R[i][j]), absent_edge(V[i][j])))
                slv.add(Or(Not(R[i][j]), absent_edge(H[i][j])))

    # arrow boundaries
    for i in range(nrow):
        for j in range(ncol):
            # pointing up
            if i == 0:#if in top row, can't point up
                slv.add(Not(up_right_edge(V[i][j])))
            else: #else, if ij points up, ij and i-1 j must have same shading
                slv.add(Or(Not(up_right_edge(V[i][j])), C[i][j][0] == C[i-1][j][0]))
            # pointing down
            if i == nrow-1: #if in bottom row, cant point down
                slv.add(Not(down_left_edge(V[i][j])))
            else: #else, if ij points down, ij and i+1 j must have same shading
                slv.add(Or(Not(down_left_edge(V[i][j])), C[i][j][0] == C[i+1][j][0]))
            #pointing left
            if j == 0: #if on left side, can't point left
                slv.add(Not(down_left_edge(H[i][j])))
            else: #else, if ij points left, ij and i j-1 must have same shading
                slv.add(Or(Not(down_left_edge(H[i][j])), C[i][j][0] == C[i][j-1][0]))
            #pointing right
            if j == ncol - 1: # if on right side, can't point right
                slv.add(Not(up_right_edge(H[i][j])))
            else: #else, if ij points right, ij and i j+1 must have same shading
                slv.add(Or(Not(up_right_edge(H[i][j])), C[i][j][0] == C[i][j+1][0]))

            #stop 2 squares from pointing into each other
            if j>0:
                # ij can't point left while i j-1 points right
                slv.add(Or(Not(down_left_edge(H[i][j])), Not(up_right_edge(H[i][j-1]))))
            if i > 0:
                # ij can't point up while i-1 j points down
                slv.add(Or(Not(up_right_edge(V[i][j])), Not(down_left_edge(V[i-1][j]))))




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
    H = [[[Bool(f'h_{i}_{j}_{k}') for k in range(2)] # makes sure to check h_i_j_0 (left) and h_i_j_1 (right)
          for j in range(ncol)]
          for i in range(nrow)]
    # Vertical edges.
    V = [[[Bool(f'v_{i}_{j}_{k}') for k in range(2)] # makes sure to check v_i_j_0 (down) and v_i_j_1 (up)
          for j in range(ncol)]
          for i in range(nrow)]

    # Turn parity variables.
    P = [[Bool(f'p_{i}_{j}') # defining the parity bool
           for j in range (ncol)]
           for i in range (nrow)]

    # Root variables.
    R = [[Bool(f'r_{i}_{j}') # defines root
          for j in range (ncol)]
          for i in range (nrow)] 

    add_constraints(grid, slv, C, H, V, P, R, clues, args)

    if args.verbose > 1:
        for a in slv.assertions():
            print(a)

    print(comment, 'Encoding time: {0:.4} s'.format(time.process_time() - starttime))

    solve_and_print(grid, slv, C, H, V, P, R)

    print(comment, 'CPU time: {0:.4} s'.format(time.process_time() - starttime))
