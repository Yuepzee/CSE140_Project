import os

# Global variables
pc = 0
next_pc = 0
branch_target = 0
alu_zero = 0
total_clock_cycles = 0
instructions = []
registers = [0] * 32  # Register file (x0-x31)
data_memory = [0] * 32  # Data memory (32 entries)

# Control signals
RegWrite = 0
Branch = 0
MemRead = 0
MemWrite = 0
MemtoReg = 0
ALUOp = 0
ALUSrc = 0

# Initialize registers and memory as specified
def initialize():
    global registers, data_memory
    registers[1] = 0x20  # x1
    registers[2] = 0x5    # x2
    registers[10] = 0x70  # x10
    registers[11] = 0x4   # x11
    
    # Memory addresses are divided by 4 since each entry is 4 bytes
    data_memory[0x70 // 4] = 0x5
    data_memory[0x74 // 4] = 0x10

# Instruction set and decoding
instruction_set = {
    "0110011": "R",
    "0000011": "I",  # lw
    "0010011": "I",  # addi, andi, ori
    "0100011": "S",  # sw
    "1100011": "SB", # beq
    "1101111": "UJ"  # jal
}

r_instructions = {
    ("000", "0000000"): "add",
    ("000", "0100000"): "sub",
    ("111", "0000000"): "and",
    ("110", "0000000"): "or"
}

i_instructions = {
    ("010", "0000011"): "lw",  # lw has funct3=010
    ("000", "0010011"): "addi",
    ("111", "0010011"): "andi",
    ("110", "0010011"): "ori"
}

sb_instructions = {
    "000": "beq"
}

s_instructions = {
    "010": "sw"
}

def load_program(file_name):
    global instructions
    try:
        # Get the directory where the script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Construct full file path
        file_path = os.path.join(script_dir, file_name)
        
        with open(file_path, 'r') as f:
            instructions = [line.strip() for line in f.readlines()]
        print(f"Successfully loaded program from {file_path}")
    except FileNotFoundError:
        print(f"Error: The file '{file_name}' was not found in directory: {script_dir}")
        print("Please ensure:")
        print(f"1. The file '{file_name}' exists in the same directory as this script")
        print(f"2. The filename is spelled correctly (including .txt extension)")
        print("\nFiles found in directory:")
        for f in os.listdir(script_dir):
            print(f"  - {f}")
        exit(1)

def Fetch():
    global pc, next_pc, branch_target
    if pc // 4 >= len(instructions):
        print("Program completed")
        return None
    
    instruction = instructions[pc // 4]
    next_pc = pc + 4
    
    # Handle branch (simplified - should use control signals)
    if alu_zero and Branch:
        pc = branch_target
    else:
        pc = next_pc
    
    print(f"Fetched instruction at PC={pc-4}: {instruction}")
    return instruction

def Decode(instruction):
    opcode = instruction[-7:]
    instr_type = instruction_set.get(opcode, None)
    
    if instr_type is None:
        print("Unknown instruction")
        return None
    
    decoded = {"opcode": opcode, "type": instr_type}
    
    if instr_type == "R":
        decoded["rd"] = int(instruction[20:25], 2)
        decoded["funct3"] = instruction[17:20]
        decoded["rs1"] = int(instruction[12:17], 2)
        decoded["rs2"] = int(instruction[7:12], 2)
        decoded["funct7"] = instruction[0:7]
        decoded["operation"] = r_instructions.get((decoded["funct3"], decoded["funct7"]), "unknown")
    
    elif instr_type == "I":
        decoded["rd"] = int(instruction[20:25], 2)
        decoded["funct3"] = instruction[17:20]
        decoded["rs1"] = int(instruction[12:17], 2)
        decoded["imm"] = int(instruction[0:12], 2)
        decoded["operation"] = i_instructions.get((decoded["funct3"], opcode), "unknown")
    
    elif instr_type == "S":
        decoded["funct3"] = instruction[17:20]
        decoded["rs1"] = int(instruction[12:17], 2)
        decoded["rs2"] = int(instruction[7:12], 2)
        decoded["imm"] = int(instruction[0:7] + instruction[20:25], 2)
        decoded["operation"] = s_instructions.get(decoded["funct3"], "unknown")
    
    elif instr_type == "SB":
        decoded["funct3"] = instruction[17:20]
        decoded["rs1"] = int(instruction[12:17], 2)
        decoded["rs2"] = int(instruction[7:12], 2)
        imm = instruction[0] + instruction[24] + instruction[1:7] + instruction[20:24] + '0'
        decoded["imm"] = int(imm, 2)
        decoded["operation"] = sb_instructions.get(decoded["funct3"], "unknown")
    
    elif instr_type == "UJ":
        decoded["rd"] = int(instruction[20:25], 2)
        imm = instruction[0] + instruction[12:20] + instruction[11] + instruction[1:11] + '0'
        decoded["imm"] = int(imm, 2)
        decoded["operation"] = "jal"
    
    print(f"Decoded: {decoded}")
    return decoded

# Update the Execute function
def Execute(decoded):
    global alu_zero, branch_target, next_pc
    
    result = 0  # Initialize result to avoid UnboundLocalError
    
    if decoded["type"] == "R":
        val1 = registers[decoded["rs1"]]
        val2 = registers[decoded["rs2"]]
        
        if decoded["operation"] == "add":
            result = val1 + val2
        elif decoded["operation"] == "sub":
            result = val1 - val2
        elif decoded["operation"] == "and":
            result = val1 & val2
        elif decoded["operation"] == "or":
            result = val1 | val2
        else:
            print(f"Unsupported R-type operation: {decoded['operation']}")
            
    elif decoded["type"] == "I":
        val1 = registers[decoded["rs1"]]
        imm = decoded["imm"]
        
        if decoded["operation"] == "addi":
            result = val1 + imm
        elif decoded["operation"] == "andi":
            result = val1 & imm
        elif decoded["operation"] == "ori":
            result = val1 | imm
        elif decoded["operation"] == "lw":
            result = val1 + imm  # Calculate memory address
        else:
            print(f"Unsupported I-type operation: {decoded['operation']}")
            
    elif decoded["type"] == "SB":
        val1 = registers[decoded["rs1"]]
        val2 = registers[decoded["rs2"]]
        branch_target = next_pc + decoded["imm"]
        
        if decoded["operation"] == "beq":
            alu_zero = 1 if val1 == val2 else 0
        return None  # Branches don't produce ALU results
        
    elif decoded["type"] == "S":
        val1 = registers[decoded["rs1"]]
        val2 = registers[decoded["rs2"]]
        result = val1 + decoded["imm"]  # Memory address calculation
        
    elif decoded["type"] == "UJ":
        branch_target = next_pc + decoded["imm"]
        return next_pc  # For JAL to store PC+4 in rd
        
    else:
        print(f"Unsupported instruction type: {decoded['type']}")
        return None
    
    alu_zero = 1 if result == 0 else 0
    return result

def Mem(decoded, alu_result):
    if decoded["type"] == "lw":
        mem_addr = alu_result // 4
        return data_memory[mem_addr]
    elif decoded["type"] == "sw":
        mem_addr = alu_result // 4
        data_memory[mem_addr] = registers[decoded["rs2"]]
        print(f"Memory[{hex(alu_result)}] = {registers[decoded['rs2']]}")
    return alu_result

def Writeback(decoded, result):
    global total_clock_cycles
    
    if decoded["type"] in ["R", "I", "lw", "jal"] and decoded.get("rd", 0) != 0:
        registers[decoded["rd"]] = result
        print(f"x{decoded['rd']} = {hex(result)}")
    
    total_clock_cycles += 1
    print(f"total_clock_cycles {total_clock_cycles}: pc = {hex(pc)}")

def ControlUnit(opcode, funct3):
    global RegWrite, Branch, MemRead, MemWrite, MemtoReg, ALUOp, ALUSrc
    
    # Default values
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
    elif opcode == "0010011":  # I-type (addi, andi, ori)
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

def main():
    initialize()
    print("RISC-V CPU Simulator")
    
    # List available files
    script_dir = os.path.dirname(os.path.abspath(__file__))
    print("\nAvailable files in directory:")
    for i, f in enumerate(os.listdir(script_dir)):
        if f.endswith('.txt'):
            print(f"{i+1}. {f}")
    
    filename = input("\nEnter program file name (e.g., sample_part1.txt): ")
    load_program(filename)
    
    while True:
        print("\nOptions:")
        print("1. Run next instruction")
        print("2. Run all instructions")
        print("3. Show registers")
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
            for i, val in enumerate(registers):
                if val != 0:
                    print(f"x{i} = {hex(val)}")
        elif choice == "4":
            for i, val in enumerate(data_memory):
                if val != 0:
                    print(f"Mem[{hex(i*4)}] = {hex(val)}")
        elif choice == "5":
            break
        else:
            print("Invalid choice")

if __name__ == "__main__":
    main()