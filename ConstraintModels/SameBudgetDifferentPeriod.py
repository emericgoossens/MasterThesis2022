from z3 import *

# This configuration builds on top of the simplest configuration (see SamePeriodSameBudgetSameRelease.py).
# The release is assumed to be at 0 and the budget will be fixed too (and the same for all tasks)
# However, now the period can vary from task to task. It will be bound to be a common divisor of the OBSERVATION_WINDOW
# In this case, only one OBSERVATION_WINDOW length has to be simulated
CLIX_BOUND = 3
NR_TASKS = 3
OBSERVATION_WINDOW = 20
MAX_RUNS = OBSERVATION_WINDOW # this constant is needed to make the model solvable, to make the for-loops usable...
                # It should be at least OBS_WINDOW/CLIX_BOUND
#RELEASE by default at timepoint 0

# --------------Additional rules ---------------------------

# List with the clix-length for the tasks
period_length = [Int("period_%s" % (i+1)) for i in range(NR_TASKS)]


# The period has to be bigger than 0 and cannot be greater than the OBSERVATION_WINDOW.
# It furthermore has to be a divisor of the OBSERVATION_WINDOW.
period_c = [And(period_length[i] > 0, period_length[i] <= OBSERVATION_WINDOW,
                OBSERVATION_WINDOW % period_length[i] == 0)
            for i in range(NR_TASKS)]


# Return the period of the given task
def get_period(taskNr):
    return period_length[taskNr]


# Return whether the timepoint is in between begin and end, including the begin and end-point.
def in_between(time, begin, end):
    return And(begin <= time, time <= end)


# PeriodNr starts at 0 and ends at (OBSERVATION_WINDOW/period_length) - 1
def get_begin_of_period(taskNr, periodNr):
    return periodNr * get_period(taskNr)


def get_begin_of_period_given_timepoint(taskNr, time):
    return (Sum([If(get_begin_of_period(taskNr, periodNr) <= time, 1, 0) for periodNr in range(MAX_RUNS)])
            - 1) * get_period(taskNr)


# Return the number of cycles the task has run in between the two time points
def nr_cycles_ran_in_between_timepoints(sched, taskNr, begin, end):
    return \
        Sum([If(
            And(in_between(j, begin, end - 1), sched[taskNr][j]) #end - 1 because in-between includes the endpoints
            , 1, 0)
            for j in range(OBSERVATION_WINDOW)])


# Return whether the task has run less than one clix within it's period
def task_will_run_not_longer_than_one_clix_per_period(sched, taskNr, periodNr):
    return nr_cycles_ran_in_between_timepoints(sched, taskNr,
                                               get_begin_of_period(taskNr, periodNr),
                                               get_begin_of_period(taskNr, periodNr + 1)) \
           <= CLIX_BOUND


# Return whether the task has run at least a complete clix this period
def task_has_fully_run_this_period(sched, taskNr, periodNr):
    return nr_cycles_ran_in_between_timepoints(sched, taskNr,
                                               get_begin_of_period(taskNr, periodNr),
                                               get_begin_of_period(taskNr, periodNr + 1)) \
           >= CLIX_BOUND


def get_nr_of_runs(taskNr):
    return OBSERVATION_WINDOW/get_period(taskNr)


# NrOfPeriods is the number of periods this task has to run within the observation window (see get_nr_of_runs(...))
# periodNr will range from 0 to NrOfPeriods - 1
def task_has_run_fully_all_periods(sched, taskNr, NrOfPeriods):
    return And([Or(task_has_fully_run_this_period(sched, taskNr, periodNr), periodNr >= NrOfPeriods)
                for periodNr in range(MAX_RUNS)])

# --------------Adapted code---------------------------------------------------------------------------------
# The differences are located at the points where first the DEFAULT_PERIOD parameter was used...
# In most cases, this was where an iteration over all the time points was needed (there OBSERVATION_WINDOW is used instead)
# In some cases, for the completion of a task however, the task period (get_period(taskNr)) has to be taken into account
# Because a task with a short period can run multiple times in the OBSERVATION_WINDOW time.

