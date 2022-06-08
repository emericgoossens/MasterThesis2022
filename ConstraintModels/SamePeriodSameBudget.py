from z3 import *

# In this case, only one period length has to be simulated, to check if it is possible
CLIX_BOUND = 7
NR_TASKS = 4
DEFAULT_PERIOD = 21 # T1: D1: 20, D2: 40,  -> max_diff between 2 runs is 2*p - 2*b
# RELEASE by default at time-point 0


# Print the schedule in a more readable way
def print_schedule(sched_matrix):
    numbers = ""
    print("-------------SCHEDULE----------------------------------")
    for j in range(DEFAULT_PERIOD):
        if j < 10:
            numbers += "   " + str(j) + "   "
        else:
            numbers += "  " + str(j) + "   "
    print(numbers)
    for i in range(NR_TASKS):
        matrix_row = ""
        for j in range(DEFAULT_PERIOD):
            if sched_matrix[i][j]:
                matrix_row += " True  "
            else:
                matrix_row += " False "
            if j % DEFAULT_PERIOD == (DEFAULT_PERIOD - 1):
                matrix_row = matrix_row[:-1]
                matrix_row += "|"
        print(matrix_row)
    print("--------------------------------------------------------")


# Based on https://ericpony.github.io/z3py-tutorial/guide-examples.htm
# Matrix with the tasks on the rows (NR_TASKS) and the timepoints on the columns (DEFAULT_PERIOD)
X = [[Bool("x_%s_%s" % (i+1, j+1)) for j in range(DEFAULT_PERIOD)]
     for i in range(NR_TASKS)]


# Return if some task is running at the given time
def some_task_is_running(sched, time):
    return Or([sched[i][time] for i in range(NR_TASKS)])


# Return if all tasks have finished before the given time
def all_tasks_finished(sched, time):
    return And([task_finished_at_time_point(sched, i, time) for i in range(NR_TASKS)])


# Return the number of cycles the task has run till the given time point
def nr_cycles_ran_before_time(sched, taskNr, time):
    return Sum([If(sched[taskNr][j], 1, 0) for j in range(time)])


# Return if the given task has already finished before the given time
def task_finished_at_time_point(sched, taskNr, time):
    return nr_cycles_ran_before_time(sched, taskNr, time) >= CLIX_BOUND


# Return if the task-run was non-interrupted (2 transitions, one start and end)
# or doesn't run at all (0 transitions)
def atomicity_of_task(sched, taskNr):
    nr_transitions = Sum([
        Sum([If(Xor(sched[taskNr][j], sched[taskNr][j + 1]), 1, 0),  # There is a transition
             If(And(j == 0, sched[taskNr][j]), 1, 0),  # the  task starts at begin of timeframe
             If(And(j + 1 == DEFAULT_PERIOD - 1, sched[taskNr][j + 1]), 1, 0)]) # the  task ends at end of timeframe
        for j in range(DEFAULT_PERIOD - 1)])  # OBS_WINDOW - 1 because the j + 1 will point till the next time point
    return Or(nr_transitions == 2, nr_transitions == 0)


# Constraints
# Each cell is true or false: is already implied by the cells being of type bool

# Only one task can run at the same moment (in the same column, only one true-value)
no_overlap_c = [Sum([If(X[i][j],1,0) for i in range(NR_TASKS)]) <= 1 for j in range(DEFAULT_PERIOD)]

# A task can only start after release: is already done by having some finite number of time points starting at 0

# A task should run for maximal a certain amount of time ( <= DEFAULT_CLIX_LENGTH)
run_time_c = [nr_cycles_ran_before_time(X, i, DEFAULT_PERIOD) <= CLIX_BOUND for i in range(NR_TASKS)]

# To meet its requirements, a task should at least run the clix_length (scheduling goal, >= clix_length)
sched_goal_c = [task_finished_at_time_point(X, i, DEFAULT_PERIOD) for i in range(NR_TASKS)]
# The negation of the scheduling goal, has some task missed its deadline?
neg_sched_goal = Or([Not(task_finished_at_time_point(X, i, DEFAULT_PERIOD)) for i in range(NR_TASKS)])

# Atomicity (no preemption possible)
atomicity_c = [atomicity_of_task(X, i) for i in range(NR_TASKS)]

# ---EDF Constraints---
# There will be at each moment one task running, or all tasks have finished running
no_idling_when_tasks_ready_c = [Or(some_task_is_running(X, j), all_tasks_finished(X, j)) for j in range(DEFAULT_PERIOD)]
# The task running, will be that with the earliest deadline: in this simple case all the tasks have the same deadline,
#   so no constraint is needed...

# ---Acceptance test---
acc_test = [NR_TASKS * CLIX_BOUND <= DEFAULT_PERIOD for i in range(NR_TASKS)]

# Add all constraints to the solver
s = Solver()
s.add(no_overlap_c)
s.add(run_time_c)
s.add(atomicity_c)
s.add(no_idling_when_tasks_ready_c)

# ---Check if the acceptance test is sufficient---
# There are different phrasings, only one may be used at a time (uncomment the needed one)!!!:
# - The acceptance test implies schedulability
# s.add(Implies(And(acc_test), And(sched_goal_c)))
# - It should not be possible to have a situation that satisfies the acc_test and misses deadlines
s.add(And(acc_test + [neg_sched_goal]))
# - Or in this simple case, a manually check of the acceptance test is also possible, by checking if some
# bad schedule can be found
# s.add(neg_sched_goal)

# It can be interesting to look at valid schedules too. By enabling this goal (and commenting out the above ones)
# s.add(sched_goal_c)


value = s.check()
print(value)
if value == sat:
    m = s.model()
    schedule = [[m.evaluate(X[i][j]) for j in range(DEFAULT_PERIOD)] for i in range(NR_TASKS)]
    print_schedule(schedule)

print(s.statistics())
