import Timer as tim
import Task
import MCU as mcu
# The policy that is used to schedule: This policy can be easily changed to another policy
import EDF_Policy_Periodic as pol

# FLAGS and FIELDS concerning the scheduling operation
# Tasks that are ready to be scheduled. Aperiodic tasks should be treated differently
# by the scheduling policy than periodic tasks. NOTE: Aperiodic tasks are not fully supported yet
periodic_ready_queue = []
aperiodic_ready_queue = []

# Current first task, will be scheduled or is already scheduled
first_task = None
# Enclaves that are sleeping (sleep())
sleeping_tasks = []

# Constant reflecting the worst-case execution time of the scheduler
WCET_SCHEDULER = 20
# Interrupt mask flag that is set when running the scheduler or executing a section of bounded atomicity
interrupt_mask = False
# Variable registering the scheduler task. This tasks has different aspects compared to normal tasks.
dummy_scheduler_task = None


# Initialize the scheduler task. The max_nr_time_points are used to make the scheduler_task look like a normal task
# to make visualization easier, but has no real implications for the run of the program.
def init_scheduler(max_nr_time_points):
    global dummy_scheduler_task
    dummy_scheduler_task = Task.SchedulerTask("Scheduler", WCET_SCHEDULER, max_nr_time_points)


# Return the scheduler task
def get_scheduler_task():
    return dummy_scheduler_task


# Submit a new enclave to this scheduler. If it is already present then an error is produced.
# Before submitting the enclave, the acceptance test is performed.
# If the enclave is accepted, it will be added to the ready queue,
# otherwise false will be returned
def submit_new_task(new_task, current_time):
    if new_task in get_all_tasks():
        raise ValueError
    # Using the acceptance test to ensure that the system is still schedulable
    # This assumes the acceptance test is sufficient. In the current case the acceptance test will accept everything
    # for illustration purposes. In a real system, this function should be implemented in the scheduler or the
    # scheduler should use some computed accepting value, received externally from a trusted component.
    if pol.is_schedulable(new_task, get_all_tasks(), current_time + 1):
        pol.add_task_to_queue(new_task, periodic_ready_queue, aperiodic_ready_queue)
        return True
    return False


# This function assumes that the system is schedulable (system has passed the acceptance test)
# It will run and schedule either a task or None, when no task is waiting. It makes use of the scheduling policy
# to determine which task has to be scheduled next. The interrupt mask is used to ensure that the scheduling task will
# not be interrupted before completion.
def run_scheduler(current_time, interrupt):
    global first_task
    global interrupt_mask
    # The CPU will set this to false after termination of the scheduler task
    interrupt_mask = True

    # Start the scheduler enclave
    dummy_scheduler_task.schedule_task()

    # If an interrupt is present, then it should be handled.
    if interrupt is not None:
        handle_interrupt(current_time, interrupt)

    # A new task is scheduled,
    # so the current budget timer can be removed (a new timer instance will be set for the new task)
    # The time that is already ran will be decremented from the periodic budget counter, when some task is
    # preempted before completion of its period.
    current_budget_timer = tim.get_budget_timer_associated_with_task(get_current_scheduled())
    if current_budget_timer is not None:
        current_budget_timer.remove_timer()

    # Deschedule the previously scheduled task
    if first_task is not None and first_task.is_scheduled():
        first_task.deschedule_task(current_time)

    # Find the task to be scheduled according to the policy, can be the same one.
    first_task = pol.get_next_scheduled(periodic_ready_queue, aperiodic_ready_queue, current_time)

    # If there is a task that can be scheduled, then schedule it and add a budget timer (this timer will fire right
    # after the end of the budget of the task, to ensure that control goes back to the scheduler).
    # NOTE: for the moment a task is not descheduled if it is not finished/terminated. This is done for simplicity, but
    #       could of course be adapted
    if first_task is not None:
        #if not first_task.is_scheduled():
        first_task.schedule_task()
        add_budget_timer(current_time, first_task)


# Add a budget timer for the given task. A budget timer is used to prevent tasks from going out of budget. The timer
# interrupt will make the scheduler gain control, after which a problematic task can be terminated.
def add_budget_timer(current_time, task):
    # It is assumed, that the scheduler already ran before the beginning of the time frame.
    if current_time == 0:
        expected_end = task.get_periodic_budget() + 1
    else:
        # The expected end should account also for the delay by the scheduler.
        expected_end = task.get_periodic_budget() + WCET_SCHEDULER + 1
    # Add a new budget timer to the registered timers.
    timer1 = tim.Timer("budget", budget_timer=True, value=expected_end, task=task)
    tim.add_timer_to_mcu(timer1)


# Add a sleep timer for the given task. This timer is needed to make the scheduler wake up the task
# when sleeping is over.
def add_sleep_timer(current_time, task):
    value = task.get_end_of_previous_period() - current_time
    timer1 = tim.Timer("sleep", budget_timer=False, value=value, task=task)
    tim.add_timer_to_mcu(timer1)


# Handle the given interrupt and other potential timers that are finished meanwhile.
# Note: if other interrupts would be added in the future, this function should be adapted.
def handle_interrupt(current_time, interrupt):
    # for the moment only timer interrupts are accepted.
    if interrupt.is_timer_interrupt():
        for timer in tim.get_timers().copy():
            if timer.is_finished():
                handle_timer(timer, current_time)
    else:
        raise TypeError("Type of interrupt not supported yet")


# Handle the timer. Check if it is a budget timer (set by the scheduler), and flag the misbehaving task.
def handle_timer(timer, current_time):
    task = timer.get_task_of_timer()
    if timer.is_budget_timer():
        if task == get_current_scheduled():
            task.flag_out_of_budget()
            terminate_execution(task, current_time)
    else:
        # if it was a sleep timer, then the task should be replaced in the ready queue.
        sleeping_tasks.remove(task)
        pol.add_task_to_queue(task, periodic_ready_queue, aperiodic_ready_queue)
    timer.remove_timer()


# Terminate the execution of the given task. The task is descheduled, corresponding timers are removed and interrupts
# are re-enabled.
def terminate_execution(task, current_time):
    task.deschedule_task(current_time)
    tim.get_timer_associated_with_task(task).remove_timer()
    mcu.enable_interrupts_system_call()

    if task.is_periodic():
        add_sleep_timer(current_time, task)
        periodic_ready_queue.remove(task)
        sleeping_tasks.append(task)
    else:
        remove_task(task)


# Getters and Setters #


# Return all tasks on this scheduler
def get_all_tasks():
    return periodic_ready_queue + aperiodic_ready_queue + sleeping_tasks


# Remove a task from the scheduler
def remove_task(task):
    global sleeping_tasks
    global periodic_ready_queue
    global aperiodic_ready_queue

    if task in sleeping_tasks:
        sleeping_tasks.remove(task)
    elif task.is_periodic():
        periodic_ready_queue.remove(task)
    else:
        aperiodic_ready_queue.remove(task)


# Return the currently first scheduled task
def get_current_scheduled():
    return first_task


# Return if there are tasks in the ready queue
def has_jobs_waiting(current_time):
    return len(aperiodic_ready_queue) > 0 or len(periodic_ready_queue) > 0


# Debugging purposes + Illustration purposes #

# Print the state of the scheduler
def to_string_scheduler():
    s = "Scheduler: \n"
    for enc in aperiodic_ready_queue:
        s += enc.to_string() + "\n"
    return s

