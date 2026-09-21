# ANSWER: [8, 1, 15, 10, 6, 3, 13, 12, 4, 5, 11, 14, 2, 7, 9]

import sys
from z3 import *

# Read optional command line argument
if len(sys.argv) > 2:
    raise SystemExit("There should be at most one argument")
elif len(sys.argv) == 2:
    try:
        N = int(sys.argv[1])
    except:
        raise SystemExit("N should be an integer")
    if N < 0:
        raise SystemExit("N should be non-negative")
else:
    N = 15 # default value

def solve_square_permutation(N):
    X = [Int(f'x_{i}') for i in range(N)]
    s = Solver()
    
    for x in X:
        s.add(And(x >= 1, x <= N))
        
    s.add(Distinct(X))
    
    # computing the list S of all perfect squares less than 2*N
    S = []
    k = 1
    while k * k < 2 * N:
        S.append(k * k)
        k += 1
        
    for i in range(N - 1):
        #list of boolean value for each square
        valid_sums = [X[i] + X[i+1] == sq for sq in S]
        s.add(Or(valid_sums))
        
    if s.check() == sat:
        m = s.model()
        # Integer result
        result = [m.evaluate(x).as_long() for x in X]
        print(f"Solution: {result}")
    else:
        print(f"No solution found")

if __name__ == '__main__':
    solve_square_permutation(N)
