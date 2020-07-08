__author__ = 'github.com/wardsimon'
__version__ = '0.0.1'

from copy import deepcopy
from enum import Enum
from typing import List, Union, Any
from functools import cached_property

from easyCore import borg, ureg
from easyCore.Utils.typing import noneType
from easyCore.Utils.UndoRedo import stack_deco

import numpy as np
from monty.json import MSONable
from lmfit import Parameter as lmfitPar

Q_ = ureg.Quantity
M_ = ureg.Measurement


class Descriptor(MSONable):

    _storer = Q_
    _borg = borg
    _args = {
        'value': None,
        'units': ''
    }

    def __init__(self, name: str,
                 value: Any,
                 units: Union[noneType, str, ureg.Quantity, ureg.Measurement, ureg.Unit] = None,
                 description: str = '',
                 url: str = '',
                 callback: property = None,
                 parent=None):
        self.__borg = borg
        self.__borg.map.add_vertex(id(self))
        self._parent = parent
        if self._parent is not None:
            self.__borg.map.add_edge({id(self._parent), id(self)})
        self.name: str = name
        self._units = ureg.parse_expression(units)
        self._args['value'] = value
        self._args['units'] = str(self.unit)
        self._value = self.__class__._storer(**self._args)
        self.description: str = description
        self._display_name: str = ''
        self.url: str = url
        self._callback: property = callback
        self.user_data: dict = {}
        self._type = type(value)

    # This should not
    @property
    def display_name(self) -> str:
        display_name = self._display_name
        if display_name is None:
            display_name = self.name
        return display_name

    @display_name.setter
    @stack_deco
    def display_name(self, name_str):
        self._display_name = name_str

    @property
    def unit(self):
        # Should implement the undo/redo functionality
        return self._units.units

    @unit.setter
    @stack_deco
    def unit(self, unit_str: str):
        new_unit = ureg.parse_expression(unit_str)
        self._units = new_unit
        self._args['units'] = str(new_unit)
        self._value = self.__class__._storer(**self._args)

    @property
    def value(self):
        # Cached property? Should reference callback.
        # Also should reference for undo/redo
        return self._value

    @value.setter
    @stack_deco
    def value(self, value):
        # There should be a callback to the base module which has a Borg, with
        # if self._parent is not None and hasattr(self._parent, '_history'):
        #     self._parent._history[self._parent.__hash__()].append(self, 'value_change', value)
        # Cached property?
        if hasattr(value, 'magnitude'):
            value = value = value.magnitude
            if hasattr(value, 'nominal_value'):
                value = value.nominal_value
        self._args['value'] = value
        self._value = self.__class__._storer(**self._args)

    @property
    def raw_value(self):
        value = self._value
        if hasattr(value, 'magnitude'):
            value = value = value.magnitude
            if hasattr(value, 'nominal_value'):
                value = value.nominal_value
        return value

    def _validator(self, value):
        assert isinstance(value, self._type)

    def convert_unit(self, unit_str: str):
        new_unit = ureg.parse_expression(unit_str)
        self._value = self._value.to(new_unit)
        self._args['value'] = self.raw_value
        self._args['units'] = str(self.unit)

    @cached_property
    def compatible_units(self) -> List[str]:
        return [str(u) for u in self.unit.compatible_units()]

    def __del__(self):
        # Remove oneself from the map
        # self.__borg.map.remove_vertice(id(self))
        pass

    def __repr__(self):
        """Return printable representation of a Parameter object."""
        sval = "= %s" % self._value.magnitude
        if not self.value.unitless:
            sval += ' %s' % self.unit
        return "<%s '%s' %s>" % (self.__class__.__name__, self.name, sval)

    def as_dict(self) -> dict:
        super_dict = super().as_dict()
        super_dict['value'] = self.raw_value
        super_dict['units'] = self._args['units']
        return super_dict

    def to_parameter(self, error: Union[float, np.ndarray]):
        pickled_obj = self.as_dict()
        pickled_obj['error'] = error
        return Parameter.from_dict(pickled_obj)


