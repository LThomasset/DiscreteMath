"""Functions to verify Nurikabe solutions."""

from collections.abc import Sequence

from nurikabeinputs import find_clues
from nurikabedisplay import print_matplotlib

Square = tuple[int,int]

def find_first_shaded(shaded: Sequence[Sequence[bool]]) -> Square:
    """Return coordinates of first shaded square."""
    nrow = len(shaded)
    ncol = len(shaded[0])

    for i in range(nrow):
        for j in range(ncol):
            if shaded[i][j]:
                return i,j

    raise ValueError('No shaded square!')

def get_neighbors(current: Square,
                  shaded: Sequence[Sequence[bool]]) -> list[Square]:
    """Collect shaded neighbors of current."""
    nrow = len(shaded)
    ncol = len(shaded[0])

    i, j = current
    nbors = []
    if i > 0 and shaded[i-1][j]:
        nbors.append((i-1,j,))
    if i < nrow-1 and shaded[i+1][j]:
        nbors.append((i+1,j,))
    if j > 0 and shaded[i][j-1]:
        nbors.append((i,j-1,))
    if j < ncol-1 and shaded[i][j+1]:
        nbors.append((i,j+1,))

    return nbors

def verify(grid: Sequence[Sequence[int]],
           shaded: Sequence[Sequence[bool]],
           allow_weak: bool = False) -> None:
    """Verify solution to Nurikabe puzzle."""
    nrow = len(grid)
    ncol = len(grid[0])

    # No clues are shaded.
    clues = find_clues(grid)
    nclues = len(clues)
    for (i,j), clue in clues:
        if shaded[i][j]:
            raise ValueError(f'Clue at ({i+1},{j+1}) is shaded')

    # No 2x2 region is entirely shaded.
    for i in range(nrow-1):
        for j in range(ncol-1):
            if shaded[i][j] and shaded[i][j+1] and shaded[i+1][j] and shaded[i+1][j+1]:
                raise ValueError(f'Shaded 2x2 with upper-left corner at ({i+1},{j+1}).')

    # Count shaded cells in the whole grid.
    totalcount = 0
    for i in range(nrow):
        count = sum([shaded[i][j] for j in range(ncol)])
        totalcount += count

    if totalcount < 1:
        raise ValueError('There should be at least one shaded cell.')

    # If no clue is a '?', then we can check whether
    # all cells are accounted for.
    determined = all(clue != -1 for root, clue in clues)

    if determined:
        dryland = sum(clue for root, clue in clues)
        if totalcount + dryland != nrow * ncol:
            raise ValueError(f'{totalcount} shaded cells plus '
                             f'{dryland} cells from clues do not '
                             f'add up to {nrow} * {ncol} = {nrow*ncol} cells')

    if not allow_weak:
        # Check reachability of all shaded cells from a root.
        root = find_first_shaded(shaded)

        reached = set()
        work = {root}

        while len(work) > 0:
            current = work.pop()
            reached.add(current)
            for cell in get_neighbors(current, shaded):
                if cell not in reached:
                    work.add(cell)

        if len(reached) != totalcount:
            i, j = root
            raise ValueError(f'Reached {len(reached)} shaded cells '
                             f'from ({i+1},{j+1}) instead of {totalcount}.')

        # Check whether islands have the right size.
        regions = [[0 if shaded[i][j] else -2 for j in range(ncol)] for i in range(nrow)]
        unshaded = [[not shaded[i][j] for j in range(ncol)] for i in range(nrow)]
        for k in range(nclues):
            (i,j), clue = clues[k]
            # Find cells reachable from this root.
            reached = set()
            work = {(i,j)}

            while len(work) > 0:
                current = work.pop()
                reached.add(current)
                for cell in get_neighbors(current, unshaded):
                    if cell not in reached:
                        work.add(cell)
            if clue != -1 and len(reached) != clue:
                raise ValueError(f'Reached {len(reached)} cells '
                                 f'from ({i+1},{j+1}) instead of {totalcount}.')

            for r,c in reached:
                regions[r][c] = k+1

        # for i in range(nrow):
        #     print(' '.join([f'{regions[i][j]}' for j in range(ncol)]))

        # All cells are either shaded or in one of the islands.
        for i in range(nrow):
            for j in range(ncol):
                if regions[i][j] == -2:
                    raise ValueError(f'Cell ({i+1},{j+1}) is neither shaded nor part of an island.')

        # Islands do not share edges.
        for i in range(nrow):
            for j in range(ncol):
                island = regions[i][j]
                if island != 0: # part of an island
                    if i > 0:
                        above = regions[i-1][j]
                        if above != 0 and above != island:
                            raise ValueError(f'Different islands touch at'
                                             f' ({i},{j+1}) and ({i+1},{j+1}).')
                    if j > 0:
                        left = regions[i][j-1]
                        if left != 0 and left != island:
                            raise ValueError(f'Different islands touch at'
                                             f' ({i+1},{j}) and ({i+1},{j+1}).')

