# pythonSchedulingSimulation

Simulator for scheduling policies on 1-core processors. The code could probably be more modular, etc. 

Assumptions: 
    - when a process is submitted, also some meta-data with specifications about the process is submitted.
    This meta-data provides the scheduler with precise information about the process and is used when scheduling.

The scheduler can process two types of threads: Aperiodic <-> Periodic
|For the moment the scheduling policy only supports periodic threads.

There are three main files:
- CPU : simulates CPU, loads new modules when needed, runs threads and thus scheduler too when needed
- Scheduler: is run as a process by the CPU, chooses the new job to be scheduled
- Enclave: This is the thread/enclave to be scheduled



- main.py : to run the simulation. 
  - Will first simulate the CPU (this will output the thread that is run at each cycle)
  - Will then use the simulation data to make a timeline of the CPU utilization
- MCU.py : TODO
- Interrupt.py:
  - This represents an interrupt, with the specific timer that triggered it and if it is a timer interrupt
- Timer.py:
  - File handling the details about timers, making it possible to schedule timers 
  (for budget monitoring or other purposes). 
- Scheduler.py:
  - The working of the scheduler: handles interrupts (for the moment only timer interrupts), schedules task given 
  a policy and enforces the contract of the different tasks.
- EDF_Policy_periodic: 
  - This file embeds all the behaviour concerning the EDF policy.

All the files could be interpreted as being part of two modules:
1. Scheduler module (SW): scheduler, used policy,
2. Device Hardware : mcu, interrupt, 
3. Timer file is a little bit of the two part: the timer class will typically just be hardware features, 
but the functions will need to be implemented in software

Notes
-
Aperiodic tasks are not fully supported yet. Some support is already added in the scheduler.py file, but that's
only to ease further extension of the simulator. 

The scheduler does not ensure that the task doesn't end before its clix-period. This can lead to problems if the 
acceptance test is not sustainable. A system could be in theory schedulable, but if one of the tasks ends before its
budget is finished, the system becomes suddenly unschedulable (because of the bounded atomicity regions - clix()).

DEPENDENCIES:
-
- plotly
- pandas

Further extensions:
- 
- Adding scheduled interrupts for tasks:
  - change task class + policy behaviour
- Adding extra resources for tasks:
  - Add resource class per resource
  - Change task class + policy behaviour
