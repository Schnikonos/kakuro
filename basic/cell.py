from collections import defaultdict
from enum import Enum
from functools import reduce
from typing import Optional, List, Set, Dict

activate_debug = False
activate_map_print = False


class CellType(Enum):
    INSTRUCTION = 1
    TARGET = 2
    FIXED = 3
    EMPTY = 4


class CellDirection(Enum):
    DOWN = 1
    RIGHT = 2


class Position(object):
    def __init__(self, x: int, y: int):
        self.x: int = x
        self.y: int = y

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y


class SubCell(object):
    def __init__(self, position: Position, value: Optional[int] = None):
        self.fixed_value = value
        self.possible_values: List[List[int]] = [] if not value else [[value]]
        self.possible_values_set: Set[int] = set() if not value else {value}  # to be computed each time possible_values changes
        self.associated_cells: List[Cell] = []
        self.possible_values_backup: List[List[List[int]]] = []
        self.old_possible_values_backup: List[List[List[int]]] = []
        self.position = position

    @property
    def possible_values(self):
        return self._possible_values

    @possible_values.setter
    def possible_values(self, values: List[List[int]]):
        self._possible_values = values

    def has_one_value(self):
        return len(self.possible_values_set) == 1

    def build_set(self):
        self.possible_values_set = set(i for j in self.possible_values for i in j)

    def print_debug(self) -> str:
        a = [','.join([str(j) for j in i]) for i in self.possible_values]
        return ' ; '.join([','.join([str(j) for j in i]) for i in self.possible_values])


def sub_cell_has_one_value(down: SubCell, right: SubCell):
    return (down is None or down.has_one_value()) and (right is None or right.has_one_value())


def sub_cell_value(down: SubCell, right: SubCell):
    if sub_cell_has_one_value(down, right):
        return list(down.possible_values_set)[0] if down is not None else list(right.possible_values_set)[0]
    return 'x'


class Cell(object):
    def __init__(self, value: str, x: int, y: int):
        value = value.strip()
        self.type: CellType = get_cell_type(value)
        self.position: Position = Position(x, y)
        self.right = None
        self.down = None
        if self.type == CellType.INSTRUCTION:
            value_list = value.split(';')
            for value in value_list:
                if value.startswith('d'):
                    self.right: SubCell = SubCell(self.position, int(value[1:]))
                if value.startswith('b'):
                    self.down: SubCell = SubCell(self.position, int(value[1:]))
        else:
            value_int = int(value) if value != '' and value != 'x' else None
            self.down: SubCell = SubCell(self.position, value_int)
            self.right: SubCell = SubCell(self.position, value_int)

    def __str__(self):
        type_cell = 'I' if self.type == CellType.INSTRUCTION else 'T' if self.type == CellType.TARGET else 'F'
        if self.type == CellType.INSTRUCTION:
            down = f'D{self.down.fixed_value}' if self.down else None
            right = f'R{self.right.fixed_value}' if self.right else None
            return f'{type_cell}-' + ','.join([i for i in [down, right] if i is not None])
        else:
            return f'{type_cell}-' + sub_cell_value(self.down, self.right)

    def __eq__(self, other):
        return self.position == other.position

    def get_sub_cell(self, direction: CellDirection) -> SubCell:
        return self.right if direction == CellDirection.RIGHT else self.down

    def has_one_value(self) -> bool:
        return sub_cell_has_one_value(self.down, self.right)

    def build_set(self):
        if self.down:
            self.down.build_set()
        if self.right:
            self.right.build_set()

    def print_debug(self, label: str) -> None:
        if not activate_debug:
            return
        down = 'None' if not self.down else self.down.print_debug()
        right = 'None' if not self.right else self.right.print_debug()
        print(f'**** {label} [{self.position.x},{self.position.y}] - {down} / {right}')


