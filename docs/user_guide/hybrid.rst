Hybrid Co-Simulation
====================

SysSimX supports hybrid co-simulation with discrete events, enabling
accurate simulation of systems with discontinuities and mode switches.

Overview
--------

Hybrid simulation combines:

- **Continuous dynamics**: ODEs/DAEs evolving over time
- **Discrete events**: Instantaneous state changes at specific times

SysSimX handles this via:

1. **Event indicators**: Functions that cross zero at event times
2. **Bisection localization**: Precise event time detection
3. **Superdense time**: Ordering of simultaneous events
4. **Commutativity checking**: Safe handling of concurrent events

Event Detection
---------------

Event Indicators
^^^^^^^^^^^^^^^^

An event is triggered when an indicator function crosses zero:

.. code-block:: python

   def contact_indicator(component):
       """Returns negative when in contact, positive otherwise."""
       return component.position - component.ground_level

   # Register on component
   component.add_event_indicator(
       name="ground_contact",
       func=contact_indicator,
       direction=-1  # Falling edge only (entering contact)
   )

**Direction options:**

- ``-1``: Falling edge (positive → negative/zero)
- ``+1``: Rising edge (negative → positive/zero)
- ``0``: Any crossing

Rollback Requirement
^^^^^^^^^^^^^^^^^^^^

Components with event indicators must support state rollback:

.. code-block:: python

   class BounceComponent(CoSimComponent):
       def snapshot_state(self):
           return {"t": self.t, "x": self.x, "v": self.v}
       
       def restore_state(self, snapshot, t=None):
           self.t = snapshot["t"]
           self.x = snapshot["x"]
           self.v = snapshot["v"]
       
       # Now you can add event indicators
       # self.add_event_indicator("bounce", indicator_func, direction=-1)

Event Handling
--------------

Event Connections
^^^^^^^^^^^^^^^^^

Connect events to listeners:

.. code-block:: python

   from syssimx.system.connection import EventConnection

   # Event connection from detector to handler
   system.add_event_connection(EventConnection(
       src_comp="BallComponent",
       src_port="ground_contact",  # Event indicator name
       dst_comp="Controller",
       dst_port="collision_event"   # Event input port
   ))

Event Handlers
^^^^^^^^^^^^^^

Implement event handling in your component:

.. code-block:: python

   class Controller(CoSimComponent):
       def __init__(self, name):
           super().__init__(name)
           self.input_specs = {
               "collision_event": PortSpec(
                   name="collision_event",
                   type=PortType.EVENT,
                   direction="in"
               )
           }
       
       def _handle_events_internal(self, event_names: list[str], t: float):
           if "ground_contact" in event_names:
               # React to collision
               self.mode = "contact"
               self.reset_integrator()

Superdense Time
---------------

When multiple events occur at the same real time, they are ordered
using **superdense time** ``(t, micro)``:

.. code-block:: text

   Time    Microstep   Description
   ─────   ─────────   ───────────────────────
   0.5     0           First event detected
   0.5     1           Event triggered by handler
   0.5     2           Cascaded event
   0.5+ε   0           Continue simulation

This ensures deterministic ordering of event cascades.

Accessing Event Times
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from syssimx.core.events import DenseTime

   # Get event history after simulation
   event_history = system.history.get_all_event_histories()
   
   for (comp_name, event_name), times in event_history.items():
       for dense_time in times:
           print(f"{event_name} at t={dense_time.t:.6f}, micro={dense_time.micro}")

Simultaneous Events
-------------------

