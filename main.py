import os
import machine_to_binary
 

# Global variables
pc = 0
#VVV maybe could be changed
next_pc = 0
branch_target = 0
alu_zero = 0
total_clock_cycles = 0
instructions = []
rf = [0] * 32  # Register file (x0-x31)
d_mem = [0] * 32  # Data memory (32 entries)

# Control signals
RegWrite = 0
Branch = 0
MemRead = 0
MemWrite = 0
MemtoReg = 0
ALUOp = 0
ALUSrc = 0

# rf and memory as specified
def initialize():
    global rf, d_mem
    rf[1] = 0x20  # x1
    rf[2] = 0x5    # x2
    rf[10] = 0x70  # x10
    rf[11] = 0x4   # x11
    
    # Memory addresses (4 bytes)
    d_mem[0x70 // 4] = 0x5
    d_mem[0x74 // 4] = 0x10


def load_program(file_name):
    global instructions
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, file_name)
        
        with open(file_path, 'r') as f:
            instructions = [line.strip() for line in f.readlines()]
    except FileNotFoundError:
        print("Error no files")
        exit(1)

def Fetch(): #explain what the pc implemention is
    global pc, next_pc, branch_target
    if pc // 4 >= len(instructions):
        print("Program completed")
        return None
    
    instruction = instructions[pc // 4]
    next_pc = pc + 4
    
    if alu_zero and Branch:
        pc = branch_target
    else:
        pc = next_pc
    
    print(f"Fetched instruction at PC={pc-4}: {instruction}")
    return instruction

def Decode(instruction):

    intermediary = machine_to_binary.decode_helper(instruction)

    ControlUnit(intermediary["Opcode"], intermediary["Funct3"])

    #where do we pull the rf vaules from?

def Execute(decoded):
    global alu_zero, branch_target, pc

    # val1 = decoded["val1"]
    # val2 = decoded["val2"]
    # alu_ctrl = decoded["alu_ctrl"]

    # result = 0
    # if alu_ctrl == "0000":
    #     result = val1 & val2
    # elif alu_ctrl == "0010":
    #     result = val1 + val2
    # # Add more cases...

    # alu_zero = 1 if result == 0 else 0

    # if decoded.get("type") == "beq":
    #     offset = decoded["imm"] << 1
    #     branch_target = pc + 4 + offset

    # return result

    # #update branch_target adress
    # return 0


def Mem(decoded, alu_result):
    if decoded["Operation"] == "lw":
        mem_addr = alu_result // 4
        return d_mem[mem_addr]
    elif decoded["Operation"] == "sw":
        mem_addr = alu_result // 4
        d_mem[mem_addr] = rf[decoded["rs2"]]
        print(f"memory {hex(alu_result)} is modified to {hex(rf[decoded['rs2']])}")
    #return alu_result

def Writeback(decoded, result):
    global total_clock_cycles
    total_clock_cycles += 1
    print(f"total_clock_cycles {total_clock_cycles}:")
    
    
    if decoded["Operation"] in ["R", "I", "lw", "jal"] and decoded.get("rd", 0) != 0:
        rf[decoded["rd"]] = result
        print(f"x{decoded['rd']} is modified to {hex(result)}")
    
    if decoded["Operation"] == "sw":
        Mem(decoded, result)
    elif decoded["Operation"] == "lw":
        word = Mem(decoded, result)
        rf[decoded["rd"]] = word


    print(f"pc is modified to {hex(pc)}")

def ControlUnit(opcode, funct3):
    global RegWrite, Branch, MemRead, MemWrite, MemtoReg, ALUOp, ALUSrc
    
    RegWrite = 0
    Branch = 0
    MemRead = 0
    MemWrite = 0
    MemtoReg = 0
    ALUOp = 0b00  # 2-bit field
    ALUSrc = 0
    
    if opcode == "0110011":  # R-type
        RegWrite = 1
        ALUOp = 0b10
    elif opcode == "0000011":  # lw
        RegWrite = 1
        MemRead = 1
        MemtoReg = 1
        ALUSrc = 1
    elif opcode == "0100011":  # sw
        MemWrite = 1
        ALUSrc = 1
    elif opcode == "0010011":  # I-type
        RegWrite = 1
        ALUSrc = 1
        ALUOp = 0b11
    elif opcode == "1100011":  # beq
        Branch = 1
        ALUOp = 0b01

def run_instruction():
    instr = Fetch()
    if not instr:
        return False
    
    decoded = Decode(instr)
    if not decoded:
        return False
    
    ControlUnit(decoded["opcode"], decoded.get("funct3", "000"))
    alu_result = Execute(decoded)
    mem_result = Mem(decoded, alu_result)
    Writeback(decoded, mem_result)
    
    return True

def main(): # for debugging reasons

    initialize()
    print("RISC-V CPU Simulator")
    
    filename = input("\nEnter program file name (sample_part1.txt): ")
    load_program(filename)
    
    while True:
        print("1. Run next instruction")
        print("2. Run all instructions")
        print("3. Show register")
        print("4. Show memory")
        print("5. Exit")
        
        choice = input("Select option: ")
        
        if choice == "1":
            if not run_instruction():
                break
        elif choice == "2":
            while run_instruction():
                pass
        elif choice == "3":
            for i, val in enumerate(rf):
                if val != 0:
                    print(f"x{i} = {hex(val)}")
        elif choice == "4":
            for i, val in enumerate(d_mem):
                if val != 0:
                    print(f"Mem[{hex(i*4)}] = {hex(val)}")
        elif choice == "5":
            break
        else:
            print("Invalid choice")

if __name__ == "__main__":
    main()