class CellData(object):
    def __init__(self):
        self.instr: List[Cell] = []
        self.cell_map: Dict[int, Dict[int, Cell]] = defaultdict(dict)
        self.failed_branch = 0
        self.branch_count = 0
        self.active_branch = 0

    def a_intersection_internal(self) -> bool:
        cells = get_cells(self.cell_map, cell_filter_target_not_unique)
        list_bool = [_a_intersection_internal(cell) for cell in cells]
        return True in list_bool

    def b_intersection_target_instruction(self) -> bool:
        list_bool = [_b_intersection_target_instruction(instr) for instr in self.instr]
        return True in list_bool

    def c_remove_value_from_lines(self) -> bool:
        cells = get_cells(self.cell_map, cell_filter_target)
        list_bool = [_c_remove_value_from_lines(cell) for cell in cells]
        return True in list_bool

    def d_remove_empty_possibility(self) -> bool:
        cells = get_cells(self.cell_map, cell_filter_target)
        list_bool = [_d_remove_empty_possibility(cell) for cell in cells]
        return True in list_bool

    def e_restore_from_backup(self) -> bool:
        cells = get_cells(self.cell_map, cell_filter_target_not_unique)
        for cell in cells:
            if (cell.down and len(cell.down.possible_values_set) == 0) or (cell.right and len(cell.right.possible_values_set) == 0):
                _e_restore_from_backup(self)
                return True

        for cell in self.instr:
            if (cell.down and len(cell.down.possible_values_set) == 0) or (cell.right and len(cell.right.possible_values_set) == 0):
                _e_restore_from_backup(self)
                return True

        return False

    def create_branches(self):
        print('############ CREATE BRANCH ! ############')
        _branch_creation(self)
        self.active_branch += 1

    def is_invalid(self):
        for instr in self.instr:
            if _is_instr_invalid(instr.down) or _is_instr_invalid(instr.right):
                return True
        return False

    def print_res(self):
        print(f'### Res: NbBranch=[{self.branch_count}] - triedBranch=[{self.failed_branch}]')
        for i in range(1, len(self.cell_map) + 1):
            line_print = []
            for j in range(1, len(self.cell_map[i]) + 1):
                cell = self.cell_map[i][j]
                if cell.type == CellType.INSTRUCTION:
                    line_print.append('I')
                else:
                    line_print.append(str(sub_cell_value(cell.down, cell.right)))
            print(' '.join(line_print))

    def print_investigation(self, label):
        if not activate_map_print:
            return
        print(f'################# INVESTIGATION - START [{label}] ###################')
        print('## Cells: ', ' '.join([f'[{c.position.x}-{c.position.y}]' for c in get_cells(self.cell_map, filter_cell=cell_filter_target_not_unique)]))
        print('## Instructions:')
        for i in self.instr:
            if i.down:
                print(f'  - [{i.position.x}-{i.position.y}] Down set=[{','.join(list(str(x) for x in i.down.possible_values_set))}] Values=[{' ; '.join([','.join(str(x) for x in p) for p in i.down.possible_values])}]')
            if i.right:
                print(f'  - [{i.position.x}-{i.position.y}] Right set=[{','.join(list(str(x) for x in i.right.possible_values_set))}] Values=[{' ; '.join([','.join(str(x) for x in p) for p in i.right.possible_values])}]')
        print('## Cells:')
        for x in range(1, len(self.cell_map) + 1):
            for y in range(1, len(self.cell_map[x]) + 1):
                c = self.cell_map[x][y]
                if c.type != CellType.TARGET:
                    continue
                if c.down:
                    print(f'  - [{c.position.x}-{c.position.y}] Active=[{1 if c in c.has_one_value() else 0}] Down set=[{','.join(list(str(x) for x in c.down.possible_values_set))}] Values=[{' ; '.join([','.join(str(x) for x in p) for p in c.down.possible_values])}]')
                if c.right:
                    print(f'  - [{c.position.x}-{c.position.y}] Active=[{1 if c in c.has_one_value() else 0}] Right set=[{','.join(list(str(x) for x in c.right.possible_values_set))}] Values=[{' ; '.join([','.join(str(x) for x in p) for p in c.right.possible_values])}]')
        print(f'################# INVESTIGATION - END   [{label}] ###################')


def get_cell_type(value: str) -> CellType:
    if value.startswith('d') or value.startswith('b'):
        return CellType.INSTRUCTION
    if value.isdigit():
        return CellType.FIXED
    return CellType.TARGET


# ##### REDUCE A - intersection in cell.right and cell.down #####
def _a_intersection_internal(cell: Cell) -> bool:
    has_changed = False
    cell.print_debug('A-START')
    if not cell.down or not cell.right:
        return False
    intersection = cell.down.possible_values_set ^ cell.right.possible_values_set

    if cell.down and remove_elements(cell.down.possible_values, intersection):
        cell.down.build_set()
        has_changed = True

    if cell.right and remove_elements(cell.right.possible_values, intersection):
        cell.right.build_set()
        has_changed = True

    cell.print_debug(f'A-END [{has_changed}]')
    return has_changed