When multiple events occur at exactly the same time on the same component,
SysSimX checks that handlers **commute** (order doesn't matter).

Annotation-Based Commutativity
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Declare commutativity explicitly:

.. code-block:: python

   class MyListener(CoSimComponent):
       def __init__(self, name):
           super().__init__(name)
           
           # Declare which variables each event modifies
           self.event_annotations = {
               "event_a": {"modifies": {"x"}, "type": "RMW"},
               "event_b": {"modifies": {"y"}, "type": "RMW"}
           }
           
           # Explicitly declare commutativity
           self.event_commutativity = {
               ("event_a", "event_b"): True  # Order doesn't matter
           }

Dynamic Commutativity Checking
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If no annotations provided, SysSimX checks dynamically by:

1. Saving component state
2. Running all event orderings
3. Comparing final states

.. code-block:: python

   # Requires rollback support
   def snapshot_state(self):
       return {"x": self.x, "y": self.y}
   
   def restore_state(self, snapshot, t=None):
       self.x = snapshot["x"]
       self.y = snapshot["y"]

Non-Commutative Events
^^^^^^^^^^^^^^^^^^^^^^

If handlers don't commute, SysSimX raises an error:

.. code-block:: python

   RuntimeError: Non-commutative events ['event_a', 'event_b'] on 
   component 'Listener' detected. Cannot handle simultaneously at (0.5, 0).

**Solution**: Ensure events are separated in time or modify handlers
to be order-independent.

Hybrid Algorithm Configuration
------------------------------

.. code-block:: python

   from syssimx.system.algorithms import HybridAlgorithm

   hybrid = HybridAlgorithm()
   
   # Event localization settings
   hybrid.tol_time = 1e-6      # Time tolerance for bisection
   hybrid.tol_value = 1e-6     # Indicator value tolerance
   hybrid.max_iter = 50        # Max bisection iterations
   
   # Superdense time limits
   hybrid.max_microsteps = 100 # Max events per time instant
   
   # Debugging
   hybrid.verbose = True       # Print event detection info
   
   system.algorithm = hybrid

Internal Event Hints
--------------------

Components with internal micro-stepping (e.g., FEM with adaptive time
stepping) can provide hints to accelerate event localization:

.. code-block:: python

   def _do_step_internal(self, t: float, dt: float):
       # Internal adaptive stepping
       internal_t = t
       while internal_t < t + dt:
           self._internal_step()
           
           # Report detected event
           if self._event_crossed():
               self.report_internal_event(
                   event_name="contact",
                   t_before=internal_t - self._last_dt,
                   t_after=internal_t,
                   indicator_before=self._prev_indicator,
                   indicator_after=self._curr_indicator
               )
               break
           
           internal_t += self._adaptive_dt()

Example: Bouncing Ball
----------------------

Complete example of a bouncing ball with ground contact:

.. code-block:: python

   class BouncingBall(CoSimComponent):
       def __init__(self, name, h0=1.0, cor=0.8):
           super().__init__(name)
           self.h0 = h0      # Initial height
           self.cor = cor    # Coefficient of restitution
           self.h = h0
           self.v = 0.0
           self.g = 9.81
           
           self.output_specs = {
               "h": PortSpec(name="h", type=PortType.REAL, direction="out"),
               "v": PortSpec(name="v", type=PortType.REAL, direction="out")
           }
       
       def _initialize_component(self, t0):
           self.h = self.h0
           self.v = 0.0
           
           # Register ground contact event
           self.add_event_indicator(
               "ground_contact",
               lambda c: c.h,  # Zero when h=0
               direction=-1    # Falling (approaching ground)
           )
       
       def _do_step_internal(self, t, dt):
           # Simple Euler integration
           self.v = self.v - self.g * dt
           self.h = self.h + self.v * dt
       
       def _handle_events_internal(self, event_names, t):
           if "ground_contact" in event_names:
               # Bounce: reverse velocity with energy loss
               self.v = -self.cor * self.v
               self.h = 0.0  # Ensure on ground
       
       def snapshot_state(self):
           return {"t": self.t, "h": self.h, "v": self.v}
       
       def restore_state(self, snapshot, t=None):
           self.t = snapshot["t"]
           self.h = snapshot["h"]
           self.v = snapshot["v"]

   # Simulate
   system = System("BouncingBall")
   ball = BouncingBall("Ball", h0=1.0, cor=0.8)
   system.add_component(ball)
   system.initialize(t0=0.0)
   system.run(t0=0.0, tf=5.0, dt=0.01)
