from dataclasses import dataclass
from typing import Optional, List, Dict


@dataclass
class ReservationStation:
    name: str
    kind: str
    busy: bool = False
    op: Optional[str] = None
    instruction_id: Optional[int] = None
    vj: Optional[float] = None
    vk: Optional[float] = None
    qj: Optional[str] = None
    qk: Optional[str] = None
    remaining: int = 0
    executing: bool = False
    result_ready: bool = False
    result: Optional[float] = None
    unit_id: Optional[str] = None


class TomasuloSimulator:
    """
    Educational Tomasulo-style scheduler with:
      * in-order issue (one instruction per cycle)
      * register renaming through producer tags
      * reservation stations
      * non-pipelined functional units
      * one common-data-bus (CDB) broadcast per cycle
      * out-of-order execution and completion

    Cycle convention:
      1. Broadcast one result that became ready in an earlier cycle.
      2. Issue at most one instruction.
      3. Start ready instructions if a compatible functional unit is free.
      4. Advance each running instruction by one execution cycle.
      Results completing in step 4 can be broadcast no earlier than the next cycle.
    """

    def __init__(self, instructions: List, add_stations=3, mul_stations=3,
                 div_stations=1, add_units=2, mul_units=2, div_units=1,
                 add_latency=2, mul_latency=4, div_latency=8):
        self.instructions = list(instructions)
        self.latencies = {
            "ADD": int(add_latency), "SUB": int(add_latency),
            "MUL": int(mul_latency), "DIV": int(div_latency)
        }
        self.station_specs = (
            [("A", "ADD") for _ in range(add_stations)] +
            [("M", "MUL") for _ in range(mul_stations)] +
            [("D", "DIV") for _ in range(div_stations)]
        )
        self.stations: Dict[str, ReservationStation] = {}
        counters = {"A": 0, "M": 0, "D": 0}
        for prefix, kind in self.station_specs:
            counters[prefix] += 1
            name = f"{prefix}{counters[prefix]}"
            self.stations[name] = ReservationStation(name=name, kind=kind)

        self.unit_counts = {"ADD": int(add_units), "MUL": int(mul_units), "DIV": int(div_units)}
        self.unit_busy = {"ADD": {}, "MUL": {}, "DIV": {}}
        self.registers: Dict[str, float] = {}
        self.register_status: Dict[str, Optional[str]] = {}
        self.cycle = 0
        self.next_instruction = 0
        self.completed = set()
        self.status = []
        self.trace = []
        self._instruction_to_station = {}

    def set_register(self, register, value):
        self.registers[register] = float(value)
        self.register_status.setdefault(register, None)

    @staticmethod
    def _kind(op):
        if op in ("ADD", "SUB"):
            return "ADD"
        if op == "MUL":
            return "MUL"
        if op == "DIV":
            return "DIV"
        raise ValueError(f"Unsupported operation: {op}")

    def _free_station(self, op):
        kind = self._kind(op)
        for station in self.stations.values():
            if station.kind == kind and not station.busy:
                return station
        return None

    def _free_unit(self, kind):
        for i in range(1, self.unit_counts[kind] + 1):
            unit_id = f"{kind}{i}"
            if unit_id not in self.unit_busy[kind]:
                return unit_id
        return None

    def _record_event(self, event, instruction_id, details):
        self.trace.append({
            "Cycle": self.cycle,
            "Event": event,
            "Instruction ID": instruction_id + 1 if instruction_id is not None else None,
            "Instruction": (
                self.status[instruction_id]["Instruction"]
                if instruction_id is not None and instruction_id < len(self.status)
                else ""
            ),
            "Details": details
        })

    def _issue(self):
        if self.next_instruction >= len(self.instructions):
            return

        idx = self.next_instruction
        inst = self.instructions[idx]
        station = self._free_station(inst.op)
        if station is None:
            self._record_event("Issue Stall", idx, "No free reservation station")
            return

        station.busy = True
        station.op = inst.op
        station.instruction_id = idx
        station.remaining = self.latencies[inst.op]
        station.executing = False
        station.result_ready = False
        station.result = None
        station.unit_id = None

        # Capture source values or the tags of their latest producers.
        for src_attr, q_attr, v_attr in [
            (inst.src1, "qj", "vj"),
            (inst.src2, "qk", "vk")
        ]:
            producer = self.register_status.get(src_attr)
            if producer is not None:
                setattr(station, q_attr, producer)
                setattr(station, v_attr, None)
            else:
                setattr(station, q_attr, None)
                setattr(station, v_attr, self.registers.get(src_attr, 0.0))

        # Register renaming: only later instructions see this new producer tag.
        self.register_status[inst.dst] = station.name
        self.status.append({
            "Instruction ID": idx + 1,
            "Instruction": f"{inst.op} {inst.dst}, {inst.src1}, {inst.src2}",
            "Description": getattr(inst, "description", ""),
            "Station": station.name,
            "Issue": self.cycle,
            "Execute Start": None,
            "Execute End": None,
            "Write Result": None,
            "Status": "Issued"
        })
        self._instruction_to_station[idx] = station.name
        self._record_event("Issue", idx, f"Allocated reservation station {station.name}")
        self.next_instruction += 1

    @staticmethod
    def _evaluate(op, a, b):
        if op == "ADD":
            return a + b
        if op == "SUB":
            return a - b
        if op == "MUL":
            return a * b
        if op == "DIV":
            if b == 0:
                raise ZeroDivisionError("Division by zero in simulated instruction")
            return a / b
        raise ValueError(f"Unknown operation: {op}")

    def _start_ready_instructions(self):
        # Older ready instructions are considered first, but younger independent
        # instructions can start while older instructions wait for operands.
        candidates = sorted(
            [s for s in self.stations.values()
             if s.busy and not s.executing and not s.result_ready
             and s.qj is None and s.qk is None],
            key=lambda s: s.instruction_id
        )
        for station in candidates:
            kind = self._kind(station.op)
            unit_id = self._free_unit(kind)
            if unit_id is None:
                continue
            station.executing = True
            station.unit_id = unit_id
            station.remaining = self.latencies[station.op]
            self.unit_busy[kind][unit_id] = station.name
            self.status[station.instruction_id]["Execute Start"] = self.cycle
            self.status[station.instruction_id]["Status"] = "Executing"
            self._record_event("Execute Start", station.instruction_id,
                               f"{station.name} acquired {unit_id}")

    def _advance_execution(self):
        for station in list(self.stations.values()):
            if not station.busy or not station.executing:
                continue
            station.remaining -= 1
            if station.remaining <= 0:
                station.result = self._evaluate(station.op, station.vj, station.vk)
                station.executing = False
                station.result_ready = True
                idx = station.instruction_id
                self.status[idx]["Execute End"] = self.cycle
                self.status[idx]["Status"] = "Waiting for CDB"
                kind = self._kind(station.op)
                if station.unit_id is not None:
                    self.unit_busy[kind].pop(station.unit_id, None)
                self._record_event("Execute Complete", idx,
                                   f"{station.name} result ready: {station.result:.5f}")

    def _broadcast_one_result(self):
        ready = sorted(
            [s for s in self.stations.values() if s.busy and s.result_ready],
            key=lambda s: s.instruction_id
        )
        if not ready:
            return
        station = ready[0]
        tag = station.name
        value = station.result
        idx = station.instruction_id
        inst = self.instructions[idx]

        # Wake dependent instructions.
        for waiting in self.stations.values():
            if not waiting.busy:
                continue
            if waiting.qj == tag:
                waiting.vj = value
                waiting.qj = None
            if waiting.qk == tag:
                waiting.vk = value
                waiting.qk = None

        # Write architectural register only if this is still the latest producer.
        if self.register_status.get(inst.dst) == tag:
            self.registers[inst.dst] = value
            self.register_status[inst.dst] = None

        self.status[idx]["Write Result"] = self.cycle
        self.status[idx]["Status"] = "Completed"
        self.completed.add(idx)
        self._record_event("CDB Broadcast", idx, f"{tag} broadcast {value:.5f}")

        # Release the station after its result has been broadcast.
        station.busy = False
        station.op = None
        station.instruction_id = None
        station.vj = station.vk = None
        station.qj = station.qk = None
        station.remaining = 0
        station.executing = False
        station.result_ready = False
        station.result = None
        station.unit_id = None

    def step(self):
        self.cycle += 1
        self._broadcast_one_result()
        self._issue()
        self._start_ready_instructions()
        self._advance_execution()

    def run(self, max_cycles=100000):
        while len(self.completed) < len(self.instructions) and self.cycle < max_cycles:
            self.step()
        if len(self.completed) != len(self.instructions):
            raise RuntimeError(
                f"Simulation stopped after {self.cycle} cycles; "
                f"{len(self.completed)}/{len(self.instructions)} instructions completed."
            )
        return {
            "cycles": self.cycle,
            "registers": dict(self.registers),
            "instructions": list(self.status),
            "trace": list(self.trace),
            "stations": self.station_table()
        }

    def station_table(self):
        rows = []
        for s in self.stations.values():
            rows.append({
                "Station": s.name,
                "Type": s.kind,
                "Busy": s.busy,
                "Operation": s.op,
                "Instruction ID": s.instruction_id + 1 if s.instruction_id is not None else None,
                "Vj": s.vj,
                "Vk": s.vk,
                "Qj": s.qj,
                "Qk": s.qk,
                "Remaining Cycles": s.remaining if s.busy else None,
                "Executing": s.executing,
                "Result Ready": s.result_ready
            })
        return rows
