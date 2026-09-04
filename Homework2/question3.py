# ANSWER: returned sat, which means the two expressions are not equivalent.
from z3 import *

# variable declarations
a = Bool('a')
b = Bool('b')

# making a solver instance
s = Solver()
# checks if the two expressions are not equivalent
s.add((a == b) != (a == Or(Not(a), b))) 
print(s.check()) #result: sat
print(s.model()) #result: [a = False, b = False]