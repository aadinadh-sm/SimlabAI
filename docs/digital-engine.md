# SIMLAB AI: Digital Logic Engine (Multisim Equivalent)

## Purpose & Scope
The Digital Logic Engine provides deterministic simulation for combinational digital logic circuits, fulfilling syllabus requirements for Experiments 7, 8, 9, and 10 without requiring NI Multisim or any external software.

## Gate Implementations
The engine models pure Boolean logic mappings:
- **AND**: $Y = A \cdot B$
- **OR**: $Y = A + B$
- **NOT**: $Y = \overline{A}$
- **NAND**: $Y = \overline{A \cdot B}$ (Universal Gate)
- **NOR**: $Y = \overline{A + B}$ (Universal Gate)
- **XOR**: $Y = A \oplus B = \overline{A}B + A\overline{B}$
- **XNOR**: $Y = \overline{A \oplus B}$

## Experiment Implementations
### Experiment 8: Half & Full Adder
- **Half Adder**:
  - $\text{SUM} = A \oplus B$
  - $\text{CARRY} = A \cdot B$
- **Full Adder**:
  - $\text{SUM} = A \oplus B \oplus C_{in}$
  - $\text{CARRY} = (A \cdot B) + ((A \oplus B) \cdot C_{in})$

### Experiment 9: Boolean SOP & POS Implementation
- Documented canonical minterms: $X_{SOP} = \Sigma(1, 3, 6)$
  - $m_1 = \overline{A}\overline{B}C$
  - $m_3 = \overline{A}BC$
  - $m_6 = AB\overline{C}$

### Experiment 10: Combinational Logic with Minimum NAND Gates
- Target function: $F = AB + BC + AC$ (Majority / Carry function)
- Pure NAND Realization:
  - Stage 1: $N_1 = \overline{AB}$, $N_2 = \overline{BC}$, $N_3 = \overline{AC}$
  - Stage 2: $F = \overline{N_1 \cdot N_2 \cdot N_3} = \overline{\overline{AB} \cdot \overline{BC} \cdot \overline{AC}} = AB + BC + AC$
