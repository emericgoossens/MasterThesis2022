import Task as e
import Scheduler as s
import plotly.express as px
import plotly
import pandas as pd
import json
import Timer as tim
import Interrupt as i

########################################################################################################################
# This file embeds the details concerning the MCU. It simulates cycle per cycle and runs idle if no task is
# ready to run. The simulator will output/print for each cycle which task is running, and some details about that task.
# If a task has finished running, or went over it's budget, then this will also be printed in the corresponding MCU
# cycle.
# The simulator takes only scheduler important details into account and so doesn't simulate the functionality of
# the tasks involved. Only some coarse description of the task functionality is used to make the simulation.

# Note: For the moment, the simulator has only support for tasks consisting of one thread (so task and thread are
#       equal concepts in this case). These tasks can only consist of a combination of some clix instructions
#       (to start a bounded timelapse with interrupts disabled) and instructions that do not need other peripherals or
#       timers (these instructions are called calculations for simplicity). So no support is available for tasks who
#       need access to resources other than the MCU, or who need to schedule timers. This simulator was not meant
#       to embed all the specificities of Aion and the programs who could run on Aion, but it could be extended to
#       embed more of these aspects.
#
#       With this limited amount of "instructions" that a task can run, an attacker is also limited in the ways that
#       he/she can compromise the availability of the system. This makes it possible to zoom in on these aspects.
#
#       Furthermore, this means only one source of interrupts has to be taken into account, namely timer interrupts.
#
# ######################################################################################################################

# TERMINOLOGY
# Time-points are the points at the begin/end of a CPU-cycle
# CPU-cycles thus actually do the work and happen between two time-points.
# The first cycle is between the 0th and 1th time_point

#####
# SIMULATION PARAMETERS (will be set at the beginning of the simulation)
# -Number of cycles that will be simulated
MAX_NR_TIME_POINTS = -1
# -Tasks that will be released at later times (in the given scenario)
tasks_to_release = []
#####

#####
# MCU PARAMETERS
# --------------
# Upper bound on the duration of a clix section (static upper bound)
MAX_CLIX_DURATION = 1000
#
# MCU STATE
# ---------
# The task that is currently running
running_task = None
# The scheduler is a special task. This boolean denotes if the scheduler has finished its job.
has_run_scheduler = False
# Counter that counts how many cycles are left in the current clix()-section
clix_counter = 0
# Variable registering if currently a clix()-section is performed (to know if the clix counter has to be decremented)
performing_clix = False
####


# Initialize the MCU and some helper variables
def init_MCU(test_script, nr_time_points):
    global running_task
    global MAX_NR_TIME_POINTS

    MAX_NR_TIME_POINTS = nr_time_points

    # The scheduler will have a deadline equal to the max simulation time. This is needed to prevent the
    # visualization to flag it as a task that went beyond deadline.
    s.init_scheduler(MAX_NR_TIME_POINTS + s.WCET_SCHEDULER + 1)

    # open file and read test script from it
    file = open('testScript.json')
    list_task_data = json.load(file)[test_script]
    file.close()

    # Make tasks-object by using the data from the file
    for task_data in list_task_data:
        newtask = e.new_task(task_data)
        tasks_to_release.append((task_data["release_time"], newtask))

    # Submit tasks that already run in our system (for simulation)
    load_new_task(-1)

    # Run the scheduler with the init time 0, to initialise the starting state of the CPU
    s.run_scheduler(0, None)
    # Set interrupt mask to false, because scheduler has finished running
    s.interrupt_mask = False
    # Start running the scheduled task
    running_task = s.get_current_scheduled()


# Return if the MCU is idle
def MCU_is_idle():
    # If running_task is None, means that no jobs are in the ready queue and thus the MCU is idle
    return running_task is None


# Reset the interrupt state (after servicing an interrupt...)
def reset_interrupt_state():
    i.interrupt_present_flag = False
    i.pending_interrupt = None


# Check if there are new tasks that are released and need to be submitted to the scheduler.
# NOTE: to be completely precise, this should be done using a special interrupt. For simplicity this has been left out.
# But it would be an even better reflection of reality if the scheduler would be invoked when new task is released.
def load_new_task(current_time):
    global tasks_to_release
    released = []
    for task_with_release in tasks_to_release:
        (rel_time, task) = task_with_release
        if rel_time == current_time:
            # Submit the new secure modules to the scheduler (scheduler will check if they can be accepted)
            if not s.submit_new_task(task, current_time):
                print("****Task: " + task.get_name() + " IS NOT ACCEPTED!****")
            # Task has been released, so can be removed from the list
            released.append(task_with_release)
        # Else: the Task will be released at a later time
    # Remove all the released tasks from the list
    # From: https://stackoverflow.com/questions/36268749/remove-multiple-items-from-a-python-list-in-just-one-statement
    tasks_to_release = [elem for elem in tasks_to_release if elem not in released]


