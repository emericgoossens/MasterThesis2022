# EDF policy for periodic tasks
# No support is currently provided for aperiodic/sporadic tasks

# All the functions in this file have general headers, to make it possible to just plug in a new policy
# file into the scheduler and it should work.

# Acceptance test: check if system is still schedulable if a new task is added to it.
# NOTE: for a real system, this acceptance test should be not just returning True!
def is_schedulable(new_task, other_tasks, current_time):
    return True


# Add the new task to the ready queues. Depending on the policy the task will be set more at the begin
# or the end of the queues.
def add_task_to_queue(new_task, periodic_ready_queue, aperiodic_ready_queue):
    if not new_task.is_periodic():
        # NOTE: for aperiodic tasks a similar approach as periodic tasks should be followed
        raise ValueError
    else:
        d_task = new_task.get_deadline()
        # Put the task at the right place depending on the deadlines.
        for i in range(len(periodic_ready_queue)):
            if d_task < periodic_ready_queue[i].get_deadline():
                periodic_ready_queue.insert(i, new_task)
                return
        periodic_ready_queue.append(new_task)


# Get the next task to be scheduled. This method for the moment only uses the periodic queue.
# The EDF policy is used to determine which one is the next task. It is assumed that the queues are only
# manipulated through the policy interface and thus that the tasks are in order of increasing deadline.
def get_next_scheduled(periodic_ready_queue, aperiodic_ready_queue, current_time):
    for i in range(len(periodic_ready_queue)):
        first = periodic_ready_queue[0]
        periodic_ready_queue.remove(first)
        add_task_to_queue(first, periodic_ready_queue, aperiodic_ready_queue)
        if first.can_already_run(current_time):
            return first
    # Return None if for the moment no periodic job can run
    return None