class Parameter(Descriptor):
    _storer = M_
    _args = {
        'value': None,
        'units': '',
        'error': None
    }

    def __init__(self,
                 name: str,
                 value: Union[float, np.ndarray, noneType],
                 error: Union[float, np.ndarray, noneType] = None,
                 min: float = -np.Inf,
                 max: float = np.Inf,
                 fixed: bool = False,
                 **kwargs):
        self._args['error'] = error
        super().__init__(name, value, **kwargs)
        self._min: float = min
        self._max: float = max
        self._fixed: bool = fixed
        self.initial_value = self.value
        self.constraints: dict = {
            'user': [],
            'physical': [],
            'builtin': [Constraint(lambda x: x < self.min, self.min),
                        Constraint(lambda x: x > self.max, self.max)]
        }
        self._kwargs = kwargs
        self.__previous_set = self.__class__.value.fset
        self.__previous_unit = self.__class__.unit

        setattr(self.__class__, 'unit', property(fget=self.__class__.unit.fget,
                                                 fset=lambda obj, new_value: obj.__unit_setter(new_value),
                                                 fdel=self.__class__.unit.fdel))

        setattr(self.__class__, 'value', property(fget=self.__class__.value.fget,
                                                  fset=lambda obj, val: self.__previous_set(obj, obj._validate(val)),
                                                  fdel=self.__class__.value.fdel))

    def __unit_setter(self, value_str: str):
        old_unit = str(self._args['units'])
        self.__previous_unit.fset(self, value_str)
        # Deal with min/max
        if not self.value.unitless:
            self._min = Q_(self.min, old_unit).to(self._units).magnitude
            self._max = Q_(self.max, old_unit).to(self._units).magnitude
        # Log the converted error
        self._args['error'] = self.value.error.magnitude

    @property
    def min(self) -> float:
        # Should implement the undo/redo functionality
        return self._min

    @min.setter
    @stack_deco
    def min(self, value: float):
        # Should implement the undo/redo functionality
        self._min = value

    @property
    def max(self) -> float:
        # Should implement the undo/redo functionality
        return self._max

    @max.setter
    @stack_deco
    def max(self, value: float):
        # Should implement the undo/redo functionality
        self._max = value

    @property
    def fixed(self) -> bool:
        # Should implement the undo/redo functionality
        return self._fixed

    @fixed.setter
    @stack_deco
    def fixed(self, value: bool):
        # Should implement the undo/redo functionality
        self._fixed = value

    @property
    def error(self) -> float:
        return self._value.error.magnitude

    @error.setter
    def error(self, value: float):
        self._args['error'] = value
        self._value.error.magnitude = value

    def for_fit(self) -> lmfitPar:
        return lmfitPar(self.name, value=self.value, vary=~self.fixed, min=self.min, max=self.max,
                        expr=None, brute_step=None, user_data=self.user_data)

    def _validate(self, value):
        new_value = value
        for constraint in self.constraints.values():
            for test in constraint:
                if test(value):
                    new_value = test.value()
        return new_value

    def __repr__(self):
        """Return printable representation of a Parameter object."""
        super_str = super().__repr__()
        super_str = super_str[:-1]
        s = []
        if self.fixed:
            super_str += " (fixed)"
        s.append(super_str)
        s.append("bounds=[%s:%s]" % (repr(self.min), repr(self.max)))
        return "%s>" % ', '.join(s)


class Constraint:
    def __init__(self, validator, fail_value):
        self._validator = validator
        self._fail_value = fail_value

    def __call__(self, *args, **kwargs):
        return self._validator(*args, **kwargs)

    def value(self):
        return self._fail_value


class BaseObj(MSONable):
    _parent = None
    _borg = borg

    def __init__(self, parent=None, **kwargs):
        self._parent = parent

    def sub_fittables(self) -> List[Parameter]:
        vals = []
        for key, item in self.__dict__.items():
            if hasattr(item, 'sub_fittables'):
                vals = [vals, *item.sub_fittables()]
            elif isinstance(item, Parameter) and not item.fixed:
                vals.append(item.for_fit())
        return vals