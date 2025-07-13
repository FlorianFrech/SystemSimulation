from math import isclose
from collections import defaultdict
import networkx as nx
from physical_value import PhysicalValue
from scipy.integrate import solve_ivp
from scipy.optimize import root
import numpy as np



class CoupledBlock:
    def __init__(self, name, modules, global_connections):
        self.name = name
        self.modules = modules
        self.module_map = {mod.name: mod for mod in modules}
        self.global_connections = global_connections
        self.dt = self._validate_dt()
        self.ode_method, self.nle_method = self._validate_methods()

        self.input_mapping = {}   # cb_input_name → (mod_name, mod_input_name)
        self.output_mapping = {}  # cb_output_name → (mod_name, mod_output_name)
        self.inputs = {}    # input_name → PhysicalValue
        self.outputs = {}   # output_name → PhysicalValue
        self.variable_to_module = {}  # maps variable → module_name
        self.variable_aliases = {}    # maps alias → canonical name (for coupled variables)
        self.level_map = {}           # will be assigned from simulation._assign_levels() once the order has been determined
        
        self._register_external_connections() # establish simulation level IOs of a CB (information that a CB needs)
        
        self.y = {}
        self.z = {}
        self.dydt = {}
        self.internal = {}
        self.common_output = {}
        self.parameters = {}
        
        # Allow to send y[k] & z[k] predicted at t=k-1 as outputs
        self.y_output = {}
        self.z_output = {}
        
        self._prepare_variables() # collect the variables from modules (y, z, common and internal)
        
        self.differential_functions = []  # list of (function, [outputs], [inputs])
        self.algebraic_functions = []
        self.common_functions = []
        self.internal_functions = []
        
        self._gather_functions() # from all the modules
        self._warn_on_wrong_dependency()
        
        
        
    def __repr__(self):
        return f"{self.name}"

    def _validate_dt(self):
        dts = [mod.dt for mod in self.modules]
        first_dt = dts[0]
        for dt in dts[1:]:
            scale = 10**10
            if round(dt * scale) != round(first_dt * scale):
                raise ValueError(f"All modules in CoupledBlock '{self.name}' must have the same dt")
        return first_dt
    
    def _validate_methods(self):
        ode_methods = {mod.ode_method for mod in self.modules}
        nle_methods = {mod.nle_method for mod in self.modules}
        
        if len(ode_methods) > 1:
            print(f"⚠️ Warning: Multiple ode_method values found in CoupledBlock '{self.name}': {ode_methods}")
        if len(nle_methods) > 1:
            print(f"⚠️ Warning: Multiple nle_method values found in CoupledBlock '{self.name}': {nle_methods}")
        
        # Fallback to first method seen
        ode_method = next(iter(ode_methods))
        nle_method = next(iter(nle_methods))
        
        return ode_method, nle_method

    def _check_common_function_usage(self):
        """
        Ensures that common function outputs are not used in feedback connections.
        Feedback = destination level < source level.
    
        Must be called after self.level_map is assigned by Simulation._assign_levels().
        """
        for dst_mod, conn_dict in self.global_connections.items():
            if dst_mod not in self.module_map:
                continue  # Skip external targets
    
            for input_name, (src_mod, src_output) in conn_dict.items():
                if src_mod not in self.module_map:
                    continue  # Skip external sources
    
                # Check if this output is from a common function
                full_src_var = f"{src_mod}.{src_output}"
                if full_src_var not in self.common_output:
                    continue  # Not a common output → allowed
    
                # Compare levels
                level_src = self.level_map.get(src_mod)
                level_dst = self.level_map.get(dst_mod)
    
                if level_src is None or level_dst is None:
                    raise RuntimeError(f"Missing sublevel info for '{src_mod}' or '{dst_mod}' in CoupledBlock '{self.name}'")
    
                if level_dst < level_src:
                    raise RuntimeError(
                        f"Invalid feedback connection in CoupledBlock '{self.name}': "
                        f"Output '{src_output}' from common function in module '{src_mod}' "
                        f"is used as input in earlier module '{dst_mod}'."
                    )
                elif level_dst == level_src:
                    print(
                        f"⚠️  Warning: Ambiguous same-level dependency in CoupledBlock '{self.name}': "
                        f"common output '{src_mod}.{src_output}' → '{dst_mod}.{input_name}'"
                    )


    def _register_external_connections(self):
        """
        This method is called by Simulation to tell the CoupledBlock
        which inputs and outputs are externally connected.
        """
        
        global_connections = self.global_connections
        internal_names = set(self.module_map.keys())
        
        for dst_mod, conns in global_connections.items():
            if dst_mod in internal_names:
                for input_name, (src_mod, src_output) in conns.items():
                    if src_mod not in internal_names:
                        # External input
                        original = f"{src_mod}.{src_output}"
                        cb_input = f"CB input from {original}"  # Input name says where the input comes from 
                        self.input_mapping[cb_input] = (src_mod, src_output) # where this input comes from
                        input_unit = self.module_map[dst_mod].inputs[input_name].unit
                        self.inputs[cb_input] = PhysicalValue(name=cb_input, value=None, unit=input_unit) # value will be set by simulation at each time step
                        dst_input_name = f"{dst_mod}.{input_name}"
                        self.variable_aliases[dst_input_name] = cb_input  # Alias module input to unified CB input

        # Detect all external outputs
        for dst_mod, conns in global_connections.items():
            for input_name, (src_mod, src_output) in conns.items():
                if src_mod in internal_names and dst_mod not in internal_names:
                    original = f"{src_mod}.{src_output}"
                    cb_output_name = f"CB output from {original}"
                    output_unit = self.module_map[src_mod].outputs[src_output].unit
                    self.outputs[cb_output_name] = PhysicalValue(name=cb_output_name, value=None, unit=output_unit) # value will be set by simulation at each time step
                    self.output_mapping[cb_output_name] = (src_mod, src_output)
        
        print(f"CB {self.name} external inputs: {self.input_mapping}")
        print(f"CB {self.name} external outputs: {self.output_mapping}\n")
        
        # Variable coupling detection
        for dst_mod, conn_dict in global_connections.items():
            if dst_mod in self.module_map:  # dst is internal
                for input_name, (src_mod, src_output) in conn_dict.items():
                    if src_mod in self.module_map:  # src is also internal → coupling
                        dst_var = f"{dst_mod}.{input_name}"
                        src_var = f"{src_mod}.{src_output}"
                        self.variable_aliases[dst_var] = src_var  # Make dst an alias of src
            

    def _prepare_variables(self):
        """ Variables have a unique name mod_name.var_name and we keep track
            where they come from """
        
        for mod in self.modules:
            # Prefix for traceability
            mod_prefix = mod.name + "."
        
            for name in mod.y:
                full_name = mod_prefix + name
                self.y[full_name] = mod.y[name]
                self.variable_to_module[full_name] = mod.name
                self.dydt[full_name] = mod.dydt[name]
        
            for name in mod.z:
                full_name = mod_prefix + name
                self.z[full_name] = mod.z[name]
                self.variable_to_module[full_name] = mod.name
        
            for name in mod.internal_values:
                full_name = mod_prefix + name
                self.internal[full_name] = mod.internal_values[name]
                self.variable_to_module[full_name] = mod.name
        
            for name in mod.common_output:
                full_name = mod_prefix + name
                self.common_output[full_name] = mod.common_output[name]
                self.variable_to_module[full_name] = mod.name
        
            for name, pv in mod.parameters.items():
                full_name = mod.name + "." + name
                self.parameters[full_name] = pv
                self.variable_to_module[full_name] = mod.name


    def _resolve_alias(self, name):
        """ If variable is input, return the output name
         if the variable is output keep its name """
        return self.variable_aliases.get(name, name)


    def _gather_functions(self):
        for mod in self.modules:
            mod_prefix = mod.name + "."
    
            for f, outs, ins in mod.differential_functions:
                out_names = [mod_prefix + name for name in outs]
                in_names = [self._resolve_alias(mod_prefix + name) for name in ins]
                self.differential_functions.append((f, out_names, in_names))
    
            for f, outs, ins in mod.algebraic_functions:
                out_names = [mod_prefix + name for name in outs]
                in_names = [self._resolve_alias(mod_prefix + name) for name in ins]
                self.algebraic_functions.append((f, out_names, in_names))
    
            for f, outs, ins in mod.common_functions:
                out_names = [mod_prefix + name for name in outs]
                in_names = [self._resolve_alias(mod_prefix + name) for name in ins]
                self.common_functions.append((f, out_names, in_names))
    
            for f, outs, ins in mod.internal_functions:
                out_names = [mod_prefix + name for name in outs]
                in_names = [self._resolve_alias(mod_prefix + name) for name in ins]
                self.internal_functions.append((f, out_names, in_names))


    def _gather_values(self, y_dict, z_dict):
        """
        Gather all known values into a single flat dictionary:
        - Parameters
        - External inputs
        - Internals
        - Predicted y/z (optional)
        - With alias resolution
        """
            
        vals = {}       
        vals = {p.name: p.value for p in self.parameters.values()}
        vals.update({i.name: i.value for i in self.inputs.values()})
        vals.update(y_dict)
        vals.update(z_dict)
        vals.update({i.name: i.value for i in self.internal.values()})
        vals.update(self.common_output)
        
        return vals


    def _warn_on_wrong_dependency(self):
        """
        Warn if number of unknowns (outputs) does not match number of equations
        OR if the number of truly unknown inputs is inconsistent.
        Outputs from sibling functions in the same block are considered known.
        """
    
        known_global = set(self.parameters.keys()) | set(self.inputs.keys()) | set(self.internal.keys()) | set(self.common_output.keys())
    
        for kind, funcs in [
            ("differential", self.differential_functions),
            ("algebraic", self.algebraic_functions)
        ]:
            total_equations = len(funcs)
            all_outputs = set()
            for _, outs, _ in funcs:
                for out in outs:
                    if out not in self.outputs.keys():
                        all_outputs.update(outs)
    
            all_unknown_inputs = set()
            for _, _, ins in funcs:
                for var in ins:
                    if var not in known_global and var not in all_outputs:
                        all_unknown_inputs.add(var)
    
            if len(all_unknown_inputs) < total_equations:
                        print(f"⚠️ Note: {len(all_unknown_inputs)} unknown inputs used by {total_equations} {kind} functions in CoupledBlock '{self.name}' (possibly constant equations)")
            
            elif len(all_unknown_inputs) > total_equations:
                print(f"⚠️ Warning: {len(all_unknown_inputs)} unknown inputs used by {total_equations} {kind} functions in CoupledBlock '{self.name}' — system likely overspecified or unsolvable")


    def initialize(self):
        """ Sets up y[0], y[0] and dydt[0] which will be used to predict values in step(t=0)"""
        
        # 1. Set initial y
        for name in self.y:
            mod_name = self.variable_to_module[name]
            local_name = name.split(".")[1]
            mod = self.module_map[mod_name]
            if local_name not in mod.initial_values:
                raise ValueError(f"Missing initial value for '{name}'")
            self.y[name] = mod.initial_values[local_name].value
    
        # 2. Solve algebraic equations by iteration
        z = {}
        pending = list(self.algebraic_functions)
        for _ in range(len(pending)):
            solved = []
            vals = self._gather_values(self.y, z)
            for f, outs, ins in pending:
                if all(k in vals for k in ins):
                    args = [vals[k] for k in ins]
                    result = f(0.0, self.dt, *args)
                    if not isinstance(result, tuple):
                        result = (result,)
                    for name, val in zip(outs, result):
                        z[name] = val
                    solved.append((f, outs, ins))
            pending = [item for item in pending if item not in solved]
            if not solved:
                break
    
        for name in self.z:
            if name not in z:
                raise ValueError(f"Failed to initialize algebraic variable '{name}' in CoupledBlock '{self.name}'")
            self.z[name] = z[name]
    
        # 3. Zero dydt
        for name in self.dydt:
            self.dydt[name] = 0.0
    
        # 4. Store outputs
        self.y_output = self.y.copy()
        self.z_output = self.z.copy()


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
                        if name not in self.internal:
                            raise KeyError(f"Internal value '{name}' not declared in INTERNAL_INITIAL_VALUES")
                        self.internal[name].set_value(val)
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
        """
        Return externally visible outputs as:
        { module_name: { output_name: PhysicalValue(...) } }
        Used for propagating external outputs of a CoupledBlock during the simulation execution.
        """
        grouped = defaultdict(dict)
    
        for cb_output_name, (mod_name, output_name) in self.output_mapping.items():
            # Create a clone of the PhysicalValue with the correct unit
            unit = self.module_map[mod_name].outputs[output_name].unit
            pv = PhysicalValue(name=output_name, value=None, unit=unit)
    
            # Determine the output value
            full_name = f"{mod_name}.{output_name}"
            if full_name in self.y_output:
                pv.set_value(self.y_output[full_name])
            elif full_name in self.z_output:
                pv.set_value(self.z_output[full_name])
            elif full_name in self.common_output:
                pv.set_value(self.common_output[full_name])
            else:
                raise KeyError(f"Output '{output_name}' not found in y/z/common outputs of module '{mod_name}'")
    
            grouped[mod_name][output_name] = pv
    
        return dict(grouped)


    def get_all_outputs(self):
        """
        Returns all outputs from all internal modules, regardless of external visibility.
        Used for writting histoy within Simulation class.
        Format: { module_name: { output_name: PhysicalValue(...) } }
        
        - No need to worry about uniqueness or aliases because each output is already unique,
          only function arguments of modules functions pointing to its inputs might not be. 
        """
        
        
        grouped = defaultdict(dict)
        for mod in self.modules:
            for name, pv in mod.outputs.items():
                full_name = f"{mod.name}.{name}"
                unit = pv.unit
                val = None
                if full_name in self.y_output:
                    val = self.y_output[full_name]
                elif full_name in self.z_output:
                    val = self.z_output[full_name]
                elif full_name in self.common_output:
                    val = self.common_output[full_name]
                else:
                    raise KeyError(f"Output '{full_name}' not found in CoupledBlock internal state.")
                grouped[mod.name][name] = PhysicalValue(name=name, value=val, unit=unit)
        return dict(grouped)

