# -*- coding: utf-8 -*-
"""Module for statistical filtering and smoothing."""
__version__ = '0.7.0'
__status__ = 'Beta'
__author__ = 'Libor Gabaj'
__copyright__ = 'Copyright 2018-2020, ' + __author__
__credits__ = []
__license__ = 'MIT'
__maintainer__ = __author__
__email__ = 'libor.gabaj@gmail.com'


import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, NoReturn


def register(func):
    """Decorator of astatistical function by registering its value."""

    def _decorator(self, value: float = None):
        value = self.filter(value)
        if value is not None:
            # Shift if any real value is stored
            if self.readings:
                for i in range(self.buffer_len - 1, 0, -1):
                    self.buffer[i] = self.buffer[i - 1]
            self.buffer[0] = value
        result = value
        if self.readings:
            result = func(self, result)
        if result is not None:
            msg = \
                f'Buffer={self.buffer_len}' \
                f', Type={self.stat_type.name}' \
                f', Value={value}' \
                f', Statistic={result}'
            self.logger.debug(msg)
        return result
    return _decorator


###############################################################################
# Abstract class as a base for all statistical filters
###############################################################################
class StatFilter(ABC):
    """Common statistical smoothing management."""

    def __init__(self) -> NoReturn:
        """Create the class instance - constructor."""
        self.reset()
        # Logging
        msg = f'Instance of "{self.__class__.__name__}" created'
        self.logger = logging.getLogger(' '.join([__name__, __version__]))
        self.logger.debug(msg)

    @abstractmethod
    def __str__(self) -> str:
        """Represent instance object as a string."""
        ...

    @abstractmethod
    def __repr__(self) -> str:
        """Represent instance object officially."""
        ...

    @property
    def value_min(self) -> float:
        """Minimal acceptable value."""
        if not hasattr(self, '_value_min'):
            self._value_min = None
        return self._value_min

    @value_min.setter
    def value_min(self, value: Optional[float]) -> NoReturn:
        """Set minimal acceptable value if correct."""
        try:
            self._value_min = float(value)
        except (TypeError, ValueError):
            if value is None:
                self._value_min = None
        msg = f'Minimal value set to {self._value_min}'
        self.logger.debug(msg)

    @property
    def value_max(self) -> float:
        """Maximal acceptable value."""
        if not hasattr(self, '_value_max'):
            self._value_max = None
        return self._value_max

    @value_max.setter
    def value_max(self, value: Optional[float]) -> NoReturn:
        """Set maximal acceptable value if correct."""
        try:
            self._value_max = float(value)
        except (TypeError, ValueError):
            if value is None:
                self._value_max = None
        msg = f'Maximal value set to {self._value_max}'
        self.logger.debug(msg)

    def filter(self, value: Optional[float]) -> Optional[float]:
        """Filter value against acceptable value range.

        Arguments
        ---------
        value
            Value to be filtered.

        Returns
        -------
        If the input value is outside of the acceptable value range, None
        is returned, otherwise that value.

        """
        if value is None:
            return None
        if self.value_max is not None and value > self.value_max:
            errmsg = f'Rejected value {value} greater than {self.value_max}'
            self.logger.warning(errmsg)
            return None
        if self.value_min is not None and value < self.value_min:
            errmsg = f'Rejected value {value} less than {self.value_min}'
            self.logger.warning(errmsg)
            return None
        return value

    @property
    def readings(self) -> int:
        """Current number of values in data buffer.

        Notes
        -----
        - The statistical calculation can be provided before filling
          the entire data buffer. In that case the method returns the values
          count, which a statistic is calculated from.
        - Usually the returned value should be the same as length of the data
          buffer at the end of a measurement cycle.

        """
        return len([i for i in self.buffer if i is not None])

    @abstractmethod
    def reset(self):
        """Reset instance object to initial state."""
        self.buffer = []

    @abstractmethod
    def result(self, value: float = None) -> Optional[float]:
        """Calculate statistically smoothed value.

        Arguments
        ---------
        value
            Sample value to be filtered.

        Returns
        -------
        Input value is returned, if it is within filtering ranger, otherwise
        None.

        """
        return self.filter(value)

