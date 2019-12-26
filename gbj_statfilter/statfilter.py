# -*- coding: utf-8 -*-
"""Module for statistical filtering and smoothing."""
__version__ = '0.7.0'
__status__ = 'Beta'
__author__ = 'Libor Gabaj'
__copyright__ = 'Copyright 2018-2019, ' + __author__
__credits__ = []
__license__ = 'MIT'
__maintainer__ = __author__
__email__ = 'libor.gabaj@gmail.com'


import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Any, NoReturn, List


###############################################################################
# Abstract class as a base for all statistical filters
###############################################################################
class StatFilter(ABC):
    """Common statistical smoothing management."""

    def __init__(self) -> NoReturn:
        """Create the class instance - constructor."""
        self._buffer = []
        # Logging
        self._logger = logging.getLogger(' '.join([__name__, __version__]))

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
                self._value_max = None

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
            self._logger.warning(errmsg)
            return None
        if self.value_min is not None and value < self.value_min:
            errmsg = f'Rejected value {value} less than {self.value_min}'
            self._logger.warning(errmsg)
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
        return len([i for i in self._buffer if i is not None])

    @abstractmethod
    def reset(self):
        """Reset instance object to initial state."""
        ...

    @abstractmethod
    def result(self, value: Optional[float]) -> Optional[float]:
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
        DEFAULT = 0.5
        MINIMUM = 0.0
        MAXIMUM = 1.0

    def __init__(self) -> NoReturn:
        super().__init__()
        self.factor = self.Factor.DEFAULT.value
        self._buffer = [None]
        self._logger.debug(
            f'Instance of "{self.__class__.__name__}" created: {self}')

    def __str__(self) -> str:
        """Represent instance object as a string."""
        msg = f'ExponentialSmoothing({self.factor})'
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
        finally:
            f_min = self.Factor.MINIMUM.value
            f_max = self.Factor.MAXIMUM.value
            self._factor = max(min(abs(self._factor), f_max), f_min)

    def reset(self) -> NoReturn:
        """Reset instance object to initial state."""
        self._buffer[0] = None

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
                self._buffer[0] += self.factor * (value - self._buffer[0])
            else:
                self._buffer[0] = value
            msg = f'Value={value}, Statistic={self._buffer[0]}'
            self._logger.debug(msg)
        return self._buffer[0]


###############################################################################
# Running statistics filtering
###############################################################################
class Running(StatFilter):
    """Running statistical smoothing."""

    class BufferLength(Enum):
        DEFAULT = 5
        MINIMUM = 1
        MAXIMUM = 15

    class StatisticType(Enum):
        AVERAGE = 'AVG'
        MINIMUM = 'MIN'
        MAXIMUM = 'MAX'
        MEDIAN = 'MED'

    def __init__(self) -> NoReturn:
        super().__init__()
        self.buffer_len = self.BufferLength.DEFAULT.value
        self.stat_type = self.StatisticType.AVERAGE
        self._logger.debug(
            f'Instance of "{self.__class__.__name__}" created: {self}')

    def __str__(self) -> str:
        """Represent instance object as a string."""
        msg = \
            f'RunningSmoothing(' \
            f'{self.stat_type.value}-' \
            f'{self.buffer_len})'
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
        return len(self._buffer)

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
                self._buffer.extend([None] * (buffer_len - self.buffer_len))
            elif self.buffer_len > buffer_len:
                for i in range(self.buffer_len - buffer_len):
                    self._buffer.pop(i)

    @property
    def stat_type(self) -> str:
        """Default statistic type for general result."""
        return self._def_stat

    @stat_type.setter
    def stat_type(self, def_stat: StatisticType) -> NoReturn:
        """Set default statistic type if correct."""
        if isinstance(def_stat, self.StatisticType):
            self._def_stat = def_stat

    def _register(self, value: float) -> NoReturn:
        """Filter and register new value to the data buffer.

        Arguments
        ---------
        value
            Sample value to be registered in the data buffer and use for
            statistical smoothing.

        Notes
        -----
        - If the instance of statistical filter has an instance of value
          filter, the input value is filtered against it.
        - If new value does not fit to the filter range, it is ignored.
        - The most recent (fresh) sample value is always in the 0 index of the
          data buffer.
        - Sample values are shifted to the right in the data buffer (to higher
          indices), so that the most recent value is lost.

        """
        value = self.filter(value)
        if value is not None:
            # Shift if any real value is stored
            if self.readings:
                for i in range(self.buffer_len - 1, 0, -1):
                    self._buffer[i] = self._buffer[i - 1]
            self._buffer[0] = value
        return value

    def reset(self) -> NoReturn:
        """Reset instance object to initial state."""
        self._buffer = [None] * self.buffer_len

    def _REGISTER(func):
        """Decorate statistical function by registering its value."""

        def _decorator(self, value):
            result = self._register(value)
            if result is None:
                return
            if self.readings:
                result = func(self, result)
            if result is not None:
                msg = f'Value={value},=Statistic {result}'
                self._logger.debug(msg)
            return result
        return _decorator

    @_REGISTER
    def result_min(self, value: float = None) -> float:
        """Calculate minimum from data buffer."""
        return min([i for i in self._buffer if i is not None])

    @_REGISTER
    def result_max(self, value: float = None) -> float:
        """Calculate maximum from data buffer."""
        return max([i for i in self._buffer if i is not None])

    @_REGISTER
    def result_avg(self, value: float = None) -> float:
        """Calculate mean from data buffer."""
        l = [i for i in self._buffer if i is not None]
        if len(l):
            return sum(l) / len(l)

    @_REGISTER
    def result_med(self, value: float = None) -> float:
        """Calculate median from data buffer."""
        l = self.readings
        if l:
            return self._buffer[l // 2]

    def result(self, value: float = None) -> float:
        """Calculate default statistic from data buffer."""
        func = eval('self.result_' + self._def_stat.value.lower())
        return func(value)
