"""
This plugin captures stdout during test execution. If the test fails
or raises an error, the captured output will be appended to the error
or failure output. It is enabled by default but can be disabled with
the options ``-s`` or ``--nocapture``.

:Options:
  ``--nocapture``
    Don't capture stdout (any stdout output will be printed immediately)
  ``--capture-tee``
    Capture stdout, but also print everything immediately

"""
import logging
import os
import sys
from nose.plugins.base import Plugin
from nose.pyversion import exc_to_unicode, force_unicode
from nose.util import ln
from StringIO import StringIO


log = logging.getLogger(__name__)



class Capture(Plugin):
    """
    Output capture plugin. Enabled by default. Disable with ``-s`` or
    ``--nocapture``. This plugin captures stdout during test execution,
    appending any output captured to the error or failure output,
    should the test fail or raise an error.
    """
    
    class CompositeObject(object):
        '''
        Proxy object to distribute all method calls to multiple objects.
        '''
        class Caller(object):
            def __init__(self, comp_obj, method_name):
                self.comp_obj = comp_obj
                self.method_name = method_name
                
            def __call__(self, *args, **kwargs):
                ret = None
                for obj in self.comp_obj.objects:
                    method = getattr(obj, self.method_name)
                    ret = method(*args, **kwargs)
                return ret
        
        def __init__(self, objects):
            self.objects = objects
            
        def __getattr__(self, attr):
            return self.Caller(self, attr)
        

    enabled = True
    capture_tee = False
    env_opt = 'NOSE_NOCAPTURE'
    name = 'capture'
    score = 1600

    def __init__(self):
        self.stdout_stack = []
        self.orig_stdout = sys.stdout
        self._buf = None

    def options(self, parser, env):
        """Register commandline options
        """
        parser.add_option(
            "-s", "--nocapture", action="store_false",
            default=not env.get(self.env_opt), dest="capture",
            help="Don't capture stdout (any stdout output "
            "will be printed immediately) [NOSE_NOCAPTURE]")
        parser.add_option(
            "--capture-tee", action="store_true",
            default=False, dest="capture_tee",
            help="Capture stdout, but also print everything immediately. Default false.")

    def configure(self, options, conf):
        """Configure plugin. Plugin is enabled by default.
        """
        self.conf = conf
        if not options.capture:
            self.enabled = False
        if options.capture_tee:
            self.capture_tee = True

    def afterTest(self, test):
        """Clear capture buffer.
        """
        self.end()
        self._buf = None

    def begin(self):
        """Replace sys.stdout with capture buffer.
        """
        self.start() # get an early handle on sys.stdout

    def beforeTest(self, test):
        """Flush capture buffer.
        """
        self.start()

    def formatError(self, test, err):
        """Add captured output to error report.
        """
        test.capturedOutput = output = self.buffer
        self._buf = None
        if not output:
            # Don't return None as that will prevent other
            # formatters from formatting and remove earlier formatters
            # formats, instead return the err we got
            return err
        ec, ev, tb = err
        return (ec, self.addCaptureToErr(ev, output), tb)

    def formatFailure(self, test, err):
        """Add captured output to failure report.
        """
        return self.formatError(test, err)

    def addCaptureToErr(self, ev, output):
        ev = exc_to_unicode(ev)
        output = force_unicode(output)
        return u'\n'.join([ev, ln(u'>> begin captured stdout <<'),
                           output, ln(u'>> end captured stdout <<')])

    def start(self):
        self.stdout_stack.append(sys.stdout)
        self._buf = StringIO()
        
        if self.capture_tee:
            sys.stdout = self.CompositeObject([self.orig_stdout, self._buf])
        else:
            sys.stdout = self._buf

    def end(self):
        if self.stdout_stack:
            sys.stdout = self.stdout_stack.pop()

    def finalize(self, result):
        """Restore stdout.
        """
        while self.stdout_stack:
            self.end()

    def _get_buffer(self):
        if self._buf is not None:
            return self._buf.getvalue()

    buffer = property(_get_buffer, None, None,
                      """Captured stdout output.""")
