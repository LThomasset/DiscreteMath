from z3 import *
from sympy import isprime, exp

estring = str(exp(1).evalf(100)).replace('.','')
print(estring)

i = 0

while i+12 <= len(estring):
    candidate_str= estring[i:i+12]
    num = int(candidate_str)
    if isprime(num):
        print(f"Found 12-digit prime: {num} at position {i}")
        break
    i+=1