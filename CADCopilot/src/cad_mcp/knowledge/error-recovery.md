# Error recovery (for CADCopilot)

When a tool fails, call `get_last_error`, then map the symptom:

| Symptom | Likely cause | Fix |
|---|---|---|
| "No closed profile" / AddForSolid Count 0 | sketch loop not closed or self-intersecting | close the loop (set `closed=true` on add_line; check coincident endpoints); for revolve keep the axis line as construction so it isn't part of the profile |
| Hole feature created but body unchanged (health error) | drilled away from material | the tool auto-retries the opposite direction; if still failing, the center point isn't over the body — re-check coords with `list_faces` centroid |
| Pattern E_FAIL (`-2147467259`) | an instance lands off the body (identical compute) | move the seed so all instances stay on the body, reduce count/spacing, or pattern after the body is large enough |
| Revolve E_INVALIDARG (`-2147024809`) | axis is a work axis perpendicular to / not in the sketch plane | use `add_axis_line` to draw a construction centerline in the profile sketch and pass its name as `axis` |
| Fillet/chamfer fails on an edge | edge was consumed/changed by a prior feature | re-run `list_edges` to get fresh names and retarget |
| Boolean leaves 2 bodies | wrong target/tool or non-touching bodies | ensure bodies overlap; `union` keeps target, consumes tools |
| Non-manifold / STL won't slice | open bodies or overlapping un-unioned solids | union overlapping bodies, shell to a real wall, re-export |
| RPC server unavailable / disconnected | Inventor closed or crashed | reconnect via `connect_cad`; if it crashed, the doc may be lost — rebuild from the scratchpad plan |
| "No active document" | no part/assembly open | `new_document('part'|'assembly', ...)` first |

General loop: after every 3–5 operations, `screenshot` + a `list_*`/`measure` to confirm
intent before continuing. Keep the build plan in the scratchpad so a crash is recoverable.
