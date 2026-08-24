"""FMI 2.0 Co-Simulation FMU wrapper.

This module exposes :class:`FMUComponent`, a :class:`~syssimx.core.base.CoSimComponent`
implementation backed by an FMI 2.0 co-simulation FMU via ``fmpy``. The component
derives input/output ports from the FMU model description, handles units for REAL
signals, applies parameter starts during initialization, and supports direct
feedthrough evaluation.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

from ..core.base import CoSimComponent
from ..core.port import PortSpec, PortType
from ..utilities.units import QuantityClass, QuantityType, to_pint_unit

_FMPY_IMPORT_ERROR: ModuleNotFoundError | None = None

try:
    from fmpy import extract, read_model_description
    from fmpy.fmi2 import FMU2Slave
    from fmpy.model_description import ModelDescription, ScalarVariable
except ModuleNotFoundError as e:
    extract = None  # type: ignore[assignment]
    read_model_description = None  # type: ignore[assignment]
    FMU2Slave = None  # type: ignore[assignment]
    ModelDescription = None  # type: ignore[assignment]
    ScalarVariable = None  # type: ignore[assignment]
    _FMPY_IMPORT_ERROR = e


def _require_fmpy() -> None:
    if _FMPY_IMPORT_ERROR is not None:
        raise ModuleNotFoundError(
            "Optional dependency 'fmpy' is required for FMUComponent. "
            "Install with: pip install syssimx[fmu] (or pip install fmpy)."
        ) from _FMPY_IMPORT_ERROR


_LOG = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# Extraction cache (issues.md HARD-07)
# ----------------------------------------------------------------------------
# ``fmpy.extract()`` unpacks into a fresh temporary directory that nobody
# removes, so every component and every repeated ``initialize()`` used to strand
# a whole copy of the archive. Extraction depends only on the file, so it is
# cached on the file's identity and shared by every consumer of that archive.
_EXTRACTION_CACHE: dict[tuple[str, int, int], str] = {}


def _extraction_key(path: str) -> tuple[str, int, int]:
    """Identify an archive by path, size, and modification time."""
    stat = os.stat(path)
    return (path, stat.st_size, stat.st_mtime_ns)


def extract_cached(path: str) -> str:
    """Extract ``path`` once and reuse that directory for every later call.

    A rebuilt or replaced archive gets a new key and is extracted again, so a
    stale directory is never handed out. If a cached directory has disappeared
    underneath us, the archive is extracted afresh.

    Args:
        path: Resolved path to the ``.fmu`` archive.

    Returns:
        Path of the extraction directory. Callers must not delete it; it is
        shared with every other component using the same archive.
    """
    key = _extraction_key(path)
    cached = _EXTRACTION_CACHE.get(key)
    if cached is not None and Path(cached).is_dir():
        return cached
    unzipdir = str(extract(path))
    _EXTRACTION_CACHE[key] = unzipdir
    return unzipdir


def clear_extraction_cache() -> None:
    """Remove every cached extraction directory.

    Only safe once no native instance remains alive anywhere in the process:
    the shared libraries are loaded out of these directories, and on Windows an
    open handle keeps them locked. Intended for teardown at the end of a run,
    not between steps.
    """
    for unzipdir in list(_EXTRACTION_CACHE.values()):
        try:
            shutil.rmtree(unzipdir, ignore_errors=True)
        except OSError:  # pragma: no cover - platform-specific cleanup fault
            _LOG.warning("Could not remove FMU extraction directory %s", unzipdir)
    _EXTRACTION_CACHE.clear()


# ----------------------------------------------------------------------------
# Release policy (issues.md HARD-05)
# ----------------------------------------------------------------------------
@dataclass(frozen=True)
class FMUReleasePolicy:
    """Whether an export tolerates ``fmi2FreeInstance`` and ``fmi2Reset``.

    Calling either on an OpenModelica CVODE export that allocates a solver
    corrupts the heap and takes the process down. The condition is a property
    of the archive, readable without executing anything, so a component can
    know before it ever instantiates.

    Attributes:
        releasable: True when the native instance may be terminated and freed.
        solver: Solver recorded by the export, or ``None`` if not an
            OpenModelica archive.
        continuous_states: Continuous states declared by the model description.
        reason: Human-readable justification, used in logs and diagnostics.
    """

    releasable: bool
    solver: str | None
    continuous_states: int
    reason: str


def _read_solver_flag(path: str) -> str | None:
    """Return the solver an OpenModelica export recorded, if any.

    The flag lives in ``resources/<model>_flags.json`` inside the archive. Any
    other producer, or a malformed archive, yields ``None``.
    """
    try:
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if name.startswith("resources/") and name.endswith("_flags.json"):
                    flags = json.loads(archive.read(name))
                    solver = flags.get("s")
                    return str(solver) if solver is not None else None
    except (OSError, zipfile.BadZipFile, ValueError, UnicodeDecodeError):
        return None
    return None


def resolve_release_policy(path: str, model_description: Any) -> FMUReleasePolicy:
    """Decide statically whether ``path`` may have its instance released.

    An OpenModelica CVODE export with at least one continuous state allocates a
    SUNDIALS solver whose teardown is defective, and freeing it corrupts the
    heap. A zero-state CVODE export never allocates the solver and is safe, as
    is any export using another solver.

    The predicate was derived from eight archives and then correctly predicted
    the remaining four, including both zero-state CVODE exports that survive
    and the one-state export that does not.

    Args:
        path: Resolved path to the ``.fmu`` archive.
        model_description: Parsed ``fmpy`` model description.

    Returns:
        The policy for this archive.
    """
    solver = _read_solver_flag(path)
    states = int(getattr(model_description, "numberOfContinuousStates", 0) or 0)

    if solver == "cvode" and states > 0:
        return FMUReleasePolicy(
            releasable=False,
            solver=solver,
            continuous_states=states,
            reason=(
                f"OpenModelica CVODE export with {states} continuous state(s); "
                "fmi2FreeInstance and fmi2Reset corrupt the heap (issues.md HARD-05)"
            ),
        )
    if solver == "cvode":
        return FMUReleasePolicy(
            releasable=True,
            solver=solver,
            continuous_states=states,
            reason="CVODE export with no continuous states, so no solver is allocated",
        )
    return FMUReleasePolicy(
        releasable=True,
        solver=solver,
        continuous_states=states,
        reason=f"solver {solver!r} is not the defective CVODE teardown path",
    )


# ----------------------------------------------------------------------------
# FMU Component Class
# ----------------------------------------------------------------------------
class FMUComponent(CoSimComponent):
    """FMU co-simulation wrapper implementing the CoSimComponent interface.

    Supports FMI 2.0 co-simulation FMUs, typed input/output ports (REAL, INT,
    BOOL, STRING), and unit-aware REAL ports via ``pint``.
    """

    # State of all FMU variables
    state: dict[str, Any]

    _md: ModelDescription
    _md_vars: dict[str, ScalarVariable]
    _instance: FMU2Slave | None
    _unzipdir: str | None

    # Direct Feedthrough for output dependencies
    direct_feedthrough: dict[str, set[str]]

    # Cached value references per base type and causality
    _vrs_in_real: dict[str, int]
    _vrs_in_int: dict[str, int]
    _vrs_in_bool: dict[str, int]
    _vrs_in_str: dict[str, int]
    _vrs_in_bytes: dict[str, int]

    _vrs_out_real: dict[str, int]
    _vrs_out_int: dict[str, int]
    _vrs_out_bool: dict[str, int]
    _vrs_out_str: dict[str, int]
    _vrs_out_bytes: dict[str, int]

    def __init__(self, name: str, fmu_path: str, group: str | None = None):
        """Create the FMU component and derive port specifications.

        Args:
            name: Component name.
            fmu_path: Path to the FMU file.
            group: Optional component group for organization.

        Raises:
            RuntimeError: If the FMU is not a co-simulation FMU.
            NotImplementedError: If the FMU uses an unsupported FMI version.
        """
        _require_fmpy()
        super().__init__(name=name, group=group)
        self._path = str(Path(fmu_path).resolve())
        self._md = read_model_description(self._path)
        self._md_vars = {var.name: var for var in self._md.modelVariables}
        if not self._md.coSimulation:
            raise RuntimeError(f"FMU '{fmu_path}' is not a Co-Simulation FMU.")
        if self._md.fmiVersion != "2.0":
            raise NotImplementedError(
                f"FMU '{fmu_path}' has unsupported FMI version '{self._md.fmiVersion}'. Only FMI 2.0 is supported."
            )
        self._instance = None
        self._unzipdir = None

        # Whether this archive tolerates fmi2FreeInstance / fmi2Reset. Derived
        # statically from the archive, so it is known before the first
        # instantiation (issues.md HARD-05).
        self.release_policy: FMUReleasePolicy = resolve_release_policy(self._path, self._md)
        if not self.release_policy.releasable:
            _LOG.debug(
                "%s: native instances will be retained - %s",
                name,
                self.release_policy.reason,
            )

        # Port specification containers
        self.input_specs: dict[str, PortSpec] = {}
        self.output_specs: dict[str, PortSpec] = {}
        self.direct_feedthrough = {}
        self._detect_direct_feedthrough()
        self._analyze_model_structure()

        # Build port specifications from model description (Real, Int, Bool, Str, Bytes)
        self._build_port_specs()
        self._initialize_ports_from_specs()

        # Cache value references map
        self._vrs_in_real = {}
        self._vrs_in_int = {}
        self._vrs_in_bool = {}
        self._vrs_in_str = {}
        self._vrs_out_real = {}
        self._vrs_out_int = {}
        self._vrs_out_bool = {}
        self._vrs_out_str = {}
        self._build_value_reference_map()

        # Parameters dictionary
        self.parameters: dict[str, Any] = self.get_default_parameters()

    # ----------------------------------------------------------------------------
    # Get default parameters from model description
    # ----------------------------------------------------------------------------
    def get_default_parameters(self) -> dict[str, Any]:
        """Return default parameter values from the FMU model description.

        Returns:
            Dict of parameter names to default values.
        """
        defaults: dict[str, Any] = {}
        for var in self._md.modelVariables:
            if var.causality not in ("parameter", "calculatedParameter", "structuralParameter"):
                continue
            name = var.name
            unit = to_pint_unit(var.unit) if var.unit else None
            type = _port_type_from_var(var)
            value = _convert_start_value(var.start, type, unit)
            defaults[name] = value
        return defaults

    # ----------------------------------------------------------------------------
    # Build helper for port specifications and value reference maps
    # ----------------------------------------------------------------------------
    def _build_port_specs(self) -> None:
        """Build input/output PortSpec objects from the model description."""
        for var in self._md.modelVariables:
            if var.causality not in ("input", "output"):
                continue
            direction: Literal["in", "out"] = "in" if var.causality == "input" else "out"
            port_type = _port_type_from_var(var)
            if port_type is None:
                continue
            unit = None
            if port_type == PortType.REAL and var.unit:
                unit = str(to_pint_unit(var.unit)) if var.unit else None

            spec = PortSpec(
                name=var.name,
                type=port_type,
                direction=direction,
                unit=unit,
                description=var.description,
            )
            if direction == "in":
                self.input_specs.update({var.name: spec})
            else:
                self.output_specs.update({var.name: spec})

    def _build_value_reference_map(self) -> None:
        """Cache value references for fast typed access."""
        for var in self._md.modelVariables:
            causality = var.causality
            if causality not in ("input", "output"):
                continue
            port_type = _port_type_from_var(var)
            value_reference = var.valueReference
            if causality == "input":
                if port_type == PortType.REAL:
                    self._vrs_in_real[var.name] = value_reference
                elif port_type == PortType.INT:
                    self._vrs_in_int[var.name] = value_reference
                elif port_type == PortType.BOOL:
                    self._vrs_in_bool[var.name] = value_reference
                elif port_type == PortType.STRING:
                    self._vrs_in_str[var.name] = value_reference

            elif causality == "output":
                if port_type == PortType.REAL:
                    self._vrs_out_real[var.name] = value_reference
                elif port_type == PortType.INT:
                    self._vrs_out_int[var.name] = value_reference
                elif port_type == PortType.BOOL:
                    self._vrs_out_bool[var.name] = value_reference
                elif port_type == PortType.STRING:
                    self._vrs_out_str[var.name] = value_reference

    def _analyze_model_structure(self) -> None:
        """Populate model structure dependencies for outputs/derivatives/initials."""
        for output in self._md.outputs:
            out_var = output.variable.name
            deps = []
            for dep in output.dependencies:
                deps.append(dep.name)
            self.model_structure["outputs"][out_var] = deps

        for derivative in self._md.derivatives:
            der_var = derivative.variable.name
            deps = []
            for dep in derivative.dependencies:
                deps.append(dep.name)
            self.model_structure["derivatives"][der_var] = deps

        for init_unknown in self._md.initialUnknowns:
            init_var = init_unknown.variable.name
            deps = []
            for dep in init_unknown.dependencies:
                deps.append(dep.name)
            self.model_structure["initialUnknowns"][init_var] = deps

    def _detect_direct_feedthrough(self) -> dict[str, set[str]]:
        """Detect direct feedthrough dependencies for FMU outputs."""
        feedthrough: dict[str, set[str]] = {}
        for unknown in self._md.outputs:
            feedthrough[unknown.variable.name] = set()
            for dep in unknown.dependencies:
                if dep.causality == "input":
                    feedthrough[unknown.variable.name].add(dep.name)
        self.direct_feedthrough = feedthrough
        return feedthrough

    def _require_instance(self) -> FMU2Slave:
        """Return the FMU instance or raise if not initialized."""
        if self._instance is None:
            raise RuntimeError(f"{self.name}: FMU instance not initialized")
        return self._instance

    # ----------------------------------------------------------------------------
    # Initialization
    # ----------------------------------------------------------------------------
    def _initialize_component(self, t0: float) -> None:
        """Initialize and instantiate the FMU for simulation.

        1. Extracts the FMU archive.
        2. Creates the FMU2Slave instance.
        3. Sets up the experiment with the start time.
        4. Enters initialization mode.
        5. Applies parameter start values.
        6. Applies input start values from PortStates.
        7. Exits initialization mode.

        Args:
            t0: Simulation start time.
        """
        # Extraction is cached on the archive's identity, so repeated
        # initialization and sibling components reuse one directory instead of
        # stranding a copy each time (issues.md HARD-07).
        self._unzipdir = extract_cached(self._path)
        self._instantiate_instance(t0)

    def _instantiate_instance(self, t0: float) -> None:
        """Create and initialize one native instance from the extracted FMU."""
        if self._unzipdir is None:
            raise RuntimeError(f"{self.name}: FMU archive has not been extracted")
        self._instance = FMU2Slave(
            instanceName=self.name,
            guid=self._md.guid,
            unzipDirectory=self._unzipdir,
            modelIdentifier=self._md.coSimulation.modelIdentifier,
        )
        self._instance.instantiate()
        self._instance.setupExperiment(startTime=t0)
        self._instance.enterInitializationMode()
        self._apply_parameters_starts()
        self._apply_input_starts()
        self._instance.exitInitializationMode()

    def reinitialize_instance(self, t0: float) -> None:
        """Recreate the FMU instance and enter initialized state at ``t0``.

        This is intentionally different from FMI ``reset()``. Some FMUs do not
        support reliable rollback through ``fmi2Reset`` after stepping, but can
        be restored by creating a fresh instance and applying reconstructed
        initial conditions through parameters.

        The outgoing instance is released when :attr:`release_policy` allows it.
        For the defective CVODE exports it is dropped without ``fmi2Terminate``
        or ``fmi2FreeInstance`` and stays resident until the process ends,
        because freeing it corrupts the heap (issues.md HARD-05). This is the
        hybrid rollback path, so it runs once per restore.
        """
        self._release_instance()
        self._instantiate_instance(t0)

    # ----------------------------------------------------------------------------
    # Native resource release
    # ----------------------------------------------------------------------------
    def _release_instance(self) -> None:
        """Terminate and free the native instance when the policy allows.

        Ownership is cleared first, so a fault during cleanup cannot lead to a
        second release through ``reset()`` or error handling. When the policy
        forbids release the reference is dropped and the instance is left
        resident; that leak is deliberate and is measured under HARD-07.
        """
        instance = self._instance
        if instance is None:
            return
        self._instance = None

        if not self.release_policy.releasable:
            _LOG.debug("%s: retaining native instance - %s", self.name, self.release_policy.reason)
            return

        errors: list[Exception] = []
        if self._is_initialized:
            try:
                instance.terminate()
            except Exception as exc:  # pragma: no cover - backend-specific cleanup fault
                errors.append(exc)
        try:
            instance.freeInstance()
        except Exception as exc:  # pragma: no cover - backend-specific cleanup fault
            errors.append(exc)
        if errors:
            raise RuntimeError(
                f"{self.name}: FMU cleanup reported {len(errors)} error(s)."
            ) from errors[0]

    def free(self) -> None:
        """Release the native instance permanently.

        The extraction directory is shared through the module-level cache and is
        deliberately not removed here; :func:`clear_extraction_cache` owns that
        and is safe only once no instance remains alive in the process.

        For an archive whose :attr:`release_policy` forbids release this is a
        no-op beyond dropping the reference, and it says so in the log rather
        than silently doing nothing.
        """
        self._release_instance()

    # ----------------------------------------------------------------------------
    # Initialization helpers
    # ----------------------------------------------------------------------------
    def _apply_parameters_starts(self) -> None:
        """Apply parameter start values to the FMU instance."""
        instance = self._require_instance()
        # batch parameters by base type
        real_vrs: list[int] = []
        real_vals: list[float] = []
        int_vrs: list[int] = []
        int_vals: list[int] = []
        bool_vrs: list[int] = []
        bool_vals: list[int] = []
        str_vrs: list[int] = []
        str_vals: list[str] = []

        for name, value in self.parameters.items():
            if value is None:
                continue
            var = self._md_vars.get(name)
            if var is None:
                continue
            if var._python_type is float:
                real_vrs.append(var.valueReference)
                value = value.magnitude if isinstance(value, QuantityClass) else value
                real_vals.append(float(value))
            elif var._python_type is int:
                int_vrs.append(var.valueReference)
                int_vals.append(int(value))
            elif var._python_type is bool:
                bool_vrs.append(var.valueReference)
                bool_vals.append(1 if bool(value) else 0)
            elif var._python_type is str:
                str_vrs.append(var.valueReference)
                str_vals.append(str(value))

        if real_vrs:
            instance.setReal(real_vrs, real_vals)
        if int_vrs:
            instance.setInteger(int_vrs, int_vals)
        if bool_vrs:
            instance.setBoolean(bool_vrs, bool_vals)
        if str_vrs:
            instance.setString(str_vrs, str_vals)

    def _apply_input_starts(self) -> None:
        """Push initial input values from PortStates into the FMU."""
        # If PortStates contain initial values (via specs or pre-set), push them into the FMU
        init_vals = {
            name: in_port.get()
            for name, in_port in self.inputs.items()
            if in_port.get() is not None
        }
        if init_vals:
            self._set_inputs(init_vals, t=None, refresh_outputs=False)

    # ----------------------------------------------------------------------------
    # Parameter and Initial Condition Handling
    # ----------------------------------------------------------------------------
    def set_parameters(self, **parameters) -> None:
        """Set parameter values with validation and unit handling.

        Args:
            **parameters: Parameter name/value pairs.

        Raises:
            KeyError: If a parameter name is unknown.
            TypeError: If a value does not match the parameter type or unit.
        """
        for name, value in parameters.items():
            if name not in self.parameters:
                raise KeyError(
                    f"Unknown parameter '{name}' for component '{self.name}'. "
                    f"Available parameters: {list(self.parameters.keys())}"
                )
            self.parameters[name] = self._validate_parameter(name, value)

    def get_parameters(self, *names: str) -> dict[str, Any]:
        """Return parameter values, optionally limited to specific names.

        Args:
            *names: Optional parameter names to fetch.

        Raises:
            KeyError: If a requested parameter name is unknown.
        """
        if not names:
            return self.parameters.copy()

        result = {}
        for name in names:
            if name not in self.parameters:
                raise KeyError(
                    f"Unknown parameter '{name}' for component '{self.name}'. "
                    f"Available parameters: {list(self.parameters.keys())}"
                )
            result[name] = self.parameters[name]
        return result

    # ----------------------------------------------------------------------------
    # Input/output methods
    # ----------------------------------------------------------------------------
    def set_inputs(self, signals: dict[str, Any], t: float | None = None) -> None:
        """Set input port values and push them to the FMU.

        Args:
            signals: Mapping of input names to values.
            t: Optional timestamp to record with inputs.

        Raises:
            KeyError: If an input name is unknown.
            TypeError: If a value type does not match the port type.
            ValueError: If a REAL input is missing a value after unit conversion.
        """
        self._set_inputs(signals, t=t, refresh_outputs=True)

    def _set_inputs(
        self,
        signals: dict[str, Any],
        *,
        t: float | None,
        refresh_outputs: bool,
    ) -> None:
        """Write inputs, optionally refreshing direct-feedthrough outputs."""
        if not signals:
            return
        instance = self._require_instance()

        # Set inputs by batch per type
        real_vrs: list[int] = []
        real_vals: list[float] = []
        int_vrs: list[int] = []
        int_vals: list[int] = []
        bool_vrs: list[int] = []
        bool_vals: list[int] = []
        str_vrs: list[int] = []
        str_vals: list[str] = []

        for name, val in signals.items():
            if name not in self.inputs:
                raise KeyError(f"{self.name}: Unknown input '{name}")
            port_state = self.inputs[name]
            port_state.set(value=val, t=t)
            spec = port_state.spec
            vr_map = _in_vr_map_for_type(self, spec.type)
            if name not in vr_map:
                continue
            vr = vr_map[name]

            # Convert to raw value
            if spec.type == PortType.REAL:
                unit_str = str(spec.unit) if spec.unit is not None else None
                q = port_state.get(as_unit=unit_str)
                if q is None:
                    raise ValueError(f"{self.name}: REAL input '{name}' has no value")
                mag = float(q.magnitude) if isinstance(q, QuantityClass) else float(q)
                real_vrs.append(vr)
                real_vals.append(mag)
            elif spec.type == PortType.INT:
                if type(port_state.value) is not int:
                    raise TypeError(f"{self.name}: INT input '{name}' must be int")
                int_vrs.append(vr)
                int_vals.append(port_state.value)
            elif spec.type == PortType.BOOL:
                if not isinstance(port_state.value, bool):
                    raise TypeError(f"{self.name}: BOOL input '{name}' must be bool")
                bool_vrs.append(vr)
                bool_vals.append(1 if port_state.value else 0)
            elif spec.type == PortType.STRING:
                if not isinstance(port_state.value, str):
                    raise TypeError(f"{self.name}: STRING input '{name}' must be str")
                str_vrs.append(vr)
                str_vals.append(port_state.value)

        # Set the values by batch
        if real_vrs:
            instance.setReal(real_vrs, real_vals)
        if int_vrs:
            instance.setInteger(int_vrs, int_vals)
        if bool_vrs:
            instance.setBoolean(bool_vrs, bool_vals)
        if str_vrs:
            instance.setString(str_vrs, str_vals)

        if refresh_outputs:
            self._update_output_states(t=None)

    def get_outputs(self) -> dict[str, Any]:
        """Return current output values as a dict of name to value."""
        return {
            name: out_port.get()
            for name, out_port in self.outputs.items()
            if out_port.get() is not None
        }

    def _update_output_states(
        self, t: float | None = None, event_names: list[str] | None = None
    ) -> None:
        """Refresh output PortStates from the FMU instance.

        Args:
            t: Optional timestamp to record with outputs.
            event_names: Reserved for event-based updates (unused).
        """
        instance = self._require_instance()
        # For each base type, batch get and set into PortStates as Quantities (REAL) or raw types
        if self._vrs_out_real:
            vrs = list(self._vrs_out_real.values())
            vals = instance.getReal(vrs)
            for name, val in zip(self._vrs_out_real.keys(), vals):
                spec = self.output_specs[name]
                q = (val * to_pint_unit(spec.unit)) if spec.unit else val
                self.outputs[name].set(q, t=t)

        if self._vrs_out_int:
            vrs = list(self._vrs_out_int.values())
            vals = instance.getInteger(vrs)
            for name, val in zip(self._vrs_out_int.keys(), vals):
                self.outputs[name].set(int(val), t=t)

        if self._vrs_out_bool:
            vrs = list(self._vrs_out_bool.values())
            vals = instance.getBoolean(vrs)
            for name, val in zip(self._vrs_out_bool.keys(), vals):
                self.outputs[name].set(bool(val), t=t)

        if self._vrs_out_str:
            vrs = list(self._vrs_out_str.values())
            vals = instance.getString(vrs)
            for name, val in zip(self._vrs_out_str.keys(), vals):
                self.outputs[name].set(str(val), t=t)

    # ----------------------------------------------------------------------------
    # Time stepping method
    # ----------------------------------------------------------------------------
    def _do_step_internal(self, t: float, dt: float) -> None:
        """Perform a single time step in the FMU.

        Args:
            t: Current communication point.
            dt: Communication step size.
        """
        self._require_instance().doStep(currentCommunicationPoint=t, communicationStepSize=dt)

    # ----------------------------------------------------------------------------
    # State methods for setting and getting simulation state
    # ----------------------------------------------------------------------------
    def set_state(self, state: dict[str, Any], t: float) -> None:
        """Restore FMU state from a serialized variable dictionary.

        Args:
            state: Mapping of variable names to stored attributes/values.
            t: Time to reinitialize the FMU at.
        """
        params = {}
        inputs = {}
        for var_name, attr in state.items():
            if var_name in self.parameters:
                params[var_name] = attr["value"]
            if var_name in self.inputs:
                inputs[var_name] = attr["value"]

        self.set_parameters(**params)
        for name, value in inputs.items():
            self.inputs[name].set(value, t=t)
        self.reinitialize_instance(t)

        self.t = t
        self._update_output_states(t)

    def get_state(self) -> dict[str, dict[str, Any]]:
        """Return FMU variables as a serialized dictionary.

        The dictionary includes variables that are not fixed and not local,
        along with their units and current values pulled from the FMU instance.

        Returns:
            Dict mapping variable names to unit/value attributes.
        """
        instance = self._require_instance()
        state: dict[str, dict[str, Any]] = {}
        for var in self._md.modelVariables:
            if var.variability == "fixed" or var.causality == "local":
                continue
            name = var.name
            state[name] = {}
            state[name]["unit"] = var.unit
            vr = var.valueReference
            if var.type == "Real":
                val = instance.getReal([vr])[0]
                # if unit:
                #     val = val * ureg(unit)
                state[name]["value"] = val
            elif var.type == "Integer":
                val = instance.getInteger([vr])[0]
                state[name]["value"] = val
            elif var.type == "Boolean":
                val = instance.getBoolean([vr])[0]
                state[name]["value"] = bool(val)
            elif var.type == "String":
                val = instance.getString([vr])[0]
                state[name]["value"] = val
        self.state = state
        return self.state

    # ----------------------------------------------------------------------------
    # Evaluate outputs without time step for direct feedthrough
    # ----------------------------------------------------------------------------
    def evaluate_outputs(self, inputs: dict[str, Any], t: float | None = None) -> dict[str, Any]:
        """Evaluate outputs for a given input set without advancing time.

        Args:
            inputs: Input values to apply.
            t: Optional time to use for evaluation.

        Returns:
            Mapping of output names to raw (unitless) values.
        """
        # 1) Apply inputs without touching histories
        self.set_inputs(inputs, t=None)

        # 2) Do a zero-time step to update outputs
        step_time = self.t if t is None else t
        self._do_step_internal(t=step_time, dt=0.0)

        # 3) Read outputs
        self._update_output_states(t=None)

        # 4) Return outputs as raw values (Quantities converted to magnitudes)
        outputs = self.get_outputs()
        for key, value in outputs.items():
            value = value.magnitude if isinstance(value, QuantityClass) else value
            outputs[key] = value
        return outputs

    # ----------------------------------------------------------------------------
    # Reset method
    # ----------------------------------------------------------------------------
    def reset(self) -> None:
        """Reset the component, releasing the native instance where safe.

        The instance is terminated and freed when :attr:`release_policy` allows
        it, and merely dropped when it does not, because freeing a defective
        CVODE export corrupts the heap (issues.md HARD-05).

        The extraction directory is kept either way. It is shared through the
        module-level cache, so removing it here would pull it out from under
        every other component using the same archive (issues.md HARD-07).

        After reset the component can be reinitialized via ``initialize()``,
        which reuses the cached extraction and instantiates anew.
        """
        cleanup_error: Exception | None = None
        try:
            self._release_instance()
        except Exception as exc:
            cleanup_error = exc

        # Clear runtime state (including _is_initialized via super) even when
        # native cleanup reported an error, so callers never observe a
        # half-reset component.
        super().reset()
        self.inputs.clear()
        self.outputs.clear()
        self.parameters.clear()
        self.parameters = self.get_default_parameters()
        if cleanup_error is not None:
            raise cleanup_error

    def soft_reset(self, t0: float = 0.0) -> None:
        """Reset the FMU to initial state without releasing the instance.

        Uses FMI ``reset()`` to return to the instantiated state, then
        reinitializes with parameter and input starts.

        Args:
            t0: New start time for the simulation.

        Raises:
            RuntimeError: If the FMU is not initialized, or if this archive
                cannot survive ``fmi2Reset``. That call fails on exactly the
                exports that cannot be freed, so the release policy governs it
                too (issues.md HARD-05). Use ``reinitialize_instance()``
                instead, which rebuilds the instance rather than resetting it.
        """
        if self._instance is None:
            raise RuntimeError(f"{self.name}: Cannot soft_reset - FMU not initialized")
        if not self.release_policy.releasable:
            raise RuntimeError(
                f"{self.name}: fmi2Reset is unsafe for this FMU - "
                f"{self.release_policy.reason}. Use reinitialize_instance() instead."
            )

        # FMI reset() returns to Instantiated state
        self._instance.reset()

        # Must go through full initialization sequence
        self._instance.setupExperiment(startTime=t0)
        self._instance.enterInitializationMode()
        self._apply_parameters_starts()
        self._apply_input_starts()
        self._instance.exitInitializationMode()

        # Clear and update state
        self.history.clear()
        self.t = t0
        self._update_output_states(t=t0)
        self._record_outputs(t0)

    def _validate_parameter(self, name: str, value: Any) -> QuantityType | float | int | bool | str:
        """Validate and normalize a parameter value.

        Args:
            name: Parameter name.
            value: Proposed parameter value.

        Returns:
            Validated value, converted to the expected type/unit.

        Raises:
            TypeError: If the value is incompatible with the parameter type or unit.
        """
        model_var = self._md_vars.get(name)
        if model_var is None:
            raise KeyError(f"{self.name}: Unknown parameter '{name}'")
        type = _port_type_from_var(model_var)
        unit = model_var.unit
        if type == PortType.REAL:
            if not isinstance(value, (float, int, QuantityClass)):
                raise TypeError(f"{self.name}: Parameter '{name}' must be float.")
            if unit:
                if isinstance(value, QuantityClass):
                    unit = to_pint_unit(unit)
                    if value.is_compatible_with(unit):
                        return cast(QuantityType, value.to(unit))
                    else:
                        raise TypeError(
                            f"{self.name}: Parameter '{name}' must have unit compatible with '{unit}'."
                        )
                else:
                    q = float(value) * to_pint_unit(unit)
                    return cast(QuantityType, q)
            return float(value)
        elif type == PortType.INT:
            if not isinstance(value, int):
                raise TypeError(f"{self.name}: Parameter '{name}' must be int.")
            return int(value)
        elif type == PortType.BOOL:
            if not isinstance(value, bool):
                raise TypeError(f"{self.name}: Parameter '{name}' must be bool.")
            return bool(value)
        elif type == PortType.STRING:
            if not isinstance(value, str):
                raise TypeError(f"{self.name}: Parameter '{name}' must be str.")
            return str(value)
        raise NotImplementedError(f"{self.name}: Unsupported parameter type for '{name}'.")


# ----------------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------------
def _port_type_from_var(var: ScalarVariable) -> PortType:
    """Determine PortType from ScalarVariable type.

    Args:
        var (ScalarVariable): The model variable to determine the port type for.

    Returns:
        PortType: The corresponding PortType.

    Raises:
        NotImplementedError: If the variable type is unsupported.
    """
    if var._python_type is float:
        return PortType.REAL
    elif var._python_type is int:
        return PortType.INT
    elif var._python_type is bool:
        return PortType.BOOL
    elif var._python_type is str:
        return PortType.STRING
    else:
        raise NotImplementedError(
            f"Unsupported variable type '{var._python_type}' for variable '{var.name}'."
        )


def _convert_start_value(
    start: str | None, port_type: PortType, unit: str | None
) -> QuantityType | float | int | bool | str | None:
    """Convert start value string to appropriate type based on PortType and unit.

    Args:
        start (str | None): The start value as a string.
        port_type (PortType): The type of the port.
        unit (str | None): The unit of the port, if applicable.

    Returns:
        Union[float, int, bool, str, None]: The converted start value in the appropriate type.
    """
    if start is None:
        return None
    if port_type == PortType.REAL:
        val = float(start)
        if unit:
            val = val * to_pint_unit(unit)
        return val
    elif port_type == PortType.INT:
        return int(start)
    elif port_type == PortType.BOOL:
        return start.lower() in ("true", "1")
    elif port_type == PortType.STRING:
        return str(start)
    else:
        return None


def _in_vr_map_for_type(comp: FMUComponent, pt: PortType) -> dict[str, int]:
    """Return the input value-reference map for a port type."""
    return (
        comp._vrs_in_real
        if pt == PortType.REAL
        else comp._vrs_in_int
        if pt == PortType.INT
        else comp._vrs_in_bool
        if pt == PortType.BOOL
        else comp._vrs_in_str
    )
