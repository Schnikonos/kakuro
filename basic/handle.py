from basic.cell import CellData, get_cells, cell_filter_target_not_unique, _e_restore_from_backup
from basic.parser import parser
import time


def handle(filename: str):
    start_time = time.time()
    cell_data = parser(filename)
    parse_time = time.time()
    print('## Parsing OK ', parse_time - start_time)

    try:
        cells_size = len(get_cells(cell_data.cell_map, filter_cell=cell_filter_target_not_unique))
        while cells_size > 0:
            has_changed = _reduce_loop(cell_data)
            if not has_changed:
                cell_data.create_branches()
            if cell_data.is_invalid():
                _e_restore_from_backup(cell_data)
            cells_size = len(get_cells(cell_data.cell_map, filter_cell=cell_filter_target_not_unique))
        cell_data.print_res()
        print('## Solve OK ', time.time() - parse_time)
    except Exception as e:
        print('##### ERROR !!!!! ####', e)
        cell_data.print_res()
        raise e


def _reduce_loop(cell_data: CellData) -> bool:
    has_changed = cell_data.a_intersection_internal()
    has_changed = cell_data.b_intersection_target_instruction() or has_changed
    has_changed = cell_data.d_remove_empty_possibility() or has_changed
    has_changed = cell_data.c_remove_value_from_lines() or has_changed
    has_changed = cell_data.e_restore_from_backup() or has_changed
    return has_changed


if __name__ == '__main__':
    handle('../data/normal_3.csv')
