import matplotlib.pyplot as plt
import networkx as nx
from coupled_block import CoupledBlock
from graphviz import Digraph
import pandas as pd
import os
import matplotlib



class Simulation:
    def __init__(self, modules, dt=0.01, t_end=1):
        self.modules = modules                      # list of Module instances
        self.module_map = {mod.name: mod for mod in modules}
        self.connections = {}                       # dst_module → {input_name: (src_module, output_name)}
        self.coupled_blocks = []                    # Will store CoupledBlock instances
        self.execution_order = []                   # For sim.run() and sim.initialize()
        self.modules_ordered = []                   # Order of all modules including the coupling
        self.module_to_block = {}                   # Maps modules to the CoupledBlock where they belong to
        self.module_levels = {}                     # Orders of execution assigned to self.execution_order
        self.sublevels = {}                         # Orders of execution assigned to modules of each CoupledBlock
        
        self.dt = dt
        self.t_end = t_end
        self.time = 0.0
        
        self.history = {mod.name: {} for mod in modules}

        self._set_dts()
        
        self._monitor_initialized = False
        self._monitor_config = None


    def _set_dts(self):
        for mod in self.modules:
            if mod.dt is None:
                mod.dt = self.dt

        dts = [mod.dt for mod in self.modules]
        self.dt = min(dts)
        self.constant_dts = all(abs(dt - self.dt) < 1e-12 for dt in dts) # will be used to show or not shows dt in visualisation


        for mod in self.modules:
            scale = 10**10
            ratio_scaled = round(mod.dt * scale) / round(self.dt * scale)
            if not ratio_scaled.is_integer():
                raise ValueError(
                    f"Module '{mod.name}' has dt = {mod.dt}, which does not evenly divide simulation dt = {self.dt}"
                )


    def connect(self, src, output, dst, input=None):
        if dst not in self.connections:
            self.connections[dst] = {}
        
        input_name = input or output

        if input_name in self.connections[dst]:
            existing_src, existing_output = self.connections[dst][input_name]
            raise ValueError(
                f"Input '{input_name}' of module '{dst}' is already connected "
                f"to output '{existing_output}' from module '{existing_src}'."
            )
        
        self.connections[dst][input_name] = (src, output)



    def _assign_levels(self):
        """
        Assigns topological levels to all modules and sublevels within CoupledBlocks.
        Returns:
            module_levels: dict of module_name → level (int)
            sublevels: dict of coupled_block_name → {module_name → sublevel (float)}
        """
        def increment_sublevel(current):
            """Helper to generate sublevels like 3.1 → 3.9 → 3.91
                → 3.99 → 3.991 ..."""
                
            str_val = str(current)
            if '.' not in str_val:
                return current + 0.1
            prefix, suffix = str_val.split('.')
            start = suffix[:-1]
            last_digit = suffix[-1]
            if last_digit == "9":
                last_digit = "91"
            else:
                last_digit = int(last_digit) + 1
            return float(f"{prefix}.{start}{last_digit}")
    
        # === Stage 1: Assign top-level levels ===
        module_levels = {}
        for item in self.execution_order:
            if isinstance(item, CoupledBlock):
                max_level = 0
                for cb_input, (src_mod, _) in item.input_mapping.items():
                    if src_mod in module_levels:
                        max_level = max(max_level, module_levels[src_mod])
                    elif src_mod in self.module_to_block and self.module_to_block[src_mod] in module_levels: # if src in a CB
                        max_level = max(max_level, module_levels[self.module_to_block[src_mod]])
                module_levels[item.name] = max_level + 1 # source
            else:
                max_level = 0
                for input_name, (src_mod, _) in self.connections.get(item.name, {}).items():
                    if src_mod in module_levels:
                        max_level = max(max_level, module_levels[src_mod])
                    elif src_mod in self.module_to_block and self.module_to_block[src_mod] in module_levels: # if src in a CB
                        max_level = max(max_level, module_levels[self.module_to_block[src_mod]])
                module_levels[item.name] = max_level + 1 # source
    
        # === Stage 2: Assign sublevels within CoupledBlocks ===
        sublevels = {}
        level_map = {} # keep an empty one in case there were no CBs
        
        for cb in self.coupled_blocks:
            base_level = module_levels[cb.name]
            level_map = {}
            remaining = [mod.name for mod in cb.modules]
        
            while remaining:
                progressed = False
                for mod_name in list(remaining):

                    internal_inputs = [
                        src_mod for input_name, (src_mod, _) in self.connections.get(mod_name, {}).items()
                        if src_mod in cb.module_map
                    ]
        
                    external_inputs = [
                        src_mod for input_name, (src_mod, _) in self.connections.get(mod_name, {}).items()
                        if src_mod not in cb.module_map
                    ]
        
                    internal_known = any(src in level_map for src in internal_inputs)
                                        
                    valid_external = any(
                        module_levels.get(src, 0) < base_level for src in external_inputs
                    )
                    
                    
                    if valid_external: # First level in a CB if there are external inputs
                        level = base_level + 0.1
                        level_map[mod_name] = round(level, 5)
                        remaining.remove(mod_name)
                        progressed = True
                        continue

                    elif internal_inputs and not internal_known:
                        continue  # Internal inputs exist but their sources haven't been assigned → skip for now
        
                    elif not internal_inputs:
                        # Either external source or true source node
                        if valid_external or not external_inputs: # Ensure that this is a correct case of a source module
                            level = base_level + 0.1
                            level_map[mod_name] = round(level, 5)
                            remaining.remove(mod_name)
                            progressed = True
                    else:  
                        # Module of a CB with only internal inputs, that at this point already has SOME assigned predecessors
                        # Inner modules that send outputs to this Module that have not been assigned yet are assumed to be a feedback loop
                        # Internal sources are all known
                        parent_levels = [level_map[src] for src in internal_inputs if src in level_map] # get the parents that have been processed
                        level = increment_sublevel(max(parent_levels))
                        level_map[mod_name] = round(level, 5)
                        remaining.remove(mod_name)
                        progressed = True
        
                if not progressed:
                    # Feedback loop: assign remaining to base_level + 0.1
                    print(f"Warning: Unresolved feedback loop was detected within a CoupledBlock: {cb.name}")
                    for mod_name in remaining:
                        level_map[mod_name] = round(base_level + 0.1, 5)
                    break
            
            cb.level_map = level_map # pass the level map to the CB object itself
            sublevels[cb.name] = level_map
        
        print(f"\nModule levels: {module_levels}")
        print(f"Sublevels: {sublevels}\n")

        return module_levels, sublevels        



    def _build_execution_order(self):
        
        # Step 1: Build the full dependency graph from all module connections
        G = nx.DiGraph()
        for dst_mod, conn_dict in self.connections.items():
            for _, (src_mod, _) in conn_dict.items():
                G.add_edge(src_mod, dst_mod)
    
        # Step 2: Detect strongly connected components (SCCs) - modules with cycles
        sccs_raw = list(nx.strongly_connected_components(G))
    
        # Step 3: Extract internal order for each SCC
        ordered_sccs = []
        for group in sccs_raw:
            group = list(group)
            if len(group) == 1:             # Single module — no cycle, just add as-is
                ordered_sccs.append(group)
            else:
                # For coupled group, extract a meaningful order using reversed DFS- depth-first traversas
                subgraph = G.subgraph(group).copy()
                ordered = list(reversed(list(nx.dfs_postorder_nodes(subgraph)))) # dfs_postorder_nodes returns reversed order
                ordered_sccs.append(ordered)
    
        # Step 4: Instantiate CoupledBlocks and prepare group mapping    
        for group in ordered_sccs:
            if len(group) > 1:
                block_name = f"CoupledBlock from {group[0]}"  # Deterministic name for the block
                modules = [self.module_map[name] for name in group]
                block = CoupledBlock(name=block_name, modules=modules, global_connections=self.connections)
                self.coupled_blocks.append(block)
                for name in group:
                    self.module_to_block[name] = block_name
    
        # Step 5: Build reduced dependency graph (between modules and CoupledBlocks)
        reduced_graph = nx.DiGraph()
        for dst_mod, conn_dict in self.connections.items():
            dst_group = self.module_to_block.get(dst_mod, dst_mod)  # Ret CoupledBlock where dst_mod is, otherwise ret just dst_mod
            for _, (src_mod, _) in conn_dict.items():
                src_group = self.module_to_block.get(src_mod, src_mod)  # Likewise for src
                if src_group != dst_group:
                    # Only add edge if it's a true inter-block or inter-module dependency
                    reduced_graph.add_edge(src_group, dst_group)
    
        # Sanity check to ensure reduced graph is still acyclic
        if not nx.is_directed_acyclic_graph(reduced_graph):
            raise RuntimeError("Cycle detected between CoupledBlocks or modules — execution order is invalid.")
    
        # Step 6: Topologically sort the reduced graph to get execution order
        name_to_object = {mod.name: mod for mod in self.modules}
        name_to_object.update({cb.name: cb for cb in self.coupled_blocks}) # Containes all module and coupled_block objects
    
        sorted_names = list(nx.topological_sort(reduced_graph))
        self.execution_order = [name_to_object[name] for name in sorted_names]
        # Ensure coupled_blocks is in the same order as execution_order
        self.coupled_blocks = [item for item in self.execution_order if isinstance(item, CoupledBlock)]

        
        # Step 7: Get the final module order based on levels of execution
        self.module_levels, self.sublevels = self._assign_levels()

        # Step 8: Check for invalid common output usages
        # Common function outputs should never have a feedback direction (never a responsible for algebraic loops)
        for cb in self.coupled_blocks:
            cb._check_common_function_usage()


    def _write_history(self, mod):
        if isinstance(mod, CoupledBlock):
            outputs_by_module = mod.get_all_outputs()
        else:
            outputs_by_module = {mod.name: mod.get_outputs()}
    
        for module_name, outputs in outputs_by_module.items():
            for name, pv in outputs.items():
                self.history[module_name].setdefault(name, []).append((self.time, pv.value))


    def _set_inputs(self, mod):
        if isinstance(mod, CoupledBlock):
            # CoupledBlock gets external inputs through input_mapping
            for cb_input_name, (src_mod_name, src_output) in mod.input_mapping.items():
                src_mod = self.module_map[src_mod_name]
                # Check if this module is part of a coupled block
                if src_mod_name in self.module_to_block:
                    src_block = self.module_to_block[src_mod_name]
                    outputs = src_block.get_outputs()
                    if src_mod_name not in outputs or src_output not in outputs[src_mod_name]:
                        raise KeyError(f"Output '{src_output}' not found in CoupledBlock from '{src_mod_name}'")
                    value = outputs[src_mod_name][src_output].value
                else:
                    outputs = src_mod.get_outputs()
                    if src_output not in outputs:
                        raise KeyError(f"Output '{src_output}' not found in module '{src_mod_name}'")
                    value = outputs[src_output].value
    
                mod.inputs[cb_input_name].set_value(value)
        else:
            if mod.name not in self.connections:
                return
            for input_name, (src_mod_name, src_output) in self.connections[mod.name].items():
                src_mod = self.module_map[src_mod_name]
                if src_mod_name in self.module_to_block:
                    src_block = self.module_to_block[src_mod_name]
                    outputs = src_block.get_outputs()
                    if src_mod_name not in outputs or src_output not in outputs[src_mod_name]:
                        raise KeyError(f"Output '{src_output}' not found in CoupledBlock from '{src_mod_name}'")
                    value = outputs[src_mod_name][src_output].value
                else:
                    outputs = src_mod.get_outputs()
                    if src_output not in outputs:
                        raise KeyError(f"Output '{src_output}' not found in module '{src_mod_name}'")
                    value = outputs[src_output].value
    
                mod.inputs[input_name].set_value(value)


    def _initialize(self):
        for mod in self.execution_order:  # should already be in topological order
            self._set_inputs(mod)       # fill inputs from self.current_values
            mod.initialize()            # sets internal state
                   
                    
    def _step(self):     
        
        def is_aligned(time, dt, scale=10**10):
            # Skip modules if it is not their turn
            # at t=0 this will return True which is what we want
            return round(time * scale) % round(dt * scale) == 0

        for mod in self.execution_order:
            if is_aligned(self.time, mod.dt):
                self._set_inputs(mod)
                mod.step(self.time)
                self._write_history(mod)
        
        self.time = round(self.time + self.dt, 10)



    def _enable_monitoring(self, config, matplotlib_backend, save_results, file_name):
        """ Sets up the blank plot canvas where the data will be monitored"""
        
        # Change matplotlib for live monitoring plot
        # Must be BEFORE importing pyplot -> its fine to change it here because this is the first time in code matplotlib is used (at start of run())
        
        matplotlib.use(matplotlib_backend)  
        
        self._monitor_config = config
        self._monitor_groups = config.get("groups", [])
        self._monitor_labels = config.get("labels", None)
        self._monitor_titles = config.get("titles", None)
        self._monitor_y_labels = config.get("y_labels", None)
        self._monitor_save = save_results
        self._monitor_file = file_name
    
        num_subplots = len(self._monitor_groups)
        height_per_subplot = 3  # or 3.5 for a bit more space
        self._monitor_fig, self._monitor_axes = plt.subplots(
            num_subplots, 1,
            figsize=(10, height_per_subplot * num_subplots),
            dpi=150,
            sharex=True
        )
        if num_subplots == 1:
            self._monitor_axes = [self._monitor_axes]
    
        self._monitor_lines = []
    
        for i, group in enumerate(self._monitor_groups):
            ax = self._monitor_axes[i]
            ax.set_xlim(0, self.t_end)
            group_labels = self._monitor_labels[i] if self._monitor_labels and i < len(self._monitor_labels) else None
            line_group = []
            for j, (mod, out) in enumerate(group):
                label = (group_labels[j] if group_labels and j < len(group_labels)
                         else f"{mod} {out} [{self.get_output_unit(mod, out)}]")
                line, = ax.plot([], [], label=label)
                line_group.append((mod, out, line))
            ylabel = self._monitor_y_labels[i] if self._monitor_y_labels and i < len(self._monitor_y_labels) else "Module Output Signals"
            ax.set_ylabel(ylabel)
            ax.set_title(self._monitor_titles[i] if self._monitor_titles and i < len(self._monitor_titles) else f"Output Signals {i+1}")
            ax.grid(True)
            ax.legend()
            self._monitor_lines.append(line_group)
    
        self._monitor_axes[-1].set_xlabel("Time [s]")
        self._monitor_fig.tight_layout()
        plt.ion()
        plt.show()
        
        self._monitor_initialized = True


    def _monitor_results(self, plt_pause):
        """ Plots new data as it is being calculated"""
        
        if not self._monitor_initialized:
            return
    
        for ax, group in zip(self._monitor_axes, self._monitor_lines):
            for mod_name, out, line in group:
                if mod_name in self.history and out in self.history[mod_name]:
                    timeseries = self.history[mod_name][out]
                    if timeseries:
                        times, values = zip(*timeseries)
                        line.set_data(times, values)
                        
            ax.relim()
            ax.autoscale_view()
            
        
        self._monitor_fig.canvas.draw()
        self._monitor_fig.canvas.flush_events()
        plt.pause(plt_pause)    
    
    
    def run(self, monitor_results=False, monitor_config=None, matplotlib_backend="TkAgg", save_results=False, file_name="output_results", plt_pause=0.001):

        def execute_this_turn(scale=10**10, turns=5):
            # Monitor every 5th data to save CPU
            return round(( round(self.time * scale) / round(self.dt * scale) )) % 5 == 0
        
        self._build_execution_order()
        self._initialize()
        
        if monitor_results:
            self._enable_monitoring(monitor_config or {}, matplotlib_backend, save_results, file_name)
        
        try:
            while self.time <= self.t_end: # Execution
                self._step()
                if monitor_results and execute_this_turn():
                    self._monitor_results(plt_pause)
             
        finally:
            if monitor_results: # This prevents the GUI from freezing
                plt.pause(1)  # keep the result for a second until the plot_outputs() closes it due to change of backend
                plt.ioff()
                self._monitor_fig.tight_layout()
                if self._monitor_save:
                    filename = f"{self._monitor_file}.png"
                    self._monitor_fig.savefig(filename, dpi=300)
                    print(f"✅ Monitoring plot saved as {filename}")
                self._monitor_fig.show()  # ← shows the correct window only

    
    def get_output_timeseries(self, module_name, output_name):
        if module_name not in self.history or output_name not in self.history[module_name]:
            raise KeyError(f"No history found for {module_name}.{output_name}")
        return self.history[module_name][output_name]
        
    
    def get_output_unit(self, module_name, output_name):
        mod = self.module_map[module_name]
        if output_name not in mod.outputs:
            raise KeyError(f"Output '{output_name}' not found in module '{module_name}'")
        return str(mod.outputs[output_name].unit)
  

    def export_history_to_excel(self, filename="simulation_export.xlsx", outputs=None, time_range=None, step_skip=1, force_single_sheet=False):
        """
        Export simulation history to Excel.
    
        Parameters:
        - filename: str, name of the Excel file to save.
        - outputs: list of (module_name, output_name) tuples to export. If None, export all outputs.
        - time_range: tuple (start_time, end_time) in seconds. If None, export entire time range.
        - step_skip: int, export every nth data point (default: 1 means no skipping).
        - force_single_sheet: if True, uses one sheet and fills missing values by repeating the last known value.
        """
    
        # Step 1: Determine outputs if not specified
        if outputs is None:
            outputs = []
            for mod in self.execution_order:
                mod_name = mod.name
                if mod_name in self.history:
                    for out in self.history[mod_name]:
                        outputs.append((mod_name, out))
    
        # Step 2: Get all unique times from the module with the smallest dt
        all_times = []
        for mod, out in outputs:
            series = self.history[mod][out]
            if series:
                times = [t for t, _ in series]
                if len(times) > len(all_times):
                    all_times = times
        if time_range:
            t_start, t_end = time_range
            mask = [(t >= t_start) and (t <= t_end) for t in all_times]
        else:
            mask = [True] * len(all_times)
        filtered_times = [t for t, m in zip(all_times, mask) if m][::step_skip]
    
        if force_single_sheet:
            df = pd.DataFrame()
            df["Time [s]"] = filtered_times
    
            for mod, out in outputs:
                series = self.history[mod][out]
                times, values = zip(*series)
                latest_value = values[0]
                expanded = []
                index = 0
                for t in filtered_times:
                    while index + 1 < len(times) and times[index + 1] <= t:
                        index += 1
                        latest_value = values[index]
                    expanded.append(latest_value)
                unit = str(self.module_map[mod].outputs[out].unit)
                df[f"{mod}.{out} [{unit}]"] = expanded
    
            df.to_excel(filename, index=False)
            print(f"✅ Exported single-sheet Excel file with repeated values to: {os.path.abspath(filename)}")
    
        else:
            writer = pd.ExcelWriter(filename)
            grouped = {}
            for mod, out in outputs:
                grouped.setdefault(mod, []).append(out)
    
            mod_names_ordered = [mod.name for mod in self.execution_order]
            ordered_modules = [mod for mod in mod_names_ordered if mod in grouped]
    
            for mod in ordered_modules:
                out_list = grouped[mod]
                if mod not in self.history:
                    continue
    
                time_series = list(self.history[mod].values())[0]
                times = [t for t, _ in time_series]
                if time_range:
                    t_start, t_end = time_range
                    mask = [(t >= t_start) and (t <= t_end) for t in times]
                else:
                    mask = [True] * len(times)
                filtered_times_mod = [t for t, m in zip(times, mask) if m][::step_skip]
    
                df = pd.DataFrame()
                df["Time [s]"] = filtered_times_mod
    
                for out in sorted(out_list):
                    series = self.history[mod][out]
                    values = [v for (t, v), m in zip(series, mask) if m][::step_skip]
                    unit = str(self.module_map[mod].outputs[out].unit)
                    df[f"{mod}.{out} [{unit}]"] = values
    
                df.to_excel(writer, sheet_name=mod[:31], index=False)  # Sheet name limit = 31
    
            writer.close()
            print(f"✅ Exported multi-sheet Excel file to: {os.path.abspath(filename)}")

    

    def plot_outputs(self, config, matplotlib_backend="inline", save_results=False, file_name="output_results"):
        """
        Plots output signals grouped into subplots.
    
        Parameters:
        - groups: List of lists of (module_name, output_name) tuples.
                  Each inner list defines one subplot.
        - labels: Optional list of lists of labels for each curve.
                  Defaults to 'module output [unit]' format.
        - titles: Optional list of titles for each subplot.
                  Defaults to "Output Signals {i+1}"
        - y_labels: Optional list of y-axis labels per subplot.
                    Defaults to "Module Output Signals"
        """
        
        matplotlib.use(matplotlib_backend) # Change backend for plotting to avoid crashes
        groups = config.get("groups", [])
        labels = config.get("labels", None)
        titles = config.get("titles", None)
        y_labels = config.get("y_labels", None)
        
        num_subplots = len(groups)
        height_per_subplot = 3  # Same as in _enable_monitoring
        fig, axs = plt.subplots(
            num_subplots, 1,
            figsize=(12, height_per_subplot * num_subplots),
            dpi=150,
            sharex=True
        )
        if num_subplots == 1:
            axs = [axs]
    
        for i, group in enumerate(groups):
            ax = axs[i]
            group_labels = labels[i] if labels and i < len(labels) else None
            for j, (mod, out) in enumerate(group):
                timeseries = self.get_output_timeseries(mod, out)
                times, values = zip(*timeseries)
                unit = self.get_output_unit(mod, out)
                label = (group_labels[j] if group_labels and j < len(group_labels)
                         else f"{mod} {out} [{unit}]")
                ax.plot(times, values, label=label, linewidth=1.2)
    
            ylabel = y_labels[i] if y_labels and i < len(y_labels) else "Module Output Signals"
            ax.set_ylabel(ylabel)
            ax.set_title(titles[i] if titles and i < len(titles) else f"Output Signals {i+1}")
            ax.grid(True)
            ax.legend()
    
        axs[-1].set_xlabel("Time [s]")
        plt.tight_layout()
        
        if save_results:
            filename = f"{file_name}.png"
            plt.savefig(filename, dpi=300)
            print(f"✅ Plot saved as {filename}")
    
        plt.show()
        
        
    def visualise(self, filename="simulation_graph", show_edge_labels=False, splines='true', ranksep='1.1', nodesep='0.7', show_parameters=True, show_io=True, show_dt=True):
        
        # Step 1: Flatten execution order to get all modules as well as levels
        all_modules_ordered = []
        all_levels = {}

        for item in self.execution_order:
            if isinstance(item, CoupledBlock):
                cb_name = item.name
                sublevel_map = self.sublevels.get(cb_name, {})
                # Sort internal modules by sublevel
                ordered = sorted(item.modules, key=lambda m: sublevel_map.get(m.name, 0))
                for mod in ordered:
                    all_modules_ordered.append(mod)
                    all_levels[mod.name] = sublevel_map.get(mod.name, 0)
            else:
                all_modules_ordered.append(item)
                all_levels[item.name] = self.module_levels.get(item.name, 0)
    
    
        # Step 2: Setup graph
        dot = Digraph(format='png')
        dot.attr(rankdir='LR', dpi='300', splines=splines, ranksep=ranksep, nodesep=nodesep)  

    
        # Step 3: Add nodes
        for mod in all_modules_ordered:
            lines = [
                f"<font point-size='10'>{mod.type.upper()}:</font><br/>" +
                f"<b><font point-size='10'>{mod.name}</font></b><br/><br/>"
            ]
    
            # Add dt only if different
            if show_dt and not self.constant_dts:
                lines.append(f"<font point-size='10'>dt = {mod.dt}</font><br/><br/>")
    
            # Parameters with units
            if show_parameters:
                for param in mod.parameters.values():
                    lines.append(f"<font point-size='10'>{param.name} = {param.original_value} {param.original_unit}</font><br/>")
                if mod.parameters:
                    lines.append("<br/>")  # Empty line between params and I/O
    
            # Inputs / Outputs
            if show_io:
                if mod.inputs:
                    lines.append(f"<font point-size='10'>Inputs: {', '.join(mod.inputs.keys())}</font>")
                if mod.inputs:
                    lines.append("<br/>")  # Empty line between params and I/O
                if mod.outputs:
                    lines.append(f"<font point-size='10'>Outputs: {', '.join(mod.outputs.keys())}</font>")
    
            label = "<" + "".join(lines) + ">"
            dot.node(
                mod.name,
                label=label,
                shape="box",
                style="rounded,filled",
                fillcolor="#d0e7ff"  # Light transparent blue
            )
    
        # Step 4: Add edges
        for dst, conn_dict in self.connections.items():
            for input_name, (src, output_name) in conn_dict.items():
                src_idx = all_levels.get(src)
                dst_idx = all_levels.get(dst)
                if src_idx is None or dst_idx is None:
                    continue
        
                is_feedback = src_idx >= dst_idx
                # style = "dashed" if is_feedback else "solid"
                # color = "black"
        
                kwargs = {
                    "tailport": "e",
                    "headport": "w",
                    "style": "dashed" if is_feedback else "solid",
                    "color": "black"
                }
                if show_edge_labels:
                    kwargs["label"] = f"{output_name} → {input_name}"
                
                if is_feedback:
                    kwargs["minlen"] = "3"
                    kwargs["constraint"] = "false"
                    kwargs["weight"] = "0"
                
                dot.edge(src, dst, **kwargs)
    
        # Step 5: Render
        dot.render(filename=filename, cleanup=True)
        print(f"Graph saved as {filename}.png")
        
