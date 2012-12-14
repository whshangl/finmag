import unittest
import numpy as np
import dolfin as df
import os
from finmag.native.llg import compute_lindholm_L, compute_lindholm_K, compute_bem_fk, compute_bem_gcr, OrientedBoundaryMesh
from finmag.util import time_counter
from finmag.util import helpers
from finmag.util.meshes import mesh_volume
from finmag.energies.demag import belement_magpar
from finmag.tests.test_solid_angle_invariance import random_3d_rotation_matrix
from problems.prob_fembem_testcases import MagSphereBase
from finmag.energies import Demag

compute_belement = belement_magpar.return_bele_magpar()

def compute_belement_magpar(r1, r2, r3):
    res = np.zeros(3)
    compute_belement(np.zeros(3), np.array(r1, dtype=float), np.array(r2, dtype=float), np.array(r3, dtype=float), res)
    return res

def compute_demag_solver():
    g1 = df.assemble(self.Ms * df.dot(self.n, self.m) * self.v * df.ds\
    - self.Ms * df.div(self.m) * self.v * df.dx)
    self.phi1_solver.solve(self.phi1.vector(), g1)

def normalise_phi(phi, mesh):
    volume = mesh_volume(mesh)
    average = df.assemble(phi * df.dx, mesh=mesh)
    phi.vector()[:] = phi.vector().array() - average / volume

def compute_scalar_potential_llg(mesh, m_expr=df.Constant([1, 0, 0]), Ms=1.):
    S3 = df.VectorFunctionSpace(mesh, "Lagrange", 1, dim=3)
    m = df.interpolate(m_expr, S3)

    demag = Demag()
    demag.setup(S3, m, Ms=Ms, unit_length=1)

    phi = demag.compute_potential()
    normalise_phi(phi, mesh)
    return phi

# Computes the derivative f'(x) using the finite difference approximation
def differentiate_fd(f, x, eps=1e-4, offsets=(-2,-1,1,2), weights=(1./12.,-2./3.,2./3.,-1./12.)):
    return sum(f(x+eps*dx)*weights[i] for i, dx in enumerate(offsets))/eps

def compute_scalar_potential_native_fk(mesh, m_expr=df.Constant([1, 0, 0]), Ms=1.):
    fkdemag = Demag("FK")
    V = df.VectorFunctionSpace(mesh,"Lagrange",1)
    m = df.interpolate(m_expr, V)
    m.vector()[:] = helpers.fnormalise(m.vector().array())
    fkdemag.setup(V,m,Ms,unit_length = 1)
    phi1 = fkdemag.compute_potential()
    normalise_phi(phi1, mesh)
    return phi1

## Solves the demag problem for phi using the GCR method and the native BEM matrix
def compute_scalar_potential_native_gcr(mesh, m_expr=df.Constant([1, 0, 0]), Ms=1.0):
    gcrdemag = Demag("GCR")
    V = df.VectorFunctionSpace(mesh,"Lagrange",1)
    m = df.interpolate(m_expr, V)
    m.vector()[:] = helpers.fnormalise(m.vector().array())
    gcrdemag.setup(V,m,Ms,unit_length = 1)
    phi1 = gcrdemag.compute_potential()
    normalise_phi(phi1, mesh)
    return phi1

