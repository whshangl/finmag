import os
import dolfin as df
import numpy as np
from finmag.field import Field
from finmag.util import magpar
from finmag.energies import Exchange
from finmag.util.helpers import vector_valued_function


#df.parameters["allow_extrapolation"] = True


# REL_TOLERANCE = 3e-6 #passes with 'normal magpar'
REL_TOLERANCE = 9e-8  # needs higher accuracy patch
# for saved files to pass
# install magpar via finmag/install/magpar.sh to get this.

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))


def test_three_dimensional_problem():
    results = three_dimensional_problem()
    assert np.nanmax(results["rel_diff"]) < REL_TOLERANCE


def three_dimensional_problem():
    x_max = 10e-9
    y_max = 1e-9
    z_max = 1e-9
    mesh = df.BoxMesh(df.Point(0, 0, 0), df.Point(x_max, y_max, z_max), 40, 2, 2)

    V = df.VectorFunctionSpace(mesh, 'Lagrange', 1)

    Ms = 8.6e5

    m0_x = "pow(sin(0.2*x[0]*1e9), 2)"
    m0_y = "0"
    m0_z = "pow(cos(0.2*x[0]*1e9), 2)"
    m = Field(V, value=vector_valued_function(
        (m0_x, m0_y, m0_z), V, normalise=True))

    C = 1.3e-11

    u_exch = Exchange(C)
    u_exch.setup(m, Field(df.FunctionSpace(mesh, 'DG', 0), Ms))
    finmag_exch = u_exch.compute_field()

    magpar_result = os.path.join(MODULE_DIR, 'magpar_result', 'test_exch')
    nodes, magpar_exch = magpar.get_field(magpar_result, 'exch')

    ## Uncomment the line below to invoke magpar to compute the results,
    ## rather than using our previously saved results.
    # nodes, magpar_exch = magpar.compute_exch_magpar(m, A=C, Ms=Ms)

    print magpar_exch

    # Because magpar have changed the order of the nodes!!!

    tmp = df.Function(V)
    tmp_c = mesh.coordinates()
    mesh.coordinates()[:] = tmp_c * 1e9

    finmag_exch, magpar_exch, \
        diff, rel_diff = magpar.compare_field(
            mesh.coordinates(), finmag_exch,
            nodes, magpar_exch)

    return dict(m0=m.get_numpy_array_debug(),
                mesh=mesh,
                exch=finmag_exch,
                magpar_exch=magpar_exch,
                diff=diff,
                rel_diff=rel_diff)


if __name__ == '__main__':

    res = three_dimensional_problem()

    print "finmag:", res["exch"]
    print "magpar:", res["magpar_exch"]
    print "rel_diff:", res["rel_diff"]
    print "max rel_diff", np.max(res["rel_diff"])
