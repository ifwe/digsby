from util.fsm import StateMachine

if __name__ == "__main__":
    machine = StateMachine('status', ["off", "fleft", "left", "bleft",
                            "fright", "right", "bright"], "left")

    machine.create_trans("left", "fleft", "otherleft")

    print machine.process("otherleft")

#>>> states = ["off", "fleft", "left", "bleft", "fright", "right", "bright"]
#>>> ops = ["buddy_icon_disabled", "buddy_icon_enabled"]
#>>> ops2 = ["enabled", "disabled", "off", "fleft", "left", "bleft", "fright", "right", "bright"]
#>>> ["status_" + op for op in ops2]
#['status_enabled', 'status_disabled', 'status_off', 'status_fleft', 'status_left', 'status_bleft', 'status_fright', 'status_right', 'status_bright']
#>>> ops3 = ["status_" + op for op in ops2]
#>>> for state in states:
#...     for op in ops + ops3:
#...         print "machine.create_transition('%s', '%s', None)" % (state, op)

    import sys
    sys.exit(0)

    """
    below is what I believe to be a complete state machine definition for
    a status or service icon, neglecting the off states.
    so far, my idea for implementation is incomplete, it is lacking
    the interaction between state machines necessary for the whole thing to
    work.  One can see, however, that the number of needed transitions is
    much smaller than the possible ones.
    """

    machine = None
    to_state = None

    'buddy_icon_disabled'
    'buddy_icon_left'
    'buddy_icon_right'

    states = ['fleft', 'left', 'bleft_l', 'bright_l', 'bleft_r', 'bright_r', 'right', 'fright']

    #definition of simple transitions (someone else wants my spot)

    #I'm in the far left, other bumps me
    machine.create_trans('fleft', 'left', 'other_fleft')

    #I'm in the left, other bumps me
    machine.create_trans('left', 'fleft', 'other_left')

    #buddy icon is on the left
    #badge on left
    machine.create_trans('bleft_l', 'bright_l', 'other_bleft_l')
    #badge on right
    machine.create_trans('bright_l', 'bleft_l', 'other_bright_l')

    #buddy icon is on the right
    #badge on left
    machine.create_trans('bleft_r', 'bright_r', 'other_bleft_r')
    #badge on right
    machine.create_trans('bright_r', 'bleft_r', 'other_bright_r')

    #I'm in the far right, other bumps me
    machine.create_trans('fright', 'right', 'other_fright')

    #I'm in the right, other bumps me
    machine.create_trans('right', 'fright', 'other_right')

    #definition of buddy icon translation
    #badge on left
    machine.create_trans('bleft_l', 'bleft_r', 'buddy_icon_right')
    #badge on right
    machine.create_trans('bright_l', 'bright_r', 'buddy_icon_right')
    #badge on left
    machine.create_trans('bleft_r', 'bleft_l', 'buddy_icon_left')
    #badge on right
    machine.create_trans('bright_r', 'bright_l', 'buddy_icon_left')


    #these are the hard ones
    #buddy icon disabled.  where to go
    #ok, the definition is easy, the trouble is, you have to tell them in the
    #correct order.  If you do, the state machines do the heavy lifting for you
    #else, you get the wrong result
    machine.create_trans('bleft_l', 'left', 'buddy_icon_disabled')
    machine.create_trans('bright_l', 'left', 'buddy_icon_disabled')
    machine.create_trans('bleft_r', 'right', 'buddy_icon_disabled')
    machine.create_trans('bright_r', 'right', 'buddy_icon_disabled')

    #example
    states1 = ['off', 'fleft', 'left', 'bleft_l', 'bright_l',
               'bleft_r', 'bright_r', 'right', 'fright']
    states2 = ['off', 'left', 'right']
    manager = StateManager()
    status_machine = StateMachine("status", states1, "off")
    service_machine = StateMachine("service", states1, "off")
    buddy_icon_machine = StateMachine("buddy_icon", states2, "off")
    manager.add_machine(status_machine)
    manager.add_machine(service_machine)
    manager.add_machine(buddy_icon_machine)

    status_machine.create_trans('fleft', 'left', 'service_fleft')
    status_machine.create_trans('left', 'fleft', 'service_left')
    status_machine.create_trans('bleft_l', 'bright_l', 'service_bleft_l')
    status_machine.create_trans('bright_l', 'bleft_l', 'service_bright_l')
    status_machine.create_trans('bleft_r', 'bright_r', 'service_bleft_r')
    status_machine.create_trans('bright_r', 'bleft_r', 'service_bright_r')
    status_machine.create_trans('fright', 'right', 'service_fright')
    status_machine.create_trans('right', 'fright', 'service_right')
    status_machine.create_trans('bleft_l', 'bleft_r', 'buddy_icon_right')
    status_machine.create_trans('bright_l', 'bright_r', 'buddy_icon_right')
    status_machine.create_trans('bleft_r', 'bleft_l', 'buddy_icon_left')
    status_machine.create_trans('bright_r', 'bright_l', 'buddy_icon_left')
    status_machine.create_trans('bleft_l', 'left', 'buddy_icon_off')
    status_machine.create_trans('bright_l', 'left', 'buddy_icon_off')
    status_machine.create_trans('bleft_r', 'right', 'buddy_icon_off')
    status_machine.create_trans('bright_r', 'right', 'buddy_icon_off')

    service_machine.create_trans('fleft', 'left', 'status_fleft')
    service_machine.create_trans('left', 'fleft', 'status_left')
    service_machine.create_trans('bleft_l', 'bright_l', 'status_bleft_l')
    service_machine.create_trans('bright_l', 'bleft_l', 'status_bright_l')
    service_machine.create_trans('bleft_r', 'bright_r', 'status_bleft_r')
    service_machine.create_trans('bright_r', 'bleft_r', 'status_bright_r')
    service_machine.create_trans('fright', 'right', 'status_fright')
    service_machine.create_trans('right', 'fright', 'status_right')
    service_machine.create_trans('bleft_l', 'bleft_r', 'buddy_icon_right')
    service_machine.create_trans('bright_l', 'bright_r', 'buddy_icon_right')
    service_machine.create_trans('bleft_r', 'bleft_l', 'buddy_icon_left')
    service_machine.create_trans('bright_r', 'bright_l', 'buddy_icon_left')
    service_machine.create_trans('bleft_l', 'left', 'buddy_icon_off')
    service_machine.create_trans('bright_l', 'left', 'buddy_icon_off')
    service_machine.create_trans('bleft_r', 'right', 'buddy_icon_off')
    service_machine.create_trans('bright_r', 'right', 'buddy_icon_off')
