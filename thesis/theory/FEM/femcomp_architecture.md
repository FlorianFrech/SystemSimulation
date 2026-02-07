# FEM Component Architecture Documentation

## Overview

This document outlines the comprehensive FEM (Finite Element Method) component architecture implemented in SysSimX, consisting of:

1. **FEMComponent Base Class** (`SysSimX/core/fem_comp.py`)
2. **Clean FEMPendulum Example** (`SysSimX/fem/pendulum_clean.py`)

## Architecture Benefits

### 1. Clean Separation of Concerns
- **Geometry Creation**: Abstract method for domain-specific geometry
- **Mesh Generation**: Standardized mesh handling with quality controls
- **Material Laws**: Pluggable material law system
- **Solver Configuration**: Centralized Newton solver and time stepping
- **Co-simulation Interface**: Standardized input/output port system
- **Visualization**: Reusable visualization and diagnostics framework

### 2. Reusable Framework
- Base class handles common FEM patterns (80% of code)
- Derived classes focus on problem-specific implementations (20% of code)
- Configuration classes for clean parameter management
- Abstract template method pattern for extensibility

### 3. Quality Assurance
- Built-in error handling and validation
- Mesh quality diagnostics
- Newton solver convergence monitoring
- Time step adaptation
- Comprehensive logging and debugging support

## Class Hierarchy

```
CoSimComponent (base co-simulation interface)
    ├── FEMComponent (FEM-specific base class)
    │   ├── FEMSolverConfig (solver parameters)
    │   ├── FEMVisualizationConfig (visualization settings)
    │   └── Abstract methods for geometry/mesh/materials
    │
    └── FEMPendulumClean (example implementation)
        ├── PendulumFEMConfig (pendulum parameters)
        ├── Concrete geometry/mesh/material implementations
        └── Pendulum-specific physics and co-simulation
```

## Implementation Patterns

### 1. Configuration Classes
```python
@dataclass
class FEMSolverConfig:
    default_dt: float = 1e-3
    newton_tolerance: float = 1e-6
    newton_maxiter: int = 25
    mesh_order: int = 2
    # ... other solver parameters

@dataclass  
class PendulumFEMConfig:
    geom_params: GeometryParameters
    mat_params: MaterialParameters
    mesh_params: MeshParameters
    # ... pendulum-specific config
```

### 2. Abstract Template Methods
```python
class FEMComponent(CoSimComponent):
    # Template method - calls abstract methods in sequence
    def initialize(self, t0: float = 0.0) -> None:
        self._geometry = self._create_geometry()        # Abstract
        self._mesh = self._create_mesh()               # Abstract  
        self._setup_finite_element_spaces()           # Abstract
        self._setup_material_laws()                   # Abstract
        self._setup_bilinear_form()                   # Abstract
        # ... concrete initialization steps
    
    # Abstract methods - must be implemented by derived classes
    @abstractmethod
    def _create_geometry(self) -> Any: ...
    
    @abstractmethod
    def _create_mesh(self) -> Mesh: ...
    # ... other abstract methods
```

### 3. Co-simulation Integration
```python
def _define_ports(self):
    """Define standardized input/output ports."""
    self.input_specs['torque'] = PortSpec(
        name='torque', type=PortType.REAL, unit='N*m',
        description='Applied torque about rotation axis'
    )
    
    self.output_specs['q_state'] = PortSpec(
        name='q_state', type=PortType.REAL, unit='rad',
        description='Angular position of pendulum'
    )
```

### 4. Material Law System
```python
class NeoHookeanMaterial:
    def energy_density(self, C, u):
        """Compute strain energy density."""
        return self.mu/2 * (Trace(C) - 3) - self.mu * log(sqrt(Det(C))) + \
               self.lam/2 * log(sqrt(Det(C)))**2

class LinearElasticMaterial:
    def energy_density(self, eps, u):
        """Linear elastic strain energy."""
        return self.mu * InnerProduct(eps, eps) + self.lam/2 * Trace(eps)**2
```

## Key Features

### 1. NGSolve Integration
- **Mesh Management**: Automatic mesh creation and quality validation
- **Finite Element Spaces**: H1, VectorH1, NumberSpace for constraints
- **Material Laws**: Neo-Hookean, Linear Elastic with extensible framework
- **Contact Mechanics**: Penalty method contact with gap functions
- **Time Integration**: Implicit time stepping with Newton solver

