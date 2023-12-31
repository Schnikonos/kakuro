from enum import Enum
from typing import List


class Abc(Enum):
    AA = 1
    BB = 2


def test(abc: Abc):
    print('ok', abc)


test(Abc.AA)
