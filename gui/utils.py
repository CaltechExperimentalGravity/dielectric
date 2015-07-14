#!/usr/bin/env python
# This work is licensed under the Creative Commons Attribution-NonCommercial-
# ShareAlike 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc-sa/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.

import numpy as np
from contextlib import contextmanager
from PyQt4.QtGui import QMessageBox

version_number = {'major': 0, 'minor': 2}
version_string = 'CoatingGUI v{major}.{minor}'.format(**version_number)

# This Singleton implementation is taken from
# http://stackoverflow.com/questions/42558/python-and-the-singleton-pattern
# by Paul Manta, licensed as CC-BY-SA 3.0
class Singleton:
    """
    A non-thread-safe helper class to ease implementing singletons.
    This should be used as a decorator -- not a metaclass -- to the
    class that should be a singleton.

    The decorated class can define one `__init__` function that
    takes only the `self` argument. Other than that, there are
    no restrictions that apply to the decorated class.

    To get the singleton instance, use the `Instance` method. Trying
    to use `__call__` will result in a `TypeError` being raised.

    Limitations: The decorated class cannot be inherited from.
    """

    def __init__(self, decorated):
        self._decorated = decorated

    def Instance(self):
        """
        Returns the singleton instance. Upon its first call, it creates a
        new instance of the decorated class and calls its `__init__` method.
        On all subsequent calls, the already created instance is returned.
        """
        try:
            return self._instance
        except AttributeError:
            self._instance = self._decorated()
            return self._instance

    def __call__(self):
        raise TypeError('Singletons must be accessed through `Instance()`.')

    def __instancecheck__(self, inst):
        return isinstance(inst, self._decorated)

class UnexpectedFileLayout(Exception):
    pass

class UnreadableFile(Exception):
    pass

class DataFileWrapper(object):
    def __init__(self, filename):
        self.filename = filename
        self.read_file()

    def value(self, x):
        return np.interp(x, self._x, self._y)

    def read_file(self):
        try:
            x, y = np.loadtxt(self.filename, ndmin=2, unpack=True)
        except IOError as e:
            raise UnreadableFile(str(e))
        except ValueError as e:
            raise UnexpectedFileLayout(
                'Unexpected format of data file.')

        self._x = x
        self._y = y


def export_data(filename, xdata, ydata, labels):
    """
    Exports data from xdata, ydata as ASCII file (tab-separated).

    xdata and ydata should be arrays with (possibly) multiple data sets.
    """
    X = xdata[0]
    unionised = False

    # combine multiple x datasets into one, interpolating y data
    if len(xdata) > 1:
        unionised = True
        for ii in range(1, len(xdata)):
            X = np.union1d(X, xdata[ii])
    Y = []
    for ii in range(len(ydata)):
        if unionised:
            Y.append(np.interp(X, xdata[ii], ydata[ii]))
        else:
            Y.append(ydata[ii])

    data = np.vstack((X, Y))

    header = version_string + "\n\n" + "\t".join(labels)
    np.savetxt(filename, data.T, delimiter="\t", fmt='%.5g', header=header)


@contextmanager
def block_signals(obj):
    """
    Context Manager for use in with statements, temporarily
    disables signals from a QObject
    """
    state = obj.blockSignals(True)
    try:
        yield obj
    finally:
        obj.blockSignals(state)


def to_float(number):
    """Converts a floating point number to a sensible string representation"""
    return '{0:g}'.format(number)
    
def int_conversion_error(text, parent=None):
    QMessageBox.critical(parent, 'Conversion Error',
       'The input "{0}" could not be converted to an integer number.'.format(text))

def float_conversion_error(text, parent=None):
    QMessageBox.critical(parent, 'Conversion Error',
        'The input "{0}" could not be converted to an integer number.'.format(text))

def float_set_from_lineedit(widget, config, key, parent=None):
    if widget.isModified():
        text = widget.text()
        try:
            config.set(key, float(text))
        except ValueError:
            float_conversion_error(text, parent)

def int_set_from_lineedit(widget, config, key, parent=None):
    if widget.isModified():
        text = widget.text()
        try:
            config.set(key, int(text))
        except ValueError:
            int_conversion_error(text, parent)