### 2. Solver Configuration
- **Newton Solver**: Configurable tolerance and iteration limits
- **Time Stepping**: Adaptive time step control
- **Convergence Monitoring**: Built-in convergence diagnostics
- **Error Handling**: Robust error recovery and reporting

### 3. Visualization Framework
- **WebGUI Integration**: Automatic visualization setup
- **Interactive Widgets**: IPywidgets for parameter control
- **Diagnostics**: Real-time solver and mesh quality metrics
- **Export Capabilities**: Results export in standard formats

### 4. Co-simulation Interface
- **Port System**: Standardized input/output port definitions
- **Unit Management**: Physical unit tracking and validation
- **State Management**: Save/restore simulation state
- **Synchronization**: Time step coordination with other components

## Usage Examples

### 1. Basic FEM Component Creation
```python
# Create configuration
config = PendulumFEMConfig(
    geom_params=GeometryParameters(L_pendulum=1.0, r_rod=0.05),
    mat_params=MaterialParameters(E_pendulum=1e6, nu_pendulum=0.3),
    mesh_params=MeshParameters(mesh_order=2, max_h_pendulum=0.1)
)

# Create component
pendulum = FEMPendulumClean(name="MyPendulum", config=config)

# Initialize and simulate
pendulum.initialize(t0=0.0)
pendulum.set_inputs({'torque': 0.1})
pendulum.do_step(t=0.0, dt=0.01)
outputs = pendulum.get_outputs()  # {'q_state': 0.0, 'omega_state': 0.0}
```

### 2. Co-simulation Integration
```python
from SysSimX.core.scheduler import SystemScheduler

# Create system with multiple components
scheduler = SystemScheduler()
scheduler.add_component(pendulum)
scheduler.add_component(controller)
scheduler.add_connection(controller.outputs['torque'], pendulum.inputs['torque'])

# Run co-simulation
scheduler.simulate(t_end=10.0, dt=0.01)
```

### 3. Custom Material Law
```python
class CustomMaterial:
    def energy_density(self, C, u):
        """Custom material law implementation."""
        # Implement your material model here
        return custom_energy_expression
        
# Use in FEM component
def _setup_material_laws(self):
    self._material = CustomMaterial(E=self.config.E, nu=self.config.nu)
```

## Extension Points

### 1. New FEM Components
To create new FEM components, inherit from `FEMComponent` and implement:
- `_create_geometry()`: Define computational domain
- `_create_mesh()`: Generate finite element mesh
- `_setup_finite_element_spaces()`: Define function spaces
- `_setup_material_laws()`: Configure material models
- `_setup_bilinear_form()`: Assemble weak form
- `_compute_outputs()`: Extract co-simulation outputs

### 2. Material Law Extensions
Create new material classes with:
- `energy_density()` method for strain energy
- Parameter configuration
- Integration with NGSolve coefficient functions

### 3. Contact Mechanics
Extend contact handling by:
- Defining contact boundaries
- Implementing gap functions
- Adding penalty or Lagrange multiplier methods

### 4. Solver Enhancements
Add custom solvers by:
- Extending `FEMSolverConfig`
- Implementing solver-specific methods
- Integrating with NGSolve solver framework

## Performance Considerations

### 1. Mesh Optimization
- Use adaptive mesh refinement
- Monitor element quality metrics
- Balance accuracy vs computational cost

### 2. Solver Efficiency
- Choose appropriate preconditioners
- Monitor Newton convergence
- Use sparse matrix techniques

### 3. Memory Management
- Reuse grid functions when possible
- Clear temporary objects
- Monitor memory usage in long simulations

### 4. Parallelization
- Leverage NGSolve parallel capabilities
- Use OpenMP for assembly operations
- Consider MPI for large-scale problems

## Testing and Validation

### 1. Unit Tests
- Test each abstract method implementation
- Validate material law implementations
- Check co-simulation interface compliance

### 2. Integration Tests
- Full component initialization and simulation
- Co-simulation with multiple components
- Long-term stability tests

### 3. Physical Validation
- Compare with analytical solutions
- Cross-validate with other FEM codes
- Experimental validation where possible

This architecture provides a robust, extensible foundation for FEM-based co-simulation components while maintaining clean separation of concerns and promoting code reuse.