def remove_elements(list: List[List[int]], elements: set[int]) -> bool:
    res = False
    for i in list:
        for j in elements:
            if j in i:
                res = True
                i.remove(j)
    return res


# ##### REDUCE B - intersection between target and instruction
def _b_intersection_target_instruction(instr: Cell) -> bool:
    has_changed = False
    instr.print_debug('B-START')
    has_changed = _b_intersection_target_instruction_sub_cell(instr.down, CellDirection.DOWN) or has_changed
    has_changed = _b_intersection_target_instruction_sub_cell(instr.right, CellDirection.RIGHT) or has_changed
    instr.print_debug(f'B-END [{has_changed}]')
    return has_changed


def _b_intersection_target_instruction_sub_cell(sub_instr: SubCell, direction: CellDirection) -> bool:
    if not sub_instr:
        return False

    has_changed = False
    global_target_set = set()
    for target in sub_instr.associated_cells:
        sub_target = target.get_sub_cell(direction)
        global_target_set.update(sub_target.possible_values_set)
        if target.type == CellType.FIXED:
            continue
        local_only_in_target = (sub_instr.possible_values_set ^ sub_target.possible_values_set) & sub_target.possible_values_set
        if len(local_only_in_target) == 0:
            continue
        has_changed = _b_remove_values(sub_target, local_only_in_target) or has_changed

    only_in_instr = (sub_instr.possible_values_set ^ global_target_set) & sub_instr.possible_values_set
    has_changed = _b_remove_values(sub_instr, only_in_instr) or has_changed
    return has_changed


def _b_remove_values(sub_cell: SubCell, values: set) -> bool:
    if len(values) == 0:
        return False

    for l in sub_cell.possible_values:
        for v in values:
            if v in l:
                l.remove(v)

    sub_cell.build_set()
    return True


# ##### REDUCE C - single value in cell -> remove value from other cells ######
def _c_remove_value_from_lines(cell: Cell) -> bool:
    if not sub_cell_has_one_value(cell.down, cell.right):
        return False

    cell.print_debug('C-START')
    has_changed = False
    value = list(cell.down.possible_values_set)[0] if cell.down else list(cell.right.possible_values_set)[0]
    if cell.down:
        for instr in cell.down.associated_cells:
            has_changed = _c_remove_value_from_cells(instr.down.associated_cells, cell, value) or has_changed
    if cell.right:
        for instr in cell.right.associated_cells:
            has_changed = _c_remove_value_from_cells(instr.right.associated_cells, cell, value) or has_changed

    cell.print_debug(f'C-END [{has_changed}]')
    return has_changed


def _c_remove_value_from_cells(cells: List[Cell], origin_cell: Cell, value: int) -> bool:
    has_changed = False

    def _remove_values_from_sub_cells(sub_cell: SubCell) -> bool:
        if not sub_cell:
            return False

        _has_changed = False
        for sub_list in sub_cell.possible_values:
            if value in sub_list:
                sub_list.remove(value)
                _has_changed = True
        if _has_changed:
            sub_cell.build_set()
        return _has_changed

    for c in cells:
        if c == origin_cell:
            continue
        has_changed = _remove_values_from_sub_cells(c.down) or has_changed
        has_changed = _remove_values_from_sub_cells(c.right) or has_changed

    return has_changed


# ###### REDUCE D - if possible_values empty, remove possibility from line / col + instr
def _d_remove_empty_possibility(cell: Cell) -> bool:
    cell.print_debug('D-START')
    change_down = _d_remove_empty_possibility_for_sub_cells(cell.down, CellDirection.DOWN)
    change_right = _d_remove_empty_possibility_for_sub_cells(cell.right, CellDirection.RIGHT)

    cell.print_debug(f'D-END [{change_right or change_down}]')
    return change_right or change_down


