'''
Created on Apr 9, 2012

@author: "Michael Dougherty <mdougherty@tagged.com>"
'''
import logging

__all__ = ['phase', 'Clean', 'Checkout', 'Compile', 'Test', 'Freeze', 'Prepare', 'Verify', 'Package', 'Upload', 'Deploy']

class Strategy(type):
    _strategies = {}
    def __new__(cls, name, bases, dct):
        new_cls = type.__new__(cls, name, bases, dct)
        strat = getattr(new_cls, 'strategy')
        if strat is not None:
            phase = getattr(new_cls, 'phase')
            Strategy._strategies.setdefault(phase, {})[strat] = new_cls
        return new_cls

def phase(phase, strategy, target, **options):
    return Strategy._strategies[phase][strategy](target, **options)

class DeploymentPhase(object):
    __metaclass__ = Strategy
    strategy = None

    def __init__(self, target, **options):
        self.target = target
        self.options = options
        for key, val in options.items():
            setattr(self, key, val)

    def pre(self):
        target_pre = getattr(self.target, 'pre_%s' % self.phase, None)
        if target_pre is not None:
            # Allow target to configure this for our phase
            target_pre(self)
        if self.strategy is not None:
            target_pre_strat = getattr(self.target, 'pre_%s_%s' % (self.phase, self.strategy), None)
            if target_pre_strat is not None:
                # Allow target to configure this for our phase and strategy
                target_pre_strat(self)

        print('*** starting %s (%s) ***' % (self.phase, self.strategy))

    def do(self):
        pass

    def post(self, *exc_info):
        target_post = getattr(self.target, 'post_%s' % self.phase, None)
        if target_post is not None:
            # Allow target to configure this for our phase
            target_post(self)
        if self.strategy is not None:
            target_post_strat = getattr(self.target, 'post_%s_%s' % (self.phase, self.strategy), None)
            if target_post_strat is not None:
                # Allow target to configure this for our phase and strategy
                target_post_strat(self)

    def __enter__(self):
        self.pre()
        return self

    def __exit__(self, *exc_info):
        if any(exc_info):
            import traceback; traceback.print_exception(*exc_info)
        return self.post()

class Clean(DeploymentPhase):
    phase = 'clean'
class Checkout(DeploymentPhase):
    phase = 'checkout'
class Compile(DeploymentPhase):
    phase = 'compile'
class Test(DeploymentPhase):
    phase = 'test'
class Freeze(DeploymentPhase):
    phase = 'freeze'
class Prepare(DeploymentPhase):
    phase = 'prepare'
class Verify(DeploymentPhase):
    phase = 'verify'
class Package(DeploymentPhase):
    phase = 'package'
class Upload(DeploymentPhase):
    phase = 'upload'
class Deploy(DeploymentPhase):
    phase = 'deploy'

if __name__ == '__main__':
    class FakeUploader(Upload):
        strategy = 'fake'

    print Strategy._strategies
    print phase('upload', 'fake')

