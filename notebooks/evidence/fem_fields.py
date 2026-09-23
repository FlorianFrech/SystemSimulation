"""Field frames of the FEM pendulum, for the model-artifact figures of 03_switching.

The FEM records a displacement frame and a von Mises frame at the end of every
accepted sub-step, and ``FEMComponent.history_times`` stamps each one. This
module turns a finished run into plain arrays, so the figures rebuild from a
cache and never from a live solver (figure_style.md section 10).

Two frames are selected, both on the committed trajectory.

* **Impact.** The first dispatched wall contact that the FEM resolved, and in
  it the frame of largest von Mises stress. The contact instant itself is the
  wrong frame, because the gap has only just closed there and the field is
  still near zero. The window runs from that contact to the next dispatched
  contact or to the end of the FEM interval, whichever comes first.
* **Handover.** The FEM -> rigid switch that discarded the most elastic strain
  energy, at the frame stamped with the switch instant. That frame is the
  outgoing state the transfer read.

Fields are evaluated per triangle, at its three corners and its three edge
midpoints, and every triangle is drawn as four linear sub-triangles. The
elements are of order two, so the corners alone would draw a quadratic field
as a linear one. The six points are reference-element points mapped through
NGSolve's own element geometry (``Mesh.MapToAllElements``). A midpoint on a
curved edge therefore lies on the curve, where a midpoint of the straight chord
would fall into the hole, and every value is read inside its own element, so
no point picks up the value of the other body.

The module reads private attributes of ``FEMPendulum`` (``_mesh``, ``_V``,
``_V_vm`` and the two history grid functions). It never writes to the model.
"""

from __future__ import annotations

from typing import Any

import numpy as np

# The accepted advance ends on the switch instant up to floating-point
# round-off of T_k + (t_e - T_k). Anything larger means the frame is not the
# state the transfer read.
SWITCH_TIME_TOL_S = 1e-9
# Boundaries without a name of their own are drawn by the mesh outline.
_UNNAMED_BOUNDARY = "default"
# Per triangle: corners 0, 1, 2, then the midpoints of edges 0-1, 1-2, 2-0.
# SUBTRIANGLES splits it into four linear pieces over those six points.
POINTS_PER_TRIANGLE = 6
SUBTRIANGLES = ((0, 3, 5), (3, 1, 4), (5, 4, 2), (3, 4, 5))
# The same six points on NGSolve's reference triangle, whose vertices 0, 1, 2
# sit at (1, 0), (0, 1), (0, 0). mesh_points checks that correspondence.
_REFERENCE_POINTS = ((1.0, 0.0), (0.0, 1.0), (0.0, 0.0), (0.5, 0.5), (0.0, 0.5), (0.5, 0.0))


# ---------------------------------------------------------------------------
# Frames and their times
# ---------------------------------------------------------------------------
def frame_times(fem) -> np.ndarray:
    """Time of every recorded field frame, checked against the frame counts."""
    times = np.asarray(fem.history_times, dtype=float)
    for name in ("_gf_u_history", "_gf_von_mises_history"):
        n_frames = len(getattr(fem, name).vecs)
        if n_frames != len(times):
            raise RuntimeError(
                f"{name} holds {n_frames} frames but {len(times)} frame times were "
                "recorded. The field history and its time stamps are out of step."
            )
    if len(times) > 1 and np.any(np.diff(times) <= 0.0):
        raise RuntimeError("Field frame times are not strictly increasing.")
    return times


def peak_von_mises(fem) -> np.ndarray:
    """Largest vertex value of the von Mises field in every frame, in Pa.

    The first ``nv`` coefficients of an NGSolve H1 function are its vertex
    values, so this reads the stored vectors without evaluating anything.
    """
    nv = fem._mesh.nv
    return np.array(
        [float(np.max(vec.FV().NumPy()[:nv])) for vec in fem._gf_von_mises_history.vecs]
    )


