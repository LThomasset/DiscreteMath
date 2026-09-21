#ANSWER: y = 5/3, x = 4/3

from z3 import *

def solve_inequalities():
    x = Real('x')
    y = Real('y')
    s = Solver()
    
    #2x + y <= 13/3
    s.add(2*x + y <= RatVal(13, 3)) 
    # x + 3y <=19/3
    s.add(x + 3*y <= RatVal(19, 3))
    #x + y >= 3
    s.add(x + y >= 3)
    
    if s.check() == sat:
        print(s.model())
    else:
        print("No solution")

if __name__ == '__main__':
    solve_inequalities()
