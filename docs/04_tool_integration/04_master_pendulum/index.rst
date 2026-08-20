Master Pendulum (MultiComponent)
================================

Motivation: why multiple models for one pendulum?
-------------------------------------------------

In bio-mechatronic system simulation (e.g., prostheses and exoskeletons), the
system-level behavior is shaped by *coupled subsystems* that are often best
modeled with *different* tools:

- **Rigid-body dynamics** (fast, robust, good for control design and early
  integration)
- **Musculoskeletal dynamics** (to capture human-device interaction and
  physiology-driven constraints)
- **Deformable-body mechanics / FEM** (to resolve local stresses, contact, and
  compliance that cannot be captured by rigid models)

This naturally leads to *heterogeneous submodels* of the *same physical thing*
depending on your question:

- For controller development and system wiring, a rigid-body pendulum can be
  sufficient and cheap.
- For human-in-the-loop studies, an OpenSim model enables physiology-inspired
  modeling while still supporting rigid-body motion.
- For contact phases (impact with a wall, compliant interaction, local stress),
  FEM provides the detail needed to study loads and material response.

The key challenge is that these models live at different fidelity levels and
often have different internal states. A *multi-model component* provides a
pragmatic workflow: **use the simplest model that is "good enough" most of the
time, and switch to a more detailed model only when needed** (e.g., around
contact).


What is a MultiComponent?
-------------------------

:class:`syssimx.core.multi_comp.MultiComponent` wraps multiple
:class:`syssimx.core.base.CoSimComponent` instances behind a single, unified
port interface.

Conceptually:

- The *system* connects to one component (here: ``MasterPendulum``).
- Internally, ``MasterPendulum`` contains several interchangeable models
  (modes), e.g. ``"FMU"``, ``"OpenSim"``, ``"FEM"``.
- A **region map** decides which internal model is active from a scalar signal.
- On every switch, the wrapper **translates and synchronizes state** so the new
  model continues from a consistent configuration.
- Nonzero **boundary bands** prevent rapid chattering near switching thresholds.

See the API docs for details:
:class:`syssimx.core.multi_comp.MultiComponent` and
:class:`syssimx.core.multi_comp.SwitchRegions`.


MasterPendulum: one interface, three implementations
----------------------------------------------------

In this repository, the Master Pendulum is implemented as a multi-model
component that bundles three pendulum implementations:

- **Modelica / FMU pendulum** (rigid-body mechanics, exported as FMU)
- **OpenSim pendulum** (rigid-body mechanics with OpenSim tooling)
- **FEM pendulum** (deformable mechanics and optional contact)

The wrapper exposes a consistent set of ports (inputs/outputs) so it can be
dropped into a larger system without re-wiring when the internal model changes.

Typical minimal ports are:

- input: ``torque`` (and optionally event inputs such as ``omega_invert``)
- outputs: ``theta``, ``omega``, ``alpha`` (and optionally contact diagnostics)

Workflow: building your own multi-model component
-------------------------------------------------

1. **Implement each submodel as a** :class:`syssimx.core.base.CoSimComponent`
   (or reuse existing ones) with the same *external* ports (inputs/outputs).
2. **Create a wrapper class** that inherits from
   :class:`syssimx.core.multi_comp.MultiComponent`.
3. **Register models** in ``self.models`` (e.g. ``{"FMU": ..., "OpenSim": ..., "FEM": ...}``)
   and pick an ``initial_mode``.
4. **Unify ports** so the wrapper exposes one consistent interface.
5. **Implement** ``_adapt_state(...)`` to translate between state conventions.
6. **Define switching regions** with ``set_switch_regions()`` and a nonzero
   band around every boundary.
7. **Use the wrapper as a single plant component** inside a
   :class:`syssimx.system.system.System`, connected to sensors, a controller,
   and an actuator/drive.


Why switch models at runtime?
-----------------------------

Runtime switching is useful when *different phases* of the motion require
different physics:

- **Free swing / control tracking**: rigid-body models are usually sufficient
  to capture kinematics and sensor/controller dynamics at low cost.