def select_impact_frame(
    times: np.ndarray,
    peaks: np.ndarray,
    contact_times,
    intervals,
) -> dict[str, Any]:
    """Peak-stress frame of the first contact the FEM resolved.

    ``intervals`` are ``(start, stop, mode)`` triples as returned by
    ``evidence.mode_intervals``.
    """
    contacts = np.sort(np.asarray(contact_times, dtype=float))
    fem_intervals = [(float(a), float(b)) for a, b, mode in intervals if mode == "FEM"]

    for index, t_contact in enumerate(contacts):
        holding = [(a, b) for a, b in fem_intervals if a <= t_contact <= b]
        if holding:
            break
    else:
        raise RuntimeError("No dispatched wall contact falls inside a FEM interval.")

    stops = [holding[0][1]]
    if index + 1 < len(contacts):
        stops.append(float(contacts[index + 1]))
    t_stop = min(stops)

    window = np.flatnonzero((times >= t_contact) & (times <= t_stop))
    if window.size == 0:
        raise RuntimeError(
            f"No field frame between the contact at {t_contact:.6f} s and {t_stop:.6f} s."
        )
    frame = int(window[np.argmax(peaks[window])])
    return {
        "frame": frame,
        "t_frame_s": float(times[frame]),
        "t_contact_s": float(t_contact),
        "contact_index": int(index),
        "window_s": [float(t_contact), float(t_stop)],
        "peak_von_mises_pa": float(peaks[frame]),
    }


def select_handover_frame(times: np.ndarray, peaks: np.ndarray, transfers) -> dict[str, Any]:
    """Outgoing FEM state of the switch that discarded the most strain energy.

    ``transfers`` is the per-switch table 03_switching builds, with the columns
    ``t``, ``from``, ``to`` and ``elastic_lost``.
    """
    outgoing = transfers[transfers["from"] == "FEM"]
    if outgoing.empty:
        raise RuntimeError("The run has no switch out of the FEM.")
    label = outgoing["elastic_lost"].idxmax()
    row = outgoing.loc[label]
    t_switch = float(row["t"])

    frame = int(np.argmin(np.abs(times - t_switch)))
    offset = float(times[frame] - t_switch)
    if abs(offset) > SWITCH_TIME_TOL_S:
        raise RuntimeError(
            f"The nearest field frame is {offset:+.3e} s from the switch at "
            f"{t_switch:.9f} s, so it is not the state the transfer read."
        )
    return {
        "frame": frame,
        "t_frame_s": float(times[frame]),
        "t_switch_s": t_switch,
        "switch_index": int(transfers.index.get_loc(label)),
        "direction": f"{row['from']} -> {row['to']}",
        "elastic_lost_j": float(row["elastic_lost"]),
        "peak_von_mises_pa": float(peaks[frame]),
    }


# ---------------------------------------------------------------------------
# Geometry and fields
# ---------------------------------------------------------------------------
def mesh_points(mesh) -> dict[str, Any]:
    """Reference triangles as independent points, with the named boundaries.

    Returns ``points`` of shape (n_triangles, 6, 2), three corners then three
    edge midpoints on the curved element geometry, the material of every
    triangle, and for every named boundary its segments as pairs of flat
    corner indices into ``points.reshape(-1, 2)``. A segment's corners belong to
    the one triangle that holds that boundary edge, so a deformed boundary
    moves with its own body.
    """
    from ngsolve import BND, VOL

    coords = np.array([vertex.point[:2] for vertex in mesh.vertices], dtype=float)
    triangles, materials = [], []
    for element in mesh.Elements(VOL):
        vertices = [v.nr for v in element.vertices]
        if len(vertices) != 3:
            raise ValueError("mesh_points expects a triangle mesh.")
        triangles.append(vertices)
        materials.append(element.mat)
    triangles = np.asarray(triangles, dtype=int)
    points = _mapped_points(mesh)
    mismatch = float(np.max(np.abs(points[:, :3] - coords[triangles])))
    if mismatch > 1e-12:
        raise RuntimeError(
            f"Mapped reference corners miss the element vertices by {mismatch:.2e} m. "
            "The reference-triangle vertex order assumed here does not hold."
        )

    edge_owner: dict[frozenset, list[int]] = {}
    for tri_index, (a, b, c) in enumerate(triangles):
        for p, q in ((a, b), (b, c), (c, a)):
            edge_owner.setdefault(frozenset((p, q)), []).append(tri_index)

    segments: dict[str, list[tuple[int, int]]] = {}
    for element in mesh.Elements(BND):
        if element.mat == _UNNAMED_BOUNDARY:
            continue
        a, b = (v.nr for v in element.vertices)
        owners = edge_owner.get(frozenset((a, b)), [])
        if len(owners) != 1:
            raise RuntimeError(
                f"Boundary edge {a}-{b} of '{element.mat}' borders {len(owners)} triangles."
            )
        tri_index = owners[0]
        local = list(triangles[tri_index])
        base = POINTS_PER_TRIANGLE * tri_index
        segments.setdefault(element.mat, []).append(
            (base + local.index(a), base + local.index(b))
        )

    return {
        "points": points,
        "materials": np.asarray(materials, dtype=object),
        "segments": {name: np.asarray(pairs, dtype=int) for name, pairs in segments.items()},
    }


