"""
SIMLAB AI - Knowledge Base Ingestion Script
Parses 'Manual complete.txt' into structured SQLite FTS5 database,
JSON experiment schemas, and Viva question banks.
"""

import os
import sys
import json
import sqlite3
import re

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWLEDGE_DIR = os.path.join(APP_ROOT, "knowledge")
EXPERIMENTS_DIR = os.path.join(KNOWLEDGE_DIR, "experiments")
VIVA_DIR = os.path.join(KNOWLEDGE_DIR, "viva")
DB_PATH = os.path.join(KNOWLEDGE_DIR, "manual_db.sqlite")
MANUAL_TXT = os.path.join(KNOWLEDGE_DIR, "Manual complete.txt")

EXPERIMENT_META = {
    1: {
        "title": "Computation of DC Biases in a Resistor Bridge Using PySpice",
        "software": "PySpice, Python 3.x, Ngspice",
        "pages": [3, 4],
        "category": "Analog / PySpice",
        "tags": "resistor bridge, DC bias, operating point, PySpice, node voltage, KVL, KCL"
    },
    2: {
        "title": "Simulation of a Current-Controlled Current Source (CCCS) Circuit Using PySpice",
        "software": "PySpice, Python 3.x, Ngspice",
        "pages": [5, 6],
        "category": "Analog / PySpice",
        "tags": "CCCS, current-controlled current source, F element, PySpice, operating point, branch current"
    },
    3: {
        "title": "Simulation of a Voltage-Controlled Voltage Source (VCVS) Circuit Using PySpice",
        "software": "PySpice, Python 3.x, Ngspice",
        "pages": [7, 8],
        "category": "Analog / PySpice",
        "tags": "VCVS, voltage-controlled voltage source, E element, PySpice, operating point, node voltage"
    },
    4: {
        "title": "Simulating Natural Response of RC Circuits Using PySpice",
        "software": "PySpice, Python 3.x, Ngspice, Matplotlib",
        "pages": [9, 10, 11],
        "category": "Transient / RC",
        "tags": "natural response, RC circuit, time constant, tau, transient simulation, capacitor discharge, voltage-controlled switch"
    },
    5: {
        "title": "Simulating Step Response of RC Circuits Using PySpice",
        "software": "PySpice, Python 3.x, Ngspice, Matplotlib",
        "pages": [12, 13, 14],
        "category": "Transient / RC",
        "tags": "step response, RC circuit, time constant, charging capacitor, transient simulation, pulse source, voltage-controlled switch"
    },
    6: {
        "title": "Simulation of a Pacemaker Circuit in PySpice",
        "software": "PySpice, Python 3.x, Ngspice, Matplotlib",
        "pages": [15, 16, 17, 18],
        "category": "Biomedical / PySpice",
        "tags": "pacemaker, heart rate, BPM, RC timing, switching factor, theoretical calculation, pulse generator"
    },
    7: {
        "title": "Verification of Truth Tables of Logic Gates Using Multisim",
        "software": "Multisim / SIMLAB Digital Logic Engine",
        "pages": [19, 20, 21, 22, 23, 24],
        "category": "Digital Logic",
        "tags": "logic gates, AND, OR, NOT, NAND, NOR, XOR, XNOR, truth table, TTL 7408, 7432, 7404, 7400, 7402, 7486, 74266"
    },
    8: {
        "title": "Simulation of Half Adder and Full Adder Circuit in Multisim",
        "software": "Multisim / SIMLAB Digital Logic Engine",
        "pages": [25, 26, 27, 28],
        "category": "Digital Combinational",
        "tags": "half adder, full adder, SUM, CARRY, XOR, AND, OR, truth table, arithmetic circuit"
    },
    9: {
        "title": "Implementation of Boolean Function in SOP and POS Form Using Multisim",
        "software": "Multisim / SIMLAB Digital Logic Engine",
        "pages": [29, 30, 31, 32, 33],
        "category": "Boolean Algebra",
        "tags": "Boolean function, SOP, POS, sum of products, product of sums, minterms, maxterms, sigma 1 3 6, logic gates"
    },
    10: {
        "title": "Implementation of Combinational Circuit Using Minimum Number of NAND Gates Using Multisim",
        "software": "Multisim / SIMLAB Digital Logic Engine",
        "pages": [34, 35, 36],
        "category": "Digital Combinational",
        "tags": "NAND gate implementation, universal gate, F=AB+BC+AC, combinational logic, logic minimization"
    },
    11: {
        "title": "Characteristics of PN-Junction Diode in MATLAB/Simulink",
        "software": "MATLAB Simulink / SIMLAB Numerical Engine",
        "pages": [37, 38],
        "category": "Semiconductor / Analog",
        "tags": "PN junction diode, I-V characteristics, forward bias, reverse bias, knee voltage, barrier potential, ramp voltage"
    },
    12: {
        "title": "Design a Voltage Regulator Using Zener Diode in MATLAB/Simulink",
        "software": "MATLAB Simulink / SIMLAB Numerical Engine",
        "pages": [39, 40],
        "category": "Power / Analog",
        "tags": "Zener diode, voltage regulator, breakdown voltage, line regulation, load regulation, 5.1V Zener, current limiting resistor"
    },
    13: {
        "title": "Simulation of Half-Wave Rectifier in MATLAB/Simulink",
        "software": "MATLAB Simulink / SIMLAB Numerical Engine",
        "pages": [41],
        "category": "Power Electronics",
        "tags": "half-wave rectifier, AC to DC, diode, ripple factor, capacitor filter, peak inverse voltage, efficiency"
    },
    14: {
        "title": "Simulation of Full-Wave Rectifier in MATLAB/Simulink",
        "software": "MATLAB Simulink / SIMLAB Numerical Engine",
        "pages": [42],
        "category": "Power Electronics",
        "tags": "full-wave rectifier, bridge rectifier, 4 diodes, ripple factor, capacitor filter, PIV, AC to DC"
    }
}