if __name__ == '__main__':

    _ = 0
    grid = ((_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_),
            (_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_),
            (_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_),
            (_,_,_,_,_,_,_,_,_,6,_,_,_,_,_,_,_,_,_,_),
            (_,_,_,_,_,_,_,_,_,_,_,_,6,_,_,_,_,40,_,_),
            (_,_,_,_,_,_,_,_,_,_,7,_,_,_,_,_,_,_,_,_),
            (_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,40,_),
            (_,_,_,_,_,_,_,_,_,_,_,_,_,6,_,2,_,_,_,_),
            (_,_,_,_,7,_,_,_,_,_,_,8,_,_,_,_,_,_,_,_),
            (_,_,_,_,_,_,_,_,6,_,_,_,_,_,_,_,_,_,_,_),
            (_,_,_,6,_,_,7,_,_,_,_,_,_,_,_,_,_,_,_,_),
            (_,_,_,_,_,1,_,_,_,_,_,_,_,_,_,_,1,_,1,_),
            (_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,3,_,_,_,_),
            (_,_,_,_,_,_,_,_,_,_,_,_,8,_,_,_,_,_,_,_),
            (_,_,_,_,_,_,_,4,_,_,_,_,_,_,_,_,_,_,_,_),
            (_,_,_,3,_,_,_,_,_,_,_,6,_,_,_,_,_,_,_,_),
            (_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_),
            (_,_,_,_,_,_,_,_,_,_,2,_,_,_,_,_,_,_,_,_),
            (_,_,_,_,_,3,_,_,_,_,_,_,_,_,_,_,_,_,_,_),
            (_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_))

    T, _ = True, False

    shaded = ((T,T,T,T,T,T,T,T,T,T,T,T,T,T,T,T,T,T,T,T),
              (T,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,_,T),
              (T,_,T,T,T,T,T,T,T,T,T,T,T,T,T,T,T,T,_,T),
              (T,_,T,_,T,_,_,_,_,_,_,T,_,_,_,_,_,T,_,T),
              (T,_,T,_,T,T,T,T,T,T,T,T,_,T,T,T,T,_,_,T),
              (T,_,T,_,T,_,_,_,_,_,_,T,T,T,_,_,_,T,T,T),
              (T,_,T,_,T,_,T,T,T,T,T,_,T,_,_,T,T,T,_,T),
              (T,_,T,_,T,T,_,_,_,T,_,_,T,_,T,_,_,T,_,T),
              (T,_,T,_,_,T,_,T,T,T,_,_,_,T,T,T,T,T,_,T),
              (T,_,T,T,T,_,_,T,_,T,_,_,T,T,_,_,_,_,_,T),
              (T,_,T,_,T,T,_,T,_,T,T,T,T,_,_,T,T,T,T,T),
              (T,_,T,_,T,_,T,T,_,T,_,_,_,_,T,T,_,T,_,T),
              (T,_,T,_,T,T,_,_,_,T,_,T,T,T,T,_,T,T,T,T),
              (T,_,T,_,_,T,T,T,T,_,_,T,_,_,T,_,_,T,_,T),
              (T,_,T,T,_,T,_,_,T,_,T,T,T,_,_,T,T,T,_,T),
              (T,_,T,_,T,T,_,T,_,_,T,_,_,T,_,_,_,T,_,T),
              (T,_,T,_,_,T,_,T,_,T,_,T,_,T,T,T,_,T,_,T),
              (T,_,T,T,T,T,T,T,_,T,_,T,_,_,_,T,T,T,_,T),
              (T,_,_,T,_,_,_,T,_,T,T,T,T,T,T,T,_,_,_,T),
              (T,T,T,T,T,T,T,T,_,_,_,_,_,_,_,_,_,T,T,T))

    print_matplotlib(grid, shaded)
    verify(grid, shaded)
              