def _mapped_integration_points(mesh):
    from ngsolve import VOL, IntegrationRule

    rule = IntegrationRule(points=list(_REFERENCE_POINTS), weights=[0.0] * POINTS_PER_TRIANGLE)
    return mesh.MapToAllElements(rule, VOL)


def _mapped_points(mesh) -> np.ndarray:
    from ngsolve import x, y

    mips = _mapped_integration_points(mesh)
    xs = np.asarray(x(mips), dtype=float).ravel()
    ys = np.asarray(y(mips), dtype=float).ravel()
    return np.stack([xs, ys], axis=1).reshape(mesh.ne, POINTS_PER_TRIANGLE, 2)


def frame_fields(fem, frame: int, geometry: dict[str, Any]) -> dict[str, np.ndarray]:
    """Displacement in m and von Mises stress in Pa at every point of one frame."""
    from ngsolve import GridFunction

    u = GridFunction(fem._V)
    u.vec.data = fem._gf_u_history.vecs[frame]
    von_mises = GridFunction(fem._V_vm)
    von_mises.vec.data = fem._gf_von_mises_history.vecs[frame]

    points = _mapped_integration_points(fem._mesh)
    shape = geometry["points"].shape[:2]
    return {
        "u": np.asarray(u(points), dtype=float).reshape(*shape, 2),
        "von_mises": np.asarray(von_mises(points), dtype=float).reshape(shape),
    }


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
FRAME_KEYS = ("impact", "handover")


def pack_fields(geometry, frames, meta) -> dict[str, np.ndarray]:
    """Flatten geometry, the two frames, and their selection records for ``np.savez``."""
    payload = {
        "points": geometry["points"],
        "materials": geometry["materials"],
        "segment_names": np.asarray(sorted(geometry["segments"]), dtype=object),
    }
    for name, pairs in geometry["segments"].items():
        payload[f"segment_{name}"] = pairs
    for key in FRAME_KEYS:
        payload[f"{key}_u"] = frames[key]["u"]
        payload[f"{key}_von_mises"] = frames[key]["von_mises"]
        for field, value in meta[key].items():
            payload[f"{key}_meta_{field}"] = np.asarray(value, dtype=object)
    return payload


def unpack_fields(store) -> tuple[dict, dict, dict]:
    """Inverse of :func:`pack_fields` for an ``np.load(..., allow_pickle=True)``."""
    names = [str(n) for n in store["segment_names"]]
    geometry = {
        "points": store["points"],
        "materials": store["materials"],
        "segments": {name: store[f"segment_{name}"] for name in names},
    }
    frames, meta = {}, {}
    for key in FRAME_KEYS:
        frames[key] = {"u": store[f"{key}_u"], "von_mises": store[f"{key}_von_mises"]}
        prefix = f"{key}_meta_"
        meta[key] = {
            name[len(prefix):]: store[name].item() if store[name].shape == () else store[name].tolist()
            for name in store.files
            if name.startswith(prefix)
        }
    return geometry, frames, meta