STANDARD_VIVA_QUESTIONS = {
    1: [
        {"q": "What is the purpose of operating point (.op) analysis in PySpice?", "a": "Operating point analysis determines the steady-state DC node voltages and branch currents of an analog circuit with all inductors short-circuited and capacitors open-circuited.", "key_concepts": ["DC steady state", "node voltages", "capacitors open", "inductors short", "quiescent point"]},
        {"q": "How does PySpice represent circuit connections between nodes?", "a": "PySpice represents circuits through Netlist objects where each component specifies its unique identifier, connecting nodes, and value using unit decorators (e.g. 10@u_kOhm).", "key_concepts": ["netlist", "connecting nodes", "unit decorators", "component identifier"]},
        {"q": "What is the role of the ground node (node 0 / GND) in Spice simulations?", "a": "The ground node acts as the 0V reference datum against which all other node voltages are calculated. Every Spice circuit must have an explicit path to ground.", "key_concepts": ["0V reference", "reference datum", "must have path to ground"]}
    ],
    2: [
        {"q": "What is a Current-Controlled Current Source (CCCS)?", "a": "A CCCS is a dependent source whose output current is directly proportional to a controlling current flowing through an identified branch or dummy voltage source in the circuit.", "key_concepts": ["dependent source", "output current", "controlling current", "proportionality factor", "gain"]},
        {"q": "How is a CCCS modeled in SPICE netlists?", "a": "In SPICE, a CCCS is designated by the 'F' element prefix, specifying the output nodes, the name of the controlling voltage source used to sense current, and the current gain factor.", "key_concepts": ["F element", "controlling voltage source", "sense current", "current gain"]},
        {"q": "Why is a 0V DC voltage source often inserted when simulating a CCCS?", "a": "A 0V DC voltage source acts as an ammeter in SPICE to sample and measure the controlling branch current without introducing any impedance or voltage drop.", "key_concepts": ["acts as ammeter", "measures controlling current", "zero impedance", "0V source"]}
    ],
    3: [
        {"q": "What is a Voltage-Controlled Voltage Source (VCVS)?", "a": "A VCVS is a dependent source where the output voltage is proportional to the differential voltage measured between two controlling nodes.", "key_concepts": ["dependent source", "output voltage", "controlling node voltage", "voltage gain"]},
        {"q": "What SPICE element letter represents a VCVS?", "a": "The letter 'E' represents a VCVS in SPICE (e.g., E1 n_pos n_neg nc_pos nc_neg gain).", "key_concepts": ["E element", "four nodes", "voltage gain"]},
        {"q": "Give an operational amplifier application that acts as a VCVS.", "a": "A non-inverting operational amplifier configuration acts as a practical realization of a VCVS with high input impedance and finite closed-loop voltage gain.", "key_concepts": ["op-amp", "non-inverting amplifier", "high input impedance"]}
    ],
    4: [
        {"q": "What is the natural response of an RC circuit?", "a": "The natural response is the circuit's transient behavior when stored energy in the capacitor discharges through the resistive network in the absence of external independent sources.", "key_concepts": ["stored energy", "capacitor discharge", "no external sources", "exponential decay"]},
        {"q": "What is the formula for the time constant (tau) of an RC circuit?", "a": "Tau = R * C, representing the time required for the capacitor voltage to decay to approximately 36.8% (1/e) of its initial charged value.", "key_concepts": ["R * C", "36.8%", "1/e", "seconds"]},
        {"q": "How does a voltage-controlled switch work in PySpice transient analysis?", "a": "A voltage-controlled switch transitions between high OFF resistance and low ON resistance based on a controlling voltage threshold, modeling the opening or closing of an ideal switch at t = 0.", "key_concepts": ["controlling voltage", "threshold", "ON resistance", "OFF resistance", "t=0 transition"]}
    ],
    5: [
        {"q": "What is the step response of an RC circuit?", "a": "The step response is the time-domain behavior when an uncharged (or partially charged) capacitor is suddenly energized by an abrupt DC step voltage.", "key_concepts": ["abrupt step voltage", "charging capacitor", "transient to steady state", "exponential rise"]},
        {"q": "How much percentage of the final voltage does the capacitor reach after 1 time constant?", "a": "After 1 time constant (t = tau), the capacitor voltage reaches approximately 63.2% of the input step amplitude: V(tau) = V_final * (1 - e^-1).", "key_concepts": ["63.2%", "1 - e^-1", "1 tau"]},
        {"q": "How many time constants does it take for an RC circuit to reach practical steady state?", "a": "Practically 5 time constants (5 * tau), at which point the capacitor voltage reaches over 99.3% of the final applied voltage.", "key_concepts": ["5 tau", "5 time constants", "99.3%", "steady state"]}
    ],
    6: [
        {"q": "What is the basic engineering principle of the simulated pacemaker circuit?", "a": "The pacemaker circuit uses an RC relaxation timing network to generate rhythmic electrical stimulation pulses at a calibrated heart rate (e.g. 70 BPM).", "key_concepts": ["RC timing network", "relaxation oscillator", "rhythmic stimulation", "heart rate BPM"]},
        {"q": "How is the timing resistance calculated from heart rate and capacitance?", "a": "The required pulse period T is 60 / BPM. Given T = R * C * ln(1/(1 - switching_factor)), the resistance R is calculated as T / (C * ln(Vdd / (Vdd - Vth))).", "key_concepts": ["period T = 60/BPM", "R = T / (C * ln)", "switching factor", "threshold voltage"]},
        {"q": "What voltage waveform appears across the timing capacitor in the pacemaker?", "a": "A repetitive sawtooth/exponential charging and rapid discharging waveform that resets every cardiac cycle when reaching the trigger threshold.", "key_concepts": ["exponential charging", "rapid discharging", "sawtooth waveform", "trigger threshold"]}
    ],
    7: [
        {"q": "Which logic gates are considered 'universal gates' and why?", "a": "NAND and NOR gates are universal gates because any combinational or sequential Boolean logic function (AND, OR, NOT, etc.) can be constructed using only NAND or only NOR gates.", "key_concepts": ["NAND and NOR", "universal gates", "implement any function", "functionally complete"]},
        {"q": "What is the truth table definition of an XOR (Exclusive-OR) gate?", "a": "An XOR gate yields a HIGH (1) output when the inputs are different (odd parity, e.g. 0-1 or 1-0) and LOW (0) when the inputs are identical (0-0 or 1-1).", "key_concepts": ["inputs are different", "odd parity", "1 when A != B"]},
        {"q": "What is the standard 74xx TTL IC number for quad 2-input NAND gates?", "a": "The 7400 IC contains four independent 2-input NAND gates.", "key_concepts": ["7400", "quad 2-input", "TTL NAND"]}
    ],
    8: [
        {"q": "What is the difference between a Half Adder and a Full Adder?", "a": "A Half Adder adds two 1-bit binary inputs (A, B) generating SUM and CARRY, while a Full Adder adds three 1-bit inputs (A, B, and a Carry-in Cin) to support cascaded multi-bit addition.", "key_concepts": ["Half adder: 2 inputs", "Full adder: 3 inputs", "carry-in Cin", "cascaded addition"]},
        {"q": "What are the Boolean logic equations for a Half Adder?", "a": "SUM = A XOR B; CARRY = A AND B.", "key_concepts": ["SUM = A XOR B", "CARRY = A AND B"]},
        {"q": "How can a Full Adder be constructed using Half Adders?", "a": "A Full Adder can be constructed using two Half Adders and one OR gate: the first HA adds A and B, the second HA adds the first SUM with Cin, and the two CARRY outputs are combined through an OR gate.", "key_concepts": ["two half adders", "one OR gate", "SUM = A XOR B XOR Cin", "CARRY = (A AND B) OR ((A XOR B) AND Cin)"]}
    ],
    9: [
        {"q": "What is the difference between Sum of Products (SOP) and Product of Sums (POS)?", "a": "SOP combines product (AND) terms using addition (OR) representing minterms where the output is 1, whereas POS combines sum (OR) terms using multiplication (AND) representing maxterms where the output is 0.", "key_concepts": ["SOP: OR of AND terms", "POS: AND of OR terms", "minterms", "maxterms", "1s vs 0s"]},
        {"q": "In Experiment 9, what Boolean expression is implemented in SOP form?", "a": "XSOP = Sigma(1, 3, 6) = A'B'C + A'BC + ABC'.", "key_concepts": ["Sigma(1,3,6)", "A'B'C", "A'BC", "ABC'"]},
        {"q": "What is a minterm?", "a": "A minterm is a product of all literals in the function (in either complemented or uncomplemented form) that evaluates to logic 1 for exactly one row of the truth table.", "key_concepts": ["product of all literals", "evaluates to 1", "single row of truth table"]}
    ],
    10: [
        {"q": "What is the Boolean expression implemented in Experiment 10?", "a": "F = AB + BC + AC (representing the majority function / carry generation logic).", "key_concepts": ["F = AB + BC + AC", "majority logic", "carry function"]},
        {"q": "How is an AND operation realized using only NAND gates?", "a": "By feeding the output of a NAND gate into a second NAND gate wired as an inverter (both inputs tied together): (AB)'' = AB.", "key_concepts": ["NAND followed by inverter", "tied inputs", "double inversion"]},
        {"q": "How is an OR operation realized using only NAND gates (De Morgan's theorem)?", "a": "According to De Morgan's Law, A + B = (A' * B')'. Invert input A and input B each using a NAND gate, then feed both into a third NAND gate.", "key_concepts": ["De Morgan's law", "A + B = (A'B')'", "invert inputs then NAND"]}
    ],
    11: [
        {"q": "What is the cut-in (knee) voltage for a standard silicon PN-junction diode?", "a": "Approximately 0.6V to 0.7V at room temperature. Below this voltage, forward current is negligible; above it, current increases exponentially.", "key_concepts": ["0.6V to 0.7V", "knee voltage", "exponential current", "barrier potential"]},
        {"q": "Why does a PN-junction diode conduct heavily in forward bias but barely in reverse bias?", "a": "Forward bias reduces the potential barrier and narrows the depletion width, allowing majority carriers to diffuse across the junction; reverse bias widens the barrier, allowing only minute minority carrier leakage current.", "key_concepts": ["depletion region", "potential barrier", "majority carriers", "minority leakage"]},
        {"q": "What is the dynamic resistance of a diode and how is it determined from the I-V curve?", "a": "Dynamic resistance r_d = dV / dI, which is the reciprocal of the slope of the forward I-V characteristic curve at a specified operating quiescent point.", "key_concepts": ["dV / dI", "reciprocal of slope", "quiescent point", "small signal resistance"]}
    ],
    12: [
        {"q": "How does a Zener diode function as a voltage regulator?", "a": "When reverse biased past its Zener breakdown voltage (Vz), the diode maintains an almost constant terminal voltage over a wide variation of reverse current, clamping the load voltage.", "key_concepts": ["reverse breakdown", "constant voltage", "Zener voltage Vz", "voltage clamping"]},
        {"q": "What is the role of the series resistor (Rs) in a Zener regulator circuit?", "a": "The series resistor drops the excess input voltage (Vin - Vz) and limits the maximum current flowing through the Zener diode to prevent thermal damage.", "key_concepts": ["drops excess voltage", "limits current", "prevents thermal burnout", "Vin - Vz"]},
        {"q": "Under what condition will the Zener diode stop regulating?", "a": "Regulation fails if the input voltage falls below the Zener breakdown voltage (Vin < Vz) or if the load current is so high that the Zener current drops below its minimum knee current (Iz < Izk).", "key_concepts": ["Vin < Vz", "load current too high", "below knee current Izk"]}
    ],
    13: [
        {"q": "What is the theoretical maximum efficiency of a Half-Wave Rectifier without filter?", "a": "40.6% (eta = (0.406 * Vm^2 / RL) / (Vm^2 / 2RL)).", "key_concepts": ["40.6%", "efficiency", "one half cycle wasted"]},
        {"q": "What is the function of a shunt capacitor filter in a rectifier circuit?", "a": "The capacitor charges to the peak AC voltage during diode conduction and slowly discharges through the load during the non-conducting half-cycle, drastically reducing AC ripple and smoothing the DC output.", "key_concepts": ["charges to peak", "discharges through load", "reduces ripple", "smooths DC voltage"]},
        {"q": "What is the ripple factor of a half-wave rectifier with and without filter?", "a": "Without filter, the ripple factor is 1.21. With a shunt capacitor filter, it reduces to approximately 1 / (2 * sqrt(3) * f * R_L * C).", "key_concepts": ["1.21 without filter", "1 / (2 * sqrt(3) * f * R * C)", "inversely proportional to C and R"]}
    ],
    14: [
        {"q": "What is the ripple frequency of a Full-Wave Bridge Rectifier compared to input frequency?", "a": "The ripple frequency is double the input frequency (2 * f, i.e. 100 Hz for a 50 Hz mains input) because both positive and negative half-cycles are converted to unidirectional output.", "key_concepts": ["double the input frequency", "2 * f", "100 Hz for 50 Hz", "both half cycles"]},
        {"q": "How many diodes conduct simultaneously in a Full-Wave Bridge Rectifier?", "a": "Two diodes conduct simultaneously in series with the load during each half cycle (D1 and D2 during positive; D3 and D4 during negative).", "key_concepts": ["two diodes simultaneously", "series with load", "diagonal pairs"]},
        {"q": "What is the theoretical maximum rectification efficiency of a Full-Wave Rectifier?", "a": "81.2%, which is exactly double the maximum efficiency of a half-wave rectifier.", "key_concepts": ["81.2%", "double half-wave efficiency", "full cycle utilized"]}
    ]
}


