# module.py

import importlib.util
import os
import inspect
from .physical_value import PhysicalValue, Unit, convert_to_si
from scipy.integrate import solve_ivp
from scipy.optimize import root
import numpy as np

# ------------------------------------------
# Decorators: Tag functions with types/outputs
# ------------------------------------------

def differential(outputs):
    def wrapper(func):
        func._function_type = 'differential'
        func._function_outputs = outputs
        return func
    return wrapper

def algebraic(outputs):
    def wrapper(func):
        func._function_type = 'algebraic'
        func._function_outputs = outputs
        return func
    return wrapper

def common(outputs):
    def wrapper(func):
        func._function_type = 'common'
        func._function_outputs = outputs
        return func
    return wrapper

def internal(outputs):
    def wrapper(func):
        func._function_type = 'internal'
        func._function_outputs = outputs
        return func
    return wrapper

# ------------------------------------------
# Module class
# ------------------------------------------

class Module:
    def __init__(self, name, path, parameters=None, initial_values=None, dt=None, normalise_units=False):
        self.name = name
        self.dt = dt  # May be None for now
        self.t = None
        self.ode_method = "LSODA" # unless overwritten by the user
        self.nle_method = "hybr" # unless overwritten by the user ( method of non linear equation system solver)
        
        self.parameters = {}
        self.initial_values = {}
        self.internal_values = {}           # Runtime values (updated each step)

        
        self.inputs = {}
        self.outputs = {}
        
        self.differential_functions = []
        self.algebraic_functions = []
        self.common_functions = []
        self.internal_functions = []
        
        self.type = path[:-3]               # path = band_pass_filter.py -> type = band_pass_filter
        self._load_description_file(path)   # import information and data from description file
        
        # overwrite parameters and initial state values if user spesified them
        if parameters: 
            self.parameters.update(self._wrap_physical_values(parameters))
        if initial_values:
            self.initial_values.update(self._wrap_physical_values(initial_values))
        
        # # done to normalise all the values (1mF = 0.001F)
        if normalise_units:
            self._convert_all_physical_values_to_si()
            
        # DEACTIVATED: done once at load time, after correct parameters have been placed
        #self._validate_unit_consistency() 
        
        # Execution state variables
        # Collect all state, algebraic, and derivative variable names
        self.y = {name: None for _, outs, _ in self.differential_functions for name in outs}
        self.dydt = {name: 0.0 for name in self.y}
        self.z = {name: 0.0 for _, outs, _ in self.algebraic_functions for name in outs}
                
        # Output buffers (predicted values, e.g., y[k+1], z[k+1] and return from common funcs)
        self.y_output = self.y.copy()
        self.z_output = self.z.copy()
        self.common_output = {name: 0.0 for _, outs, _ in self.common_functions for name in outs}
                

    def _wrap_physical_values(self, data):
        """Wrap dict or list of (name, value, unit) tuples into PhysicalValue objects."""
        wrapped = {}
        if isinstance(data, dict):
            for name, val in data.items():
                if isinstance(val, PhysicalValue):
                    wrapped[name] = val
                else:
                    value, unit = val
                    wrapped[name] = PhysicalValue(name, value, unit)
        elif isinstance(data, list):
            for pv in data:
                assert isinstance(pv, PhysicalValue), "Expected list of PhysicalValue"
                wrapped[pv.name] = pv
        return wrapped

    def _load_description_file(self, filename):
        """Dynamically loads a Python module from 'modules/filename'."""
        path = os.path.join("modules", filename)
        module_name = f"mod_{self.name}"
        spec = importlib.util.spec_from_file_location(module_name, path) # tells Python where to find the file and how to interpret it.
        mod = importlib.util.module_from_spec(spec) # At this point, mod is a blank module with the right name, but nothing has been executed yet.
        # This is equivalent to `import`, but it's done dynamically
        # Functions, variables, decorators, etc. from the file are now accessible via `mod.MODULE_INPUTS`, `mod.PARAMETERS`, etc.
        spec.loader.exec_module(mod)

        # Load and convert inputs/outputs to dict {name: PhysicalValue}
        self.inputs = self._resolve_io(mod, "MODULE_INPUTS")
        self.outputs = self._resolve_io(mod, "MODULE_OUTPUTS")

        # Optional: parameters, initial values (internal and external)
        if hasattr(mod, "PARAMETERS"):
            self.parameters.update(self._wrap_physical_values(mod.PARAMETERS))
        if hasattr(mod, "INITIAL_VALUES"):
            self.initial_values.update(self._wrap_physical_values(mod.INITIAL_VALUES))
        if hasattr(mod, "INTERNAL_INITIAL_VALUES"):
            self.internal_values.update(self._wrap_physical_values(mod.INTERNAL_INITIAL_VALUES))

        # Collect all decorated functions
        self._gather_decorated_functions(mod)

    def _resolve_io(self, mod, attr):
        """Convert list of strings or list of PhysicalValue into dict[str, PhysicalValue]."""
        result = {}
        items = getattr(mod, attr, [])
        for item in items:
            if isinstance(item, PhysicalValue):
                result[item.name] = item
            elif isinstance(item, str):
                raise ValueError(
                    f"IO declaration '{item}' must be a PhysicalValue with unit. "
                    f"Strings are not allowed in MODULE_INPUTS or MODULE_OUTPUTS."
                )
            else:
                raise ValueError(f"Unsupported format in {attr}: {item}")
        return result

    def _gather_decorated_functions(self, mod):
        for _, obj in inspect.getmembers(mod):
            if callable(obj) and hasattr(obj, "_function_type"):
                ftype = obj._function_type
                outs = obj._function_outputs
                ins = list(inspect.signature(obj).parameters)
                if "t" in ins: ins.remove("t")
                if "dt" in ins: ins.remove("dt")
                entry = (obj, outs, ins)
                if ftype == "differential":
                    self.differential_functions.append(entry)
                elif ftype == "algebraic":
                    self.algebraic_functions.append(entry)
                elif ftype == "common":
                    self.common_functions.append(entry)
                elif ftype == "internal":
                    self.internal_functions.append(entry)
                else:
                    raise ValueError(f"Unknown function type: {ftype}")

    def __repr__(self):
        #return f"<Module {self.name} | inputs: {list(self.inputs)}, outputs: {list(self.outputs)}>"
        return f"Module {self.name}"
    
    def _convert_all_physical_values_to_si(self):
        """
        Converts all relevant PhysicalValue instances in the module to base SI units in-place.
        """
        for collection in [
            self.inputs,
            self.parameters,
            self.initial_values,
            self.internal_values
        ]:
            for _, pv in collection.items():
                try:
                    val = pv.value if pv.value is not None else 1.0
                    new_value, new_unit = convert_to_si(val, str(pv.unit))
                    pv.set_value(new_value)
                    pv.set_unit(new_unit)
                except ValueError as e:
                    raise ValueError(f"Failed to convert '{pv.name}' to SI units: {e}")
                
    def _validate_unit_consistency(self):
        
        """ - Checks if the units chosen for the outputs are consistent with what its respective function would return based on
              the given inputs, parameters, etc. Could be useful to find mistakes in function defintion or chosen units.
              Currently this method fails because functions such as sin, log, etc. which would in reality return unitless results,
              cannot be processed by Unit() class -> those operations are not handled by units.
            - In the future this could be corrected by parsing the function and automatically removing all the problematic 
              subterms of a function.
            - Until then this method is deactivated but preserved due to its good basis.
            """

        all_known_vars = {
            **self.inputs,
            **self.parameters,
            **self.initial_values,
            **self.internal_values
        }
    
        all_outputs = self.outputs
                                    
        function_groups = (
            self.differential_functions +
            self.algebraic_functions +
            self.common_functions +
            self.internal_functions
        )
        
        for f, outs, ins in function_groups:
            #output_names = getattr(fn, "_function_outputs", [])
            output_names = outs
            ftype = getattr(f, "_function_type", "")
    
            # Get input argument names
            arg_names = list(inspect.signature(f).parameters)
            
            # Get function arguments equivalent in units instead of variables
            mock_args = []
            for arg in arg_names:
                if arg in all_known_vars:
                    mock_args.append(all_known_vars[arg].unit)
                elif arg == "t":
                    mock_args.append(Unit("s"))
                elif arg == "dt":
                    mock_args.append(Unit("s"))
                else:
                    raise ValueError(f"Missing variable '{arg}' for function '{f.__name__}'.")
    
            # Evaluate function with unit-only args
            try:
                result = f(*mock_args)
            except Exception as e:
                raise ValueError(f"Failed unit check for '{f.__name__}': {e}")
    
            # Wrap single return as tuple
            if not isinstance(result, tuple):
                result = (result,)
    
            if len(result) != len(output_names):
                raise ValueError(f"{f.__name__} returns {len(result)} values but declares {len(output_names)} outputs.")
    
            for name, actual_unit in zip(output_names, result):
                if name not in all_outputs:
                    # Possibly internal-use only — skip for now
                    continue
    
                declared_unit = all_outputs[name].unit
                expected_unit = declared_unit / Unit("s") if ftype == "differential" else declared_unit
                
                # convert the units to SI
                _, actual_si_unit = convert_to_si(1.0, str(actual_unit))
                _, expected_si_unit = convert_to_si(1.0, str(expected_unit))
                                
                # Raise an error if they are not the same
                if not Unit(actual_si_unit).is_compatible_with(Unit(expected_si_unit)):
                    raise ValueError(
                        f"Unit mismatch for '{name}' in '{f.__name__}':\n"
                        f"  expected: {expected_si_unit}\n"
                        f"  got:      {actual_si_unit}"
                    )

    def initialize(self):
        """Initializes y and solves for consistent z at t=0 based on initial state values."""
        
        # 1. Set initial y from initial_values
        for name in self.y:
            if name not in self.initial_values:
                raise ValueError(f"Missing initial value for state '{name}' in module '{self.name}'")
            self.y[name] = self.initial_values[name].value
    
        # 2. Loop through algebraic equations until all of them are solved
        z = {}
        pending = list(self.algebraic_functions)
        for _ in range(len(pending)):
            solved = []
            vals = self._gather_values(self.y, z)
            for triplet in pending:
                f, outs, ins = triplet
                if all(k in vals for k in ins):
                    result = f(self.t, self.dt, *[vals[k] for k in ins])
                    if not isinstance(result, tuple):
                        result = (result,)
                    for name, val in zip(outs, result):
                        z[name] = val
                    solved.append(triplet)
            pending = [t for t in pending if t not in solved]
            if not solved:
                break
    
        # 3. Final safety check: make sure all z are filled
        for name, value in self.z.items():
            if name in z:
                self.z[name] = z[name]
            else:
                raise ValueError(f"Failed to initialize algebraic variable '{name}' in module '{self.name}'")
    
        # 4. Initialise state derivatives
        for name in self.y:
            self.dydt[name] = 0.0
    
        # 5. Store initial output predictions
        self.y_output = self.y.copy()
        self.z_output = self.z.copy()
        
    def _gather_values(self, y_dict, z_dict):
        vals = {p.name: p.value for p in self.parameters.values()}
        vals.update({i.name: i.value for i in self.inputs.values()})
        vals.update(y_dict)
        vals.update(z_dict)
        vals.update({i.name: i.value for i in self.internal_values.values()})
        vals.update(self.common_output)
        return vals

    def _evaluate_internal(self, values):
        """ Will loop multiple times through common functions if the user did not order them properly but will raise a warning """
        pending = list(self.internal_functions)
        passes = 0
        max_passes = len(pending) + 1
    
        while pending and passes < max_passes:
            progress = False
            ready = []
            for f, outs, ins in pending:
                if all(k in values for k in ins):
                    args = [values[k] for k in ins]
                    result = f(self.t, self.dt, *args)
                    if len(outs) == 1:
                        result = (result,)
                    for name, val in zip(outs, result):
                        if name not in self.internal_values:
                            raise KeyError(f"Internal value '{name}' not declared in INTERNAL_INITIAL_VALUES")
                        self.internal_values[name].set_value(val)
                        values[name] = val
                    ready.append((f, outs, ins))
                    progress = True
            pending = [fn for fn in pending if fn not in ready]
            passes += 1
    
        if pending:
            raise RuntimeError(f"Could not resolve internal functions in module '{self.name}' — cyclic or missing dependencies?")
        if passes > 2:
            print(f"⚠️  Warning: Internal functions in module '{self.name}' required {passes} passes. Consider reordering them.")
    

    def _evaluate_common(self, values):
        """ Will loop multiple times through common functions if the user did not order them properly but will raise a warning """
        self.common_output = {}
        pending = list(self.common_functions)
        passes = 0
        max_passes = len(pending) + 1  # extra safety
    
        while pending and passes < max_passes:
            progress = False
            ready = []
            for f, outs, ins in pending:
                if all(k in values for k in ins):
                    args = [values[k] for k in ins]
                    result = f(self.t, self.dt, *args)
                    if len(outs) == 1:
                        result = (result,)
                    for name, val in zip(outs, result):
                        self.common_output[name] = val
                        values[name] = val
                    ready.append((f, outs, ins))
                    progress = True
            pending = [fn for fn in pending if fn not in ready]
            passes += 1
    
        if pending:
            raise RuntimeError(f"Could not resolve common functions in module '{self.name}' — cyclic or missing dependencies?")
        
        if passes > 2:
            print(f"⚠️  Warning: Common functions in module '{self.name}' required {passes} passes. Consider reordering them for performance.")
        
    def _evaluate_diff(self, values, t=None):
        result = {}
        t = t if t is not None else self.t
        # No need to do the same for dt because dt is not used in differential functions
        # it is avaliable as argument simply for consistancy
        for f, outs, ins in self.differential_functions:
            args = [values[k] for k in ins]
            out_vals = f(t, self.dt, *args)
            if len(outs) == 1:
                result[outs[0]] = out_vals
            else:
                for name, val in zip(outs, out_vals):
                    result[name] = val
        return result
    
    def _evaluate_alg(self, values):
        result = {}
        for f, outs, ins in self.algebraic_functions:
            args = [values[k] for k in ins]
            out_vals = f(self.t, self.dt, *args)
            if len(outs) == 1:
                result[outs[0]] = values[outs[0]] - out_vals
            else:
                for name, val in zip(outs, out_vals):
                    result[name] = values[name] - val
        return result


    def step(self, t):
        """Performs one simulation step: predicts y and solves for z at t + dt."""
        
        dt = self.dt
        self.t = t
        
        # 1. Evaluate all internal functions (if any)
        if self.internal_functions:
            vals = self._gather_values(self.y, self.z)
            self._evaluate_internal(vals)
        
        # 2. Evaluate all common functions (if any)
        if self.common_functions:
            vals = self._gather_values(self.y, self.z)
            self._evaluate_common(vals)
        
        # 3. Predictions from previous time step are outputs at the current one
        self.y_output = self.y.copy()
        self.z_output = self.z.copy()
        
    
        # 4. Predict y[k+1] using solve_ivp
        if self.differential_functions:
            y0 = [self.y[name] for name in self.y]
            t_span = [t, t + dt]
        
            def dydt(t_local, y_local):
                vals = self._gather_values(dict(zip(self.y.keys(), y_local)), self.z)
                diff_results = self._evaluate_diff(vals, t=t_local) # a dict 
                return [diff_results[name] for name in self.y]
        
            sol = solve_ivp(dydt, t_span, y0, method=self.ode_method, t_eval=[t + dt])
            y_pred = sol.y[:, -1]  # predicted y[k+1]
        
            # Update state predictions
            self.y = dict(zip(self.y.keys(), y_pred))
    
        # 5. Solve for z[k+1] & dydt[k+1] using root()   
        if self.algebraic_functions:
            if self.differential_functions:
                def residual(x):
                    dydt_vals = x[:len(self.y.keys())]
                    z_vals = x[len(self.y.keys()):]
                    vals = self._gather_values(self.y, dict(zip(self.z.keys(), z_vals)))
                    f_res = self._evaluate_diff(vals) # adict
                    g_res = self._evaluate_alg(vals)
                    f_vals = [f_res[name] for name in self.y] # a list
                    g_vals = [g_res[name] for name in self.z]
                    return np.concatenate([np.array(f_vals) - dydt_vals, g_vals])
                
                x0 = np.concatenate([
                    [self.dydt[name] for name in self.y],
                    [self.z[name] for name in self.z]
                ])
            else:
                def residual(x):
                    vals = self._gather_values(self.y, dict(zip(self.z.keys(), x)))
                    g_res = self._evaluate_alg(vals)
                    return np.array([g_res[name] for name in self.z])
                
                x0 = np.array([self.z[name] for name in self.z])
                               
            
            result = root(residual, x0, method=self.nle_method)
            if not result.success:
                raise RuntimeError(f"Root solver failed in module '{self.name}' at time {t + dt}: {result.message}")
        
            if self.differential_functions:
                dydt_pred = result.x[:len(self.y.keys())]
                z_pred = result.x[len(self.y.keys()):]
                    
                self.dydt = dict(zip(self.y.keys(), dydt_pred))
                self.z = dict(zip(self.z.keys(), z_pred))
            else:
                self.z = dict(zip(self.z.keys(), result.x))
    
    
    def get_outputs(self):
        # based on MODULE_OUTPUTS return the right
        # y, z, and common as a dict of PhysicalValues
        result = {}
        for name, pv in self.outputs.items():
            # Clone the PhysicalValue object
            cloned = PhysicalValue(name, None, pv.unit)
    
            # Determine value source
            if name in self.y_output:
                cloned.set_value(self.y_output[name])
            elif name in self.z_output:
                cloned.set_value(self.z_output[name])
            elif name in self.common_output:
                cloned.set_value(self.common_output[name])
            else:
                raise KeyError(f"Output '{name}' declared in MODULE_OUTPUTS but no value available in module '{self.name}'")
    
            result[name] = cloned
        return result
    
