# SIMLAB AI: Analog Simulation Engine (PySpice & Simulink Equiv.)

## Engine Overview
The analog simulation architecture provides numerical solvers and PySpice netlist generators for Experiments 1–6 and Experiments 11–14.

## Supported Simulation Modes

### 1. DC Operating Point (.op)
- **Experiments**: Exp 1 (Resistor Bridge), Exp 2 (CCCS), Exp 3 (VCVS).
- **Behavior**: Solves Kirchhoff's Current Law nodal equations with all capacitors open-circuited and inductors short-circuited.

### 2. Transient Natural Response
- **Experiment 4**: RC circuit discharging from initial condition $V_0$.
- **Equation**: $V_c(t) = V_0 e^{-t/\tau}$, where $\tau = R \cdot C$.
- **Outputs**: Instantaneous capacitor voltage $V_c(t)$, current $I(t)$, and time constant $\tau$.

### 3. Transient Step Response
- **Experiment 5**: RC circuit charging from zero to step voltage $V_{in}$.
- **Equation**: $V_c(t) = V_{in}(1 - e^{-t/\tau})$.
- **Verification**: At $t = \tau$, $V_c = 0.632 \cdot V_{in}$. Steady-state reached at $5\tau$.

### 4. Pacemaker Timing Circuit
- **Experiment 6**: RC relaxation oscillator modeling rhythmic cardiac pulses at 70 BPM ($T = 60/70 \approx 0.857\text{ s}$).
- **Formula**: $R = \frac{T}{C \ln(1 / (1 - \text{factor}))}$.

### 5. Semiconductor Diode & Zener Regulators
- **Experiment 11**: Forward and reverse I-V characteristic curve ($0.6\text{–}0.7\text{ V}$ knee voltage).
- **Experiment 12**: Zener diode regulation clamping load voltage to $V_z = 5.1\text{ V}$.

### 6. Rectifier Circuits
- **Experiment 13**: Half-Wave Rectifier with shunt capacitor filter (ripple factor comparison).
- **Experiment 14**: Full-Wave Bridge Rectifier with 4 diodes (double ripple frequency $2f = 100\text{ Hz}$).
