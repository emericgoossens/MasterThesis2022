# FLAGS and FIELDS concerning interrupts
# Registering if an interrupt is pending
interrupt_present_flag = False
# Registering the last pending interrupt
pending_interrupt = None


# This class represents interrupts. For now these interrupts are only used as timer interrupts.
# The different fields of the interrupt class will on HardWare typically be some flags in dedicated registers.
class Interrupt:
    def __init__(self, is_timer_interrupt, triggered_by):
        self.timer_interrupt = is_timer_interrupt
        self.triggered_by = triggered_by

    # Return if the given interrupt is a timer interrupt, thus if a timer will be associated with this interrupt.
    def is_timer_interrupt(self):
        return self.timer_interrupt

    # Return the element that produced the interrupt, this could be a timer, an external resource, etc.
    def trigger(self):
        return self.triggered_by


# Return a new interrupt instance with information about what triggered it and if it is a timer interrupt.
def new_interrupt(is_timer_interrupt, triggered_by):
    return Interrupt(is_timer_interrupt, triggered_by)