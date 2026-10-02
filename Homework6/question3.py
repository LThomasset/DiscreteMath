# ANSWER: A = 0

from z3 import *

# Define variables
a = Real('a')
x = Real('x')

s = Solver()

# For all x, if x > 0, then -x < a and a < x
constraint = ForAll(x, Implies(x > 0, And(-x < a, a < x)))
s.add(constraint)

# Loop to find valid values
while s.check() == sat:
    model = s.model()
    a_val = model[a]
    print(f"Solution found: a = {a_val}")
    
    # see if other valid values exist
    s.add(a != a_val)

print("No more solutions. Set A has been fully evaluated.")
