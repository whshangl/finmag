# FinMag - a thin layer on top of FEniCS to enable micromagnetic multi-physics simulations
# Copyright (C) 2012 University of Southampton
# Do not distribute
#
# CONTACT: h.fangohr@soton.ac.uk


import logging
from finmag.sim.sim import Simulation, sim_with
from __version__ import __version__
import example

logger = logging.getLogger("finmag")
logger.debug("%20s: %s" % ("Finmag", __version__))
import util.versions
logger.debug("%20s: %s" % ("Dolfin", util.versions.get_version_dolfin()))
logger.debug("%20s: %s" % ("Matplotlib", util.versions.get_version_matplotlib()))
logger.debug("%20s: %s" % ("Numpy", util.versions.get_version_numpy()))
logger.debug("%20s: %s" % ("Scipy", util.versions.get_version_scipy()))
logger.debug("%20s: %s" % ("IPython", util.versions.get_version_ipython()))
try:
    sundials_version = util.versions.get_version_sundials()
except NotImplementedError:
    sundials_version = '<cannot determine version>'
logger.debug("%20s: %s" % ("Sundials", sundials_version))
logger.debug("%20s: %s" % ("Linux", util.versions.get_linux_issue()))


if util.versions.running_binary_distribution():
    # check that this is the same as the binary distribution has been compiled for
    # This matters for sundials: on 12.04 there is one version of sundials
    # on 12.10 there is a different one. They are not compatible, but we 
    # have no way to tell which one we are using.
    #
    # We thus assume that we use the system's sundials, and thus we 
    # should be able to check by comparing the linux distribution.
    import util.binary
    logger.debug("%20s: %s" % ("Build Linux", util.binary.buildlinux))
    if util.binary.buildlinux == util.versions.get_linux_issue():
        logger.debug("Build Linux and host linux versions agree.")
    else:
        logger.error("Build Linux = %s" % util.binary.buildlinux)
        logger.error("Host Linux = %s" % util.versions.get_linux_issue())
        raise RuntimeError("Build and Host linux must be identical, otherwise sundials may produce wrong results / crash")







