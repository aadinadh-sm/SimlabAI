# SIMLAB AI: Circuit Intermediate Representation (Circuit IR)

Circuit IR is a simulator-independent, JSON-based intermediate representation designed to bridge circuit editors, whiteboard sketches, PySpice netlists, and digital logic simulators.

## Schema Specification

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "CircuitIR",
  "type": "object",
  "properties": {
    "version": { "type": "string" },
    "metadata": {
      "type": "object",
      "properties": {
        "name": { "type": "string" },
        "experiment": { "type": "integer" },
        "description": { "type": "string" },
        "created_at": { "type": "integer" }
      }
    },
    "components": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": { "type": "string" },
          "type": {
            "type": "string",
            "enum": [
              "resistor", "capacitor", "inductor", "diode", "zener",
              "dc_voltage_source", "ac_voltage_source", "cccs", "vcvs",
              "switch", "ground", "gate"
            ]
          },
          "value": { "type": "number" },
          "unit": { "type": "string" },
          "nodes": {
            "type": "array",
            "items": { "type": "string" }
          },
          "parameters": { "type": "object" }
        },
        "required": ["id", "type", "nodes"]
      }
    },
    "nodes": {
      "type": "array",
      "items": { "type": "string" }
    },
    "ground_node": { "type": "string" },
    "analysis": {
      "type": "object",
      "properties": {
        "type": { "type": "string", "enum": ["op", "transient", "dc_sweep"] },
        "step": { "type": "number" },
        "stop": { "type": "number" },
        "use_initial_condition": { "type": "boolean" }
      }
    }
  },
  "required": ["version", "components", "nodes", "ground_node"]
}
```

## Topological Validation Rules
Before executing any simulation or generating code, the topology validator checks:
1. **Explicit Ground Reference**: A reference node `GND` or `0` must be present.
2. **Floating Node Detection**: Every node must connect to at least 2 component pins (unless designated as an open test probe).
3. **Short-Circuit Prevention**: Independent voltage sources must not have both terminals tied to the same node.
4. **Physical Value Constraints**: Component parameters ($R, C, L$) must be strictly positive non-zero values.
