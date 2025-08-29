from OptiENEA.classes.unit import *
from OptiENEA.classes.problem import Problem
import os

TEST_INFO_UNIT = {'Type': 'no type', 'Layers': ['test_layer_1', 'test_layer_2'], 'Main layer': 'test_layer_1'}
INTEREST_RATE = 0.07

__HERE__ = os.path.dirname(os.path.realpath(__file__))

def test_init_unit():
    # Tests the creation of a generic unit
    unit = Unit('test_unit', TEST_INFO_UNIT, Problem(''))
    assert unit.layers == ['test_layer_1', 'test_layer_2']
    assert unit.name == 'test_unit'
    assert unit.main_layer == 'test_layer_1'
    assert isinstance(unit.problem, Problem)

