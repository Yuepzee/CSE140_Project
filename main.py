import os
import machine_to_binary
 

# Global variables
pc = 0
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

    #REMOVE EXCEPTION HANDLING HERE
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, file_name)
        
        with open(file_path, 'r') as f:
            instructions = [line.strip() for line in f.readlines()]
    except FileNotFoundError:
        print(f"Error: File '{file_name}' not found")
        exit(1)

#=====================================================================

def Fetch():
    global pc, next_pc
    if pc // 4 >= len(instructions):
        return None
    
    instruction = instructions[pc // 4]
    next_pc = pc + 4
    
    return instruction

#=====================================================================

def Decode(instruction):
    return machine_to_binary.decode_helper(instruction)

#=====================================================================

def Execute(rs1_val, rs2_val, imm):
    global ALUOp, ALUSrc, alu_zero, branch_target
    
    if ALUSrc:
        second_operand = imm
    else:
        second_operand = rs2_val

    # Default result
    result = 0
    
    if ALUOp == 0b0000:  # AND
        result = rs1_val & second_operand
    elif ALUOp == 0b0001:  # OR
        result = rs1_val | second_operand
    elif ALUOp == 0b0010:  # ADD
        result = rs1_val + second_operand
    elif ALUOp == 0b0110:  # SUB
        result = rs1_val - second_operand
        # Set alu_zero for branch instructions
        alu_zero = (result == 0)
    elif ALUOp == 0b0111:  # SLT
        result = 1 if rs1_val < second_operand else 0
    
    # Calculate branch target for branch instructions
    if Branch:
        branch_target = pc + imm
    
    return result

#=====================================================================

def Mem(decoded, alu_result):
    if decoded["Operation"] == "lw":
        mem_addr = alu_result // 4
        loaded_value = d_mem[mem_addr]
        return loaded_value
    elif decoded["Operation"] == "sw":
        mem_addr = alu_result // 4
        rs2_index = int(decoded["Rs2"][1:])
        d_mem[mem_addr] = rf[rs2_index]
        # Print is moved to Writeback for consistent formatting
    
    # Always return alu_result for non-load operations
    return alu_result

#=====================================================================

def Writeback(decoded, result):
    global total_clock_cycles
    total_clock_cycles += 1
    print(f"total_clock_cycles {total_clock_cycles}")
    
    # Get the actual instruction from Operation (not the instruction type)
    operation = decoded["Operation"]
    
    # Handle register writeback for arithmetic, logical, load instructions
    if operation in ["add", "sub", "and", "or", "slt", "addi", "ori", "andi", "lw", "jal"]:
        if decoded.get("Rd") and decoded["Rd"] != "x0":  # Don't write to x0
            rd_index = int(decoded["Rd"][1:])  # Extract register number
            rf[rd_index] = result
            print(f"{decoded['Rd']} is modified to {hex(result)}")
    
    # Handle memory operations
    if decoded["Operation"] == "sw":
        alu_result = result
        rs2_index = int(decoded["Rs2"][1:])
        print(f"memory {hex(alu_result)} is modified to {hex(rf[rs2_index])}")

#=====================================================================

def ALUControl(funct3, funct7):
    if funct3 == "000":
        if funct7 == "0000000":
            return 0b0010  # ADD
        elif funct7 == "0100000":
            return 0b0110  # SUB
    elif funct3 == "111":
        return 0b0000  # AND
    elif funct3 == "110":
        return 0b0001  # OR
    elif funct3 == "010":
        return 0b0111  # SLT
    
    return 0b0010  # Default to ADD

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
        ALUOp = 0b0010  # ADD

    elif opcode == "0100011":  # sw
        MemWrite = 1
        ALUSrc = 1
        ALUOp = 0b0010  # ADD

    elif opcode == "0110011":  # R-type
        RegWrite = 1
        # ALU control depends on funct3/funct7
        if funct3 == "000" and funct7 == "0000000":
            ALUOp = 0b0010  # ADD
        elif funct3 == "000" and funct7 == "0100000":
            ALUOp = 0b0110  # SUB
        elif funct3 == "111":
            ALUOp = 0b0000  # AND
        elif funct3 == "110":
            ALUOp = 0b0001  # OR
        elif funct3 == "010":
            ALUOp = 0b0111  # SLT

    elif opcode == "0010011":  # I-type (addi, etc.)
        RegWrite = 1
        ALUSrc = 1
        ALUOp = 0b0010  # Default to ADD for addi

    elif opcode == "1100011":  # beq
        Branch = 1
        ALUOp = 0b0110  # SUB for comparison


#=====================================================================

def parse_immediate(imm_str):
    if not imm_str:
        return 0
        
    # Handle format like "-5 (or 0xFFFFFFFB)"
    if isinstance(imm_str, str) and "(" in imm_str:
        # Extract just the decimal value before the parenthesis
        imm_str = imm_str.split("(")[0].strip()
    
    try:
        # Try parsing as int (works for numbers like "-5")
        return int(imm_str)
    except ValueError:
        # Try parsing as hex if there's "0x"
        if isinstance(imm_str, str) and "0x" in imm_str:
            hex_part = imm_str.split("0x")[1].split(")")[0]
            return int("0x" + hex_part, 16)
    
    return 0 

#=====================================================================

def update_pc():
    global pc, next_pc, branch_target, alu_zero, Branch
    
    if Branch and alu_zero:
        pc = branch_target
        print(f"pc is modified to {hex(pc)}")
    else:
        pc = next_pc
        print(f"pc is modified to {hex(pc)}")
    print()  # Add a blank line after each instruction cycle

#=====================================================================

def run_instruction():
    instr = Fetch()
    if not instr:
        return False
    
    decoded = Decode(instr)
    if not decoded:
        return False
    
    ControlUnit(decoded["Opcode"], decoded["Funct3"], decoded["Funct7"])
    
    # Extract register indices correctly - note that the field names are "Rs1" and "Rs2" (capital R)
    rs1_index = int(decoded.get("Rs1", "x0")[1:]) if decoded.get("Rs1") else 0
    rs2_index = int(decoded.get("Rs2", "x0")[1:]) if decoded.get("Rs2") else 0
    
    rs1_val = rf[rs1_index]
    rs2_val = rf[rs2_index]
    
    # Parse immediate value from the string format returned by decode_helper
    imm = parse_immediate(decoded.get("Immediate", "0"))
    
    
    # Execute stage
    alu_result = Execute(rs1_val, rs2_val, imm)
    
    # Memory stage - for load/store instructions
    if decoded["Operation"] == "lw" or decoded["Operation"] == "sw":
        mem_result = Mem(decoded, alu_result)
        result_to_writeback = mem_result
    else:
        result_to_writeback = alu_result
    
    # Writeback stage
    Writeback(decoded, result_to_writeback)
    
    # Update PC at the end of the cycle
    update_pc()
    
    return True

#=====================================================================

def main():
    initialize()
    print("RISC-V CPU Simulator")
    
    #filename = input("\nEnter program file name (sample_part2.txt): ")
    load_program("sample_part2.txt")
    
    while True:
        if not run_instruction():
                break

if __name__ == "__main__":
    main()