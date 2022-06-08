import MCU as mcu

# This class is a representation of a concrete process. This class thus just simulates the run through the lines
# of the program. A program can consist of a sequence of computing cycles and clix()-operations (bounded atomicity).
# Extensions are of course possible.
# These methods will in practice just be the program code that is submitted to the scheduler.

# Current defined operations
CLIX_OPERATION = "clix"
CALCULATION_OPERATION = "calc"


# A concrete process could be a process or a thread.
class ConcreteProcess:

    def __init__(self, instruction_sequence):
        # This variable registers a JSON consisting of the sequence of instructions in the program
        # These instructions are ordered and numbered ("0", "1" etc). Each instruction has a type, a length and
        # optionally some additional parameters.
        self.instruction_sequence = instruction_sequence
        # Indicates the index of the current running instruction. The instructions are numbered starting from 0.
        self.programCounter = -1
        # The current instruction that is executing. Instructions can take multiple cycles, this makes it possible to
        # represent long programs in a concise manner.
        self.currentInstruction = None
        # The time that the instruction still has to run
        self.remainingCyclesForInstruction = 0
        # Is true if the program has finished executing, thus finished the last instruction
        self.finished = False
        # Is true if program has already started (first instruction was fetched)
        self.started = False
        # If the instruction has some additional parameters
        # NOTE: this could be changed to a list, if the simulator would be extended and more parameters would be needed.
        self.potentialInstructionParameter = None

    # Re-initialize this ConcreteProcess
    def reinit_process(self):
        self.programCounter = -1
        self.started = False

    # Start the execution of this ConcreteProcess. Can also be used to retake execution.
    def start_program(self):
        self.programCounter = 0
        self.load_new_instruction()
        self.finished = False
        self.started = True

    # Run one cycle of this program
    def run_for_one_cycle(self):
        # If we have to run, but the program has already finished executing, then some error occurred
        # (for Debugging purpose)
        if self.has_finished() or not self.has_started():
            raise ValueError

        # Run the instruction for one cycle
        self.remainingCyclesForInstruction -= 1
        self.perform_effect_of_instruction()

        # If the instruction has finished, the next instruction can be loaded
        if self.remainingCyclesForInstruction == 0:
            if self.programCounter < len(self.instruction_sequence) - 1:
                self.programCounter += 1
                self.load_new_instruction()
            else:
                self.finished = True

    # Load the next instruction (program counter)
    def load_new_instruction(self):
        self.currentInstruction = self.instruction_sequence[self.programCounter]["type"]
        # (For Debugging purposes)
        print("*** " + str(self.programCounter) + ": " + self.currentInstruction.upper())
        self.potentialInstructionParameter = self.instruction_sequence[self.programCounter]["param"]
        if self.currentInstruction == CLIX_OPERATION:
            self.remainingCyclesForInstruction = 1
        else:
            self.remainingCyclesForInstruction = self.instruction_sequence[self.programCounter]["length"]

    # Return if this ConcreteProcess has finished.
    def has_finished(self):
        return self.finished

    # Return if this ConcreteProcess had already fetched an instruction since initialization
    def has_started(self):
        return self.started

    # Perform the effect of the current instruction, if it has one. Clix instructions for example, will result in a
    # clix call to the hardware (and thus the start of a bounded region of atomicity).
    # NOTE: if new powerful instructions are needed, then this method should be adapted to support their effects
    def perform_effect_of_instruction(self):
        if self.currentInstruction == CLIX_OPERATION:
            mcu.clix_system_call(self.potentialInstructionParameter)


# Return a new concrete process instance, based on the given program (instruction sequence)
def new_concrete_process(program):
    return ConcreteProcess(program)