def parse_manual_pages():
    with open(MANUAL_TXT, "r", encoding="utf-8", errors="ignore") as f:
        raw = f.read()

    pages = raw.split("\x0c")
    # Clean pages
    cleaned_pages = []
    for idx, page in enumerate(pages):
        text = page.strip()
        cleaned_pages.append({
            "page_num": idx + 1,
            "content": text
        })
    return cleaned_pages


def extract_experiment_content(pages):
    experiments = {}

    for exp_num, meta in EXPERIMENT_META.items():
        page_nums = meta["pages"]
        combined_text = "\n\n".join([pages[p - 1]["content"] for p in page_nums if p <= len(pages)])

        # Extract Aim
        aim = ""
        aim_match = re.search(r'Aim[:\s]+(.*?)(?=Apparatus|Software|Theory|Circuit|Procedure|\Z)', combined_text, re.DOTALL | re.IGNORECASE)
        if aim_match:
            aim = aim_match.group(1).strip()
            # clean up multiple spaces
            aim = re.sub(r'\s+', ' ', aim)
        else:
            aim = f"To simulate and analyze {meta['title']} per manual specifications."

        # Extract Apparatus / Software
        apparatus = meta["software"]
        app_match = re.search(r'(?:Apparatus Required|Software Required)[:\s]+(.*?)(?=Theory|Circuit|Procedure|Diagram|\Z)', combined_text, re.DOTALL | re.IGNORECASE)
        if app_match:
            apparatus_text = re.sub(r'\s+', ' ', app_match.group(1).strip())
            if len(apparatus_text) > 3:
                apparatus = apparatus_text

        # Extract Procedure
        procedure = ""
        proc_match = re.search(r'Procedure[:\s]+(.*?)(?=Result|Tabular|Observation|Program|Code|\Z)', combined_text, re.DOTALL | re.IGNORECASE)
        if proc_match:
            procedure = proc_match.group(1).strip()
        else:
            procedure = f"Follow standard simulation steps detailed in manual pages {meta['pages'][0]}-{meta['pages'][-1]}."

        # Extract Result
        result = ""
        res_match = re.search(r'Result[:\s]+(.*?)(?=\Z|Experiment|\x0c)', combined_text, re.DOTALL | re.IGNORECASE)
        if res_match:
            result = re.sub(r'\s+', ' ', res_match.group(1).strip())
        else:
            result = "The circuit was simulated and the verified output was observed in accordance with the theoretical values."

        # Code block extraction (for Python/PySpice)
        code_samples = []
        code_blocks = re.findall(r'(?:from PySpice|import PySpice|import matplotlib|import numpy|Circuit\(|simulator =).*?(?=\n\n\n|\Z)', combined_text, re.DOTALL)
        if code_blocks:
            code_samples = [c.strip() for c in code_blocks]

        # Circuit diagram image paths
        diagram_images = []
        for p in page_nums:
            img_name = f"Manual complete_page-{p:04d}-compressed.jpg"
            diagram_images.append(img_name)

        experiments[exp_num] = {
            "exp_number": exp_num,
            "title": meta["title"],
            "category": meta["category"],
            "software": apparatus,
            "aim": aim,
            "procedure": procedure,
            "result": result,
            "raw_text": combined_text,
            "pages": page_nums,
            "page_start": page_nums[0],
            "page_end": page_nums[-1],
            "tags": meta["tags"],
            "diagram_images": diagram_images,
            "code_sample": code_samples[0] if code_samples else None,
            "viva": STANDARD_VIVA_QUESTIONS.get(exp_num, [])
        }

    return experiments


