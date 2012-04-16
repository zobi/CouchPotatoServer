#!/usr/bin/env python
from logging import handlers
from os.path import dirname
import logging
import os
import signal
import socket
import subprocess
import sys
import traceback

# Root path
base_path = dirname(os.path.abspath(__file__))

# Insert local directories into path
sys.path.insert(0, os.path.join(base_path, 'libs'))

class Loader(object):

    do_restart = False

    def __init__(self):

        from couchpotato.environment import Env
        from couchpotato.core.helpers.variable import getDataDir
        self.Env = Env

        # Get options via arg
        from couchpotato.runner import getOptions
        self.options = getOptions(base_path, sys.argv[1:])

        # Load settings
        settings = Env.get('settings')
        settings.setFile(self.options.config_file)

        # Create data dir if needed
        self.data_dir = os.path.expanduser(Env.setting('data_dir'))
        if self.data_dir == '':
            self.data_dir = getDataDir()

        if not os.path.isdir(self.data_dir):
            os.makedirs(self.data_dir)

        # Create logging dir
        self.log_dir = os.path.join(self.data_dir, 'logs');
        if not os.path.isdir(self.log_dir):
            os.mkdir(self.log_dir)

        # Logging
        from couchpotato.core.logger import CPLog
        self.log = CPLog(__name__)

        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', '%H:%M:%S')
        hdlr = handlers.RotatingFileHandler(os.path.join(self.log_dir, 'error.log'), 'a', 500000, 10)
        hdlr.setLevel(logging.CRITICAL)
        hdlr.setFormatter(formatter)
        self.log.logger.addHandler(hdlr)

    def addSignals(self):

        signal.signal(signal.SIGINT, self.onExit)
        signal.signal(signal.SIGTERM, lambda signum, stack_frame: sys.exit(1))

        from couchpotato.core.event import addEvent
        addEvent('app.after_shutdown', self.afterShutdown)

    def afterShutdown(self, restart):
        self.do_restart = restart

    def onExit(self, signal, frame):
        from couchpotato.core.event import fireEvent
        fireEvent('app.crappy_shutdown', single = True)

    def run(self):

        self.addSignals()

        from couchpotato.runner import runCouchPotato
        runCouchPotato(self.options, base_path, sys.argv[1:], data_dir = self.data_dir, log_dir = self.log_dir, Env = self.Env)

        if self.do_restart:
            self.restart()

    def restart(self):
        try:
            # remove old pidfile first
            try:
                if self.runAsDaemon():
                    try: self.daemon.stop()
                    except: pass
                    self.daemon.delpid()
            except:
                self.log.critical(traceback.format_exc())

            args = [sys.executable] + [os.path.join(base_path, __file__)] + sys.argv[1:]
            subprocess.Popen(args)
        except:
            self.log.critical(traceback.format_exc())

    def daemonize(self):

        if self.runAsDaemon():
            try:
                from daemon import Daemon
                self.daemon = Daemon(self.options.pid_file)
                self.daemon.daemonize()
            except SystemExit:
                raise
            except:
                self.log.critical(traceback.format_exc())

    def runAsDaemon(self):
        return self.options.daemon and  self.options.pid_file


def updatedRequirements():

    try:
        from pip.index import PackageFinder
        from pip.locations import build_prefix, src_prefix
        from pip.req import InstallRequirement, RequirementSet
    except ImportError:
        print 'You need pip (http://pypi.python.org/pypi/pip) to use CouchPotato from source'
        raise

    requirement_set = RequirementSet(build_dir = build_prefix, src_dir = src_prefix, download_dir = None)

    f = open(os.path.join(base_path, 'requirements.txt'))
    lines = f.readlines()
    f.close()

    for line in lines:
        requirement_set.add_requirement(InstallRequirement.from_line(line.strip(), None))

    finder = PackageFinder(find_links = [], index_urls = ["http://pypi.python.org/simple/"])

    install_options = []
    global_options = []
    requirement_set.prepare_files(finder, force_root_egg_info = False, bundle = False)
    requirement_set.install(install_options, global_options)

    updates = 0
    failed = 0
    for requirement in requirement_set.requirements.values():
        updates += 1 if requirement.install_succeeded else 0
        failed += 1 if not requirement.install_succeeded and not requirement.satisfied_by else 0

    if failed > 0:
        print 'Failed installing'

    return updates > 0


if __name__ == '__main__':
    if updatedRequirements():
        args = [sys.executable] + [os.path.join(base_path, __file__)] + sys.argv[1:]
        subprocess.Popen(args)
    else:
        try:
            l = Loader()
            l.daemonize()
            l.run()
        except KeyboardInterrupt:
            pass
        except SystemExit:
            raise
        except socket.error as (nr, msg):
            # log when socket receives SIGINT, but continue.
            # previous code would have skipped over other types of IO errors too.
            if nr != 4:
                try:
                    l.log.critical(traceback.format_exc())
                except:
                    print traceback.format_exc()
                raise
        except:
            try:
                # if this fails we will have two tracebacks
                # one for failing to log, and one for the exception that got us here.
                l.log.critical(traceback.format_exc())
            except:
                print traceback.format_exc()
            raise