# Print the schedule in a more readable way
def print_schedule(sched_matrix, periods):
    numbers = ""
    print("-------------SCHEDULE----------------------------------")
    for j in range(OBSERVATION_WINDOW):
        if j < 10:
            numbers += "   " + str(j) + "   "
        else:
            numbers += "  " + str(j) + "   "
    print(numbers)
    for i in range(NR_TASKS):
        matrix_row = ""
        for j in range(OBSERVATION_WINDOW):
            if sched_matrix[i][j]:
                matrix_row += " True  "
            else:
                matrix_row += " False "
            if j % periods[i].as_long() == (periods[i].as_long() - 1):
                matrix_row = matrix_row[:-1]
                matrix_row += "|"
        print(matrix_row)
    print("--------------------------------------------------------")


# Based on https://ericpony.github.io/z3py-tutorial/guide-examples.htm
# Matrix with the tasks on the rows (NR_TASKS) and the timepoints on the columns (OBSERVATION_WINDOW)
X = [[Bool("x_%s_%s" % (i+1, j+1)) for j in range(OBSERVATION_WINDOW)]
     for i in range(NR_TASKS)]


# Return if some task is running at the given time
def some_task_is_running(sched, time):
    return Or([sched[i][time] for i in range(NR_TASKS)])


# All tasks have finished their periodic run
# has run longer than the default clix length, between the begin of period and time
def finished_periodic_run(sched, time, taskNr):
    return nr_cycles_ran_in_between_timepoints(sched, taskNr,
                                               get_begin_of_period_given_timepoint(taskNr, time),
                                               time) \
           >= CLIX_BOUND


# Return if all tasks have done all their work (so all the necessary runs) before the given time
# The task needs to have finished its run within the current period.
def all_tasks_finished_their_run(sched, time):
    return And([finished_periodic_run(sched, time, i) for i in range(NR_TASKS)])


# Return if the task-run was non-interrupted (2 transitions, one start and end)
# or doesn't run at all (0 transitions)
def atomicity_of_one_run(sched, taskNr, periodNr):
    current_period_begin = get_begin_of_period(taskNr, periodNr)
    period = get_period(taskNr)
    nr_transitions = Sum([If(
        in_between(j, current_period_begin, current_period_begin + period - 2),
        # Because j + 1 == current_period_begin+period - 1 should be last point
        Sum([If(Xor(sched[taskNr][j], sched[taskNr][j + 1]), 1, 0),  # There is a transition
             If(And(j == current_period_begin, sched[taskNr][j]), 1, 0),  # the  task starts at begin of timeframe
             If(And(j + 1 == current_period_begin + period - 1, sched[taskNr][j + 1]), 1, 0)]),
             # the task ends at end of timeframe
        0)
        for j in range(OBSERVATION_WINDOW - 1)])  # OBS_WINDOW - 1 because the j + 1 will point till the next time point
    return Or(nr_transitions == 2, nr_transitions == 0)


# All runs have to be atomic
def atomicity_of_task(sched, taskNr):
    return And([Or(atomicity_of_one_run(sched, taskNr, periodNr), periodNr >= get_nr_of_runs(taskNr))
                for periodNr in range(MAX_RUNS)])

# FOR EARLIEST DEADLINE


# Return whether the task that starts at this time point is the task with the nearest deadline.
def starting_task_has_nearest_deadline(sched, time):
    # If the task has started now, then its deadline should be the nearest one.
    # Task has started clix:
    #       * is running now + is only running first cycle
    # If this is the case, the task should be the one with the smallest period
    # All other ready tasks should have higher period
    return And([
        Implies(
            And(sched[i][time],
                nr_cycles_ran_in_between_timepoints(sched, i,
                                                    get_begin_of_period_given_timepoint(i, time), time + 1) == 1),
            is_ready_with_nearest_deadline(sched, time, i))
        for i in range(NR_TASKS)])


# Return the following deadline for the given task compared to the time point.
# This is equal to the begin of the next period.
def get_deadline_given_time_point(time, taskNr):
    return get_begin_of_period_given_timepoint(taskNr, time) + period_length[taskNr]


