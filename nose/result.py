"""
Test Result
-----------

Provides a TextTestResult that extends unittest's _TextTestResult to
provide support for error classes (such as the builtin skip and
deprecated classes), and hooks for plugins to take over or extend
reporting.
"""

import logging
try:
    # 2.7+
    from unittest.runner import _TextTestResult
except ImportError:
    from unittest import _TextTestResult
from nose.config import Config
from nose.util import isclass, ln as _ln # backwards compat

log = logging.getLogger('nose.result')


def _exception_detail(exc):
    # this is what stdlib module traceback does
    try:
        return str(exc)
    except:
        return '<unprintable %s object>' % type(exc).__name__


class TextTestResult(_TextTestResult):
    """Text test result that extends unittest's default test result
    support for a configurable set of errorClasses (eg, Skip,
    Deprecated, TODO) that extend the errors/failures/success triad.
    """
    def __init__(self, stream, descriptions, verbosity, config=None,
                 errorClasses=None):
        if errorClasses is None:
            errorClasses = {}
        self.errorClasses = errorClasses
        if config is None:
            config = Config()
        self.config = config
        #self.blocked = []
        self.blocked = {'ERROR': [], 'FAIL': []}
        _TextTestResult.__init__(self, stream, descriptions, verbosity)

    def addSkip(self, test, reason):
        # 2.7 skip compat
        from nose.plugins.skip import SkipTest
        if SkipTest in self.errorClasses:
            storage, label, isfail = self.errorClasses[SkipTest]
            storage.append((test, reason))
            self.printLabel(label, (SkipTest, reason, None))

    def startTest(self, test, context=None):
        return super(TextTestResult, self).startTest(test)

    def addBlocked(self, test, err, context):
        """Overrides normal addBlocked to add support for
        errorClasses. If the exception is a registered class, the
        error will be added to the list for that class, not errors.
        """
        ec, ev, tb = err
        for cls, (_, label, isfail) in self.errorClasses.items():
            #if 'Skip' in cls.__name__ or 'Skip' in ec.__name__:
            #    from nose.tools import set_trace
            #    set_trace()
            if isclass(ec) and issubclass(ec, cls):
                if isfail:
                    test.passed = False
                s = self.blocked.setdefault(label, [])
                s.append((test, err, context))
                self.printLabel(label, err)
                return
        if isclass(ec) and issubclass(ec, test.failureException):
            label = 'FAIL'
        else:
            label = 'ERROR'
        storage = self.blocked.setdefault(label, [])
        storage.append((test, err, context))
        test.passed = False
        self.printLabel(label)

    def addError(self, test, err):
        """Overrides normal addError to add support for
        errorClasses. If the exception is a registered class, the
        error will be added to the list for that class, not errors.
        """
        ec, ev, tb = err
        for cls, (storage, label, isfail) in self.errorClasses.items():
            #if 'Skip' in cls.__name__ or 'Skip' in ec.__name__:
            #    from nose.tools import set_trace
            #    set_trace()
            if isclass(ec) and issubclass(ec, cls):
                if isfail:
                    test.passed = False
                storage.append((test, err))
                self.printLabel(label, err)
                return
        self.errors.append((test, err))
        test.passed = False
        self.printLabel('ERROR', err)

    def addFailure(self, test, err):
        """Called when an error has occurred. 'err' is a tuple of values as
        returned by sys.exc_info()."""
        self.failures.append((test, err))
        self.printLabel('FAIL', err)

    # override to bypass changes in 2.7
    def getDescription(self, test):
        if self.descriptions:
            return test.shortDescription() or str(test)
        else:
            return str(test)

    def printLabel(self, label, err=None):
        # Might get patched into a streamless result
        stream = getattr(self, 'stream', None)
        if stream is not None:
            if self.showAll:
                message = [label]
                if err:
                    detail = _exception_detail(err[1])
                    if detail:
                        message.append(detail)
                stream.writeln(": ".join(message))
            elif self.dots:
                stream.write(label[:1])

    def printErrorList(self, flavour, errors):
        for test, err in errors:
            try:
                exc_info = self._exc_info_to_string(err, test)
            except TypeError:
                # 2.3 compat
                exc_info = self._exc_info_to_string(err)

            self.stream.writeln(self.separator1)
            self.stream.writeln("%s: %s" % (flavour,self.getDescription(test)))
            self.stream.writeln(self.separator2)
            self.stream.writeln("%s" % exc_info)

    def printErrors(self):
        """Overrides to print all errorClasses errors as well.
        """
        _TextTestResult.printErrors(self)
        # TODO: Keep blocked tests count.
        for label, storage in self.blocked.items():
            grouped = {ctx: tb for t, tb, ctx in storage}
            self.printErrorList('BLOCKED %s' % label, grouped.items())
        for cls in self.errorClasses.keys():
            storage, label, isfail = self.errorClasses[cls]
            if isfail:
                self.printErrorList(label, storage)
        # Might get patched into a result with no config
        if hasattr(self, 'config'):
            self.config.plugins.report(self.stream)

    def printSummary(self, start, stop):
        """Called by the test runner to print the final summary of test
        run results.
        """
        write = self.stream.write
        writeln = self.stream.writeln
        taken = float(stop - start)
        run = self.testsRun
        plural = run != 1 and "s" or ""

        writeln(self.separator2)
        writeln("Ran %s test%s in %.3fs" % (run, plural, taken))
        writeln()

        summary = {}
        eckeys = self.errorClasses.keys()
        for cls in eckeys:
            storage, label, isfail = self.errorClasses[cls]
            count = len(storage)
            if not count:
                continue
            summary[label] = count
        if len(self.failures):
            summary['failures'] = len(self.failures)
        if len(self.errors):
            summary['errors'] = len(self.errors)
        for label, storage in self.blocked.items():
            if storage:
                summary[label] = len(storage)

        if not self.wasSuccessful():
            write("FAILED")
        else:
            write("OK")
        items = summary.items()
        if items:
            items.sort()
            write(" (")
            write(", ".join(["%s=%s" % (label, count) for
                             label, count in items]))
            writeln(")")
        else:
            writeln()

    def wasSuccessful(self):
        """Overrides to check that there are no errors in errorClasses
        lists that are marked as errors and should cause a run to
        fail.
        """
        return not self.failCount()

    def failCount(self):
        count = sum(map(len, [self.errors, self.failures,
                              self.blocked['ERROR'],
                              self.blocked['FAIL']]))
        for cls in self.errorClasses.keys():
            storage, label, isfail = self.errorClasses[cls]
            blocked = self.blocked.get(label, [])
            if not isfail:
                continue
            count += len(storage + blocked)
        return count

    def notFailCount(self):
        count = 0
        for cls in self.errorClasses.keys():
            storage, label, isfail = self.errorClasses[cls]
            blocked = self.blocked.get(label, [])
            if not isfail:
                count += len(storage + blocked)
        return count
    
    def _addError(self, test, err):
        try:
            exc_info = self._exc_info_to_string(err, test)
        except TypeError:
            # 2.3: does not take test arg
            exc_info = self._exc_info_to_string(err)
        self.errors.append((test, exc_info))
        if self.showAll:
            self.stream.write('ERROR')
        elif self.dots:
            self.stream.write('E')

    def _exc_info_to_string(self, err, test=None):
        # 2.7 skip compat
        from nose.plugins.skip import SkipTest
        if issubclass(err[0], SkipTest):
            return str(err[1])
        # 2.3/2.4 -- 2.4 passes test, 2.3 does not
        try:
            return _TextTestResult._exc_info_to_string(self, err, test)
        except TypeError:
            # 2.3: does not take test arg
            return _TextTestResult._exc_info_to_string(self, err)


def ln(*arg, **kw):
    from warnings import warn
    warn("ln() has moved to nose.util from nose.result and will be removed "
         "from nose.result in a future release. Please update your imports ",
         DeprecationWarning)
    return _ln(*arg, **kw)