def _d_remove_empty_possibility_for_sub_cells(sub_cell: SubCell, direction: CellDirection) -> bool:
    empty_indexes = [idx for (idx, elt) in enumerate(sub_cell.possible_values) if len(elt) == 0]
    if len(empty_indexes) == 0:
        return False

    empty_indexes.sort(reverse=True)
    cells = []

    for instr in sub_cell.associated_cells:
        sub_instr = instr.get_sub_cell(direction)
        cells.append(sub_instr)
        for elt in sub_instr.associated_cells:
            if elt.type == CellType.FIXED:
                continue
            sub_elt = elt.get_sub_cell(direction)
            cells.append(sub_elt)

    for cell in cells:
        for idx in empty_indexes:
            if idx >= len(cell.possible_values):
                print('oups')
            del cell.possible_values[idx]
        cell.build_set()
    return True


# ###### REDUCE E - Restore from Backup #######
def _e_restore_from_backup(cell_data: CellData):
    print('######## RESTORE FROM BACKUP ##########')
    cells = get_cells(cell_data.cell_map)
    for cell in cells:
        if (cell.down and len(cell.down.possible_values) == 0) or (cell.right and len(cell.right.possible_values) == 0):
            if cell_data.failed_branch == cell_data.branch_count:
                print('*' * 10, f' No more possibilities left !! Tried {cell_data.failed_branch} ', '*' * 10)
                raise Exception('No more possibilities left !')

        _e_restore_cell(cell)
    cell_data.failed_branch += 1
    cell_data.active_branch -= 1


def _e_restore_cell(cell: Cell):
    if cell.down:
        cell.down.possible_values = cell.down.possible_values_backup.pop()
        cell.down.build_set()
    if cell.right:
        cell.right.possible_values = cell.right.possible_values_backup.pop()
        cell.right.build_set()


# ###### BRANCH - create a branch ######
def _branch_creation(cell_data: CellData):
    active_cells = get_cells(cell_data.cell_map, filter_cell=cell_filter_target_not_unique)
    cell_data.branch_count += 1

    active_cells.sort(key=lambda c: _branch_cell_priority(c))
    branch_cell = active_cells[0]
    _branch_create_branch(branch_cell)

    all_cells = get_cells(cell_data.cell_map)
    for cell in all_cells:
        if cell == branch_cell:
            continue
        _branch_create_backup(cell)


def _branch_cell_priority(cell: Cell):
    value = max(0 if not cell.down else len(cell.down.possible_values_set), 0 if not cell.right else len(cell.right.possible_values_set))
    return 100000 if value <= 1 else value


def _branch_create_branch(cell: Cell):
    sub_cell = cell.down if cell.down else cell.right
    value = list(sub_cell.possible_values_set)[0]
    if cell.down:
        cell.down.possible_values_backup.append([[j for j in i if j != value] for i in cell.down.possible_values])
        cell.down.possible_values = [[j for j in i if j == value] for i in cell.down.possible_values]
        cell.down.possible_values_set = {value}
    if cell.right:
        cell.right.possible_values_backup.append([[j for j in i if j != value] for i in cell.right.possible_values])
        cell.right.possible_values = [[j for j in i if j == value] for i in cell.right.possible_values]
        cell.right.possible_values_set = {value}


def _branch_create_backup(cell: Cell):
    if cell.down:
        cell.down.possible_values_backup.append([[j for j in i] for i in cell.down.possible_values])
    if cell.right:
        cell.right.possible_values_backup.append([[j for j in i] for i in cell.right.possible_values])


def cell_filter_target(cell: Cell) -> Optional[Cell]:
    if cell.type == CellType.TARGET:
        return cell
    return None


def cell_filter_target_not_unique(cell: Cell) -> Optional[Cell]:
    if cell.type == CellType.TARGET and not cell.has_one_value():
        return cell
    return None


def get_cells(cell_data: Dict[int, Dict[int, Cell]], filter_cell=lambda c: c) -> List[Cell]:
    res = []
    for x in range(1, len(cell_data) + 1):
        for y in range(1, len(cell_data[x]) + 1):
            cell = cell_data[x][y]
            if filter_cell(cell):
                res.append(cell)
    return res


def _is_instr_invalid(instr: SubCell) -> bool:
    if not instr:
        return False
    sum = 0
    for cell in instr.associated_cells:
        if not cell.has_one_value():
            return False
        sum += list(cell.down.possible_values_set)[0] if cell.down else list(cell.right.possible_values_set)[0]
    return instr.fixed_value != sum