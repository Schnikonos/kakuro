from collections import defaultdict
from typing import Dict, List

from basic.cell import Cell, CellType, SubCell, CellData, CellDirection

sum_map: Dict[int, Dict[int, List[List[int]]]] = defaultdict(dict)


def parser(filename: str) -> CellData:
    cell_data = CellData()
    col_list: Dict[int, Cell] = {}
    line_list: Dict[int, Cell] = {}
    with open(filename) as f:
        lines = f.readlines()
        i = 0
        for line in lines:
            i += 1
            j = 0
            for c in line.split(','):
                j += 1
                cell = Cell(c, i, j)
                handle_cell(cell, i, j, cell_data, col_list, line_list)

    for cell in cell_data.instr:
        _fill_possibilities(cell.right, CellDirection.RIGHT)
        _fill_possibilities(cell.down, CellDirection.DOWN)

    return cell_data


def handle_cell(cell: Cell, i: int, j: int, cell_data: CellData, col_list: Dict[int, Cell], line_list: Dict[int, Cell]):
    cell_data.cell_map[i][j] = cell
    if cell.type == CellType.INSTRUCTION:
        cell_data.instr.append(cell)
        col_list[j] = cell if cell.down else None
        line_list[i] = cell if cell.right else None
    else:
        col_instr = col_list.get(j)
        line_instr = line_list.get(i)
        if not (col_instr or line_instr) and cell.type == CellType.TARGET:
            cell.type = CellType.EMPTY
        # if (col_instr or line_instr) and cell.type == CellType.TARGET:
        #     cell_data.cells.append(cell)
        if col_instr and col_instr.down:
            col_instr.down.associated_cells.append(cell)
            cell.down.associated_cells.append(col_instr)
        if line_instr and line_instr.right:
            line_instr.right.associated_cells.append(cell)
            cell.right.associated_cells.append(line_instr)


def _fill_possibilities(instr: SubCell, direction: CellDirection):
    if instr is None:
        return

    nb = len(instr.associated_cells)
    sums = _get_possibilities(nb, instr.fixed_value)

    fixed_values = set(f.get_sub_cell(direction).fixed_value for f in instr.associated_cells if f.type == CellType.FIXED)
    filtered_sums = [s for s in sums if set(s) & fixed_values] if len(fixed_values) > 0 else [s for s in sums]

    instr.possible_values = [[j for j in i] for i in filtered_sums]
    instr.build_set()
    for cell in instr.associated_cells:
        sub_cell = cell.get_sub_cell(direction)
        if cell.type == CellType.FIXED:
            sub_cell.build_set()
            continue
        sub_cell = cell.get_sub_cell(direction)
        sub_cell.possible_values = [[j for j in i if j not in fixed_values] for i in filtered_sums]
        sub_cell.build_set()


def _get_possibilities(nb: int, target: int) -> List[List[int]]:
    res_list = sum_map[target].get(nb)
    if res_list:
        return res_list
    sums = _get_sums(nb, target, [])
    sum_map[target][nb] = sums
    return sums


def _get_sums(nb: int, target: int, res: list[int]) -> List[List[int]]:
    first = res[-1] + 1 if len(res) > 0 else 1
    if len(res) == nb:
        return [res] if sum(res) == target else []
    if first > 9 or len(res) > nb or sum(res) > target:
        return []

    possibilities = [res + [i] for i in range(first, 10)]
    sums_possibilities = [_get_sums(nb, target, i) for i in possibilities]
    return [i for j in sums_possibilities for i in j]
