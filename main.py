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
MemRead = 0
MemWrite = 0
Branch = 0
ALUSrc = 0
MemtoReg = 0
ALUOp = 0  # 2-bit value for ALU control logic
alu_ctrl = 0  # Actual operation for ALU (e.g., add/sub/etc.)

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

#=====================================================================

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

#=====================================================================

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

#=====================================================================

def Decode(instruction):

    return machine_to_binary.decode_helper(instruction)

    #ControlUnit(intermediary["Opcode"], intermediary["Funct3"], intermediary["Funct7"])
#=====================================================================

def Execute(rs1_val, rs2_val, imm):
    global ALUOp, ALUSrc

    if ALUSrc:
        second_operand = imm
    else:
        second_operand = rs2_val

    if ALUOp == 0b0000:  # AND
        result = rs1_val and second_operand
    elif ALUOp == 0b0001:  # OR
        result = rs1_val or second_operand
    elif ALUOp == 0b0010:  # ADD
        result = rs1_val + second_operand
    elif ALUOp == 0b0110:  # SUB
        result = rs1_val - second_operand
    elif ALUOp == 0b0111:  # SLT
        result = int(rs1_val < second_operand)
    else:
        result = 0

    print(f"successful Execute")
    return result

#=====================================================================

def Mem(decoded, alu_result):
    if decoded["Operation"] == "lw":
        mem_addr = alu_result // 4
        return d_mem[mem_addr]
    elif decoded["Operation"] == "sw":
        mem_addr = alu_result // 4
        d_mem[mem_addr] = rf[decoded["rs2"]]
        print(f"memory {hex(alu_result)} is modified to {hex(rf[decoded['rs2']])}")
    #return alu_result

#=====================================================================

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

#=====================================================================

def ALUControl(funct3: str, funct7: str) -> int: # remember to change these to 2 bit formate
    if funct3 == "000":
        if funct7 == "0000000":
            return 0
        elif funct7 == "0100000":
            return 1
    elif funct3 == "111":
        return 2
    elif funct3 == "110":
        return 3
    return 0  # default to ADD

#=====================================================================

def ControlUnit(opcode, funct3, funct7):
    global RegWrite, MemRead, MemWrite, Branch, ALUSrc, MemtoReg, ALUOp, alu_ctrl

    # Reset all signals
    RegWrite = 0
    MemRead = 0
    MemWrite = 0
    Branch = 0
    ALUSrc = 0
    MemtoReg = 0
    ALUOp = 0
    alu_ctrl = 0

    if opcode == "0000011":  # lw
        RegWrite = 1
        MemRead = 1
        ALUSrc = 1
        MemtoReg = 1

    elif opcode == "0100011":  # sw
        MemWrite = 1
        ALUSrc = 1

    elif opcode == "0110011":  # R-type
        RegWrite = 1
        ALUOp = 2  # decides based on funct3/funct7

    elif opcode == "0010011":  # I-type
        RegWrite = 1
        ALUSrc = 1
        ALUOp = 2  # funct3

    elif opcode == "1100011":  # beq
        Branch = 1
        ALUOp = 1  #ALU sub

    # Call ALU Control logic for R/I-type
    if ALUOp == 2:
        alu_ctrl = ALUControl(funct3, funct7)
    elif ALUOp == 0:
        alu_ctrl = 0 #ALU add
    elif ALUOp == 1:
        alu_ctrl = 1 #ALU sub

#=====================================================================

def remove_prefix_and_convert(s: str) -> int:
    if s is None:
        raise ValueError("Input string cannot be None")
    
    # Remove the "0x" prefix (if it exists) and convert the remaining string to an integer
    if s.startswith("0x"):
        s = s[2:]  # Strip the first two characters
    elif s.startswith("x"):
        s = s[1:]  # Strip the first character ('x')

    return int(s)

#=====================================================================

def run_instruction():
    instr = Fetch()
    if not instr:
        return False
    
    decoded = Decode(instr)
    if not decoded:
        return False
    
    ControlUnit(decoded["Opcode"], decoded["Funct3"], decoded["Funct7"])

    # Ensure decoded values are not None
    rs1_value = decoded.get("Rs1", None)
    rs2_value = decoded.get("Rs2", None)
    
    if rs1_value is None or rs2_value is None:
        print("Error: Rs1 or Rs2 is None.")
        return False
    
    rs1_index = remove_prefix_and_convert(rs1_value)
    rs2_index = remove_prefix_and_convert(rs2_value)
    
    rs1_val = rf[rs1_index]
    rs2_val = rf[rs2_index]
    imm = decoded["Immediate"]

    alu_result = Execute(rs1_val, rs2_val, imm)
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