import os
import machine_to_binary
 

# Global variables
pc = 0
next_pc = 0
branch_target = 0
alu_zero = 0
total_clock_cycles = 0
instructions = []
rf = [0] * 32
d_mem = [0] * 32

# Control signals
RegWrite = 0
MemRead = 0
MemWrite = 0
Branch = 0
ALUSrc = 0
MemtoReg = 0
ALUOp = 0
alu_ctrl = 0
# JAL and JALR
Jump = 0
JumpReg = 0
LinkReg = 0

def initialize_part1():
    global rf, d_mem
    # sample_part1.txt
    rf[1] = 0x20  # x1
    rf[2] = 0x5    # x2
    rf[10] = 0x70  # x10
    rf[11] = 0x4   # x11
    
    # Memory addresses, 4 bytes
    d_mem[0x70 // 4] = 0x5
    d_mem[0x74 // 4] = 0x10

def initialize_part2():
    global rf, d_mem
    # sample_part2.txt
    rf[8] = 0x20   # s0 (x8)
    rf[10] = 0x5   # a0 (x10)
    rf[11] = 0x2   # a1 (x11)
    rf[12] = 0xa   # a2 (x12)
    rf[13] = 0xf   # a3 (x13)
    

#=====================================================================

def load_program(file_name):
    global instructions

    with open(file_name, 'r') as f:
        instructions = [line.strip() for line in f.readlines()]


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
    global ALUOp, ALUSrc, alu_zero, branch_target, Jump, JumpReg, next_pc, pc
    
    if ALUSrc:
        second_operand = imm
    else:
        second_operand = rs2_val

    result = None
    
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
    else:
        result = 0
    
    # Branch/jump
    if Branch:
        branch_target = pc + imm
    elif Jump:
        if JumpReg:  # JALR
            branch_target = (rs1_val + imm) & ~1
        else:  # JAL
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
    
    return alu_result

#=====================================================================

def get_register_name(rd_index):
    register_names = {
        0: "zero", 1: "ra", 2: "sp", 3: "gp", 4: "tp", 5: "t0",
        6: "t1", 7: "t2", 8: "s0/fp", 9: "s1", 10: "a0",
        11: "a1", 12: "a2", 13: "a3", 14: "a4", 15: "a5",
        16: "a6", 17: "a7", 18: "s2", 19: "s3", 20: "s4",
        21: "s5", 22: "s6", 23: "s7", 24: "s8", 25: "s9",
        26: "s10", 27: "s11", 28: "t3", 29: "t4", 30: "t5", 31: "t6"
    }
    return register_names.get(rd_index, f"x{rd_index}")

#=====================================================================

def Writeback(decoded, result, registerName=False):
    global total_clock_cycles, next_pc, LinkReg
    total_clock_cycles += 1
    print(f"total_clock_cycles {total_clock_cycles}")
    
    # Get instruction
    operation = decoded["Operation"]
    
    # For JAL and JALR
    if LinkReg and decoded.get("Rd") and decoded["Rd"] != "x0":
        rd_index = int(decoded["Rd"][1:])
        rf[rd_index] = next_pc  # Store PC+4 in rd
        
        if registerName: # geting reg names
            reg_name = get_register_name(rd_index)
            print(f"{reg_name} is modified to {hex(next_pc)}")
        else:
            print(f"{decoded['Rd']} is modified to {hex(next_pc)}")
    
    # Instructions
    elif operation in ["add", "sub", "and", "or", "slt", "addi", "ori", "andi", "lw"]:
        if decoded.get("Rd") and decoded["Rd"] != "x0":  # Don't write to x0
            rd_index = int(decoded["Rd"][1:])  # Extract register number
            rf[rd_index] = result
            
            if registerName: # geting reg names
                reg_name = get_register_name(rd_index)
                print(f"{reg_name} is modified to {hex(result)}")
            else:
                print(f"{decoded['Rd']} is modified to {hex(result)}")
    
    # memory operations
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
    
    return 0b0010  # ADD

#=====================================================================

def ControlUnit(opcode, funct3, funct7):
    global RegWrite, MemRead, MemWrite, Branch, ALUSrc, MemtoReg, ALUOp, alu_ctrl, Jump, JumpReg, LinkReg

    RegWrite = 0
    MemRead = 0
    MemWrite = 0
    Branch = 0
    ALUSrc = 0
    MemtoReg = 0
    ALUOp = 0
    alu_ctrl = 0
    Jump = 0
    JumpReg = 0
    LinkReg = 0

    if opcode == "0000011":  # lw
        RegWrite = 1
        MemRead = 1
        ALUSrc = 1
        MemtoReg = 1
        ALUOp = 0b0010

    elif opcode == "0100011":  # sw
        MemWrite = 1
        ALUSrc = 1
        ALUOp = 0b0010

    elif opcode == "0110011":  # R-type
        RegWrite = 1
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

    elif opcode == "0010011":  # I-type
        RegWrite = 1
        ALUSrc = 1
        ALUOp = 0b0010

    elif opcode == "1100011":  # beq
        Branch = 1
        ALUOp = 0b0110
    
    elif opcode == "1101111":  # JAL
        Jump = 1
        LinkReg = 1
        RegWrite = 1
    
    elif opcode == "1100111":  # JALR
        Jump = 1
        JumpReg = 1
        LinkReg = 1
        RegWrite = 1
        ALUSrc = 1
        ALUOp = 0b0010

#=====================================================================

def parse_immediate(imm_str):
    if not imm_str:
        return 0
    #print (imm_str)
    if isinstance(imm_str, str) and "(" in imm_str:
        imm_str = imm_str.split("(")[0].strip()
    
    #print (imm_str)
    if isinstance(imm_str, str) and "0x" in imm_str:
        # Parse hex
        hex_part = imm_str.split("0x")[1].split(")")[0]
        return int("0x" + hex_part, 16)
    else:
        # Parsing int
        if isinstance(imm_str, str) and imm_str.strip().lstrip('-').isdigit():
            return int(imm_str)
        else:
            return 0

#=====================================================================

def update_pc():
    global pc, next_pc, branch_target, alu_zero, Branch, Jump
    
    if (Branch and alu_zero) or Jump:
        pc = branch_target
        print(f"pc is modified to {hex(pc)}")
    else:
        pc = next_pc
        print(f"pc is modified to {hex(pc)}")
    print()

#=====================================================================

def run_instruction(registerName=False):
    instr = Fetch()
    if not instr:
        return False
    
    decoded = Decode(instr)
    if not decoded:
        return False
    
    ControlUnit(decoded["Opcode"], decoded["Funct3"], decoded["Funct7"])
    
    # Extract register
    rs1_index = int(decoded.get("Rs1", "x0")[1:]) if decoded.get("Rs1") else 0
    rs2_index = int(decoded.get("Rs2", "x0")[1:]) if decoded.get("Rs2") else 0
    rs1_val = rf[rs1_index]
    rs2_val = rf[rs2_index]
    imm = parse_immediate(decoded.get("Immediate", "0"))
    
    # Execute
    alu_result = Execute(rs1_val, rs2_val, imm)
    
    # Memory
    if decoded["Operation"] == "lw" or decoded["Operation"] == "sw":
        mem_result = Mem(decoded, alu_result)
        result_to_writeback = mem_result
    else:
        result_to_writeback = alu_result
    
    # Writeback
    Writeback(decoded, result_to_writeback, registerName)
    
    update_pc()
    
    return True

#=====================================================================

def reset():
    global pc, next_pc, branch_target, alu_zero, total_clock_cycles
    global RegWrite, MemRead, MemWrite, Branch, ALUSrc, MemtoReg, ALUOp, alu_ctrl, Jump, JumpReg, LinkReg
    
    pc = 0
    next_pc = 0
    branch_target = 0
    alu_zero = 0
    total_clock_cycles = 0
    
    RegWrite = 0
    MemRead = 0
    MemWrite = 0
    Branch = 0
    ALUSrc = 0
    MemtoReg = 0
    ALUOp = 0
    alu_ctrl = 0
    Jump = 0
    JumpReg = 0
    LinkReg = 0
    
    # Data memory
    for i in range(32):
        rf[i] = 0
        d_mem[i] = 0

#=====================================================================

def main():
    print("RISC-V CPU Simulator with JAL and JALR Support")
    
    # Part 1 test
    print("sample_part1.txt\n")
    reset()
    initialize_part1()
    load_program("CSE140_Project\sample_part1.txt") #put path of txt
    
    while True:
        if not run_instruction(registerName=False):
            break
    
    # Part 2 test
    print("Running sample_part2.txt\n")
    reset()
    initialize_part2()
    load_program("CSE140_Project\sample_part2.txt") #put path of txt
    
    while True:
        if not run_instruction(registerName=True):
            break

if __name__ == "__main__":
    main()