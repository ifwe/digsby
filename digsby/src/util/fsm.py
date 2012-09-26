from .observe import Observable

class StateMachine(Observable):
    def __init__(self, name, states_list, start_state = None):
        Observable.__init__(self)
        self.nodes = {}
        self.name = name
        for state in states_list:
            self.nodes[state] = {}

        self._current_state = None
        self.state = start_state

    def create_trans(self, from_state, to_state, input):
        assert from_state in self.nodes
        assert to_state   in self.nodes
        if not isinstance(input, basestring):
            for iota in input:
                self.nodes[from_state][iota] = to_state
        else:
            self.nodes[from_state][input] = to_state

    def process(self, input):
        if self.state not in self.nodes:
            return
        try:
            curr_node = self.nodes[self.state]
        except Exception, e:
            print self.nodes.keys(), self.state
            raise

        if input in curr_node:
            self.state = curr_node[input]

        return self.state

    def set_state(self, state):
        oldstate, self._current_state = self._current_state, state
        self.notify('state', oldstate, state)

    state = property(lambda self: self._current_state, set_state)

class StateManager(list):

    def __init__(self, important_states=None):
        list.__init__(self)
        self.important_states = important_states or []

    def add_machine(self, machine):
        if machine not in self:
            self.append(machine)
            machine.add_observer(self.machine_changed, "state")

    def machine_changed(self, src, attr, _old, new):
        important_machines = [machine for machine in self
                              if machine.state in self.important_states]
        other_machines = [machine for machine in self
                          if machine.state not in self.important_states]
        [machine.process(src.name + "_" + new) for machine in important_machines]
        [machine.process(src.name + "_" + new) for machine in other_machines]
