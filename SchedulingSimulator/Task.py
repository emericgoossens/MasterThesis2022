from abc import ABCMeta, abstractmethod
import ConcreteProcess as cp
# NOTE: No support for aperiodic tasks for the moment, but it could be added by adding a subclass here (AperiodicTask)


# This class represents the run-time description of a task. It contains on one hand the specification of a task as done
# by the Software Provider. On the other hand it contains some run-time statistics to be able to enforce the 'contract'
# of the task.
# This is thus the information the scheduler will have a priori (before the first execution of the task),
# namely a pointer to the program code and typical process meta-data (pid, etc), augmented with
# meta-data about the run-time characteristics of the program (period, time it will run, number of clix(), etc.).
# This meta-data will be used for the acceptance test to check if the task can be accepted. Furthermore the scheduler
# will also be using this information to prevent the task from violating its specification
# (e.g., running longer than promised).
class Task(metaclass=ABCMeta):
    def __init__(self, tid, budget, program):
        # Run-time entity corresponding to this description, this will be the real running process/thread
        self.process = cp.new_concrete_process(program)
        # Name of the task
        self.tid = tid
        # Original budget of task
        self.original_budget = budget
        # Remainder of the budget (while running one period)
        self.remainingBudget = budget
        # This becomes true if the tasks remaining budget is exhausted before completion of the task.
        self.ranOutOfBudget = False
        # True if the task is currently scheduled
        self.scheduled = False

    # Simulate the task for one cycle and adapt the description
    @abstractmethod
    def run_for_one_cycle(self):
        pass

    # Setters #

    @abstractmethod
    def schedule_task(self):
        pass

    @abstractmethod
    def deschedule_task(self, current_time):
        pass

    # Getters
    def get_name(self):
        return self.tid

    def get_budget(self):
        return self.original_budget

    def has_ran_out_of_budget(self):
        return self.ranOutOfBudget

    def flag_out_of_budget(self):
        self.ranOutOfBudget = True

    @abstractmethod
    def is_periodic(self):
        pass

    @abstractmethod
    def has_finished_current_task(self):
        pass

    @abstractmethod
    def get_deadline(self):
        pass

    # Return a textual representation of this task, can be used to print statistics about this task.
    @abstractmethod
    def to_string(self):
        pass


# A class of periodic tasks. These tasks run periodically and will then run according to their budget.
# Each period their budget is replenished. The deadline of the task is assumed to be equal to the end of the period.
class PeriodicTask(Task):
    def __init__(self, tid, budget, period, release_time, program):
        # Initialize the general task fields
        Task.__init__(self, tid, budget, program)
        # Period of this task in nr. of cycles
        self.period = period
        # Deadline of this task for the current period, namely the end of the period
        self.periodicDeadline = release_time + period
        # Remainder of the budget of the task for the current period.
        self.remainingPeriodicBudget = budget
        # The end of the previous period for this periodic task, is needed for the scheduler to schedule a sleep timer
        self.endOfPreviousPeriod = release_time

    def run_for_one_cycle(self):
        if not self.scheduled:
            raise ValueError

        self.process.run_for_one_cycle()
        self.remainingPeriodicBudget -= 1

    def schedule_task(self):
        if self.scheduled:
            raise ValueError

        self.scheduled = True
        if not self.process.has_started():
            self.process.start_program()
        self.ranOutOfBudget = False

    def deschedule_task(self, current_time):
        if not self.scheduled:
            raise ValueError
        self.scheduled = False

        # If it has finished, then we can re-initialise the task
        if self.has_finished_current_task() or self.has_ran_out_of_budget():
            self.initialise_periodic_task()

    # Getters
    def is_periodic(self):
        return True

    def get_periodic_budget(self):
        return self.remainingPeriodicBudget

    # Return if the periodic task has finished its current run
    def has_finished_current_task(self):
        return self.process.has_finished()

    # Return if the periodic task should run again, because a new period has begun or the previous run was not ended
    def can_already_run(self, current_time):
        return current_time >= self.endOfPreviousPeriod

    def get_period(self):
        return self.period

    def is_scheduled(self):
        return self.scheduled

    # Return the periodic deadline
    def get_deadline(self):
        return self.periodicDeadline

    def get_end_of_previous_period(self):
        return self.endOfPreviousPeriod

    # HELPER METHODS
    # Initialise the parameters for the next period
    def initialise_periodic_task(self):
        self.remainingPeriodicBudget = self.original_budget
        self.endOfPreviousPeriod = self.periodicDeadline
        self.periodicDeadline = self.endOfPreviousPeriod + self.get_period()
        self.process.reinit_process()

    def to_string(self):
        return "PeriodicTask p=" + str(self.period) + " b=" + str(self.original_budget) \
               + " |deadline : " + str(self.get_deadline())


# This is a special type of task, representing the scheduler task.
class SchedulerTask(Task):
    def __init__(self, tid, budget, max_time_points):
        # Initializing general task
        Task.__init__(self, tid, budget, None)
        # field representing the
        self.max_time_points = max_time_points

    # Simulate the task during one cycle
    def run_for_one_cycle(self):
        self.remainingBudget -= 1

        # Setters #

    def schedule_task(self):
        self.remainingBudget = self.original_budget

    def deschedule_task(self, current_time):
        raise ValueError

    def is_periodic(self):
        raise ValueError

    def has_finished_current_task(self):
        return self.remainingBudget <= 0

    def get_deadline(self):
        return self.max_time_points + 1

    def get_periodic_budget(self):
        return self.get_budget()

    # String representation of this task
    def to_string(self):
        return "SchedulerTask"


# Create a new task based on some input data (JSON file)
def new_task(task_data):
    if task_data["periodic"]:
        if "program" in task_data:
            task = PeriodicTask(task_data["pid"], task_data["budget"], task_data["period"],
                                task_data["release_time"] + 1, task_data["program"])
        else:
            dummy_program = generate_dummy_program(task_data["budget"])
            task = PeriodicTask(task_data["pid"], task_data["budget"],
                                task_data["period"], task_data["release_time"] + 1, dummy_program)
    else:
        raise ValueError

    return task


# This method makes it possible to also run test scripts where no instruction sequence is given.
def generate_dummy_program(budget):
    dummy_program = dict()
    dummy_instruction = dict()
    dummy_instruction["type"] = "calc"
    dummy_instruction["param"] = None
    dummy_instruction["length"] = budget

    dummy_program["0"] = dummy_instruction
    return dummy_program