class BemComputationTests(unittest.TestCase):
    def test_simple(self):
        r1 = np.array([1., 0., 0.])
        r2 = np.array([2., 1., 3.])
        r3 = np.array([5., 0., 1.])
        be_magpar = compute_belement_magpar(r1, r2, r3)
        be_native = compute_lindholm_L(np.zeros(3), r1, r2, r3)
        print "Magpar: ", be_magpar
        print "Native C++: ", be_native
        self.assertAlmostEqual(np.max(np.abs(be_magpar - be_native)), 0, delta=1e-12)

    def test_cell_ordering(self):
        mesh = df.UnitCube(1,1,1)
        centre = np.array([0.5, 0.5, 0.5])
        boundary_mesh = df.BoundaryMesh(mesh)
        coordinates = boundary_mesh.coordinates()
        for i in xrange(boundary_mesh.num_cells()):
            cell = df.Cell(boundary_mesh, i)
            p1 = coordinates[cell.entities(0)[0]]
            p2 = coordinates[cell.entities(0)[1]]
            p3 = coordinates[cell.entities(0)[2]]
            n = np.cross(p2 - p1, p3 - p1)
            print "Boundary face %d, normal orientation %g" % (i, np.sign(np.dot(n, p1-centre)))

    def run_bem_computation_test(self, mesh):
        S3 = df.VectorFunctionSpace(mesh, "Lagrange", 1, dim=3)
        m = df.interpolate(df.Constant((1, 0, 0)), S3)
        Ms = 1.0

        # Using the weiwei solver to compare against,
        # because this still has the magpar bem,
        # while the main fk solver now uses the native bem.
        demag = Demag(solver="weiwei")
        demag.setup(S3, m, Ms, unit_length=1)

        bem_finmag = demag.demag.B
        bem_native = np.zeros(bem_finmag.shape)
        bem, b2g = compute_bem_fk(OrientedBoundaryMesh(mesh))
        g2finmag = demag.demag.gnodes_to_bnodes
        for i_dolfin in xrange(bem.shape[0]):
            i_finmag = g2finmag[b2g[i_dolfin]]

            for j_dolfin in xrange(bem.shape[0]):
                j_finmag = g2finmag[b2g[j_dolfin]]
                bem_native[i_finmag, j_finmag] = bem[i_dolfin, j_dolfin]
        if np.max(np.abs(bem_finmag - bem_native)) > 1e-12:
            print "Finmag:", np.round(bem_finmag, 4)
            print "Native:", np.round(bem_native, 4)
            print "Difference:", np.round(bem_native - bem_finmag, 4)
            self.fail("Finmag and native computation of BEM differ, mesh: " + str(mesh))

    def test_bem_computation(self):
        self.run_bem_computation_test(df.UnitSphere(1))
        self.run_bem_computation_test(df.UnitSphere(2))
        self.run_bem_computation_test(df.UnitSphere(3))
        self.run_bem_computation_test(df.UnitSphere(4))
        self.run_bem_computation_test(df.UnitSphere(6))
        self.run_bem_computation_test(df.UnitCube(3,3,3))

    def test_bem_perf(self):
        mesh = df.UnitCube(15, 15, 15)
        boundary_mesh = OrientedBoundaryMesh(mesh)
        c = time_counter.counter()
        while c.next():
            OrientedBoundaryMesh(mesh)
        print "Boundary mesh computation for %s: %s" % (mesh, c)
        c = time_counter.counter()
        while c.next():
            bem, _ = compute_bem_fk(boundary_mesh)
            n = bem.shape[0]
        print "FK BEM computation for %dx%d (%.2f Mnodes/sec): %s" % (n, n, c.calls_per_sec(n*n/1e6), c)
        c = time_counter.counter()
        while c.next():
            bem, _ = compute_bem_gcr(boundary_mesh)
        print "GCR BEM computation for %dx%d (%.2f Mnodes/sec): %s" % (n, n, c.calls_per_sec(n*n/1e6), c)

    def test_bem_netgen(self):
        module_dir = os.path.dirname(os.path.abspath(__file__))
        netgen_mesh = df.Mesh(os.path.join(module_dir, "bem_netgen_test_mesh.xml.gz"))
        bem, b2g_map = compute_bem_fk(OrientedBoundaryMesh(netgen_mesh))

    def run_demag_computation_test(self, mesh, m_expr, compute_func, method_name, tol=1e-10, ref=compute_scalar_potential_llg,k = 0):
        phi_a = ref(mesh, m_expr)
        phi_b = compute_func(mesh, m_expr)

        error = df.errornorm(phi_a, phi_b, mesh=mesh)
        message = "Method: %s, mesh: %s, m: %s, error: %8g" % (method_name, mesh, m_expr, error)
        print message
        print "K = ",k
        print "m_expr = ",m_expr
        self.assertAlmostEqual(error, 0, delta=tol, msg="Error is above threshold %g, %s" % (tol, message))
        
    def test_compute_scalar_potential_fk(self):
        m1 = df.Constant([1, 0, 0])
        m2 = df.Expression(["x[0]*x[1]+3", "x[2]+5", "x[1]+7"])
        expressions = [m1,m2]
        for exp in expressions: 
            for k in xrange(1,5+1):
                self.run_demag_computation_test(df.UnitCube(k,k,k), exp,
                                                compute_scalar_potential_native_fk,
                                                "native, FK")
                
                self.run_demag_computation_test(df.UnitSphere(k), exp,
                                                compute_scalar_potential_native_fk,
                                                "native, FK")
                
            self.run_demag_computation_test(MagSphereBase(0.25, 1).mesh, exp,
                                            compute_scalar_potential_native_fk,
                                            "native, FK")


    def test_compute_scalar_potential_gcr(self):
        m1 = df.Constant([1, 0, 0])
        m2 = df.Expression(["x[0]*x[1]+3", "x[2]+5", "x[1]+7"])
        tol = 1e-1
        expressions = [m1,m2]
        self.run_demag_computation_test(MagSphereBase(0.1, 1).mesh, m1,
                                        compute_scalar_potential_native_gcr,
                                        "native, GCR",
                                        ref=compute_scalar_potential_native_fk, tol=tol)
        for exp in expressions: 
            for k in xrange(3,10+1,2):
                self.run_demag_computation_test(df.UnitCube(k,k,k), exp,
                                                compute_scalar_potential_native_gcr,
                                                "native, GCR, cube", tol=tol,
                                                ref=compute_scalar_potential_native_fk)
                
                self.run_demag_computation_test(MagSphereBase(1./k, 1.).mesh, exp,
                                                compute_scalar_potential_native_gcr,
                                                "native, GCR, sphere", tol=tol,
                                                ref=compute_scalar_potential_native_fk,k=k)
        
    def run_symmetry_test(self, formula):
        func = globals()[formula]
        np.random.seed(1)
        for i in xrange(100):
            r = np.random.rand(3)*2-1
            r1 = np.random.rand(3)*2-1
            r2 = np.random.rand(3)*2-1
            r3 = np.random.rand(3)*2-1
            a = np.random.rand(3)*2-1
            b = random_3d_rotation_matrix(1)[0]
            # Compute the formula
            v1 = func(r, r1, r2, r3)
            # The formula is invariant under rotations via b
            v2 = func(np.dot(b, r), np.dot(b, r1), np.dot(b, r2), np.dot(b, r3))
            self.assertAlmostEqual(np.max(np.abs(v1 - v2)), 0)
            # and under translations via a
            v3 = func(r+a, r1+a, r2+a, r3+a)
            self.assertAlmostEqual(np.max(np.abs(v1 - v3)), 0)
            # and under permutations of r1-r2-r3
            v4 = func(r, r2, r3, r1)
            self.assertAlmostEqual(np.max(np.abs(v1[[1,2,0]] - v4)), 0)

    def test_lindholm_L_symmetry(self):
        # Lindholm formulas should be invariant under rotations and translations
        self.run_symmetry_test("compute_lindholm_L")

    def test_lindholm_K_symmetry(self):
        self.run_symmetry_test("compute_lindholm_K")

    def test_lindholm_derivative(self):
        # the double layer potential is the derivative of the single layer potential
        # with respect to displacements of the triangle in the normal direction
        np.random.seed(1)
        for i in xrange(100):
            r = np.random.rand(3) * 2 - 1
            r1 = np.random.rand(3) * 2 - 1
            r2 = np.random.rand(3) * 2 - 1
            r3 = np.random.rand(3) * 2 - 1
            zeta  = np.cross(r2-r1, r3-r1)
            zeta /= np.linalg.norm(zeta)
            def f(x):
                return compute_lindholm_K(r, r1+x*zeta, r2+x*zeta, r3+x*zeta)
            L1 = compute_lindholm_L(r, r1, r2, r3)
            L2 = differentiate_fd(f, 0)
            self.assertAlmostEqual(np.max(np.abs(L1 - L2)), 0, delta=1e-10)

    def test_facet_normal_direction(self):
        mesh = df.UnitCube(1,1,1)
        field = df.Expression(["x[0]", "x[1]", "x[2]"])
        n = df.FacetNormal(mesh)
        # Divergence of R is 3, the volume of the unit cube is 1 so we divide by 3
        print "Normal: +1=outward, -1=inward:", df.assemble(df.dot(field, n) * df.ds, mesh=mesh) / 3.

if __name__ == "__main__":
    unittest.main()