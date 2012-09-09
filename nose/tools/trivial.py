"""Tools so trivial that tracebacks should not descend into them

We define the ``__unittest`` symbol in their module namespace so unittest will
skip them when printing tracebacks, just as it does for their corresponding
methods in ``unittest`` proper.

"""
import re

try:
    import unittest2 as unittest
except ImportError:
    import unittest


__all__ = ['ok_', 'eq_']

# Use the same flag as unittest itself to prevent descent into these functions:
__unittest = 1


def ok_(expr, msg=None):
    """Shorthand for assert. Saves 3 whole characters!
    """
    if not expr:
        raise AssertionError(msg)


def eq_(a, b, msg=None):
    """Shorthand for 'assert a == b, "%r != %r" % (a, b)
    """
    if not a == b:
        raise AssertionError(msg or "%r != %r" % (a, b))



def pep8_assertions(testcase):
    """Extracts assertions from testcase and pep8ifies them, returning a
       dictionary of the new names and results.

       Example use::
       
           class ModifiedTestCase(unittest.TestCase):
               failureException = MyAssertionError
               
               def nop(): pass
       
           pepd = pep8_assertions(ModifiedTestCase('nop'))
           assert_equal = pepd['assert_equal']
    """


    caps = re.compile('([A-Z])')

    def pep8(name):
        return caps.sub(lambda m: '_' + m.groups()[0].lower(), name)

    result = {}
    for at in [ at for at in dir(testcase)
                if at.startswith('assert') and not '_' in at ]:
        pepd = pep8(at)
        result[pepd] = getattr(testcase, at)
    return result


class Dummy(unittest.TestCase):
    def nop():
        pass
pepd = pep8_assertions(Dummy('nop'))
__all__.extend(pepd)
vars().update(pepd)
del Dummy
del pepd
