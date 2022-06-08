# Import MCU.
import MCU as mcu

# Important parameters for the simulation:
# - Name of the test-script to use (see "testScript.json" for possible test-scripts)
TASK_SCENARIO = 'simple_periodic_jobs_with_clix'
# - Number of cycles that will be simulated
MAX_NR_TIME_POINTS = 1500

# Run the simulation
mcu.simulate(TASK_SCENARIO, MAX_NR_TIME_POINTS)
# Make a picture of the simulated data
mcu.make_scheduler_picture()
