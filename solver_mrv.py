# solver_mrv.py
# Backtracking Sudoku solver with the Minimum Remaining Values (MRV) heuristic.
# On every call it picks the empty cell with the FEWEST legal values.
# Search node = one call to the recursive function bt()  (same definition as basic).

def solve_mrv(puzzle):
    grid = [row[:] for row in puzzle]          # copy so the original clues are never changed

    rows = [set() for _ in range(9)]
    cols = [set() for _ in range(9)]
    boxes = [set() for _ in range(9)]
    empties = []

    for r in range(9):
        for c in range(9):
            v = grid[r][c]
            if v == 0:
                empties.append((r, c))
            else:
                rows[r].add(v)
                cols[c].add(v)
                boxes[(r // 3) * 3 + c // 3].add(v)

    nodes = 0

    def bt():
        nonlocal nodes
        nodes += 1                              # count this call as one search node

        # MRV step: scan every still-empty cell and keep the one with fewest candidates
        best, best_cands = None, None
        for (r, c) in empties:
            if grid[r][c] != 0:
                continue                        # already filled in this branch
            b = (r // 3) * 3 + c // 3
            cands = [v for v in range(1, 10)
                     if v not in rows[r] and v not in cols[c] and v not in boxes[b]]
            if best is None or len(cands) < len(best_cands):
                best, best_cands = (r, c), cands
                if len(cands) == 0:
                    break                       # a cell with 0 options -> this branch is dead

        if best is None:
            return True                         # no empty cells left -> solved

        r, c = best
        b = (r // 3) * 3 + c // 3
        for v in best_cands:                    # if best_cands is empty, loop is skipped -> False
            grid[r][c] = v                      # place
            rows[r].add(v); cols[c].add(v); boxes[b].add(v)
            if bt():
                return True
            grid[r][c] = 0                      # undo (backtrack)
            rows[r].remove(v); cols[c].remove(v); boxes[b].remove(v)
        return False

    solved = bt()
    return (grid if solved else None), nodes
