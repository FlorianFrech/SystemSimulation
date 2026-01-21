Component Types
===============

SysSimX provides specialized components for different simulation environments.

FMUComponent
------------

Wraps FMI 2.0 Co-Simulation FMUs for integration with other models.

Basic Usage
^^^^^^^^^^^

.. code-block:: python

   from syssimx.components import FMUComponent
   
   # Load an FMU
   pendulum = FMUComponent(
       name="Pendulum",
       fmu_path="path/to/Pendulum.fmu",
       group="Plant"  # Optional grouping
   )
   
   # Configure parameters
   pendulum.set_parameters(
       L=1.0,      # Pendulum length [m]
       m=0.5,      # Mass [kg]
       q0=0.1,     # Initial angle [rad]
       omega0=0.0  # Initial angular velocity [rad/s]
   )

Automatic Port Discovery
^^^^^^^^^^^^^^^^^^^^^^^^

FMUComponent automatically extracts port information from the FMU's
model description:

.. code-block:: python

   # After construction, ports are available
   print(pendulum.input_specs)   # {"torque": PortSpec(...)}
   print(pendulum.output_specs)  # {"q": ..., "omega": ..., "alpha": ...}
   print(pendulum.parameters)    # {"L": ..., "m": ..., "g": ...}

Direct Feedthrough Detection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

FMUComponent detects algebraic dependencies from the FMU's model structure:

.. code-block:: python

   # Check which inputs affect outputs algebraically
   print(pendulum.direct_feedthrough)
   # {"q": set(), "omega": set(), "alpha": {"torque"}}

State Management
^^^^^^^^^^^^^^^^

.. code-block:: python

   # Get current state (for inspection)
   state = pendulum.get_state()
   
   # Soft reset (reuse FMU instance)
   pendulum.soft_reset(t0=0.0)
   
   # Full reset (releases FMU)
   pendulum.reset()

FEMComponent
------------

Base class for finite element models using NGSolve.

.. note::

   FEMComponent requires NGSolve to be installed.

Basic Structure
^^^^^^^^^^^^^^^

.. code-block:: python

   from syssimx.components import FEMComponent
   
   class HeatTransfer(FEMComponent):
       """Custom FEM component for heat transfer."""
       
       def __init__(self, name: str, mesh_file: str):
           super().__init__(name)
           self.mesh_file = mesh_file
           
           self.input_specs = {
               "heat_flux": PortSpec(
                   name="heat_flux",
                   type=PortType.REAL,
                   direction="in",
                   unit="W/m^2"
               )
           }
           self.output_specs = {
               "temperature": PortSpec(
                   name="temperature", 
                   type=PortType.REAL,
                   direction="out",
                   unit="K"
               )
           }
       
       def _initialize_component(self, t0: float):
           # Set up NGSolve mesh and spaces
           self._setup_mesh()
           self._setup_fem_spaces()
       
       def _do_step_internal(self, t: float, dt: float):
           # Solve FEM system for one time step
           self._solve_timestep(dt)

Internal Event Reporting
^^^^^^^^^^^^^^^^^^^^^^^^

FEM components with internal time stepping can report events to the
master algorithm for efficient event localization:

.. code-block:: python

   def _do_step_internal(self, t: float, dt: float):
       # Internal micro-stepping
       for micro_t in self._internal_times(t, dt):
           self._solve_step(micro_t)
           
           # Report detected event to master
           if self._event_detected():
               self.report_internal_event(
                   event_name="contact",
                   t_before=micro_t - self._internal_dt,
                   t_after=micro_t
               )

OpenSimComponent
----------------

Wraps OpenSim musculoskeletal models for biomechanics simulation.

.. note::

   OpenSimComponent requires the OpenSim Python bindings.

Basic Usage
^^^^^^^^^^^

.. code-block:: python

   from syssimx.components import OpenSimComponent
   
   arm = OpenSimComponent(
       name="SimpleArm",
       model_path="models/SimpleArm.osim"
   )
   
   # Set initial state
   arm.set_parameters(
       shoulder_angle=0.0,
       elbow_angle=0.5
   )

Creating Custom Components
--------------------------

For custom simulation logic, subclass ``CoSimComponent``:

Required Methods
^^^^^^^^^^^^^^^^

.. code-block:: python

   from syssimx.core.base import CoSimComponent
   from syssimx.core.port import PortSpec, PortType
   
   class MyComponent(CoSimComponent):
       def __init__(self, name: str):
           super().__init__(name)
           # Define ports
           self.input_specs = {...}
           self.output_specs = {...}
       
       def _initialize_component(self, t0: float) -> None:
           """Set up initial state."""
           pass
       
       def _do_step_internal(self, t: float, dt: float) -> None:
           """Advance simulation by dt."""
           pass
       
       def _update_output_states(self, t=None, event_names=None) -> None:
           """Write internal state to output ports."""
           pass
       
       def set_state(self, state: dict, t: float) -> None:
           """Set state from dictionary (for mode switching)."""
           pass
       
       def get_state(self) -> dict:
           """Return current state as dictionary."""
           pass

Optional: Rollback Support
^^^^^^^^^^^^^^^^^^^^^^^^^^

For hybrid simulation with event detection, implement rollback:

.. code-block:: python

   class RollbackCapableComponent(CoSimComponent):
       def snapshot_state(self):
           """Capture complete state for rollback."""
           return {
               "t": self.t,
               "x": self.x,
               "internal_solver_state": self._solver.get_state()
           }
       
       def restore_state(self, snapshot, t=None):
           """Restore state from snapshot."""
           self.t = snapshot["t"]
           self.x = snapshot["x"]
           self._solver.set_state(snapshot["internal_solver_state"])

Optional: Direct Feedthrough
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If outputs depend algebraically on inputs:

.. code-block:: python

   class AlgebraicComponent(CoSimComponent):
       def __init__(self, name: str):
           super().__init__(name)
           # Declare which inputs affect which outputs
           self.direct_feedthrough = {
               "y": {"u"}  # Output "y" depends on input "u"
           }
       
       def evaluate_outputs(self, inputs: dict, t=None) -> dict:
           """Evaluate outputs without stepping (for algebraic loops)."""
           self.set_inputs(inputs, t=None)
           # Compute outputs based on current inputs
           return {"y": self._compute_y()}

Next: :doc:`systems`
