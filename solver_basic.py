# solver_basic.py
# Basic backtracking Sudoku solver.
# Picks the NEXT empty cell in row-major order (left to right, top to bottom).
# Search node = one call to the recursive function bt().

def solve_basic(puzzle):
    grid = [row[:] for row in puzzle]          # copy so the original clues are never changed

    # Sets of values already used in each row, column, and 3x3 box
    rows = [set() for _ in range(9)]
    cols = [set() for _ in range(9)]
    boxes = [set() for _ in range(9)]
    empties = []                                # list of (row, col) cells that are 0

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

    def bt(k):                                  # k = index of the next empty cell to fill
        nonlocal nodes
        nodes += 1                              # count this call as one search node
        if k == len(empties):
            return True                         # all empty cells are filled -> solved
        r, c = empties[k]
        b = (r // 3) * 3 + c // 3
        for v in range(1, 10):
            if v not in rows[r] and v not in cols[c] and v not in boxes[b]:
                grid[r][c] = v                  # place
                rows[r].add(v); cols[c].add(v); boxes[b].add(v)
                if bt(k + 1):
                    return True
                grid[r][c] = 0                  # undo (backtrack)
                rows[r].remove(v); cols[c].remove(v); boxes[b].remove(v)
        return False                            # no value worked -> dead end

    solved = bt(0)
    return (grid if solved else None), nodes
