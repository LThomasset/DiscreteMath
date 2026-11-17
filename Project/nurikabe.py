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
import heapq

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

# Dijkstra shortest-path helper function
def shortest_paths(
        nrow: int,
        ncol: int,
        sources: Sequence[Square],
        obstacles: set[Square]
) -> dict[Square, int]:
    """Compute the shortest-path distances from sources, avoiding sqares in obstacles"""
    dist: dict[Square, int] = {}
    pq: list[tuple[int, Square]] = []
    for src in sources:
        if src not in obstacles:
            dist[src] = 1
            heapq.heappush(pq, (1, src))
    while pq:
        d, (r, c) = heapq.heappop(pq)
        if d > dist[(r, c)]:
            continue
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < nrow and 0 <= nc < ncol and (nr, nc) not in obstacles:
                if (nr, nc) not in dist or d + 1 < dist[(nr, nc)]:
                    dist[(nr, nc)] = d + 1
                    heapq.heappush(pq, (d+1, (nr, nc)))
    return dist

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
    nrow = len(grid)
    ncol = len(grid[0])

    # if it is a clue, then it cannot be shaded (in a stream), so C[i][j][0] must be false
    for (i, j), clue in clues:
        slv.add(Not(C[i][j][0]))

    # no 2x2 region may be entirely shaded
    for i in range(nrow - 1):
        for j in range(ncol - 1):
            # at most 3 of the 4 cells can be shaded
            slv.add(AtMost(C[i][j][0], C[i+1][j][0], C[i][j+1][0], C[i+1][j+1][0], 3))

    has_question_mark = any(clue == -1 for _, clue in clues)
    clue_set = {pos for pos, _ in clues}

    # 1. FIRST: Identify squares guaranteed to be shaded BEFORE running shortest paths
    known_shaded: set[Square] = set()

    # neighbors of 1 clues and squares adjacent to >=2 clues must be shaded
    for i in range(nrow):
        for j in range(ncol):
            if (i, j) in clue_set:
                continue
            adj_clues = 0
            adj_to_one = False
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                ni, nj = i + dr, j + dc
                if 0 <= ni < nrow and 0 <= nj < ncol and grid[ni][nj] != 0:
                    adj_clues += 1
                    if grid[ni][nj] == 1:
                        adj_to_one = True
            if adj_to_one or adj_clues >= 2:
                slv.add(C[i][j][0])
                known_shaded.add((i, j))

    # restricted penalty theory (run first so border shaded squares are added to known_shaded)
    if not has_question_mark:
        G = sum(2 * (clue_val + 1) for _, clue_val in clues)
        max_penalties = G - (nrow - 1) * (ncol - 1)
        # count penalties already accounted for by clues on border or sharing corners
        clue_penalties = 0
        for vr in range(nrow + 1):
            for vc in range(ncol + 1):
                # find how many clue squares touch grid vertex (vr, vc)
                touching_clues = 0
                for r, c in ((vr - 1, vc - 1), (vr - 1, vc), (vr, vc - 1), (vr, vc)):
                    if 0 <= r < nrow and 0 <= c < ncol and (r, c) in clue_set:
                        touching_clues += 1
                if vr == 0 or vr == nrow or vc == 0 or vc == ncol:
                    # outer boundary vertex: every clue touching it wastes 1 point
                    clue_penalties += touching_clues
                else:  # interior vertex: two clues sharing a corner wastes one point
                    if touching_clues > 1:
                        clue_penalties += touching_clues - 1

        if clue_penalties == max_penalties:
            # all non-clue squares on outer border of grid must be shaded
            for i in range(nrow):
                for j in range(ncol):
                    if (i == 0 or i == nrow - 1 or j == 0 or j == ncol - 1) and (i, j) not in clue_set:
                        slv.add(C[i][j][0])
                        known_shaded.add((i, j))
            # no 2x2 block can be completely unshaded or form a checkerboard pattern
            for i in range(nrow - 1):
                for j in range(ncol - 1):
                    s00 = C[i][j][0]
                    s10 = C[i+1][j][0]
                    s01 = C[i][j+1][0]
                    s11 = C[i+1][j+1][0]
                    # at least one square in every 2x2 is shaded
                    slv.add(Or(s00, s10, s01, s11))
                    # no checkerboard pattern (type 1)
                    slv.add(Or(Not(s00), Not(s11), s10, s01))
                    # no checkerboard pattern (type 2)
                    slv.add(Or(s00, s11, Not(s10), Not(s01)))

    # 2. SECOND: compute reachable squares for each clue (using known_shaded as obstacles too!)
    dist_from_clue: dict[int, dict[Square, int]] = {}
    reachable_by_clue: dict[int, set[Square]] = {}

    for k, ((ci, cj), clue_val) in enumerate(clues, start=1):
        # known_shaded + other clues and their orthogonal neighbors are obstacles for island k
        obstacles: set[Square] = set(known_shaded)
        for m, ((oi, oj), _) in enumerate(clues, start=1):
            if m != k:
                obstacles.add((oi, oj))
                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nr, nc = oi + dr, oj + dc
                    if 0 <= nr < nrow and 0 <= nc < ncol:
                        obstacles.add((nr, nc))

        dmap = shortest_paths(nrow, ncol, [(ci, cj)], obstacles)
        dist_from_clue[k] = dmap

        if clue_val != -1:
            reachable = {sq for sq, d in dmap.items() if d <= clue_val}
        else:
            # for ? clues, any square reachable without hitting another clue's halo
            reachable = set(dmap.keys())
        reachable_by_clue[k] = reachable

        # make cijk false if ij cannot be reached by island k
        for i in range(nrow):
            for j in range(ncol):
                if (i, j) not in reachable:
                    slv.add(Not(C[i][j][k]))

    # 3. THIRD: 2x2 shortest path
    for i in range(nrow - 1):
        for j in range(ncol - 1):
            block = [(i, j), (i+1, j), (i, j+1), (i+1, j+1)]
            # find which islands can reach at least one square in the block
            reaching_islands = [
                k for k in range(1, len(clues) + 1)
                if any(sq in reachable_by_clue[k] for sq in block)
            ]
            # at least one (square, island) pair in 2x2 must be True
            possible_vars = [
                C[r][c][k] for k in reaching_islands
                for (r, c) in block if (r, c) in reachable_by_clue[k]
            ]
            if possible_vars:
                slv.add(Or(*possible_vars))

            # if only one island k can reach 2x2, check shortest-path condition
            if len(reaching_islands) == 1:
                k = reaching_islands[0]
                (ci, cj), clue_val = clues[k-1]
                if clue_val != -1:
                    min_d = min(
                        dist_from_clue[k][sq] for sq in block
                        if sq in reachable_by_clue[k]
                    )
                    if min_d == clue_val:
                        targets = [
                            sq for sq in block
                            if sq in reachable_by_clue[k] and dist_from_clue[k][sq] == clue_val
                        ]
                        # recompute obstacles for island k (including known_shaded!)
                        obstacles = set(known_shaded)
                        for m, ((oi, oj), _) in enumerate(clues, start=1):
                            if m != k:
                                obstacles.add((oi, oj))
                                for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                                    nr, nc = oi + dr, oj + dc
                                    if 0 <= nr < nrow and 0 <= nc < ncol:
                                        obstacles.add((nr, nc))
                        dist_to_target = shortest_paths(nrow, ncol, targets, obstacles)
                        on_sp = {
                            sq for sq in reachable_by_clue[k]
                            if sq in dist_to_target
                            and dist_from_clue[k][sq] + dist_to_target[sq] - 1 == clue_val
                        }
                        # rule out squares not on any shortest path to the 2x2
                        for (r, c) in list(reachable_by_clue[k]):
                            if (r, c) not in on_sp:
                                slv.add(Not(C[r][c][k]))
                                reachable_by_clue[k].remove((r, c))
                        # if only one square is at distance d on shortest paths, make it
                        for d in range(1, clue_val + 1):
                            cells_at_d = [sq for sq in on_sp if dist_from_clue[k][sq] == d]
                            if len(cells_at_d) == 1:
                                r, c = cells_at_d[0]
                                slv.add(C[r][c][k])

    # 4. FOURTH: cardinality loop & auto-shade squares unreachable from all clues
    for k, ((i, j), clue) in enumerate(clues, start=1):
        # the clue belongs to island k
        slv.add(C[i][j][k])
        # only applies to clues that arent ? (-1)
        if clue != -1:
            # only count squares that are actually reachable by island k
            island_cells = [C[r][c][k] for (r, c) in reachable_by_clue[k]]
            slv.add(AtMost(*island_cells, clue))
            slv.add(AtLeast(*island_cells, clue))

    # squares unreachable from all clues must be shaded
    for i in range(nrow):
        for j in range(ncol):
            if all((i, j) not in reachable_by_clue[k] for k in range(1, len(clues) + 1)):
                slv.add(C[i][j][0])
                known_shaded.add((i, j))

    # mutual exclusivity of stream (shading) vs island
    for i in range(nrow):
        for j in range(ncol):
            # at most one of the options can be true
            slv.add(AtMost(*C[i][j], 1))
            # every cell must be a stream or an island
            slv.add(AtLeast(*C[i][j], 1))

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
        for j in range(ncol):
            # check incoming directions (up, down, left, right)
            # incoming from below i+1, j
            if i < nrow - 1:
                if j < ncol - 1:
                    slv.add(Or(Not(up_right_edge(V[i+1][j])),
                               Not(up_right_edge(H[i][j])),
                               P[i][j] != P[i+1][j]))
                if i > 0:
                    slv.add(Or(Not(up_right_edge(V[i+1][j])),
                               Not(up_right_edge(V[i][j])),
                               P[i][j] == P[i+1][j]))
                if j > 0:
                    slv.add(Or(Not(up_right_edge(V[i+1][j])),
                               Not(down_left_edge(H[i][j])),
                               P[i][j] == P[i+1][j]))
            # incoming from left
            if j > 0:
                if i > 0:
                    slv.add(Or(Not(up_right_edge(H[i][j-1])),
                               Not(up_right_edge(V[i][j])),
                               P[i][j] != P[i][j-1]))
                if i < nrow - 1:
                    slv.add(Or(Not(up_right_edge(H[i][j-1])),
                               Not(down_left_edge(V[i][j])),
                               P[i][j] == P[i][j-1]))
                if j < ncol - 1:
                    slv.add(Or(Not(up_right_edge(H[i][j-1])),
                               Not(up_right_edge(H[i][j])),
                               P[i][j] == P[i][j-1]))
            # incoming from above
            if i > 0:
                if i < nrow - 1:
                    slv.add(Or(Not(down_left_edge(V[i-1][j])),
                               Not(down_left_edge(V[i][j])),
                               P[i][j] == P[i-1][j]))
                if j < ncol - 1:
                    slv.add(Or(Not(down_left_edge(V[i-1][j])),
                               Not(up_right_edge(H[i][j])),
                               P[i][j] == P[i-1][j]))
                if j > 0:
                    slv.add(Or(Not(down_left_edge(V[i-1][j])),
                               Not(down_left_edge(H[i][j])),
                               P[i][j] == P[i-1][j]))
            # incoming from right
            if j < ncol - 1:
                if i < nrow - 1:
                    slv.add(Or(Not(down_left_edge(H[i][j+1])),
                               Not(down_left_edge(V[i][j])),
                               P[i][j] == P[i][j+1]))
                if j > 0:
                    slv.add(Or(Not(down_left_edge(H[i][j+1])),
                               Not(down_left_edge(H[i][j])),
                               P[i][j] == P[i][j+1]))
                if i > 0:
                    slv.add(Or(Not(down_left_edge(H[i][j+1])),
                               Not(up_right_edge(V[i][j])),
                               P[i][j] == P[i][j+1]))

    # root constraints
    # if known_shaded is not empty, pick one square from known_shaded and choose it as a unique root
    if known_shaded:
        root_r, root_c = sorted(known_shaded)[0]
        for i in range(nrow):
            for j in range(ncol):
                if (i, j) == (root_r, root_c):
                    slv.add(R[i][j])
                else:
                    slv.add(Not(R[i][j]))
    else:
        for i in range(nrow):
            for j in range(ncol):
                # either square (i,j) is not the stream root or square (i,j) is shaded
                slv.add(Or(Not(R[i][j]), C[i][j][0]))
        # at most, only one square in the grid can be the stream root
        all_roots = [R[i][j] for i in range(nrow) for j in range(ncol)]
        slv.add(AtMost(*all_roots, 1))
        slv.add(AtLeast(*all_roots, 1))

    for i in range(nrow):
        for j in range(ncol):
            # every edge must be legal, there cannot be (True, True)
            slv.add(legal_edge(H[i][j]))
            slv.add(legal_edge(V[i][j]))
            # every square that's not a root must have one outgoing arrow
            if grid[i][j] != 0:  # clue squares are roots & have no outgoing arrows
                slv.add(absent_edge(H[i][j]))
                slv.add(absent_edge(V[i][j]))
            if grid[i][j] == 0:  # either is root or has arrow (if has arrow, either H or V is not absent)
                slv.add(Or(R[i][j], absent_edge(V[i][j]) != absent_edge(H[i][j])))
                slv.add(Or(Not(R[i][j]), absent_edge(V[i][j])))
                slv.add(Or(Not(R[i][j]), absent_edge(H[i][j])))

    # arrow boundaries
    for i in range(nrow):
        for j in range(ncol):
            # pointing up
            if i == 0:  # if in top row, can't point up
                slv.add(Not(up_right_edge(V[i][j])))
            else:  # else, if ij points up, ij and i-1 j must have same shading
                slv.add(Or(Not(up_right_edge(V[i][j])), C[i][j][0] == C[i-1][j][0]))
            # pointing down
            if i == nrow - 1:  # if in bottom row, cant point down
                slv.add(Not(down_left_edge(V[i][j])))
            else:  # else, if ij points down, ij and i+1 j must have same shading
                slv.add(Or(Not(down_left_edge(V[i][j])), C[i][j][0] == C[i+1][j][0]))
            # pointing left
            if j == 0:  # if on left side, can't point left
                slv.add(Not(down_left_edge(H[i][j])))
            else:  # else, if ij points left, ij and i j-1 must have same shading
                slv.add(Or(Not(down_left_edge(H[i][j])), C[i][j][0] == C[i][j-1][0]))
            # pointing right
            if j == ncol - 1:  # if on right side, can't point right
                slv.add(Not(up_right_edge(H[i][j])))
            else:  # else, if ij points right, ij and i j+1 must have same shading
                slv.add(Or(Not(up_right_edge(H[i][j])), C[i][j][0] == C[i][j+1][0]))

            # stop 2 squares from pointing into each other
            if j > 0:
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
