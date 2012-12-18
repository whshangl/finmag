import time
import math
import dolfin as df
import numpy as np

"""
The goal is to compute the values of f(r, t) = sin(x) * sin(t) on a mesh for
different points in time. The cost of updating f a couple of times is measured.

"""

L = math.pi / 2; n = 20;
mesh = df.Box(0, 0, 0, L, L, L, n, n, n)
ts = np.linspace(0, math.pi / 2, 100)

# dolfin expression code

S = df.FunctionSpace(mesh, "CG", 1)
expr = df.Expression("sin(x[0]) * sin(t)", t = 0.0)

start = time.time()
for t in ts:
    expr.t = t
    f_dolfin = df.interpolate(expr, S)
print "Time needed for dolfin expression: {:.2g}.".format(time.time() - start)

# explicit loop code

f_loop = np.empty(mesh.num_vertices())

start = time.time()
for t in ts:
    for i, (x, y, z) in enumerate(mesh.coordinates()):
        f_loop[i] = math.sin(x) * math.sin(t)
print "Time needed for loop: {:.2g}.".format(time.time() - start)

assert np.max(np.abs(f_dolfin.vector().array() - f_loop)) < 1e-14