def run_sequential_baseline(instructions, initial_registers,
                            add_latency=2, mul_latency=4, div_latency=8):
    """
    Baseline: execute the exact same instruction trace in program order with
    no overlap. Each instruction starts only after the previous instruction
    has completed. This is a serial reference, not a model of every real CPU.
    """
    latencies = {
        "ADD": add_latency, "SUB": add_latency,
        "MUL": mul_latency, "DIV": div_latency
    }
    registers = {k: float(v) for k, v in initial_registers.items()}
    rows = []
    cycle = 0

    for idx, inst in enumerate(instructions):
        issue = cycle + 1
        start = issue
        end = start + int(latencies[inst.op]) - 1
        write = end + 1

        a = registers.get(inst.src1, 0.0)
        b = registers.get(inst.src2, 0.0)

        if inst.op == "ADD":
            value = a + b
        elif inst.op == "SUB":
            value = a - b
        elif inst.op == "MUL":
            value = a * b
        elif inst.op == "DIV":
            if b == 0:
                raise ZeroDivisionError("Division by zero in baseline")
            value = a / b
        else:
            raise ValueError(f"Unsupported operation: {inst.op}")

        registers[inst.dst] = value
        rows.append({
            "Instruction ID": idx + 1,
            "Instruction": f"{inst.op} {inst.dst}, {inst.src1}, {inst.src2}",
            "Issue": issue,
            "Execute Start": start,
            "Execute End": end,
            "Write Result": write,
            "Status": "Completed"
        })
        cycle = write

    return {"cycles": cycle, "registers": registers, "instructions": rows}
