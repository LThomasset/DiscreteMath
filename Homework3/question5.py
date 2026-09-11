# ANSWER: V and W are both guilty.

from z3 import *

# those accused of a crime
v = Bool('v')
w = Bool('w')

# witnesses
a = Bool('a') # "I am a knight."
b = Bool('b') # Silent
c = Bool('c') # "A is a knave."
d = Bool('d') # "B is a knave."
e = Bool('e') # "C and D are both knights."
f = Bool('f') # "A and B are not both knaves."
g = Bool('g') # "E and F are either both knights or both knaves."
h = Bool('h') # "G and I are either both knights or both knaves, and V and W are not both guilty."

slv = Solver()

# A says "I am a knight."
slv.add(a == (a == True))  

# B is silent
# C says "A is a knave."
slv.add(c == (a == False))

# D says "B is a knave."
slv.add(d == (b == False))

# E says "C and D are both knights."
slv.add(e == And(c == True, d == True))

# F says "A and B are not both knaves."
slv.add(f == Not(And(a == False, b == False)))

# G says "E and F are either both knights or both knaves."
slv.add(g == Or(And(e == True, f == True), And(e == False, f == False)))

# H says "G and I are either both knights or both knaves, and V and W are not both guilty."
slv.add(h == And(Or(And(g == True, h == True), And(g == False, h == False)), Not(And(v == True, w == True))))

# Check for satisfiability

def print_model(slv, variables):
    """Return a clause that blocks the current solution"""
    mdl = slv.model()
    print(', '.join([f'{var} = {mdl[var]}' for var in variables]))

def block_model(slv, variables):
    """Return a clause that blocks the current solution"""
    mdl = slv.model()
    return Or([var != mdl[var] for var in variables])

def solve_and_print(slv, variables):
    """Solve constraints, print model, check uniqueness"""
    result = slv.check()
    if result == sat:
        print_model(slv, variables)
        slv.add(block_model(slv, variables))
        if slv.check() == unsat:
            print('unique solution')
        else:
            print('solution not unique')
    elif result == unsat:
        print('unsatisfiable constraints') 
    else: # result == unknown
        print('unable to solve', slv.reason_unknown())

solve_and_print(slv, [v, w])