import Interrupt as i

# FLAGS and FIELDS concerning Timers
# A list of the currently active timers
timer_list = []


# A class of timers. Each timer has a name, a boolean indicating if it is a budget_timer
# (scheduled to interrupt tasks that try to go over budget) and a counter representing its remaining lifetime.
# If it is a budget timer then the task for which it is meant to delimit the budget, is linked to it.
class Timer:
    def __init__(self, name, budget_timer, value, task):
        self.name = name
        self.budget_timer = budget_timer
        self.counter = value
        # Task can be None
        self.task = task

    # Decrement the counter of the given timer
    def decrement_counter(self):
        self.counter = self.counter - 1
        if self.is_finished():
            self.generate_interrupt()

    # Return if the timer has finished, if the counter has reached zero.
    def is_finished(self):
        return self.counter <= 0

    # Interrupt the CPU by setting the interrupt flag to true and adding a new interrupt.
    def generate_interrupt(self):
        i.interrupt_present_flag = True
        i.pending_interrupt = i.new_interrupt(is_timer_interrupt=True, triggered_by=self)

    # Remove the timer from the CPU
    def remove_timer(self):
        global timer_list
        try:
            timer_list.remove(self)
        # It can be that the timer was already removed, in that case do nothing
        except ValueError:
            pass

    # Return the task where this timer is associated to
    def get_task_of_timer(self):
        return self.task

    # Return whether this timer is a budget timer
    def is_budget_timer(self):
        return self.budget_timer


# Run the processor clock for one cycle. This means that all timers will be decremented with one tick.
def run_clock():
    for timer in timer_list:
        timer.decrement_counter()


# Return the timer that is associated with the given task. If no timer exists for this task then return None.
def get_timer_associated_with_task(task):
    for timer in timer_list:
        if timer.get_task_of_timer() == task:
            return timer
    return None


# Equivalent to get_timer_associated_with_task but then to return timer of type 'budget_timer' if one can be found.
def get_budget_timer_associated_with_task(task):
    for timer in timer_list:
        if timer.get_task_of_timer() == task and timer.is_budget_timer():
            return timer
    return None


# Add a timer to the processor
def add_timer_to_mcu(timer):
    timer_list.append(timer)


# Return all the timers that are currently active.
def get_timers():
    return timer_list


