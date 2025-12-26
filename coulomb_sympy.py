from sympy import symbols, Matrix, diff, simplify

# Definizione simboli
R = symbols('R', real=True, positive=True)
bx, by, bz = symbols('bx by bz', real=True)
nx, ny, nz = symbols('nx ny nz', real=True)
beta_sq = symbols('beta_sq', real=True)

n = Matrix([nx, ny, nz])
beta = Matrix([bx, by, bz])

# E_vel approx = (n - beta) / ( (1 - n.dot(beta))**3 * R**2 )
denom = (1 - (nx*bx + ny*by + nz*bz))**3
E_vel = (n - beta) / (denom * R**2)

def isotropic_average(expr):
    # 0th order
    val_0 = expr.subs({bx:0, by:0, bz:0})
    
    # 2nd order derivatives at 0
    d2x = diff(expr, bx, 2).subs({bx:0, by:0, bz:0})
    d2y = diff(expr, by, 2).subs({bx:0, by:0, bz:0})
    d2z = diff(expr, bz, 2).subs({bx:0, by:0, bz:0})
    
    # Average: <bi^2> = beta_sq / 3
    avg_2nd = (d2x + d2y + d2z) * (beta_sq / 6)
    return simplify(val_0 + avg_2nd)

# Calcolo media per componente x
Ex_avg = isotropic_average(E_vel[0])

# Sostituzione n^2 = 1 per semplificare
# SymPy non lo fa automaticamente, forziamo se possibile o controlliamo il risultato
print(f"Ex_avg (raw): {Ex_avg}")

# Verifica se è proporzionale a nx / R^2
# Ex_avg dovrebbe essere nx/R^2 * (1 + beta_sq)
target = (nx / R**2) * (1 + beta_sq)
diff_val = simplify(Ex_avg - target)
print(f"Differenza da target (nx/R^2 * (1 + beta_sq)): {diff_val.subs(nx**2+ny**2+nz**2, 1)}")