def build_sqlite_database(pages, experiments):
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except Exception:
            pass

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Tables
    cur.execute("""
    CREATE TABLE experiments (
        exp_number INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        software TEXT NOT NULL,
        aim TEXT NOT NULL,
        procedure TEXT NOT NULL,
        result TEXT NOT NULL,
        page_start INTEGER NOT NULL,
        page_end INTEGER NOT NULL,
        tags TEXT NOT NULL,
        code_sample TEXT,
        diagram_images TEXT NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE pages (
        page_num INTEGER PRIMARY KEY,
        content TEXT NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE manual_chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exp_number INTEGER NOT NULL,
        section TEXT NOT NULL,
        page_start INTEGER NOT NULL,
        page_end INTEGER NOT NULL,
        content TEXT NOT NULL,
        source_type TEXT NOT NULL,
        tags TEXT,
        FOREIGN KEY(exp_number) REFERENCES experiments(exp_number)
    );
    """)

    cur.execute("""
    CREATE VIRTUAL TABLE manual_chunks_fts USING fts5(
        section,
        content,
        tags,
        content='manual_chunks',
        content_rowid='id'
    );
    """)

    cur.execute("""
    CREATE TABLE viva_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exp_number INTEGER NOT NULL,
        question TEXT NOT NULL,
        expected_answer TEXT NOT NULL,
        key_concepts TEXT NOT NULL,
        FOREIGN KEY(exp_number) REFERENCES experiments(exp_number)
    );
    """)

    # Populate Pages
    for p in pages:
        cur.execute("INSERT INTO pages (page_num, content) VALUES (?, ?)", (p["page_num"], p["content"]))

    # Populate Experiments & Chunks
    for exp_num, data in experiments.items():
        cur.execute("""
        INSERT INTO experiments (
            exp_number, title, category, software, aim, procedure, result,
            page_start, page_end, tags, code_sample, diagram_images
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            exp_num,
            data["title"],
            data["category"],
            data["software"],
            data["aim"],
            data["procedure"],
            data["result"],
            data["page_start"],
            data["page_end"],
            data["tags"],
            data["code_sample"],
            json.dumps(data["diagram_images"])
        ))

        # Chunk: Aim
        cur.execute("""
        INSERT INTO manual_chunks (exp_number, section, page_start, page_end, content, source_type, tags)
        VALUES (?, 'aim', ?, ?, ?, 'manual', ?)
        """, (exp_num, data["page_start"], data["page_end"], data["aim"], data["tags"]))
        chunk_id = cur.lastrowid
        cur.execute("INSERT INTO manual_chunks_fts (rowid, section, content, tags) VALUES (?, 'aim', ?, ?)", (chunk_id, data["aim"], data["tags"]))

        # Chunk: Procedure
        if data["procedure"]:
            cur.execute("""
            INSERT INTO manual_chunks (exp_number, section, page_start, page_end, content, source_type, tags)
            VALUES (?, 'procedure', ?, ?, ?, 'manual', ?)
            """, (exp_num, data["page_start"], data["page_end"], data["procedure"], data["tags"]))
            chunk_id = cur.lastrowid
            cur.execute("INSERT INTO manual_chunks_fts (rowid, section, content, tags) VALUES (?, 'procedure', ?, ?)", (chunk_id, data["procedure"], data["tags"]))

        # Chunk: Result
        if data["result"]:
            cur.execute("""
            INSERT INTO manual_chunks (exp_number, section, page_start, page_end, content, source_type, tags)
            VALUES (?, 'result', ?, ?, ?, 'manual', ?)
            """, (exp_num, data["page_start"], data["page_end"], data["result"], data["tags"]))
            chunk_id = cur.lastrowid
            cur.execute("INSERT INTO manual_chunks_fts (rowid, section, content, tags) VALUES (?, 'result', ?, ?)", (chunk_id, data["result"], data["tags"]))

        # Chunk: Full Page text chunks for deep search
        for p in data["pages"]:
            if p <= len(pages):
                p_text = pages[p - 1]["content"]
                if p_text:
                    cur.execute("""
                    INSERT INTO manual_chunks (exp_number, section, page_start, page_end, content, source_type, tags)
                    VALUES (?, 'page_content', ?, ?, ?, 'manual', ?)
                    """, (exp_num, p, p, p_text, data["tags"]))
                    chunk_id = cur.lastrowid
                    cur.execute("INSERT INTO manual_chunks_fts (rowid, section, content, tags) VALUES (?, 'page_content', ?, ?)", (chunk_id, p_text, data["tags"]))

        # Populate Viva
        for viva in data["viva"]:
            cur.execute("""
            INSERT INTO viva_questions (exp_number, question, expected_answer, key_concepts)
            VALUES (?, ?, ?, ?)
            """, (exp_num, viva["q"], viva["a"], json.dumps(viva["key_concepts"])))

            # Index viva questions into search
            viva_content = f"Question: {viva['q']}\nAnswer: {viva['a']}"
            cur.execute("""
            INSERT INTO manual_chunks (exp_number, section, page_start, page_end, content, source_type, tags)
            VALUES (?, 'viva', ?, ?, ?, 'manual', ?)
            """, (exp_num, data["page_start"], data["page_end"], viva_content, data["tags"]))
            chunk_id = cur.lastrowid
            cur.execute("INSERT INTO manual_chunks_fts (rowid, section, content, tags) VALUES (?, 'viva', ?, ?)", (chunk_id, viva_content, data["tags"]))

    conn.commit()
    conn.close()
    print(f"Successfully generated SQLite database at: {DB_PATH}")


def save_json_files(experiments):
    for exp_num, data in experiments.items():
        exp_file = os.path.join(EXPERIMENTS_DIR, f"exp{exp_num}.json")
        with open(exp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        viva_file = os.path.join(VIVA_DIR, f"exp{exp_num}_viva.json")
        with open(viva_file, "w", encoding="utf-8") as f:
            json.dump({
                "exp_number": exp_num,
                "title": data["title"],
                "questions": data["viva"]
            }, f, indent=2, ensure_ascii=False)

    print(f"Saved all 14 experiment JSON schemas to: {EXPERIMENTS_DIR}")
    print(f"Saved all 14 viva banks to: {VIVA_DIR}")


if __name__ == "__main__":
    print("Ingesting 23EEP20B Simulation Lab Manual...")
    pages = parse_manual_pages()
    print(f"Parsed {len(pages)} pages from manual.")
    experiments = extract_experiment_content(pages)
    print(f"Extracted structured content for {len(experiments)} experiments.")
    build_sqlite_database(pages, experiments)
    save_json_files(experiments)
    print("Ingestion completed successfully!")