# Simulate the working of the MCU by running cycle after cycle for a given number of time points. The given test script
# embeds the description (contract + run-time characteristics) of the tasks.
def simulate(test_script, nr_time_points):
    global running_task
    global pseudo_context_switch
    global has_run_scheduler
    global performing_clix
    global clix_counter

    # Initialise the current state of the CPU (with a nr of jobs, etc.)
    init_MCU(test_script, nr_time_points)

    # Simulate the cycles
    for time_point in range(MAX_NR_TIME_POINTS):
        # check if interrupts have to be re-enabled, if performing a clix
        if performing_clix and clix_counter == 0:
            s.interrupt_mask = False
            performing_clix = False
        elif performing_clix:
            clix_counter -= 1

        # START NEW CYCLE
        # Load new secure modules if there are some
        load_new_task(time_point)

        # If the scheduler has run, then it means a new task has been scheduled and so can start running.
        if has_run_scheduler:
            s.interrupt_mask = False
            has_run_scheduler = False
            running_task = s.get_current_scheduled()

        # If an interrupt is present, then the scheduler will be run to handle the interrupt.
        elif i.interrupt_present_flag and not s.interrupt_mask:
            print("INTERRUPT in cycle = " + str(time_point + 1) + " || "
                  + i.pending_interrupt.trigger().get_task_of_timer().get_name())
            s.run_scheduler(time_point, i.pending_interrupt)
            reset_interrupt_state()
            running_task = s.get_scheduler_task()

            # PRINT FOR DEBUGGING
            print("**new_scheduled: ")  ##
            if s.get_current_scheduled() is not None:  ##
                print(s.get_current_scheduled().to_string())  ##
            else:  ##
                print(None)  ##

        # If no task is currently scheduled and there are waiting jobs and no interrupt has triggered the scheduler,
        # then a new task should be scheduled.
        elif MCU_is_idle() and s.has_jobs_waiting(time_point):
            # Run the scheduler to determine the thread for the next cycle
            s.run_scheduler(time_point, None)
            running_task = s.get_scheduler_task()
            # PRINT FOR DEBUGGING
            print("**new_scheduled: ")  ##
            if s.get_current_scheduled() is not None:  ##
                print(s.get_current_scheduled().to_string())  ##
            else:  ##
                print(None)  ##

        # Evaluate the timers for the next time_point. This will generate interrupts at beginning
        # of the next time point.
        # For sake of graphical reasons this method is placed here, but could also be placed at the end.
        tim.run_clock()

        # Log Information about the given time_point (for illustration purposes)
        log_beginning_of_cycle(time_point)

        # Run the task for one cycle
        print(time_point)
        if MCU_is_idle():
            print("Pass, no tasks in Ready Queue")  ##

        else:
            try:
                running_task.run_for_one_cycle()
                print(":Running_task = " + running_task.to_string())
                if running_task.has_finished_current_task():
                    pseudo_context_switch = True
                    # PRINT FOR DEBUGGING
                    print("*Task is Done: ")  ##
                    print(running_task.to_string())  ##
                    if isinstance(running_task, e.SchedulerTask):
                        # Scheduler has finished running and selecting new job
                        has_run_scheduler = True
                    else:
                        # Remove finished task from scheduler
                        s.terminate_execution(running_task, time_point)
                    running_task = None
            except HardwareViolation:
                print("VIOLATION: Running process is terminated.")
                # NOTE: maybe a specific violation flag could be an interesting addition
                running_task.flag_out_of_budget()
                s.terminate_execution(running_task, time_point)
                running_task = None
    # FINISH LAST CYCLE
    log_beginning_of_cycle(MAX_NR_TIME_POINTS)


# This function represents the clix "system call" to the processor. A program can do this call as long as the
# asked clix length is below the MAX_CLIX_DURATION.
# NOTE: by adding a VARIABLE_CLIX_DURATION variable,
def clix_system_call(duration):
    global clix_counter
    global performing_clix
    # If the clix length is too big, then a hardware violation occurs. Same if the program tries to nest clix-sections.
    if duration > MAX_CLIX_DURATION or performing_clix:
        raise HardwareViolation
    # Set the interrupt mask and the duration
    s.interrupt_mask = True
    clix_counter = duration
    performing_clix = True


# This system call can be done at any time, it will enable the interrupts
def enable_interrupts_system_call():
    global clix_counter
    global performing_clix
    s.interrupt_mask = False
    clix_counter = 0
    performing_clix = False


# This class represents HardwareViolations
class HardwareViolation(Exception):
    pass


