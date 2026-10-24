"""Experimental strict output selection AFTER shared Plan/Benchmark hoisting.

The old strict branch tree failed on mixed-period Share matrices. This changed
dependency graph must pass full native mixed matrices and Desktop separately;
it does not inherit the eager workaround's acceptance.
"""
import cells
import prepared


def patch(database):
    fixed = cells.patch(database)
    current = prepared.adapter.planning.measures(fixed)
    for name in ('N Summary Cell', 'N Headline Cell'):
        body = current[name]['expression']
        if 'IF.EAGER(' not in body:
            raise ValueError('Unknown shared-cell expression')
        current[name]['expression'] = body.replace('IF.EAGER(', 'IF(')
    return fixed
