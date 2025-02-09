#  SPDX-FileCopyrightText: 2023 easyCore contributors  <core@easyscience.software>
#  SPDX-License-Identifier: BSD-3-Clause
#  © 2021-2023 Contributors to the easyCore project <https://github.com/easyScience/easyCore

__author__ = "github.com/wardsimon"
__version__ = "0.3.1"

import numpy as np

from easyCore.Objects.Borg import Borg
import pint
from .REDIRECT import _REDIRECT

default_fitting_engine = "lmfit"

ureg = pint.UnitRegistry()
borg = Borg()
borg.instantiate_stack()
borg.stack.enabled = False