###############################################################################
# Exponential filtering
###############################################################################
class Exponential(StatFilter):
    """Exponential statistical smoothing."""

    class Factor(Enum):
        """Exponential factor parameters."""
        DEFAULT = 0.5   # Running average
        MINIMUM = 0.0   # Only the very first value
        MAXIMUM = 1.0   # Only the newest value
        OPTIMAL = 0.2   # For usual measurements

    def __str__(self) -> str:
        """Represent instance object as a string."""
        msg = f'ExponentialSmoothing[factor={self.factor}]'
        return msg

    def __repr__(self) -> str:
        """Represent instance object officially."""
        msg = f'{self.__class__.__name__}()'
        return msg

    @property
    def factor(self) -> float:
        """Positive smoothing factor for exponential filtering.
        - Acceptable value range is ``0.0 ~ 1.0``.
        - Default value means ``running average``.
        - Maximal value means ``no smoothing``.
        """
        if not hasattr(self, '_factor') or self._factor is None:
            self._factor = self.Factor.DEFAULT.value
        return self._factor

    @factor.setter
    def factor(self, value: Optional[float]) -> NoReturn:
        """Set current float smoothing factor if correct."""
        try:
            self._factor = float(value or self.Factor.DEFAULT.value)
        except (ValueError, TypeError):
            pass
        f_min = self.Factor.MINIMUM.value
        f_max = self.Factor.MAXIMUM.value
        self._factor = max(min(abs(self._factor), f_max), f_min)
        msg = f'Smoothing factor set to {self._factor}'
        self.logger.debug(msg)

    def reset(self) -> NoReturn:
        """Reset instance object to initial state."""
        self.buffer = [None]

    def result(self, value: float = None) -> Optional[float]:
        """Calculate statistically smoothed value.

        Arguments
        ---------
        value
            Sample value to be smoothed.

        Returns
        -------
        If None input value is provided, recent result is returned,
        otherwise the new smoothed value is.

        Notes
        -----
        - The method calculates a new filtered value from the input value,
          previous stored filtered value, and stored smoothing factor in the
          class instance object.
        - The very first input value is considered as a previous filtered value
          or starting value.

        """
        value = super().result(value)
        if value is not None:
            if self.readings:
                self.buffer[0] += self.factor * (value - self.buffer[0])
            else:
                self.buffer[0] = value
            msg = \
                f'Factor={self.factor}' \
                f', Value={value}' \
                f', Statistic={self.buffer[0]}'
            self.logger.debug(msg)
        return self.buffer[0]


###############################################################################
# Running statistics filtering
###############################################################################
class Running(StatFilter):
    """Running statistical smoothing."""

    class BufferLength(Enum):
        """Sample buffer parameters."""
        DEFAULT = 5
        MINIMUM = 1
        MAXIMUM = 15

    class StatisticType(Enum):
        """Supported statistical types."""
        AVERAGE = 'AVG'
        MINIMUM = 'MIN'
        MAXIMUM = 'MAX'
        MEDIAN = 'MED'

    def __str__(self) -> str:
        """Represent instance object as a string."""
        msg = \
            f'RunningSmoothing[' \
            f'{self.stat_type.value}-' \
            f'{self.buffer_len}]'
        return msg

    def __repr__(self) -> str:
        """Represent instance object officially."""
        msg = f'{self.__class__.__name__}()'
        return msg

    @property
    def buffer_len(self) -> int:
        """Real length of the data buffer.

        Notes
        -----
        - Usually the returned value is the same as length put to the
          constructor.
        - If class has adjusted or limited the input buffer length, the
          method returns the actual length.

        """
        return len(self.buffer)

    @buffer_len.setter
    def buffer_len(self, value: int) -> NoReturn:
        """Adjust data buffer length if correct."""
        try:
            # Make odd number and minimum 1
            buffer_len = abs(int(value or self.BufferLength.DEFAULT.value)) | 1
        except (ValueError, TypeError):
            pass
        else:
            b_min = self.BufferLength.MINIMUM.value
            b_max = self.BufferLength.MAXIMUM.value
            buffer_len = max(min(buffer_len, b_max), b_min)
            if self.buffer_len < buffer_len:
                self.buffer.extend([None] * (buffer_len - self.buffer_len))
            elif self.buffer_len > buffer_len:
                for i in range(self.buffer_len - buffer_len):
                    self.buffer.pop(i)
            msg = f'Buffer length set to {self.buffer_len}'
            self.logger.debug(msg)

    @property
    def stat_type(self) -> str:
        """Default statistic type for general result."""
        if not hasattr(self, '_def_stat') \
            or not isinstance(self._def_stat, self.StatisticType):
            self.stat_type = self.StatisticType.AVERAGE
        return self._def_stat

    @stat_type.setter
    def stat_type(self, def_stat: StatisticType) -> NoReturn:
        """Set default statistic type if correct."""
        if isinstance(def_stat, self.StatisticType):
            self._def_stat = def_stat
            msg = f'Statistic type set to {self._def_stat.name}'
            self.logger.debug(msg)

    def reset(self) -> NoReturn:
        """Reset instance object to initial state."""
        if not hasattr(self, '_buffer'):
            self.buffer = [None] * self.BufferLength.DEFAULT.value
        self.buffer = [None] * self.buffer_len

    def result_min(self) -> float:
        """Calculate minimum from data buffer."""
        return min([i for i in self.buffer if i is not None])

    def result_max(self) -> float:
        """Calculate maximum from data buffer."""
        return max([i for i in self.buffer if i is not None])

    def result_avg(self) -> float:
        """Calculate mean from data buffer."""
        lov = [i for i in self.buffer if i is not None]
        if lov:
            return sum(lov) / len(lov)
        return None

    def result_med(self) -> float:
        """Calculate median from data buffer."""
        samples = self.readings
        if samples:
            return self.buffer[samples // 2]
        return None

    @register
    def result(self, value: float = None) -> float:
        """Calculate default statistic from data buffer.

        Arguments
        ---------
        value
            Sample value to be smoothed.

        Returns
        -------
        If None input value is provided, recent result is returned,
        otherwise the new smoothed value is.

        Notes
        -----
        - The method calculates a new filtered value from the input value and
          previous stored values in the class instance object.

        """
        func = getattr(self, f'result_{self._def_stat.value.lower()}')
        return func()
