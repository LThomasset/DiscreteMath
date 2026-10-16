# Answer: [0, 2, 3]

from z3 import *

opt = Optimize() # Optimizer object.

# My set_cover function.
def set_cover(Ca):
    # Constraints for the set cover problem.
    max_var = max([max(i) for i in Ca]) # Find the maximum element in all sets.
    max_var = max_var + 1 # Adjust for zero-based indexing.
    x = [Bool(f'x_{i}') for i in range(max_var)] # List of boolean variables representing whether each set is chosen.
    for i in Ca:
        opt.add(Or(*[x[j] for j in i])) # At least one set must cover each element.

    opt.minimize(Sum(*[If(v, 1, 0) for v in x])) # Minimize the number of sets chosen.
    opt.check() # Check for satisfiability.
    return [i for i in range(max_var) if is_true(opt.model()[x[i]])]

if __name__ == '__main__':
    Ca = [{0 ,10} , {0 ,1 ,4} , {1 ,2 ,4 ,5 ,6 ,7} , {0 ,1 ,3 ,5 ,9} , {0 ,3} , {2 ,6 ,8 ,11} , {2 ,7 ,8 ,10} , {3 ,9}]
    print(set_cover(Ca)) 