# Return whether the given task is the ready task with the nearest deadline.
def is_ready_with_nearest_deadline(sched, time, taskNr):
    # Either the other tasks have not the nearest deadline, or they ran already within their period.
    return And([Or(get_deadline_given_time_point(time, taskNr) <= get_deadline_given_time_point(time, j),
                   finished_periodic_run(sched, time, j))
                for j in range(NR_TASKS)])


# Constraints
# Each cell is true or false: is already implied by the cells being of type bool

# Only one task can run at the same moment (in the same column, only one true-value)
no_overlap_c = [Sum([If(X[i][j], 1, 0) for i in range(NR_TASKS)]) <= 1 for j in range(OBSERVATION_WINDOW)]

# A task can only start after release: is already done by having some finite number of time points starting at 0

# A task should run for maximal a certain amount of time ( <= CLIX_BOUND)
run_time_c = [And([Or(task_will_run_not_longer_than_one_clix_per_period(X, i, periodNr), periodNr >= get_nr_of_runs(i))
                   for periodNr in range(MAX_RUNS)])
              for i in range(NR_TASKS)]
#
# To meet its requirements, a task should at least run the clix_length (scheduling goal, >= clix_length)
sched_goal_c = [task_has_run_fully_all_periods(X, i, get_nr_of_runs(i)) for i in range(NR_TASKS)]
# The negation of the scheduling goal, has some task missed its deadline?
neg_sched_goal = Or([Not(task_has_run_fully_all_periods(X, i, get_nr_of_runs(i))) for i in range(NR_TASKS)])

# Atomicity (no preemption possible)
atomicity_c = [atomicity_of_task(X, i) for i in range(NR_TASKS)]

# ---EDF Constraints---
# There will be at each moment one task running, or all tasks have finished running
# So for each time point j: either some task is running, or all tasks have currently finished their periodic run.
no_idling_when_tasks_ready_c = [Or(some_task_is_running(X, j), all_tasks_finished_their_run(X, j))
                                for j in range(OBSERVATION_WINDOW)]

# The task running, will be that with the earliest deadline:
earliest_deadline_first_c = [starting_task_has_nearest_deadline(X, j) for j in range(OBSERVATION_WINDOW - 1)]

# ---Acceptance test---
# The following acceptance test is not sufficient. It only checks if everything would fit inside the observation
# window, but does not take care of different periodicities.
# acc_test = Sum([get_nr_of_runs(i) * CLIX_BOUND for i in range(NR_TASKS)]) <= OBSERVATION_WINDOW
# Sufficient acceptance test (but very restrictive). It ensures that each period is at least big enough to contain
# one execution of each task. This is sufficient.
acc_test = And([NR_TASKS * CLIX_BOUND <= period_length[i] for i in range(NR_TASKS)])

# Add all constraints to the solver
s = Solver()
s.add(no_overlap_c)
s.add(run_time_c)
s.add(atomicity_c)
s.add(no_idling_when_tasks_ready_c)

s.add(period_c)
s.add(earliest_deadline_first_c)

# ---Check if the acceptance test is sufficient---
# There are different phrasings:
# - The acceptance test implies schedulability
# s.add(Implies(acc_test, And(sched_goal_c)))
# - It should not be possible to have a situation that satisfies the acc_test and misses deadlines
s.add(And(acc_test, neg_sched_goal))
# - Or in this simple case, you can also manually check the acceptance test and then check if some
# bad schedule can be found
# s.add(neg_sched_goal)

# Check if there are at least some schedulable task sets that satisfy the acceptance test
# To be sure that the acceptance test is not far too restrictive
# s.add(And(sched_goal_c), acc_test)

# Checking if the acceptance test is necessary: if this gives unsat then a system is only schedulable if accepted
# If a test is both necessary and sufficient, then it is exact.
# s.add(Not(acc_test), And(sched_goal_c))

# print(s.assertions())
value = s.check()
print(value)
if value == sat:
    m = s.model()
    schedule = [[m.evaluate(X[i][j]) for j in range(OBSERVATION_WINDOW)] for i in range(NR_TASKS)]
    periods = [m.evaluate(period_length[i]) for i in range(NR_TASKS)]
    print("Periods: " + str(periods))
    print_schedule(schedule, periods)

print(s.statistics())