######################################################################################################
# Log Information (for illustration purposes): the rest of the file embeds no extra features, only the visualisation
# code used to generate the timelines
def log_beginning_of_cycle(time):
    global info
    global resources
    global tasks
    global start
    global finish
    global prev_cycle_task
    global colors
    global pseudo_context_switch
    global interrupts
    global info_interrupts

    # log interrupts
    if i.interrupt_present_flag:
        interrupts.append(time + 1)  # counters are diminished and will cause an interrupt at beginning of next cycle
        info_interrupts.append(i.pending_interrupt.trigger().get_task_of_timer().get_name() + "  " + str(i.pending_interrupt.trigger().is_budget_timer()) + "  t=" + str(time + 1))
        if i.pending_interrupt.trigger().is_budget_timer():
            color_interrupts.append(0)
        else:
            color_interrupts.append(100)

    # Log tasks
    task = running_task
    if task is None:
        # If the CPU is idle, then note that the previous task has finished
        if prev_cycle_task is not None:
            finish.append(time)
            colors.append(generate_color_last_task())
        prev_cycle_task = None

    elif len(tasks) == 0 or (task is not prev_cycle_task and not time == MAX_NR_TIME_POINTS) or pseudo_context_switch:
        # New task has been scheduled
        if prev_cycle_task is not None:
            finish.append(time)
            colors.append(generate_color_last_task())
        # Append the new task + the needed parameters for visualisation
        tasks.append(task)
        resources.append(task)
        deadlines.append(task.get_deadline())
        info.append(task.get_name() + " d=" + str(task.get_deadline()))
        start.append(time)
        prev_cycle_task = task

    else:
        # This is the case where the simulation ends now
        if time == MAX_NR_TIME_POINTS and prev_cycle_task is not None:
            finish.append(time)
            colors.append(generate_color_last_task())
        # In this case the current_task is still running and nothing has to be taken up in the picture
        pass
    pseudo_context_switch = False


def generate_color_last_task():
    print(colors)
    print(deadlines)
    print(finish)
    # If some task has tried to use more than was expected
    if tasks[-1].has_ran_out_of_budget():
        return 0
    # This is the good case in which the task has finished on time (with zero budget)
    # Or the task has not finished (the simulation ended before finalisation)
    elif (tasks[-1].has_finished_current_task() and
          finish[-1] <= deadlines[-1]) or \
            (not tasks[-1].has_finished_current_task() and
             finish[-1] + tasks[-1].get_periodic_budget() <= deadlines[-1]): # for aperiodic has just to be budget

        return 100
    # This is the bad case, where the scheduler has done something wrong and the task is scheduled too late
    else:
        return 50


def add_interrupt_info():
    global start
    global finish
    global info
    global tasks
    global resources
    global colors

    for i in range(len(interrupts)):
        start.append(interrupts[i] - MAX_NR_TIME_POINTS/1000)
        finish.append(interrupts[i] + MAX_NR_TIME_POINTS/1000)
        tasks.append("interrupts")
        resources.append("interrupts")
        info.append(info_interrupts[i])
        colors.append(color_interrupts[i])


# Generate the actual timeline
def make_scheduler_picture():

    print(info)
    add_interrupt_info()
    task_names = []
    print(tasks)
    for tsk in tasks:
        if isinstance(tsk, e.PeriodicTask):
            task_names.append(tsk.get_name() + " p=" + str(tsk.get_period()) + " b=" + str(tsk.get_budget()))
        elif isinstance(tsk, e.SchedulerTask):
            task_names.append(tsk.get_name())
        else:
            task_names.append(tsk)
    task_p = pd.DataFrame(task_names, columns=["task"])
    start_p = pd.DataFrame(start, columns=["start"])
    finish_p = pd.DataFrame(finish, columns=["end"])
    resources_p = pd.DataFrame(resources, columns=["resource"])
    complete_p = pd.DataFrame(colors, columns=["color"])
    info_p = pd.DataFrame(info, columns=["info"])

    # Merge dataframes
    df = task_p.join(start_p).join(finish_p).join(complete_p).join(resources_p).join(info_p)
    # Add necessary column for linear timeline
    df['delta'] = df["end"] - df["start"]
    # Draw Figure
    fig = px.timeline(df, x_start="start", x_end="end", y="task", color="color", title='Scheduler', hover_name='info',
                      range_x=[0, MAX_NR_TIME_POINTS],
                      color_continuous_scale=[(0, "red"), (0.5, "blue"), (1, "green")], range_color=[0, 100])

    # Update/change layout
    fig.update_yaxes(autorange='reversed')
    fig.layout.xaxis.type = 'linear'
    fig.data[0].x = df.delta.tolist()
    fig.update_layout(
        title_font_size=42,
        font_size=25,
        title_font_family='Arial',
    )

    # Save Graph and export to HTML
    plotly.offline.plot(fig, filename='Scheduler_overview.html')


######################################################################################################################

# VARIABLES for the visualisation.
prev_cycle_task = None
tasks = []
start = []
finish = []
resources = []
colors = []
info = []
# for generation of the colors
deadlines = []

# Timers
interrupts = []
info_interrupts = []
color_interrupts = []

# Shows when threads have switched/the same thread has run but in two different periods
pseudo_context_switch = False

