from sage.all import *

R = var('R', domain='real')
assume(R > 0)
bx, by, bz = var('bx by bz', domain='real')
nx, ny, nz = var('nx ny nz', domain='real')
beta_sq = var('beta_sq', domain='real')
n = vector([nx, ny, nz])
beta = vector([bx, by, bz])

# E_vel = (n - beta) / ( (1 - n.dot(beta))^3 * R^2 )
denom = (1 - n.dot(beta))^3
E_vel = (n - beta) / (denom * R^2)

def apply_isotropic_averages(expr):
    # 0th order
    val_0 = expr.subs({bx:0, by:0, bz:0})
    # 2nd order terms: 1/2 * sum( d^2/db_i^2 * <b_i^2> )
    # Termini misti <bi bj> = 0, quindi non li calcoliamo
    d2x = diff(expr, bx, 2).subs({bx:0, by:0, bz:0})
    d2y = diff(expr, by, 2).subs({bx:0, by:0, bz:0})
    d2z = diff(expr, bz, 2).subs({bx:0, by:0, bz:0})
    
    avg_2nd = (1/2) * (d2x + d2y + d2z) * (beta_sq / 3)
    return (val_0 + avg_2nd).simplify_full()

nx_sq = var('nx_sq')
E_avg = []
for i in range(3):
    res = apply_isotropic_averages(E_vel[i])
    # Usa n^2 = 1
    res = res.subs({nx**2 + ny**2 + nz**2: 1})
    E_avg.append(res)

print("Risultato Media Isotropa:")
print(f"Ex_avg: {E_avg[0]}")
print(f"Ey_avg: {E_avg[1]}")
print(f"Ez_avg: {E_avg[2]}")
