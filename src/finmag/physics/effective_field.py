import logging
import numpy as np
from finmag.field import Field
from finmag.util.helpers import vector_valued_function
from finmag.energies import TimeZeeman
from finmag.physics.errors import UnknownInteraction

logger = logging.getLogger(name="finmag")


class EffectiveField(object):

    def __init__(self, m, Ms, unit_length):
        """
        *Arguments*

        m:  Field

        Ms:  number (?)

        unit_length:  float
        """
        assert isinstance(m, Field)
        assert isinstance(Ms, Field)
        self.m_field = m
        self.Ms = Ms
        self.unit_length = unit_length

        self.output_size = self.m_field.f.vector().local_size()
        self.H_eff = np.zeros(self.output_size)

        self.interactions = {}

        # TODO: Get rid of self._callables.
        # At the moment, we keep track of which functions need
        # to be updated with simulation time. We want to move to a
        # model where we pass the simulation state (m and t at the moment)
        # explicitly to compute_field/compute_energy.
        self.need_time_update = []

    def add(self, interaction, with_time_update=None):
        """
        Add an interaction (such as Exchange, Anisotropy, Demag).

        *Arguments:*

        interaction

             The interaction to be added.

         with_time_update (optional)

             A function of the form f(t), which accepts a time step
             `t` as its only single parameter and updates the internal
             state of the interaction accordingly.
        """
        if interaction.name in self.interactions:
            raise ValueError("Interaction names must be unique, but an "
                             "interaction with the same name already "
                             "exists: {}.".format(interaction.name))

        logger.debug(
            "Adding interaction {} to simulation.".format(interaction.name))
        interaction.setup(self.m_field, self.Ms, self.unit_length)
        self.interactions[interaction.name] = interaction

        # automatic connection of TimeZeeman to with_time_update
        if isinstance(interaction, TimeZeeman) and with_time_update is None:
            with_time_update = interaction.update

        if with_time_update:
            self.need_time_update.append(with_time_update)

    def update(self, t=None):
        """
        Update the effective field internally so that its value
        reflects the value at time `t`.

        The argument `t` can be omitted if no interaction requires a
        time update.

        """
        if t is None and self.need_time_update:
            raise ValueError("Some interactions require a time update, "
                             "but no time step was given.")

        for update in self.need_time_update:
            update(t)

        self.H_eff[:] = 0
        for interaction in self.interactions.itervalues():
            self.H_eff += interaction.compute_field()

    def compute(self, t=None):
        """
        Compute and return the effective field.

        The argument `t` is only required if one or more interactions
        require a time-update.

        """
        self.update(t)
        return self.H_eff.copy()

    def compute_jacobian_only(self, t):
        """
        Compute and return the total contribution of all interactions
        that are included in the Jacobian.

        """
        for update in self.need_time_update:
            update(t)

        H_eff = np.zeros(self.output_size)
        for interaction in self.interactions.itervalues():
            if interaction.in_jacobian:
                H_eff += interaction.compute_field()
        return H_eff

    def total_energy(self):
        """
        Compute and return the total energy contribution of all
        interactions present in the simulation.

        """
        energy = 0.
        for interaction in self.interactions.itervalues():
            energy += interaction.compute_energy()
        return energy

    def exists(self, interaction_name):
        """
        Returns true if an interaction by that name is known to the system.

        """
        return interaction_name in self.interactions.keys()

    def get(self, interaction_name):
        """
        Returns the interaction object with the given name. Raises a
        ValueError if no (or more than one) matching interaction is
        found.

        Use all() to obtain list of names of available interactions.

        """
        if not self.exists(interaction_name):
            raise UnknownInteraction(interaction_name, self.all())
        return self.interactions[interaction_name]

    def all(self):
        """ Returns list of interactions names (as list of strings). """
        return sorted(self.interactions.keys())

    def remove(self, interaction_name):
        """
        Removes the interaction object of the given name. Raises a
        ValueError if no (or more than one) matching interaction is
        found.

        """
        if not self.exists(interaction_name):
            raise UnknownInteraction(interaction_name, self.all())
        del self.interactions[interaction_name]

    def get_dolfin_function(self, interaction_name, region=None):
        interaction = self.get(interaction_name)
        return vector_valued_function(interaction.compute_field(),
                                      self.m_field.functionspace)