- **Contact / impact**: FEM can resolve penetration, local compliance, and stress
  peaks that rigid models approximate poorly.

In practice, switching rules can be:

- **State-based** (e.g., switch to FEM when a contact gap becomes small or a
  threshold angle is approached),
- **Event-based** (e.g., use FEM during a wall-hit window),
- **Time-based** (useful for debugging and verification),
- **Hybrid** (combine state thresholds with dwell-time hysteresis).


State synchronization: the "hard part"
--------------------------------------

Switching is only meaningful if the target model starts from a *consistent*
state. For a pendulum, a common "shared state" is:

- angle ``theta``
- angular velocity ``omega``
- applied torque ``torque``

However, some models may require different state/parameter names. For example,
the FMU pendulum may use initial condition parameters ``q0`` and ``omega0``
instead of direct state overwrite. The multi-model wrapper handles this via an
adaptation hook:

.. code-block:: python

   def _adapt_state(self, state, target_mode):
       if target_mode == "FMU":
           return {"q0": state["q"], "omega0": state["omega"], "torque": state["torque"]}
       return state

In SysSimX, these state entries are typically structured dictionaries (e.g.,
``{"q": {"value": ..., "unit": "rad"}}``), not raw floats. State adaptation
therefore usually maps *named entries* between models (and sometimes converts
units or sign conventions).

Important modeling note: switching between FEM and rigid-body dynamics is a
*projection*. FEM contains internal deformation/strain energy states that are
not representable in a rigid model. Decide deliberately what is conserved or
discarded at the switch (energy, momentum, contact impulses), and size the
region bands to avoid excessive switching artifacts.

Practical guidelines (what to verify early)
-------------------------------------------

- **Interface consistency**: confirm the same sign conventions, units, and
  reference frames across FMU/OpenSim/FEM (especially torque direction and
  angle definition).
- **Switch variable robustness**: base switching on signals that are stable and
  physically meaningful (e.g., contact gap or angle thresholds), and use
  nonzero region bands to prevent threshold chattering.
- **Internal state mismatch**: explicitly decide how you "collapse" deformable
  states (FEM) into rigid states (and how you re-introduce deformation when
  switching back).
- **Numerical transients**: expect discontinuities at switches; validate
  continuity of the shared outputs (``theta``, ``omega``) and monitor energy where
  applicable.
- **System-level validation**: validate each pendulum model standalone first,
  then validate the closed-loop system with and without switching.


.. Controlled pendulum system (sensors-controller-actuator)
.. --------------------------------------------------------

.. The Master Pendulum is typically used as the **plant** inside a closed-loop
.. system:

.. - a reference generator provides ``theta_ref``
.. - sensors estimate/measure the pendulum state (e.g., encoder)
.. - a controller (e.g., PID) computes a control signal
.. - a drive/actuator converts control into pendulum torque

.. The key benefit of the multi-model plant is that the control architecture and
.. connections stay unchanged while you swap between plant representations.


.. Code locations
.. --------------

.. - Multi-model wrapper implementation: ``syssimx/core/multi_comp.py``
.. - Master pendulum orchestration (multi-model plant): ``demos/ControlledPendulum/src/master_pendulum/orchestration/master_pendulum.py``
.. - Submodels:

..   - FMU pendulum: ``demos/ControlledPendulum/src/master_pendulum/components/fmu/fmu_pendulum.py``
..   - OpenSim pendulum: ``demos/ControlledPendulum/src/master_pendulum/components/opensim/opensim_pendulum.py``
..   - FEM pendulum: ``demos/ControlledPendulum/src/master_pendulum/components/fem/fem_pendulum.py``

.. - System-level demonstrations and verification notebooks:

..   - ``demos/ControlledPendulum/notebooks/system/verification_master.ipynb``
..   - ``demos/ControlledPendulum/notebooks/system/verification_master_wall.ipynb``


Tutorials
---------

.. toctree::
   :maxdepth: 1
   :numbered:

   01_master_pendulum_basics
   02_master_pendulum_switching
