# Alex is a knave (a = False), which means we don't know whether Alex's mom (m) is a knight or a knave.

from z3 import *

# variable declarations
a = Bool('a')
m = Bool('m')

# making a solver instance
s = Solver()
# checks if the two expressions are not equivalent
s.add(Implies(a, m == (m != a)))

# checking solutions
if s.check() == sat:
    model = s.model()
    print("Solution found:")
    print(f"a = {model[a]}, m = {model[m]}")
    value_a = model[a]
    s.add(a != value_a)  # in order to find a different solution for 'a'
    if s.check() == unsat:
        print(f"There is a different solution, the value of 'a' is {value_a}")
    else:
        print("Multiple solutions exist for 'a'.")
else:
    print("No solution exists.")