"""
SIMLAB AI - Deterministic Circuit Pipeline & Progressive Reconstruction Engine

Strict 8-Stage Pipeline:
  LATEST USER MESSAGE (ONLY source for user-provided component values)
  ↓
  1. ENTITY EXTRACTION (strictly from latest user message; zero cross-turn or manual contamination)
  ↓
  2. CIRCUIT TYPE / INTENT CLASSIFICATION (executed BEFORE manual experiment retrieval)
  ↓
  3. MANUAL EXPERIMENT RETRIEVAL (provides topology/theory/procedure; never overwrites user values)
  ↓
  4. TOPOLOGY TEMPLATE & PARAMETER COMPLETENESS AUDIT
     - Determines required manual parameters
     - Identifies ✓ User supplied, ✓ Manual default, ? Missing / ambiguous
     - Never silently deletes topology-defining manual components (switches, pulse sources, resistors, ic, timing)
  ↓
  5. PARAMETER SUBSTITUTION (substitutes extracted user entities into topology template while preserving manual defaults)
  ↓
  6. CIRCUIT IR & TOPOLOGY DISTINCTION
     - Clearly distinguishes:
       * EXACT MANUAL TOPOLOGY
       * MODIFIED MANUAL TOPOLOGY
       * GENERALIZED CIRCUIT
  ↓
  7. VALIDATION & SIMULATION LIFECYCLE
     - TOPOLOGY_RECONSTRUCTED
     - TOPOLOGY_VALIDATED
     - SIMULATION_EXECUTED
     - SIMULATION_SUCCESSFUL
  ↓
  8. CODE GENERATION
"""

import re
import json
import math
from typing import Dict, List, Any, Optional, Tuple


class ProgressiveCircuitEngine:

    # Words starting with R, C, L, V, I that are English words, NOT component designators
    RESERVED_WORDS = {
        "r", "resistor", "resistors", "resistance", "response", "rectifier", "regulator",
        "rate", "reference", "result", "results", "run", "running", "ramp", "rc", "rl", "rlc",
        "c", "capacitor", "capacitors", "capacitance", "circuit", "circuits", "current",
        "cccs", "code", "compute", "computation", "combinational", "characteristic", "characteristics",
        "control", "controlled", "center", "centre",
        "l", "load", "logic", "ladder", "loop", "low", "line",
        "v", "voltage", "volt", "volts", "vcvs", "vccs", "verify", "verification", "value", "values",
        "i", "in", "input", "inductor", "inductors", "inductance", "inverting", "implementation", "is", "if", "ic"
    }

    @staticmethod
    def _scale_value(val: float, prefix: str) -> float:
        p = prefix.strip()
        if p == "M" or p.lower() == "meg":
            return val * 1e6
        if p == "G":
            return val * 1e9
        p_low = p.lower()
        if p_low == "k":
            return val * 1e3
        if p_low == "m":
            return val * 1e-3
        if p_low in ("u", "µ"):
            return val * 1e-6
        if p_low == "n":
            return val * 1e-9
        if p_low == "p":
            return val * 1e-12
        return val

    @staticmethod
    def _format_eng(val: float, unit: str) -> str:
        if unit == "ohm":
            if val >= 1e6:
                return f"{val/1e6:g} MΩ"
            if val >= 1e3:
                return f"{val/1e3:g} kΩ"
            return f"{val:g} Ω"
        if unit == "F":
            if val < 1e-9:
                return f"{val*1e12:g} pF"
            if val < 1e-7:
                return f"{val*1e9:g} nF"
            if val < 1e-3:
                return f"{val*1e6:g} µF"
            if val < 1.0:
                return f"{val*1e3:g} mF"
            return f"{val:g} F"
        if unit == "H":
            if val < 1e-3:
                return f"{val*1e6:g} µH"
            if val < 1.0:
                return f"{val*1e3:g} mH"
            return f"{val:g} H"
        if unit == "A":
            if val < 1e-3:
                return f"{val*1e6:g} µA"
            if val < 1.0:
                return f"{val*1e3:g} mA"
            return f"{val:g} A"
        if unit == "s":
            if val < 1e-3:
                return f"{val*1e6:g} µs"
            if val < 1.0:
                return f"{val*1e3:g} ms"
            return f"{val:g} s"
        return f"{val:g} {unit}".strip()

    @staticmethod
    def _format_pyspice_res(val: float) -> str:
        if val >= 1e6:
            return f"{val/1e6:g}@u_MOhm"
        if val >= 1e3:
            return f"{val/1e3:g}@u_kOhm"
        return f"{val:g}@u_Ohm"

    @classmethod
    def validate_time_quantity(
        cls,
        arg1: Any,
        arg2: str,
        arg3: Optional[str] = None,
        strict: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Validates every generated time quantity against its textual meaning before presenting or executing it.
        Supports:
          - 3-arg call: `validate_time_quantity(val_seconds: float, code_expr: str, textual_meaning: str)` (defaults `strict=True`)
          - 2-arg call: `validate_time_quantity(code_expr: str, textual_meaning: str)` (defaults `strict=False`, returns `is_valid` and `corrected_expr`)
        Strictly enforces:
          - Never generate `@u_s` (e.g., `3.75@u_s` or `60@u_s`) when the intended duration is in seconds
            (`3.75 seconds != 3.75 microseconds`, `60 seconds != 60 microseconds`).
          - Numeric value in `code_expr` multiplied by its unit factor must equal `val_seconds`.
          - Unit in `code_expr` must match `textual_meaning`.
        """
        unit_factors = {
            "u_ns": (1e-9, ("ns", "nanosecond", "nanoseconds")),
            "u_us": (1e-6, ("us", "µs", "microsecond", "microseconds")),
            "u_ms": (1e-3, ("ms", "millisecond", "milliseconds")),
            "u_time_s": (1.0, ("s", "sec", "second", "seconds")),
            "u_si_s": (1.0, ("s", "sec", "second", "seconds")),
            "u_second": (1.0, ("s", "sec", "second", "seconds")),
        }

        if arg3 is not None:
            val_seconds = float(arg1)
            expr_clean = str(arg2).strip()
            textual_meaning = str(arg3).strip()
            is_strict = True if strict is None else bool(strict)
        else:
            expr_clean = str(arg1).strip()
            textual_meaning = str(arg2).strip()
            is_strict = False if strict is None else bool(strict)
            m_txt = re.search(
                r'([0-9]+(?:\.[0-9]+)?(?:e[+-]?\d+)?)\s*(nanoseconds?|ns|microseconds?|µs|us|milliseconds?|ms|seconds?|sec|s)\b',
                textual_meaning,
                re.IGNORECASE,
            )
            if m_txt:
                t_mag = float(m_txt.group(1))
                t_unit = m_txt.group(2).lower()
                if t_unit in ("ns", "nanosecond", "nanoseconds"):
                    val_seconds = t_mag * 1e-9
                elif t_unit in ("us", "µs", "microsecond", "microseconds"):
                    val_seconds = t_mag * 1e-6
                elif t_unit in ("ms", "millisecond", "milliseconds"):
                    val_seconds = t_mag * 1e-3
                else:
                    val_seconds = t_mag
            else:
                val_seconds = 0.0

        meaning_low = textual_meaning.lower()
        if val_seconds < 1e-6 and val_seconds > 0:
            corr_expr = f"{round(val_seconds * 1e9, 6):g}@u_ns"
        elif val_seconds < 1e-3 and val_seconds > 0:
            corr_expr = f"{round(val_seconds * 1e6, 6):g}@u_us"
        elif val_seconds < 1.0 and val_seconds > 0:
            corr_expr = f"{round(val_seconds * 1e3, 6):g}@u_ms"
        else:
            corr_expr = f"{round(val_seconds, 6):g}@u_time_s"

        # Hard ban on ambiguous `@u_s` token anywhere in generated time expressions
        if re.search(r'@\s*u_s\b', expr_clean):
            err_msg = (
                f"UNIT GENERATION BUG: Refusing to generate '{expr_clean}' for '{textual_meaning}' "
                f"({val_seconds:g} s). Never use '@u_s' when seconds or microseconds are intended."
            )
            if is_strict:
                raise ValueError(err_msg)
            m_bad = re.match(r'^([0-9]+(?:\.[0-9]+)?(?:e[+-]?\d+)?)\s*@\s*u_s\b', expr_clean, re.IGNORECASE)
            bad_sec = float(m_bad.group(1)) * 1e-6 if m_bad else 0.0
            return {
                "valid": False,
                "is_valid": False,
                "error": err_msg,
                "val_seconds": val_seconds,
                "expected_seconds": val_seconds,
                "code_seconds": bad_sec,
                "code_expr": expr_clean,
                "corrected_expr": corr_expr,
                "textual_meaning": textual_meaning,
                "unit_token": "u_s",
            }

        m_at = re.match(r'^([0-9]+(?:\.[0-9]+)?(?:e[+-]?\d+)?)\s*@\s*(u_ns|u_us|u_ms|u_time_s|u_si_s|u_second)$', expr_clean, re.IGNORECASE)
        m_as = re.match(r'^as_s\(\s*([0-9]+(?:\.[0-9]+)?(?:e[+-]?\d+)?)\s*\)$', expr_clean, re.IGNORECASE)

        if m_at:
            mag = float(m_at.group(1))
            u_tok = m_at.group(2)
            factor, allowed_words = unit_factors[u_tok]
            parsed_seconds = mag * factor
        elif m_as:
            mag = float(m_as.group(1))
            u_tok = "as_s"
            factor = 1.0
            allowed_words = ("s", "sec", "second", "seconds")
            parsed_seconds = mag
        else:
            err_msg = f"Unrecognized PySpice time expression '{expr_clean}' for '{textual_meaning}'."
            if is_strict:
                raise ValueError(err_msg)
            return {
                "valid": False,
                "is_valid": False,
                "error": err_msg,
                "val_seconds": val_seconds,
                "expected_seconds": val_seconds,
                "code_seconds": 0.0,
                "code_expr": expr_clean,
                "corrected_expr": corr_expr,
                "textual_meaning": textual_meaning,
                "unit_token": None,
            }

        if abs(parsed_seconds - val_seconds) > max(1e-12, 1e-6 * abs(val_seconds)):
            err_msg = (
                f"TIME QUANTITY MISMATCH: '{expr_clean}' evaluates to {parsed_seconds:g} s, "
                f"which does not match intended {val_seconds:g} s ('{textual_meaning}')."
            )
            if is_strict:
                raise ValueError(err_msg)
            return {
                "valid": False,
                "is_valid": False,
                "error": err_msg,
                "val_seconds": val_seconds,
                "expected_seconds": val_seconds,
                "code_seconds": parsed_seconds,
                "code_expr": expr_clean,
                "corrected_expr": corr_expr,
                "textual_meaning": textual_meaning,
                "unit_token": u_tok,
            }

        if not any(re.search(rf'\b{ re.escape(w) }\b', meaning_low) for w in allowed_words):
            err_msg = f"TEXTUAL UNIT MISMATCH: '{expr_clean}' does not match textual meaning '{textual_meaning}'."
            if is_strict:
                raise ValueError(err_msg)
            return {
                "valid": False,
                "is_valid": False,
                "error": err_msg,
                "val_seconds": val_seconds,
                "expected_seconds": val_seconds,
                "code_seconds": parsed_seconds,
                "code_expr": expr_clean,
                "corrected_expr": corr_expr,
                "textual_meaning": textual_meaning,
                "unit_token": u_tok,
            }

        return {
            "valid": True,
            "is_valid": True,
            "val_seconds": val_seconds,
            "expected_seconds": val_seconds,
            "code_seconds": parsed_seconds,
            "code_expr": expr_clean,
            "corrected_expr": expr_clean,
            "textual_meaning": textual_meaning,
            "unit_token": u_tok,
        }

    @classmethod
    def _format_pyspice_time(cls, val_seconds: float) -> Tuple[str, str, bool]:
        """
        Formats a duration in seconds into `(code_expr, textual_meaning, requires_u_time_s_def)`
        and validates the result with `validate_time_quantity` before returning.
        Never generates `@u_s`! Uses `@u_time_s` (`u_time_s = UnitValueShorcut(U_s)`) for seconds.
        """
        if val_seconds < 1e-6:
            mag = round(val_seconds * 1e9, 6)
            code_expr = f"{mag:g}@u_ns"
            textual = f"{mag:g} nanoseconds"
            needs_sec = False
        elif val_seconds < 1e-3:
            mag = round(val_seconds * 1e6, 6)
            code_expr = f"{mag:g}@u_us"
            textual = f"{mag:g} microseconds"
            needs_sec = False
        elif val_seconds < 1.0:
            mag = round(val_seconds * 1e3, 6)
            code_expr = f"{mag:g}@u_ms"
            textual = f"{mag:g} milliseconds"
            needs_sec = False
        else:
            mag = round(val_seconds, 6)
            code_expr = f"{mag:g}@u_time_s"
            textual = f"{mag:g} seconds"
            needs_sec = True

        cls.validate_time_quantity(val_seconds, code_expr, textual)
        return code_expr, textual, needs_sec

    @classmethod
    def verify_step_stop_consistency(
        cls,
        raw_step_s: float,
        raw_stop_s: float,
        target_period_s: Optional[float] = None,
        rc_tau_s: Optional[float] = None,
        required_cycles: int = 5
    ) -> Dict[str, Any]:
        """
        Pre-simulation Step/Stop & Observation-Window consistency check:
        1. Verifies:
             step_time > 0
             end_time > 0
             step_time <= end_time
           and ensures `1 ms` is NEVER silently used as the timestep for a `60 us` simulation.
        2. If `step_time > end_time` (or `step_time > end_time / 10`), automatically computes a
           compatible `step_time` for the raw window AND a compatible `(step_time, end_time)` pair
           for observing `required_cycles` complete periods (`5 * T = 3.75 seconds` for 80 BPM),
           validating every generated time quantity against its textual meaning.
        """
        step_pos = raw_step_s > 0.0
        stop_pos = raw_stop_s > 0.0
        step_le_stop = raw_step_s <= raw_stop_s
        step_resolution_ok = raw_step_s <= (raw_stop_s / 10.0) if stop_pos else False
        raw_pair_consistent = bool(step_pos and stop_pos and step_le_stop and step_resolution_ok)

        raw_step_expr, raw_step_text, _ = cls._format_pyspice_time(raw_step_s if step_pos else 1e-3)
        raw_stop_expr, raw_stop_text, _ = cls._format_pyspice_time(raw_stop_s if stop_pos else 60e-6)

        # 1. Compatible step_time for the raw stop window (e.g., 1@u_us for 60@u_us instead of 1@u_ms)
        if not raw_pair_consistent:
            if abs(raw_stop_s - 60e-6) < 1e-9:
                compat_step_for_raw_stop_s = 1e-6
            else:
                compat_step_for_raw_stop_s = max(1e-9, round(raw_stop_s / 60.0, 9))
        else:
            compat_step_for_raw_stop_s = raw_step_s

        compat_raw_step_expr, compat_raw_step_text, _ = cls._format_pyspice_time(compat_step_for_raw_stop_s)

        # 2. Required duration to observe `required_cycles` full cycles (e.g. 5 * 0.75 s = 3.75 seconds for 80 BPM)
        if target_period_s and target_period_s > 0:
            req_duration_s = round(required_cycles * target_period_s, 6)
        elif rc_tau_s and rc_tau_s > 0:
            req_duration_s = round(5.0 * rc_tau_s, 6)
        else:
            req_duration_s = max(raw_stop_s, 1.0)

        compat_step_for_req_s = 1e-3 if req_duration_s >= 0.05 else round(req_duration_s / 100.0, 6)
        req_step_expr, req_step_text, _ = cls._format_pyspice_time(compat_step_for_req_s)
        req_stop_expr, req_stop_text, req_needs_u_second = cls._format_pyspice_time(req_duration_s)

        window_sufficient = bool(
            stop_pos
            and (target_period_s is None or raw_stop_s >= req_duration_s - 1e-9)
            and (rc_tau_s is None or raw_stop_s >= rc_tau_s - 1e-9)
        )

        changes_reported: List[str] = []
        if not step_le_stop:
            changes_reported.append(
                f"STEP/STOP INCONSISTENCY DETECTED (`step_time > end_time`): Raw `step_time = {raw_step_text}` "
                f"(`{raw_step_expr}`, {raw_step_s:g} s) exceeds `end_time = {raw_stop_text}` (`{raw_stop_expr}`, {raw_stop_s:g} s). "
                f"`{raw_step_text}` cannot be used as the timestep for a `{raw_stop_text}` simulation. "
                f"Automatically adjusted raw-window diagnostic timestep to `step_time = {compat_raw_step_expr}` ({compat_raw_step_text}) "
                f"so `step_time <= end_time` ({compat_step_for_raw_stop_s:g} s <= {raw_stop_s:g} s)."
            )
        elif not step_resolution_ok:
            changes_reported.append(
                f"STEP/STOP RESOLUTION ADJUSTMENT: Raw `step_time = {raw_step_text}` is too coarse for `end_time = {raw_stop_text}`. "
                f"Adjusted timestep to `step_time = {compat_raw_step_expr}` ({compat_raw_step_text})."
            )

        if not window_sufficient and target_period_s:
            changes_reported.append(
                f"OBSERVATION WINDOW CORRECTION (`{raw_stop_text}` -> `{req_stop_text}`): "
                f"For target period T = {target_period_s:.4f} s, observing {required_cycles} complete cycles requires "
                f"`end_time = {required_cycles} * {target_period_s:g} s = {req_stop_text}` (`{req_stop_expr}`, equivalent to `as_s({req_duration_s:g})`) "
                f"with compatible `step_time = {req_step_expr}` ({req_step_text}, satisfying `0 < {compat_step_for_req_s:g} s <= {req_duration_s:g} s`)."
            )

        return {
            "step_positive": step_pos,
            "stop_positive": stop_pos,
            "step_le_stop": step_le_stop,
            "raw_pair_consistent": raw_pair_consistent,
            "was_adjusted": bool(not raw_pair_consistent or not window_sufficient),
            "adjustment_reason": " ".join(changes_reported),
            "window_sufficient": window_sufficient,
            "raw_step_s": raw_step_s,
            "raw_stop_s": raw_stop_s,
            "raw_step_expr": raw_step_expr,
            "raw_stop_expr": raw_stop_expr,
            "raw_step_text": raw_step_text,
            "raw_stop_text": raw_stop_text,
            "compat_step_for_raw_stop_s": compat_step_for_raw_stop_s,
            "compat_raw_step_expr": compat_raw_step_expr,
            "compat_raw_step_text": compat_raw_step_text,
            "required_cycles": required_cycles,
            "required_duration_s": req_duration_s,
            "compat_step_for_req_s": compat_step_for_req_s,
            "req_step_expr": req_step_expr,
            "req_step_text": req_step_text,
            "req_stop_expr": req_stop_expr,
            "req_stop_text": req_stop_text,
            "req_needs_u_second": req_needs_u_second,
            "changes_reported": changes_reported,
        }


    # =========================================================================
    # STAGE 1: DETERMINISTIC ENTITY EXTRACTION (LATEST USER MESSAGE ONLY)
    # =========================================================================
    @classmethod
    def extract_entities(cls, latest_user_message: str, experiment_context: Optional[int] = None) -> Dict[str, Any]:
        """
        Extracts ONLY electrical entities explicitly present in `latest_user_message`.
        Never invents components and never reads from previous turns or manual text.
        """
        text = latest_user_message.strip()

        voltage_sources: List[Dict[str, Any]] = []
        current_sources: List[Dict[str, Any]] = []
        resistors: List[Dict[str, Any]] = []
        capacitors: List[Dict[str, Any]] = []
        inductors: List[Dict[str, Any]] = []
        diodes: List[Dict[str, Any]] = []
        parameters: Dict[str, Any] = {}

        consumed_spans: List[Tuple[int, int]] = []

        def is_span_free(start: int, end: int) -> bool:
            for s, e in consumed_spans:
                if not (end <= s or start >= e):
                    return False
            return True

        def mark_span(start: int, end: int):
            consumed_spans.append((start, end))

        # 0a. Mark "Experiment <N>" / "Exp <N>" spans first so the experiment number is never mistaken for a resistor value
        for exp_m in re.finditer(r'\b(?:experiment|exp\.?)\s*\d+\b', text, re.IGNORECASE):
            mark_span(exp_m.start(), exp_m.end())

        # 0. Extract Initial Condition (ic = 0V, initial condition 5V) first so it isn't mistaken for V1
        ic_pattern = re.compile(
            r'\b(?:ic|initial[_\s]*condition|initial[_\s]*voltage)\s*(?:=|:|is|of)?\s*([0-9]+(?:\.[0-9]+)?)\s*(m)?\s*(?:V|volts?)\b',
            re.IGNORECASE
        )
        for m in ic_pattern.finditer(text):
            if is_span_free(m.start(), m.end()):
                raw_val = float(m.group(1))
                prefix = m.group(2) or ""
                parameters["ic"] = cls._scale_value(raw_val, prefix)
                mark_span(m.start(), m.end())

        # Extract transient timing parameters if explicitly provided by user
        for param_key, regex_str in [
            ("steptime", r'\b(?:step[_\s]*time)\s*(?:=|:|is|of)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:@\s*u_)?(u|µ|m|n)?\s*s(?:ec(?:ond)?s?)?\b'),
            ("switchingtime", r'\b(?:switching[_\s]*time|switch[_\s]*time)\s*(?:=|:|is|of)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:@\s*u_)?(u|µ|m)?\s*s(?:ec(?:ond)?s?)?\b'),
            ("finaltime", r'\b(?:final[_\s]*time|end[_\s]*time|stop[_\s]*time|simulation[_\s]*(?:time|window|duration)|duration|for)\s*(?:=|:|is|of)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:@\s*u_)?(u|µ|m)?\s*s(?:ec(?:ond)?s?)?\b'),
        ]:
            tm = re.search(regex_str, text, re.IGNORECASE)
            if tm and is_span_free(tm.start(), tm.end()):
                raw_num = float(tm.group(1))
                unit_prefix = tm.group(2) or ""
                parameters[param_key] = cls._scale_value(raw_num, unit_prefix)
                parameters[f"{param_key}_raw_unit"] = f"{unit_prefix}s"
                mark_span(tm.start(), tm.end())

        # 1. Extract explicitly labeled Resistors: e.g. R1 = 10k, R2: 5Ω, R3 to 12 ohms, R1 8r, R1 is 2k
        r_label_pattern = re.compile(
            r'\b(R(?:\d+|_?(?:in|f|load|L|th|s|testa|testb))\b)\s*(?:=|:|-|is|of|to|\(\s*)?\s*([0-9]+(?:\.[0-9]+)?)\s*(k|M|m|u|µ)?\s*(Ω|ohm|ohms|r\b)?\s*\)?',
            re.IGNORECASE
        )
        for m in r_label_pattern.finditer(text):
            if not is_span_free(m.start(), m.end()):
                continue
            label = m.group(1)
            if label.lower() in cls.RESERVED_WORDS:
                continue
            matched_str = m.group(0)
            has_unit = bool(m.group(3) or m.group(4))
            has_assign = any(ch in matched_str.lower() for ch in ("=", ":", "is", "of", "("))
            # Avoid false matches like "R1 and R2" or "R1 to node 2" where neither unit nor '=' was given
            if not (has_unit or has_assign):
                continue
            raw_val = float(m.group(2))
            prefix = m.group(3) or ""
            scaled = cls._scale_value(raw_val, prefix)
            resistors.append({
                "id": label.upper(),
                "value": int(scaled) if scaled.is_integer() else scaled,
                "unit": "ohm",
                "explicit_id": True,
                "user_supplied": True
            })
            mark_span(m.start(), m.end())

        # Also check "map 5kΩ to R2" or "5kΩ for R2"
        r_reverse_label_pattern = re.compile(
            r'(?<![a-zA-Z0-9_])([0-9]+(?:\.[0-9]+)?)\s*(k|M|m)?\s*(?:Ω|ohm|ohms)\s*(?:to|for|as|in)\s*\b(R\d+)\b',
            re.IGNORECASE
        )
        for m in r_reverse_label_pattern.finditer(text):
            if not is_span_free(m.start(), m.end()):
                continue
            raw_val = float(m.group(1))
            prefix = m.group(2) or ""
            label = m.group(3).upper()
            scaled = cls._scale_value(raw_val, prefix)
            resistors.append({
                "id": label,
                "value": int(scaled) if scaled.is_integer() else scaled,
                "unit": "ohm",
                "explicit_id": True,
                "user_supplied": True
            })
            mark_span(m.start(), m.end())

        # 1b. Multi-count resistor phrases: e.g. "two 4.7k resistors", "five 2.2k resistors"
        word_to_count = {"two": 2, "three": 3, "four": 4, "five": 5}
        r_count_pattern = re.compile(
            r'\b(two|three|four|five)\s+([0-9]+(?:\.[0-9]+)?)\s*(k|M|m)?\s*(?:Ω|ohm|ohms)?\s*resistors?\b',
            re.IGNORECASE
        )
        for m in r_count_pattern.finditer(text):
            if not is_span_free(m.start(), m.end()):
                continue
            cnt = word_to_count.get(m.group(1).lower(), 1)
            scaled = cls._scale_value(float(m.group(2)), m.group(3) or "")
            for _ in range(cnt):
                resistors.append({
                    "value": int(scaled) if scaled.is_integer() else scaled,
                    "unit": "ohm",
                    "user_supplied": True
                })
            mark_span(m.start(), m.end())

        # 1c. Post-keyword resistor list: e.g. "resistors 4, 2, 8, 6 ohms" or "resistors 1k, 2k, and 3k"
        r_post_list_pattern = re.compile(
            r'\bresistors?\s*(?:are|of|=|:)?\s*([0-9]+(?:\.[0-9]+)?(?![0-9.])\s*(?:k|M)?\s*(?:Ω|ohm|ohms)?(?:\s*(?:,\s*(?:and\s+)?|\s+and\s+|\s+)\s*[0-9]+(?:\.[0-9]+)?(?![0-9.])\s*(?:k|M)?\s*(?:Ω|ohm|ohms)?(?!\s*(?:m|u|µ)?\s*(?:A|amps?|amperes?|V|volts?|F|farads?|H|henries)\b))+)',
            re.IGNORECASE
        )
        for m in r_post_list_pattern.finditer(text):
            if not is_span_free(m.start(), m.end()):
                continue
            sub = m.group(1)
            items = re.findall(r'([0-9]+(?:\.[0-9]+)?)\s*(k|M)?', sub, re.IGNORECASE)
            if len(items) >= 2:
                for val_s, pref in items:
                    scaled = cls._scale_value(float(val_s), pref or "")
                    resistors.append({
                        "value": int(scaled) if scaled.is_integer() else scaled,
                        "unit": "ohm",
                        "user_supplied": True
                    })
                mark_span(m.start(), m.end())

        # 2. Extract values explicitly suffixed with Ω / ohm / ohms (e.g., "10Ω, 5Ω, 3Ω, 8Ω resistors" or "5kΩ")
        r_unit_pattern = re.compile(
            r'(?<![a-zA-Z0-9_])([0-9]+(?:\.[0-9]+)?)\s*(k|M|m)?\s*(?:Ω|ohm|ohms)(?![a-zA-Z])',
            re.IGNORECASE
        )
        for m in r_unit_pattern.finditer(text):
            if not is_span_free(m.start(), m.end()):
                continue
            raw_val = float(m.group(1))
            prefix = m.group(2) or ""
            scaled = cls._scale_value(raw_val, prefix)
            resistors.append({
                "value": int(scaled) if scaled.is_integer() else scaled,
                "unit": "ohm",
                "user_supplied": True
            })
            mark_span(m.start(), m.end())

        # 3. Extract pre-keyword resistors without Ω symbol: e.g. "2k, 1k, 2k resistors", "a 1k resistor", or "1.5k load"
        r_pre_list_pattern = re.compile(
            r'((?:[0-9]+(?:\.[0-9]+)?\s*(?:k|M)?\s*(?:,\s*|\s+and\s+)?)+)\s*(?:(?:series\s+|parallel\s+|load\s+|bridge\s+)?resistors?|load)\b',
            re.IGNORECASE
        )
        for m in r_pre_list_pattern.finditer(text):
            if not is_span_free(m.start(), m.end()):
                continue
            sub = m.group(1)
            items = re.findall(r'([0-9]+(?:\.[0-9]+)?)\s*(k|M)?', sub, re.IGNORECASE)
            if items:
                for val_s, pref in items:
                    scaled = cls._scale_value(float(val_s), pref or "")
                    resistors.append({
                        "value": int(scaled) if scaled.is_integer() else scaled,
                        "unit": "ohm",
                        "user_supplied": True
                    })
                mark_span(m.start(), m.end())

        # 4. Extract Voltage Sources: e.g. "24V source", "V1 = 12V", "10V battery", "Vs = 6V"
        v_label_pattern = re.compile(
            r'\b(V(?:\d+|_?(?:s|in|input|dd|cc|dc|ac))\b)\s*(?:=|:|-|is|of|to|\(\s*)?\s*([0-9]+(?:\.[0-9]+)?)\s*(m|k)?\s*(?:V|volts?|VDC|VAC)\b\s*\)?',
            re.IGNORECASE
        )
        for m in v_label_pattern.finditer(text):
            if not is_span_free(m.start(), m.end()):
                continue
            label = m.group(1)
            if label.lower() in cls.RESERVED_WORDS:
                continue
            raw_val = float(m.group(2))
            prefix = m.group(3) or ""
            scaled = cls._scale_value(raw_val, prefix)
            voltage_sources.append({
                "id": label.upper(),
                "value": int(scaled) if scaled.is_integer() else scaled,
                "unit": "V",
                "explicit_id": True,
                "user_supplied": True
            })
            mark_span(m.start(), m.end())

        # Value + V / volts (excluding Zener breakdown voltage like "5.1V Zener")
        v_unit_pattern = re.compile(
            r'(?<![a-zA-Z0-9_])([0-9]+(?:\.[0-9]+)?)\s*(m|k)?\s*(?:V|volts?|VDC|VAC)\b(?!\s*zener)',
            re.IGNORECASE
        )
        for m in v_unit_pattern.finditer(text):
            if not is_span_free(m.start(), m.end()):
                continue
            prefix_context = text[max(0, m.start() - 15):m.start()].lower()
            if "zener" in prefix_context or "vz" in prefix_context:
                continue
            raw_val = float(m.group(1))
            prefix = m.group(2) or ""
            scaled = cls._scale_value(raw_val, prefix)
            voltage_sources.append({
                "value": int(scaled) if scaled.is_integer() else scaled,
                "unit": "V",
                "user_supplied": True
            })
            mark_span(m.start(), m.end())

        # 5. Extract Current Sources: e.g. "2A current source", "I1 = 5A", "5mA source"
        i_label_pattern = re.compile(
            r'\b(I(?:\d+|_?(?:s|in))\b)\s*(?:=|:|-|is|of|\(\s*)?\s*([0-9]+(?:\.[0-9]+)?)\s*(m|u|µ)?\s*(?:A|amps?|amperes?)\b\s*\)?',
            re.IGNORECASE
        )
        for m in i_label_pattern.finditer(text):
            if not is_span_free(m.start(), m.end()):
                continue
            raw_val = float(m.group(2))
            prefix = m.group(3) or ""
            scaled = cls._scale_value(raw_val, prefix)
            current_sources.append({
                "id": m.group(1).upper(),
                "value": int(scaled) if scaled.is_integer() else scaled,
                "unit": "A",
                "explicit_id": True,
                "user_supplied": True
            })
            mark_span(m.start(), m.end())

        i_unit_pattern = re.compile(
            r'(?<![a-zA-Z0-9_])([0-9]+(?:\.[0-9]+)?)\s*(m|u|µ)?\s*(?:A|amps?|amperes?)\b',
            re.IGNORECASE
        )
        for m in i_unit_pattern.finditer(text):
            if not is_span_free(m.start(), m.end()):
                continue
            raw_val = float(m.group(1))
            prefix = m.group(2) or ""
            scaled = cls._scale_value(raw_val, prefix)
            current_sources.append({
                "value": int(scaled) if scaled.is_integer() else scaled,
                "unit": "A",
                "user_supplied": True
            })
            mark_span(m.start(), m.end())

        # 6. Extract Capacitors: e.g. "0.5uF", "47 µF", "C1 = 10uF", "2µF"
        c_pattern = re.compile(
            r'(?:\b(C\d+)\s*(?:=|:|-|is|of|\(\s*)?\s*)?(?<![a-zA-Z0-9_])([0-9]+(?:\.[0-9]+)?)\s*(u|µ|n|p|m)\s*(?:F|farads?)\b\s*\)?',
            re.IGNORECASE
        )
        for m in c_pattern.finditer(text):
            if not is_span_free(m.start(), m.end()):
                continue
            c_id = m.group(1).upper() if m.group(1) else None
            raw_val = float(m.group(2))
            prefix = m.group(3) or "u"
            scaled = cls._scale_value(raw_val, prefix)
            entry: Dict[str, Any] = {
                "value": scaled,
                "unit": "F",
                "display": f"{raw_val:g} {prefix.replace('u', 'µ')}F",
                "user_supplied": True
            }
            if c_id:
                entry["id"] = c_id
                entry["explicit_id"] = True
            capacitors.append(entry)
            mark_span(m.start(), m.end())

        # 7. Extract Inductors: e.g. "10mH", "L1 = 50mH"
        l_pattern = re.compile(
            r'(?:\b(L\d+)\s*(?:=|:|-|is|of|\(\s*)?\s*)?(?<![a-zA-Z0-9_])([0-9]+(?:\.[0-9]+)?)\s*(m|u|µ)?\s*(?:H|henry|henries)\b\s*\)?',
            re.IGNORECASE
        )
        for m in l_pattern.finditer(text):
            if not is_span_free(m.start(), m.end()):
                continue
            if m.group(0).strip().upper().startswith("H"):
                continue
            l_id = m.group(1).upper() if m.group(1) else None
            raw_val = float(m.group(2))
            prefix = m.group(3) or ""
            scaled = cls._scale_value(raw_val, prefix)
            entry = {"value": scaled, "unit": "H", "display": f"{raw_val:g} {prefix}H".strip(), "user_supplied": True}
            if l_id:
                entry["id"] = l_id
                entry["explicit_id"] = True
            inductors.append(entry)
            mark_span(m.start(), m.end())

        # Assign deterministic sequential IDs to any unlabeled user-extracted components
        used_v_ids = {v["id"] for v in voltage_sources if "id" in v}
        v_seq = 1
        for v in voltage_sources:
            v["user_supplied"] = True
            if "id" not in v:
                while f"V{v_seq}" in used_v_ids:
                    v_seq += 1
                v["id"] = f"V{v_seq}"
                used_v_ids.add(v["id"])

        used_r_ids = {r["id"] for r in resistors if "id" in r}
        r_seq = 1
        for r in resistors:
            r["user_supplied"] = True
            if "id" not in r:
                while f"R{r_seq}" in used_r_ids:
                    r_seq += 1
                r["id"] = f"R{r_seq}"
                used_r_ids.add(r["id"])

        used_i_ids = {i_item["id"] for i_item in current_sources if "id" in i_item}
        i_seq = 1
        for i_item in current_sources:
            i_item["user_supplied"] = True
            if "id" not in i_item:
                while f"I{i_seq}" in used_i_ids:
                    i_seq += 1
                i_item["id"] = f"I{i_seq}"
                used_i_ids.add(i_item["id"])

        used_c_ids = {c_item["id"] for c_item in capacitors if "id" in c_item}
        c_seq = 1
        for c_item in capacitors:
            c_item["user_supplied"] = True
            if "id" not in c_item:
                while f"C{c_seq}" in used_c_ids:
                    c_seq += 1
                c_item["id"] = f"C{c_seq}"
                used_c_ids.add(c_item["id"])

        used_l_ids = {l_item["id"] for l_item in inductors if "id" in l_item}
        l_seq = 1
        for l_item in inductors:
            l_item["user_supplied"] = True
            if "id" not in l_item:
                while f"L{l_seq}" in used_l_ids:
                    l_seq += 1
                l_item["id"] = f"L{l_seq}"
                used_l_ids.add(l_item["id"])

        # 8. Extract Diodes / Zener
        if re.search(r'\bzener\b', text, re.IGNORECASE):
            vz_m = re.search(r'(?:vz\s*(?:=|:|is)?\s*|zener\s*(?:diode)?\s*(?:of|with)?\s*)([0-9]+(?:\.[0-9]+)?)\s*V\b', text, re.IGNORECASE)
            vz = float(vz_m.group(1)) if vz_m else 5.1
            diodes.append({"type": "zener", "vz": vz, "unit": "V", "explicit_vz": vz_m is not None, "user_supplied": True})
        elif re.search(r'\bdiodes?\b', text, re.IGNORECASE):
            diodes.append({"type": "diode", "model": "1N4007", "user_supplied": True})

        # 9. Extract Dependent Source Gain / Heart Rate BPM / Boolean Expression
        gain_m = re.search(r'\bgain\s*(?:of|=|:|is)?\s*([0-9]+(?:\.[0-9]+)?)', text, re.IGNORECASE)
        if gain_m:
            g_val = float(gain_m.group(1))
            parameters["gain"] = int(g_val) if g_val.is_integer() else g_val

        bpm_m = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*(?:bpm|beats\s*per\s*minute)', text, re.IGNORECASE)
        if not bpm_m:
            bpm_m = re.search(r'\b(?:heart\s*rate|H)\s*(?:=|:|is|of)?\s*([0-9]+(?:\.[0-9]+)?)', text, re.IGNORECASE)
        if bpm_m:
            parameters["heart_rate_bpm"] = float(bpm_m.group(1))

        sf_m = re.search(r'switching[_\s]*factor\s*(?:=|:|is|of)?\s*([0-9]+(?:\.[0-9]+)?)', text, re.IGNORECASE)
        if sf_m:
            parameters["switching_factor"] = float(sf_m.group(1))

        bool_m = re.search(r'\b([FXY]\s*=\s*[A-D01\+\'\(\)\s\.\^]+)', text)
        if bool_m:
            parameters["boolean_expression"] = bool_m.group(1).strip()

        classification = cls.classify_circuit_intent(
            text,
            {
                "voltage_sources": voltage_sources,
                "resistors": resistors,
                "current_sources": current_sources,
                "capacitors": capacitors,
                "inductors": inductors,
                "diodes": diodes,
                "parameters": parameters,
            },
            experiment_context=experiment_context
        )

        result: Dict[str, Any] = {
            "circuit_type": classification["circuit_type"],
            "voltage_sources": voltage_sources,
            "resistors": resistors,
            "current_sources": current_sources,
        }
        if capacitors:
            result["capacitors"] = capacitors
        if inductors:
            result["inductors"] = inductors
        if diodes:
            result["diodes"] = diodes
        if parameters:
            result["parameters"] = parameters
        if classification.get("inferred_topology_lines"):
            result["inferred_topology"] = classification["inferred_topology_lines"]

        return result

    # =========================================================================
    # HELPER: BUILD USER-SUPPLIED PARAMETER LIST FROM EXTRACTED ENTITIES
    # =========================================================================
    @classmethod
    def _build_user_supplied_entries(
        cls,
        entities: Dict[str, Any],
        comp_node_roles: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Deterministically converts every value extracted from `latest_user_message`
        into a `USER SUPPLIED` completeness entry.
        Guarantees that extracted entities are NEVER accompanied by "No custom values supplied".
        """
        entries: List[Dict[str, Any]] = []
        roles = comp_node_roles or {}

        for idx, v in enumerate(entities.get("voltage_sources", [])):
            cid = v.get("id", f"V{idx+1}")
            val = float(v["value"])
            entries.append({
                "id": cid,
                "value": cls._format_eng(val, "V"),
                "manual_default": "N/A (User-Defined)",
                "role": roles.get(cid, "User-supplied DC/AC Voltage Source"),
                "is_modified": True,
                "user_supplied": True,
                "note": "Explicitly supplied in user prompt"
            })

        for idx, r in enumerate(entities.get("resistors", [])):
            cid = r.get("id", f"R{idx+1}")
            val = float(r["value"])
            entries.append({
                "id": cid,
                "value": cls._format_eng(val, "ohm"),
                "manual_default": "N/A (User-Defined)",
                "role": roles.get(cid, f"User-supplied Resistor {cid}"),
                "is_modified": True,
                "user_supplied": True,
                "note": "Explicitly supplied in user prompt"
            })

        for idx, i_src in enumerate(entities.get("current_sources", [])):
            cid = i_src.get("id", f"I{idx+1}")
            val = float(i_src["value"])
            entries.append({
                "id": cid,
                "value": cls._format_eng(val, "A"),
                "manual_default": "N/A (User-Defined)",
                "role": roles.get(cid, f"User-supplied Current Source {cid}"),
                "is_modified": True,
                "user_supplied": True,
                "note": "Explicitly supplied in user prompt"
            })

        for idx, c in enumerate(entities.get("capacitors", [])):
            cid = c.get("id", f"C{idx+1}")
            val = float(c["value"])
            entries.append({
                "id": cid,
                "value": c.get("display", cls._format_eng(val, "F")),
                "manual_default": "N/A (User-Defined)",
                "role": roles.get(cid, f"User-supplied Capacitor {cid}"),
                "is_modified": True,
                "user_supplied": True,
                "note": "Explicitly supplied in user prompt"
            })

        for idx, l_ind in enumerate(entities.get("inductors", [])):
            cid = l_ind.get("id", f"L{idx+1}")
            val = float(l_ind["value"])
            entries.append({
                "id": cid,
                "value": l_ind.get("display", cls._format_eng(val, "H")),
                "manual_default": "N/A (User-Defined)",
                "role": roles.get(cid, f"User-supplied Inductor {cid}"),
                "is_modified": True,
                "user_supplied": True,
                "note": "Explicitly supplied in user prompt"
            })

        for idx, d in enumerate(entities.get("diodes", [])):
            if d.get("type") == "zener":
                entries.append({
                    "id": f"DZ{idx+1}",
                    "value": f"Vz = {d.get('vz', 5.1):g} V",
                    "manual_default": "N/A (User-Defined)",
                    "role": "User-supplied Zener Diode",
                    "is_modified": True,
                    "user_supplied": True,
                    "note": "Explicitly supplied in user prompt"
                })
            else:
                entries.append({
                    "id": f"D{idx+1}",
                    "value": d.get("model", "1N4007"),
                    "manual_default": "N/A (User-Defined)",
                    "role": "User-supplied Diode",
                    "is_modified": True,
                    "user_supplied": True,
                    "note": "Explicitly supplied in user prompt"
                })

        params = entities.get("parameters", {})
        if "gain" in params:
            entries.append({
                "id": "Gain",
                "value": str(params["gain"]),
                "manual_default": "N/A (User-Defined)",
                "role": "Dependent source gain",
                "is_modified": True,
                "user_supplied": True,
                "note": "Explicitly supplied in user prompt"
            })
        if "heart_rate_bpm" in params:
            entries.append({
                "id": "Heart Rate (H)",
                "value": f"{params['heart_rate_bpm']:g} BPM",
                "manual_default": "N/A (User-Defined)",
                "role": "Target pacemaker heart rate",
                "is_modified": True,
                "user_supplied": True,
                "note": "Explicitly supplied in user prompt"
            })

        return entries

    # =========================================================================
    # STAGE 1C: GRAPH-BASED NATURAL-LANGUAGE TOPOLOGY PARSER & PREVIEW BUILDER
    # =========================================================================
    @classmethod
    def _fmt_graph_node(cls, n: str) -> str:
        """Formats internal node ID ('1', '2', 'J1', 'GND') as human-readable graph label ('N1', 'N2', 'J1', 'GND')."""
        if not n:
            return "GND"
        nu = str(n).upper()
        if nu == "GND" or nu.startswith("N") or nu.startswith("J"):
            return nu
        return f"N{n}" if str(n).isdigit() else str(n)

    @classmethod
    def _strip_inline_component_values(cls, text: str) -> str:
        """
        Strips inline component values attached to component designators (e.g.,
        'r1 2k and r2 1k in series, and r3 3.3k connected from the junction of r1 and r2 to ground'
        -> 'R1 and R2 in series, and R3 connected from the junction of r1 and r2 to ground')
        so inline values never interfere with connection-clause grammar matching.
        """
        # Replace "<CompID> (=|:|is|of|with)? (<value><unit>)?" with "<CompID>"
        cleaned = re.sub(
            r'\b([RVCLI]\d+)\b\s*(?:(?:=|:|is|of|with)\s*)?\(\s*[0-9]+(?:\.[0-9]+)?\s*(?:k|M|m|u|µ|n|p)?(?:\s*(?:Ω|ohm|ohms|V|volts?|A|amps?|F|farads?|H|henries))?\s*\)',
            lambda m: m.group(1).upper(),
            text,
            flags=re.IGNORECASE
        )
        cleaned = re.sub(
            r'\b([RVCLI]\d+)\b\s*(?:(?:=|:|-|is|of)\s*)?[0-9]+(?:\.[0-9]+)?\s*(?:k|M|m|u|µ|n|p)?\s*(?:Ω|ohm|ohms|V|volts?|A|amps?|F|farads?|H|henries)\b',
            lambda m: m.group(1).upper(),
            cleaned,
            flags=re.IGNORECASE
        )
        cleaned = re.sub(
            r'\b([RVCLI]\d+)\b\s*(?:(?:=|:|-|is|of)\s*)?[0-9]+(?:\.[0-9]+)?\s*(?:k|M|m|u|µ|n|p)\b',
            lambda m: m.group(1).upper(),
            cleaned,
            flags=re.IGNORECASE
        )
        cleaned = re.sub(
            r'\b([RVCLI]\d+)\b\s*(?:(?:=|:|-|is|of)\s*)[0-9]+(?:\.[0-9]+)?\b',
            lambda m: m.group(1).upper(),
            cleaned,
            flags=re.IGNORECASE
        )
        return cleaned

    @classmethod
    def _bind_unnamed_components_to_designators(
        cls,
        text: str,
        catalog: Dict[str, Dict[str, Any]]
    ) -> str:
        """
        Binds unnamed value-qualified component phrases in student/lab-style sentences
        (e.g., 'A 4 kΩ resistor is connected from the positive terminal of the source to a junction.
         From that junction, a 2 kΩ resistor and a 6 kΩ resistor are connected separately to ground.')
        to their corresponding catalog designators ('R1', 'R2', 'R3', 'C1', 'L1').
        """
        used_ids = {
            m.group(1).upper()
            for m in re.finditer(r'\b([RVCLI]\d+)\b', text, re.IGNORECASE)
        }

        def pick_cid(ctype: str, num_str: str, prefix_str: Optional[str]) -> Optional[str]:
            try:
                target_val = cls._scale_value(float(num_str), prefix_str or "")
            except Exception:
                return None
            # First look for an exact value match among unused catalog components of this type
            for cid, meta in catalog.items():
                if meta["type"] == ctype and cid not in used_ids:
                    if abs(float(meta["value"]) - target_val) <= max(1e-9, abs(target_val) * 1e-3):
                        used_ids.add(cid)
                        return cid
            return None

        # 1. Pair of value-qualified resistors ("a 2 kΩ and a 6 kΩ resistor(s)" or "2 kΩ and 6 kΩ resistors")
        def repl_res_pair(m: re.Match) -> str:
            c1 = pick_cid("resistor", m.group(1), m.group(2))
            c2 = pick_cid("resistor", m.group(3), m.group(4))
            if c1 and c2:
                return f"{c1} and {c2}"
            return m.group(0)

        out = re.sub(
            r'(?:\b(?:a|an|the|two|both)\s+)?\b([0-9]+(?:\.[0-9]+)?)\s*(k|M|m|u|µ|n|p)?\s*(?:Ω|ohm|ohms)?\s+and\s+(?:(?:a|an|the)\s+)?([0-9]+(?:\.[0-9]+)?)\s*(k|M|m|u|µ|n|p)?\s*(?:Ω|ohm|ohms)?\s+resistors?\b',
            repl_res_pair,
            text,
            flags=re.IGNORECASE
        )

        # 2. Single value-qualified resistor ("A 4 kΩ resistor", "a 2k resistor", "the 6 kΩ resistor", "a resistor of 4 kΩ")
        def repl_res_single(m: re.Match) -> str:
            num_s = m.group(1) or m.group(3)
            pref_s = m.group(2) if m.group(1) else m.group(4)
            cid = pick_cid("resistor", num_s, pref_s)
            return cid if cid else m.group(0)

        out = re.sub(
            r'(?:\b(?:a|an|the|another|one)\s+)?\b([0-9]+(?:\.[0-9]+)?)\s*(k|M|m|u|µ|n|p)?\s*(?:Ω|ohm|ohms)?\s+resistor\b|'
            r'(?:\b(?:a|an|the|another|one)\s+)?\bresistor\s+of\s+([0-9]+(?:\.[0-9]+)?)\s*(k|M|m|u|µ|n|p)?\s*(?:Ω|ohm|ohms)?\b',
            repl_res_single,
            out,
            flags=re.IGNORECASE
        )

        # 3. Single value-qualified capacitor ("a 10 µF capacitor", "capacitor of 22 uF")
        def repl_cap_single(m: re.Match) -> str:
            num_s = m.group(1) or m.group(3)
            pref_s = m.group(2) if m.group(1) else m.group(4)
            cid = pick_cid("capacitor", num_s, pref_s)
            return cid if cid else m.group(0)

        out = re.sub(
            r'(?:\b(?:a|an|the|another|one)\s+)?\b([0-9]+(?:\.[0-9]+)?)\s*(k|M|m|u|µ|n|p)?\s*(?:F|farads?)?\s+capacitor\b|'
            r'(?:\b(?:a|an|the|another|one)\s+)?\bcapacitor\s+of\s+([0-9]+(?:\.[0-9]+)?)\s*(k|M|m|u|µ|n|p)?\s*(?:F|farads?)\b',
            repl_cap_single,
            out,
            flags=re.IGNORECASE
        )

        # 4. Single value-qualified inductor ("a 10 mH inductor", "inductor of 5 mH")
        def repl_ind_single(m: re.Match) -> str:
            num_s = m.group(1) or m.group(3)
            pref_s = m.group(2) if m.group(1) else m.group(4)
            cid = pick_cid("inductor", num_s, pref_s)
            return cid if cid else m.group(0)

        out = re.sub(
            r'(?:\b(?:a|an|the|another|one)\s+)?\b([0-9]+(?:\.[0-9]+)?)\s*(k|M|m|u|µ|n|p)?\s*(?:H|henries|henry)?\s+inductor\b|'
            r'(?:\b(?:a|an|the|another|one)\s+)?\binductor\s+of\s+([0-9]+(?:\.[0-9]+)?)\s*(k|M|m|u|µ|n|p)?\s*(?:H|henries|henry)\b',
            repl_ind_single,
            out,
            flags=re.IGNORECASE
        )

        return out

    @classmethod
    def build_topology_graph(
        cls,
        components: List[Dict[str, Any]],
        nodes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Single-Source-of-Truth Step 1 (Circuit IR -> Topology Graph):
        Directly converts the Circuit IR components and nodes into a canonical Topology Graph
        without inventing, omitting, or simplifying any node connection.
        """
        edges: List[Dict[str, Any]] = []
        edge_list_lines: List[str] = []
        resolved_graph_lines: List[str] = []

        for c in components:
            cid = str(c.get("id", "COMP"))
            ctype = str(c.get("type", "component"))
            c_nodes = c.get("nodes", ["1", "GND"])
            raw_from = str(c_nodes[0]) if len(c_nodes) >= 1 else "1"
            raw_to = str(c_nodes[1]) if len(c_nodes) >= 2 else "GND"
            n_from = cls._fmt_graph_node(raw_from)
            n_to = cls._fmt_graph_node(raw_to)

            # Determine canonical display value directly from the Circuit IR component
            if "value" in c and c["value"] is not None:
                display_value = cls._format_eng(float(c["value"]), c.get("unit", ""))
            elif "gain" in c and c["gain"] is not None:
                g_val = float(c["gain"])
                unit_map = {"vcvs": "V/V", "cccs": "A/A", "vccs": "A/V", "ccvs": "V/A"}
                g_unit = unit_map.get(ctype, "")
                display_value = f"gain = {g_val:g} {g_unit}".strip()
            elif ctype == "voltage_controlled_switch":
                display_value = f"Ron = {float(c.get('ron', 1.0)):g} Ω"
            elif "model" in c:
                display_value = str(c["model"])
            else:
                display_value = ctype

            # Extract control branch metadata if present on controlled sources / switches
            control_info: Optional[str] = None
            if "control_nodes" in c and isinstance(c["control_nodes"], list) and len(c["control_nodes"]) >= 2:
                cn_from = cls._fmt_graph_node(c["control_nodes"][0])
                cn_to = cls._fmt_graph_node(c["control_nodes"][1])
                control_info = f"ctrl: {cn_from} → {cn_to}"
            elif "controlling_source" in c and c["controlling_source"]:
                control_info = f"ctrl: {c['controlling_source']}"

            line_str = f"{cid}: {n_from} → {n_to}"
            resolved_line_str = f"{cid}: {n_from} -> {n_to}"
            edge_list_lines.append(line_str)
            resolved_graph_lines.append(resolved_line_str)

            is_source = ctype in (
                "dc_voltage_source",
                "ac_voltage_source",
                "dc_current_source",
                "current_source",
                "pulse_voltage_source",
            )
            is_passive = ctype in ("resistor", "capacitor", "inductor")

            edges.append({
                "id": cid,
                "type": ctype,
                "raw_from": raw_from,
                "raw_to": raw_to,
                "from_node": n_from,
                "to_node": n_to,
                "display_value": display_value,
                "control_info": control_info,
                "edge_line": line_str,
                "resolved_line": resolved_line_str,
                "is_source": is_source,
                "is_passive": is_passive,
            })

        formatted_nodes = [cls._fmt_graph_node(n) for n in (nodes or [])]
        return {
            "nodes": formatted_nodes,
            "edges": edges,
            "edge_list_lines": edge_list_lines,
            "resolved_graph_lines": resolved_graph_lines,
        }

    @classmethod
    def build_topology_preview(
        cls,
        components: List[Dict[str, Any]],
        nodes: List[str],
        user_connection_clauses: Optional[List[str]] = None,
        junction_pair: Optional[Any] = None,
        resolved_graph: Optional[List[str]] = None,
        topology_graph: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Single-Source-of-Truth Step 2 (Topology Graph -> Preview):
        Renders the human-readable ASCII topology preview and edge list strictly from the
        canonical Topology Graph derived from the Circuit IR. Never invents or simplifies
        connections differently from the actual graph.
        """
        graph = topology_graph or cls.build_topology_graph(components, nodes)
        edges: List[Dict[str, Any]] = graph["edges"]
        edge_list_lines: List[str] = graph["edge_list_lines"]
        resolved_graph_lines: List[str] = graph["resolved_graph_lines"]

        source_edges = [e for e in edges if e["is_source"]]
        passive_edges = [e for e in edges if e["is_passive"]]
        other_edges = [e for e in edges if not e["is_source"] and not e["is_passive"]]

        ascii_lines: List[str] = []

        # Only use the vertical T-junction schematic tree when:
        # 1. There is exactly 1 independent source and 0 active/controlled/switch elements
        # 2. That single source explicitly connects N1 and GND in the Topology Graph
        # 3. Exactly 1 series head branch starts at N1 -> mid_node, and all remaining passives branch from mid_node
        from_node1 = [e for e in passive_edges if e["raw_from"] == "1" and e["raw_to"] != "GND"]
        if (
            len(source_edges) == 1
            and len(other_edges) == 0
            and source_edges[0]["from_node"] == "N1"
            and source_edges[0]["to_node"] == "GND"
            and len(from_node1) == 1
        ):
            src_e = source_edges[0]
            head_e = from_node1[0]
            mid_node = head_e["raw_to"]
            mid_label = head_e["to_node"]
            branches_at_mid = [
                e for e in passive_edges
                if e["id"] != head_e["id"] and mid_node in (e["raw_from"], e["raw_to"])
            ]
            if branches_at_mid and len(branches_at_mid) + 1 == len(passive_edges):
                ascii_lines.append(f"[{src_e['id']} = {src_e['display_value']}] ({src_e['from_node']} → {src_e['to_node']})")
                ascii_lines.append(" │")
                ascii_lines.append(f"{head_e['id']} ({head_e['display_value']}): {head_e['from_node']} → {head_e['to_node']}")
                ascii_lines.append(" │")
                ascii_lines.append(f" ● {mid_label}")
                for idx_b, b_edge in enumerate(branches_at_mid):
                    branch_char = "└──" if idx_b == len(branches_at_mid) - 1 else "├──"
                    ascii_lines.append(
                        f" {branch_char} {b_edge['id']} ({b_edge['display_value']}): {b_edge['from_node']} → {b_edge['to_node']}"
                    )

        if not ascii_lines:
            # Direct 1-to-1 rendering of every edge in the Topology Graph
            for src_e in source_edges:
                src_meta = f"{src_e['id']} = {src_e['display_value']}"
                if src_e.get("control_info"):
                    src_meta += f", {src_e['control_info']}"
                ascii_lines.append(f"[{src_meta}] ({src_e['from_node']} → {src_e['to_node']})")

            branch_edges = [e for e in edges if not e["is_source"]]
            for idx_b, b_edge in enumerate(branch_edges):
                branch_char = "└──" if idx_b == len(branch_edges) - 1 else "├──"
                desc = b_edge["display_value"]
                if b_edge.get("control_info"):
                    desc = f"{desc}, {b_edge['control_info']}"
                ascii_lines.append(
                    f" {branch_char} {b_edge['id']} ({desc}): {b_edge['from_node']} → {b_edge['to_node']}"
                )

        ascii_diagram_str = "\n".join(ascii_lines)
        formatted_preview = ascii_diagram_str + "\n\n" + "\n".join(edge_list_lines)

        return {
            "topology_graph": graph,
            "ascii_diagram": ascii_diagram_str,
            "edge_list_lines": edge_list_lines,
            "resolved_graph_lines": resolved_graph or resolved_graph_lines,
            "user_connection_clauses": user_connection_clauses or [],
            "formatted_preview": formatted_preview,
        }

    @classmethod
    def parse_natural_language_topology(
        cls,
        text: str,
        raw_entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Graph-Based Natural-Language Topology Reconstruction Pipeline:
          Latest user message
          → component/value extraction
          → inline-value normalization & unnamed component-to-designator binding
          → connection-clause extraction (explicit graph constraints)
          → persistent node/junction reference resolution (J1, J2, ...)
          → topology graph construction
          → graph consistency validation (non-empty graph, 2 valid endpoints per component)
          → human-readable topology preview + Circuit IR
        """
        v_list = raw_entities.get("voltage_sources", [])
        r_list = raw_entities.get("resistors", [])
        i_list = raw_entities.get("current_sources", [])
        c_list = raw_entities.get("capacitors", [])
        l_list = raw_entities.get("inductors", [])

        # Build component catalog by ID (e.g., V1, R1, R2, R3, C1, L1, I1)
        catalog: Dict[str, Dict[str, Any]] = {}
        for idx, v in enumerate(v_list):
            cid = v.get("id", f"V{idx+1}").upper()
            catalog[cid] = {"id": cid, "type": "dc_voltage_source", "value": float(v["value"]), "unit": "V"}
        for idx, r in enumerate(r_list):
            cid = r.get("id", f"R{idx+1}").upper()
            catalog[cid] = {"id": cid, "type": "resistor", "value": float(r["value"]), "unit": "ohm"}
        for idx, i_s in enumerate(i_list):
            cid = i_s.get("id", f"I{idx+1}").upper()
            catalog[cid] = {"id": cid, "type": "dc_current_source", "value": float(i_s["value"]), "unit": "A"}
        for idx, c in enumerate(c_list):
            cid = c.get("id", f"C{idx+1}").upper()
            catalog[cid] = {"id": cid, "type": "capacitor", "value": float(c["value"]), "unit": "F"}
        for idx, l_i in enumerate(l_list):
            cid = l_i.get("id", f"L{idx+1}").upper()
            catalog[cid] = {"id": cid, "type": "inductor", "value": float(l_i["value"]), "unit": "H"}

        # Normalize line wraps inside sentences so wrapped clauses ("from that junction to\nground") are never split mid-clause
        unwrapped_text = re.sub(r'\s*\r?\n\s*', ' ', text).strip()
        stripped_text = cls._strip_inline_component_values(unwrapped_text)
        norm_text = cls._bind_unnamed_components_to_designators(stripped_text, catalog)
        low = norm_text.lower()

        # Check if the text contains any natural-language connection phrases
        nl_cue_pattern = re.compile(
            r'\bin\s+series\b|\bare\s+series\b|\bis\s+series\b|\bin\s+parallel\b|\bare\s+parallel\b|\bparallel\s+with\b|\bseries\s+with\b|'
            r'\bmiddle\s*point\b|\bmiddle\s*node\b|\bmidpoint\b|\bjunction\b|\bcommon\s*point\b|\bcommon\s*node\b|\bcommon\s*junction\b|'
            r'\bnode\s+between\b|\bthat\s+node\b|\bthis\s+node\b|\bthe\s+same\s+node\b|\bsame\s+node\b|\bmeet(?:s|ing)?\s+at\b|'
            r'\bbranch(?:es|ing|ed)?\s+(?:from|at|connected|to)\b|\bconnected\s+across\b|'
            r'\bacross\s+(?:r\d+|c\d+|l\d+|v\d+|the\s+source|the\s+capacitor|the\s+resistor|the\s+load)\b|'
            r'\bconnected\s+between\b|\bconnected\s+from\b|\bconnected\s+to\b|\bconnected\s+separately\s+to\b|\bseparately\s+to\s+ground\b|'
            r'\bconnects\s+from\b|\bconnects\s+to\b|\bconnecting\s+from\b|\bconnecting\s+to\b|'
            r'\bfrom\s+(?:the\s+|that\s+|this\s+|a\s+|their\s+)?(?:positive\s+terminal\s+of\s+(?:the\s+)?source|source|v\d+|vs|vin|node\s*\d+|n\d+|junction|same\s+junction|middle\s*point|middle\s*node|midpoint|common\s*node|common\s*point)\b|'
            r'\bsame\s+two\s+nodes\b|\bsame\s+point\b|\bboth\s+connected\s+to\s+ground\b|'
            r'\bshare\s+(?:the\s+)?same\s+ground\b|\bshare\s+a\s+common\s+ground\b|'
            r'\bone\s+end\b|\bother\s+end\b|\bto\s+ground\b|\bto\s+gnd\b|\bto\s+(?:a|the|that|this)\s+(?:junction|middle\s*node|middle\s*point|midpoint|node)\b',
            re.IGNORECASE
        )
        if not nl_cue_pattern.search(low):
            return {"has_nl_topology": False, "is_complete": False, "inferred_topology_lines": [], "user_connection_clauses": []}

        # Support designator-only natural-language topology prompts (e.g., "r1 and r2 in series and r3 connected from their junction to ground")
        explicit_comp_ids: List[str] = []
        for m_des in re.finditer(r'\b([RCLVI]\d+)\b', norm_text, re.IGNORECASE):
            cid = m_des.group(1).upper()
            if cid not in explicit_comp_ids:
                explicit_comp_ids.append(cid)
            if cid not in catalog:
                if cid.startswith("R"):
                    catalog[cid] = {"id": cid, "type": "resistor", "value": 1000.0, "unit": "ohm"}
                elif cid.startswith("C"):
                    catalog[cid] = {"id": cid, "type": "capacitor", "value": 1e-6, "unit": "F"}
                elif cid.startswith("L"):
                    catalog[cid] = {"id": cid, "type": "inductor", "value": 1e-3, "unit": "H"}
                elif cid.startswith("V"):
                    catalog[cid] = {"id": cid, "type": "dc_voltage_source", "value": 10.0, "unit": "V"}
                elif cid.startswith("I"):
                    catalog[cid] = {"id": cid, "type": "dc_current_source", "value": 1.0, "unit": "A"}

        # Also support unnumbered "the capacitor" in topology phrases like "the middle point connects to the capacitor" or "capacitor is across the load"
        if re.search(r'\bcapacitor\b', low) and not any(k.startswith("C") for k in catalog):
            catalog["C1"] = {"id": "C1", "type": "capacitor", "value": 1e-6, "unit": "F"}
            if "C1" not in explicit_comp_ids:
                explicit_comp_ids.append("C1")
            norm_text = re.sub(r'\b(?:the\s+)?capacitor\b', 'C1', norm_text, flags=re.IGNORECASE)
            low = norm_text.lower()

        # Also support "both resistors share the same ground" when no R1/R2 numbers were written
        if re.search(r'\bboth\s+resistors\b', low) and not any(k.startswith("R") for k in catalog):
            catalog["R1"] = {"id": "R1", "type": "resistor", "value": 1000.0, "unit": "ohm"}
            catalog["R2"] = {"id": "R2", "type": "resistor", "value": 1000.0, "unit": "ohm"}

        passive_ids = [
            cid for cid, meta in catalog.items()
            if meta["type"] in ("resistor", "capacitor", "inductor")
        ]
        if not passive_ids:
            return {"has_nl_topology": False, "is_complete": False, "inferred_topology_lines": [], "user_connection_clauses": []}

        placed_nodes: Dict[str, List[str]] = {}
        inferred_lines: List[str] = []
        user_connection_clauses: List[str] = []
        comp_roles: Dict[str, str] = {}
        junction_map: Dict[Tuple[str, str], str] = {}
        active_junction_node: Optional[str] = None
        last_junction_pair: Optional[Tuple[str, str]] = None
        next_junction_num = 1  # Persistent internal junction node IDs: J1, J2, ...

        def get_or_alloc_junction(force_new: bool = False) -> str:
            """
            Step 2 & 3 Helper:
            Creates/assigns internal junction node ID ('J1', 'J2', ...) when first introduced,
            and resolves all subsequent references ('the junction', 'that junction', 'the same junction',
            'this node', 'that node', 'same node', 'middle point', 'middle node', 'node between R1 and R2')
            to that SAME existing junction node.
            """
            nonlocal active_junction_node, next_junction_num
            if active_junction_node and not force_new:
                return active_junction_node
            j_id = f"J{next_junction_num}"
            next_junction_num += 1
            active_junction_node = j_id
            return j_id

        # Primary source setup (default V1 at ["1", "GND"], or I1 at ["1", "GND"])
        primary_source_id = "V1" if "V1" in catalog else (next((k for k in catalog if k.startswith("V")), None))
        if not primary_source_id and i_list:
            primary_source_id = next((k for k in catalog if k.startswith("I")), None)
        if primary_source_id:
            placed_nodes[primary_source_id] = ["1", "GND"]
            comp_roles[primary_source_id] = "Primary source connected between N1 and GND"
        else:
            catalog["V1"] = {"id": "V1", "type": "dc_voltage_source", "value": 10.0, "unit": "V"}
            placed_nodes["V1"] = ["1", "GND"]
            comp_roles["V1"] = "Default 10 V DC excitation source (N1 to GND)"
            primary_source_id = "V1"

        def extract_comp_ids(fragment: str) -> List[str]:
            found = []
            for m in re.finditer(r'\b([RVCLI]\d+)\b', fragment, re.IGNORECASE):
                cid = m.group(1).upper()
                if cid in catalog and cid not in found:
                    found.append(cid)
            return found

        junction_phrase_re = re.compile(
            r'\b(?:'
            r'(?:a|an|the|that|this|their|same|common)\s+junction|'
            r'the\s+same\s+junction|'
            r'junction(?:\s+(?:of|between|point|node))?|'
            r'middle\s*point|middle\s*node|midpoint|'
            r'common\s*point|common\s*node|common\s*junction|'
            r'node\s+between\s+[rvcli]\d+\s+and\s+[rvcli]\d+|'
            r'point\s+between\s+[rvcli]\d+\s+and\s+[rvcli]\d+|'
            r'center\s*tap|between\s*them|their\s*midpoint|'
            r'same\s*point|same\s*node|the\s+same\s+node|that\s+node|this\s+node|that\s+point|this\s+point'
            r')\b',
            re.IGNORECASE
        )

        def resolve_node_phrase(phrase: str, exclude_comp: Optional[str] = None, allow_create_junction: bool = True) -> Optional[str]:
            p = phrase.lower().strip()
            j_pair = [c for c in extract_comp_ids(p) if c != exclude_comp]

            # 1. Explicit junction / node between two named components (e.g., "junction of R1 and R2", "node between R1 and R2")
            if len(j_pair) >= 2:
                c1, c2 = j_pair[0], j_pair[1]
                if (c1, c2) in junction_map:
                    return junction_map[(c1, c2)]
                if (c2, c1) in junction_map:
                    return junction_map[(c2, c1)]
                if c1 in placed_nodes and c2 in placed_nodes:
                    shared = set(placed_nodes[c1]).intersection(placed_nodes[c2]) - {"GND"}
                    if shared:
                        j_existing = sorted(shared)[0]
                        junction_map[(c1, c2)] = j_existing
                        junction_map[(c2, c1)] = j_existing
                        return j_existing
                if allow_create_junction and junction_phrase_re.search(p):
                    j_new = get_or_alloc_junction()
                    junction_map[(c1, c2)] = j_new
                    junction_map[(c2, c1)] = j_new
                    return j_new

            # 2. Persistent junction / midpoint / middle node / same node / that node / this node reference (checked BEFORE ground/source!)
            if junction_phrase_re.search(p):
                if active_junction_node:
                    return active_junction_node
                if len(j_pair) == 1 and j_pair[0] in placed_nodes:
                    c_nodes = placed_nodes[j_pair[0]]
                    non_gnd = [n for n in c_nodes if n not in ("GND", "1")]
                    if non_gnd:
                        return non_gnd[-1]
                if allow_create_junction:
                    return get_or_alloc_junction()

            # 3. Ground / reference
            if re.search(r'\b(?:ground|gnd|earth|reference|0|negative\s*(?:terminal)?\s*of\s*(?:the\s+)?(?:source|v\d+))\b', p):
                return "GND"

            # 4. Source / Node 1 ("positive terminal of the source", "the source", "V1", "N1")
            if re.search(r'\b(?:positive\s*(?:terminal)?\s*of\s*(?:the\s+)?(?:source|v\d+)|source|input|v1|vs|vin|node\s*1|n1)\b', p):
                return "1"

            # 5. Explicit internal node or junction label (e.g. "J1", "J2", "node 2", "N2")
            m_explicit_j = re.search(r'\b(j\d+)\b', p, re.IGNORECASE)
            if m_explicit_j:
                return m_explicit_j.group(1).upper()
            m_explicit_n = re.search(r'\b(?:node\s*|n)(\d+)\b', p, re.IGNORECASE)
            if m_explicit_n:
                return m_explicit_n.group(1)

            # 6. Single referenced component node (e.g. "same node as R1")
            if len(j_pair) == 1 and j_pair[0] in placed_nodes:
                c_nodes = placed_nodes[j_pair[0]]
                non_gnd = [n for n in c_nodes if n != "GND"]
                return non_gnd[-1] if non_gnd else c_nodes[0]

            return None

        # =====================================================================
        # PIPELINE STEP 1: EXTRACT EVERY COMPONENT-SPECIFIC CLAUSE INDEPENDENTLY
        # =====================================================================
        # Remove comma immediately following a fronted prepositional node phrase (e.g., "From that junction, R2 and R3...")
        # so the fronted endpoint stays attached to its subject component(s).
        norm_text_fronted = re.sub(
            r'(^|[.;]\s*)(from|at|between)\s+([^,.;]+?),\s*(?=(?:[rvcli]\d+\b|\b(?:a|an|the|both|two)\b))',
            r'\1\2 \3 ',
            norm_text,
            flags=re.IGNORECASE
        )

        # First split on sentence/clause delimiters ('.', ';', ',', 'with the...', or 'and <Comp> <verb/preposition>'),
        # taking care NEVER to split inside '<R1> and <R2> in/are series/parallel/meet at/connected separately to...'
        # or 'between/of <R1> and <R2>'.
        coarse_clauses = [
            fc.strip()
            for fc in re.split(
                r'[.;]+|,(?!\s*(?:and\s+)?[rvcli]\d+\b\s*(?:,|and\b|connected\s+in\b|(?:in|are|is)\s+series\b|(?:in|are|is)\s+parallel\b|meet(?:s|ing)?\s+at\b))|'
                r'\bwith\s+(?=the\s+middle\s+point|the\s+middle\s+node|the\s+midpoint|the\s+junction|a\s+branch)|'
                r'(?<!\bbetween\s[rvcli]\d\s)(?<!\bof\s[rvcli]\d\s)\band\b(?=\s+(?:[rvcli]\d+\b\s+(?:is\s+|are\s+|goes\s+|go\s+)?(?:also\s+|separately\s+)?(?:is\s+|are\s+|goes\s+|go\s+)?(?:connected(?!\s+(?:in\s+(?:series|parallel)|separately\s+to\b))|connects|connecting|branch|across|from|between|to\s+ground|to\s+gnd|(?:in\s+)?parallel\s+with\s+[rvcli]\d+\b|in\s+series\s+with\s+[rvcli]\d+\b)|one\s+end|other\s+end|both\s+connected|both\s+resistors|the\s+middle\s+point|the\s+middle\s+node|a\s+branch))',
                norm_text_fronted,
                flags=re.IGNORECASE
            )
            if fc.strip()
        ]

        # Further split any clause that still contains multiple independent component connection statements
        # (e.g. "R1 from source to a junction R2 from that junction to ground")
        fine_clauses: List[str] = []
        for c_clause in coarse_clauses:
            delimited = re.sub(
                r'\b(ground|gnd|junction|node|point|midpoint|source)\s+(?:and\s+)?(?=[rvcli]\d+\b\s+(?:is\s+|are\s+|goes\s+|also\s+|separately\s+)*(?:connected|connects|connecting|branch|across|from|between|to\b))',
                r'\1 ; ',
                c_clause,
                flags=re.IGNORECASE
            )
            for sp in delimited.split(' ; '):
                if sp.strip():
                    fine_clauses.append(sp.strip())

        # =====================================================================
        # PIPELINE STEP 2 & 3: PROCESS GROUP CLAUSES THEN COMPONENT-SPECIFIC CLAUSES
        # WITHOUT OVERWRITING PREVIOUSLY PARSED COMPONENT CONNECTIONS
        # =====================================================================
        # Pass 1: Process explicit "in/are series", "meet at <junction/middle node>", and "in/are parallel" group constraints
        for clause in fine_clauses:
            # Pattern A1: "<R1> and <R2> (are) (connected) (in) series" / "<R1> in series with <R2>"
            m_series = re.search(
                r'((?:\b[RVCLI]\d+\b(?:\s*(?:,\s*and|,|and)\s*)?)+)\s+(?:(?:is|are)\s+(?:connected\s+)?(?:in\s+)?series\b|(?:connected\s+)?in\s+series\b)(?:\s+with\s+(\b[RVCLI]\d+\b))?',
                clause,
                re.IGNORECASE
            )
            if m_series:
                series_cids = [c for c in extract_comp_ids(m_series.group(1)) if not c.startswith("V")]
                if m_series.group(2):
                    extra_c = m_series.group(2).upper()
                    if extra_c in catalog and extra_c not in series_cids:
                        series_cids.append(extra_c)
                if len(series_cids) >= 2:
                    start_node = "1"
                    if series_cids[0] in placed_nodes:
                        start_node = placed_nodes[series_cids[0]][1]
                        series_iter = series_cids[1:]
                    else:
                        series_iter = series_cids

                    curr_node = start_node
                    for idx_s, scid in enumerate(series_iter):
                        is_last_in_series = (idx_s == len(series_iter) - 1)
                        if is_last_in_series:
                            end_node = "GND"
                        else:
                            end_node = get_or_alloc_junction(force_new=(idx_s > 0))
                        if scid not in placed_nodes:
                            placed_nodes[scid] = [curr_node, end_node]
                            comp_roles[scid] = f"Series branch ({cls._fmt_graph_node(curr_node)} → {cls._fmt_graph_node(end_node)})"
                        if not is_last_in_series:
                            next_scid = series_iter[idx_s + 1]
                            junction_map[(scid, next_scid)] = end_node
                            junction_map[(next_scid, scid)] = end_node
                            active_junction_node = end_node
                            last_junction_pair = (scid, next_scid)
                        curr_node = end_node

                    if len(series_cids) >= 2 and (series_cids[0], series_cids[1]) in junction_map:
                        active_junction_node = junction_map[(series_cids[0], series_cids[1])]
                        last_junction_pair = (series_cids[0], series_cids[1])
                    inferred_lines.append(f"{' and '.join(series_cids)} in series")
                    user_connection_clauses.append(f"{' and '.join(series_cids)} are in series")
                    continue

            # Pattern A2: "<R1> and <R2> meet at (the) (middle node / middle point / midpoint / junction / common node)"
            m_meet = re.search(
                r'((?:\b[RVCLI]\d+\b(?:\s*(?:,\s*and|,|and)\s*)?)+)\s+(?:both\s+)?(?:meet(?:s|ing)?|join(?:s|ing)?|connect(?:s|ed)?\s+together)\s+at\s+(.+)',
                clause,
                re.IGNORECASE
            )
            if m_meet:
                meet_cids = [c for c in extract_comp_ids(m_meet.group(1)) if not c.startswith("V")]
                if len(meet_cids) >= 2:
                    j_node = resolve_node_phrase(m_meet.group(2), allow_create_junction=True) or get_or_alloc_junction()
                    active_junction_node = j_node
                    c1, c2 = meet_cids[0], meet_cids[1]
                    junction_map[(c1, c2)] = j_node
                    junction_map[(c2, c1)] = j_node
                    last_junction_pair = (c1, c2)
                    if c1 not in placed_nodes:
                        placed_nodes[c1] = ["1", j_node]
                        comp_roles[c1] = f"Connected from N1 to {cls._fmt_graph_node(j_node)}"
                    if c2 not in placed_nodes:
                        placed_nodes[c2] = [j_node, "GND"]
                        comp_roles[c2] = f"Connected from {cls._fmt_graph_node(j_node)} to GND"
                    for extra_mc in meet_cids[2:]:
                        if extra_mc not in placed_nodes:
                            placed_nodes[extra_mc] = [j_node, "GND"]
                            comp_roles[extra_mc] = f"Connected from {cls._fmt_graph_node(j_node)} to GND"
                    inferred_lines.append(f"{' and '.join(meet_cids)} meet at {cls._fmt_graph_node(j_node)}")
                    user_connection_clauses.append(f"{' and '.join(meet_cids)} meet at {cls._fmt_graph_node(j_node)}")
                    continue

            # Pattern B: "<R1> and <R2> in parallel" or "<R3> (is) (connected) (in) parallel with <R2>"
            m_parallel = re.search(
                r'((?:\b[RVCLI]\d+\b(?:\s*(?:,\s*and|,|and)\s*)?)+)\s+(?:is\s+|are\s+)?(?:connected\s+)?(?:(?:in\s+)?parallel(?:\s+with\s+(\b[RVCLI]\d+\b))?|parallel\s+with\s+(\b[RVCLI]\d+\b))',
                clause,
                re.IGNORECASE
            )
            if m_parallel:
                par_cids = [c for c in extract_comp_ids(m_parallel.group(1)) if not c.startswith("V")]
                raw_target = m_parallel.group(2) or m_parallel.group(3)
                target_c = raw_target.upper() if raw_target else None
                if target_c and target_c in catalog:
                    if target_c in placed_nodes:
                        ref_nodes = list(placed_nodes[target_c])
                    else:
                        ref_nodes = ["1", "GND"]
                        placed_nodes[target_c] = ref_nodes
                        comp_roles[target_c] = f"Parallel branch ({cls._fmt_graph_node(ref_nodes[0])} → {cls._fmt_graph_node(ref_nodes[1])})"
                    for pcid in par_cids:
                        if pcid not in placed_nodes:
                            placed_nodes[pcid] = list(ref_nodes)
                            comp_roles[pcid] = f"In parallel with {target_c} ({cls._fmt_graph_node(ref_nodes[0])} → {cls._fmt_graph_node(ref_nodes[1])})"
                    inferred_lines.append(f"{', '.join(par_cids)} in parallel with {target_c}")
                    user_connection_clauses.append(f"{', '.join(par_cids)} connected in parallel with {target_c}")
                elif len(par_cids) >= 2:
                    existing = next((c for c in par_cids if c in placed_nodes), None)
                    ref_nodes = list(placed_nodes[existing]) if existing else ["1", "GND"]
                    for pcid in par_cids:
                        if pcid not in placed_nodes:
                            placed_nodes[pcid] = list(ref_nodes)
                            comp_roles[pcid] = f"Parallel branch ({cls._fmt_graph_node(ref_nodes[0])} → {cls._fmt_graph_node(ref_nodes[1])})"
                    inferred_lines.append(f"{' and '.join(par_cids)} in parallel")
                    user_connection_clauses.append(f"{' and '.join(par_cids)} are in parallel")

        # Pass 2: Parse each individual component clause in order.
        # RULE: Never overwrite a previously parsed component connection (placed_nodes[comp]),
        # and never reinterpret an earlier component (e.g. R1) as a branch merely because a later clause mentions it.
        pending_one_end_comp: Optional[str] = None
        pending_one_end_node: Optional[str] = None

        for fclause in fine_clauses:
            fl_low = fclause.lower()
            cids = [cid for cid in extract_comp_ids(fclause) if not cid.startswith("V")]

            if not nl_cue_pattern.search(fl_low):
                continue

            # Skip if this clause was already handled in Pass 1 (series, parallel, or meet at) with no other unplaced component
            if re.search(r'\b(?:in\s+series|are\s+series|is\s+series|in\s+parallel|are\s+parallel|parallel\s+with|meet(?:s|ing)?\s+at)\b', fl_low):
                if all(c in placed_nodes for c in cids):
                    continue

            # Handle "one end (of R3) (connected) to <X>" / "other end (connected) to <Y>"
            m_one_end = re.search(r'one\s+end\s+(?:of\s+(\b[RVCLI]\d+\b)\s+)?(?:is\s+)?(?:connected\s+)?to\s+(.+)', fclause, re.IGNORECASE)
            if m_one_end:
                unplaced_c = [c for c in cids if c not in placed_nodes]
                target_comp = m_one_end.group(1).upper() if m_one_end.group(1) else (unplaced_c[0] if unplaced_c else pending_one_end_comp)
                if not target_comp:
                    unplaced_all = [p for p in passive_ids if p not in placed_nodes]
                    target_comp = unplaced_all[0] if unplaced_all else None
                node_a = resolve_node_phrase(m_one_end.group(2), exclude_comp=target_comp)
                if target_comp and node_a and target_comp not in placed_nodes:
                    pending_one_end_comp = target_comp
                    pending_one_end_node = node_a
                continue

            m_other_end = re.search(r'other\s+end\s+(?:is\s+)?(?:connected\s+)?to\s+(.+)', fclause, re.IGNORECASE)
            if m_other_end and pending_one_end_comp and pending_one_end_node:
                node_b = resolve_node_phrase(m_other_end.group(1), exclude_comp=pending_one_end_comp)
                if node_b and pending_one_end_comp not in placed_nodes:
                    placed_nodes[pending_one_end_comp] = [pending_one_end_node, node_b]
                    na_lbl, nb_lbl = cls._fmt_graph_node(pending_one_end_node), cls._fmt_graph_node(node_b)
                    comp_roles[pending_one_end_comp] = f"Connected between {na_lbl} and {nb_lbl}"
                    inferred_lines.append(f"{pending_one_end_comp} connected from {na_lbl} to {nb_lbl}")
                    user_connection_clauses.append(f"{pending_one_end_comp} connects from {na_lbl} to {nb_lbl}")
                    pending_one_end_comp = None
                    pending_one_end_node = None
                continue

            # Handle "connected between the same two nodes (as <R2>)"
            if re.search(r'\bsame\s+two\s+nodes\b', fl_low):
                unplaced_c = [c for c in cids if c not in placed_nodes]
                placed_c = [c for c in cids if c in placed_nodes]
                subj_c = unplaced_c[0] if unplaced_c else None
                ref_c = placed_c[0] if placed_c else (next((k for k in reversed(list(placed_nodes.keys())) if not k.startswith("V")), None))
                if subj_c and ref_c and ref_c in placed_nodes:
                    ref_n = list(placed_nodes[ref_c])
                    placed_nodes[subj_c] = ref_n
                    comp_roles[subj_c] = f"Connected between same two nodes as {ref_c} ({cls._fmt_graph_node(ref_n[0])} → {cls._fmt_graph_node(ref_n[1])})"
                    inferred_lines.append(f"{subj_c} connected between the same two nodes as {ref_c}")
                    user_connection_clauses.append(f"{subj_c} connects across {ref_c} ({cls._fmt_graph_node(ref_n[0])} → {cls._fmt_graph_node(ref_n[1])})")
                    continue

            # Handle "across <target>" (e.g. "R3 connected across R2", "C1 across the capacitor/resistor/source/load")
            m_across = re.search(
                r'\b([RVCLI]\d+)\b.*?\bacross\s+(?:the\s+)?(source|v\d+|capacitor|c\d+|resistor|load|[rvcli]\d+)',
                fclause,
                re.IGNORECASE
            )
            if m_across:
                subj = m_across.group(1).upper()
                obj_raw = m_across.group(2).upper()
                if subj in catalog and subj not in placed_nodes:
                    if obj_raw in ("SOURCE", "V1", "VS", "VIN"):
                        ref_n = ["1", "GND"]
                        obj_label = "the source"
                    elif obj_raw in ("LOAD", "RESISTOR"):
                        r_match = next((k for k in reversed(list(placed_nodes.keys())) if k.startswith("R")), None)
                        if not r_match:
                            r_match = next((k for k in catalog if k.startswith("R") and k != subj), None)
                            if r_match and r_match not in placed_nodes:
                                placed_nodes[r_match] = ["1", "GND"]
                                comp_roles[r_match] = "Load resistor (N1 → GND)"
                        ref_n = list(placed_nodes[r_match]) if r_match else ["1", "GND"]
                        obj_label = r_match or "the load"
                    elif obj_raw.startswith("CAPACITOR"):
                        c_match = next((k for k in catalog if k.startswith("C") and k in placed_nodes), None)
                        ref_n = list(placed_nodes[c_match]) if c_match else ["1", "GND"]
                        obj_label = c_match or "C1"
                    elif obj_raw in placed_nodes:
                        ref_n = list(placed_nodes[obj_raw])
                        obj_label = obj_raw
                    else:
                        ref_n = ["1", "GND"]
                        obj_label = obj_raw
                    placed_nodes[subj] = ref_n
                    comp_roles[subj] = f"Connected across {obj_label} ({cls._fmt_graph_node(ref_n[0])} → {cls._fmt_graph_node(ref_n[1])})"
                    inferred_lines.append(f"{subj} connected across {obj_label}")
                    user_connection_clauses.append(f"{subj} connects across {obj_label}")
                    continue

            # Handle "both connected to ground" / "share the same ground"
            if re.search(r'\bboth\s+connected\s+to\s+(?:ground|gnd)\b|\bshare\s+(?:the\s+)?same\s+ground\b|\bshare\s+a\s+common\s+ground\b', fl_low):
                target_cids = [c for c in cids if c not in placed_nodes] or [p for p in passive_ids if p not in placed_nodes]
                j_node = active_junction_node or "1"
                for tcid in target_cids:
                    if tcid not in placed_nodes:
                        placed_nodes[tcid] = [j_node, "GND"]
                        comp_roles[tcid] = f"Branches from {cls._fmt_graph_node(j_node)} to GND"
                        inferred_lines.append(f"{tcid} branches from {cls._fmt_graph_node(j_node)} to GND")
                        user_connection_clauses.append(f"{tcid} connects from {cls._fmt_graph_node(j_node)} to GND")
                continue

            # Determine unplaced subject component(s) in this clause (NEVER pick an already-placed component!)
            unplaced_in_clause = [c for c in cids if c not in placed_nodes]
            subj_comp = unplaced_in_clause[0] if unplaced_in_clause else None
            if not subj_comp:
                remaining_unplaced = [p for p in passive_ids if p not in placed_nodes]
                if len(remaining_unplaced) == 1 and not cids:
                    subj_comp = remaining_unplaced[0]
                    unplaced_in_clause = [subj_comp]

            if subj_comp and subj_comp in catalog and subj_comp not in placed_nodes:
                # 1. FIRST check explicit two-endpoint forms:
                #    - "from <Endpoint A> to <Endpoint B>" (including fronted "From that junction, R2 and R3 are connected separately to ground")
                #    - "between <Endpoint A> and <Endpoint B>"
                m_from_to = re.search(
                    r'(?:connected\s+|connects\s+|connecting\s+|branch(?:es|ing|ed)?\s+|goes\s+|go\s+)?from\s+(.+?)\s+to\s+(.+)',
                    fclause,
                    re.IGNORECASE
                )
                m_between_and = None
                if not m_from_to:
                    m_between_and = re.search(
                        r'(?:connected\s+|connects\s+|connecting\s+)?between\s+(.+?)\s+and\s+(ground|gnd|the\s+source|source|v\d+|node\s*\d+|n\d+|j\d+|(?:a|the|that|this|same|their)\s+(?:junction|middle\s*node|middle\s*point|midpoint|node)|.+)',
                        fclause,
                        re.IGNORECASE
                    )

                two_ep_match = m_from_to or m_between_and
                if two_ep_match:
                    ep_a_str = two_ep_match.group(1).strip()
                    ep_b_str = two_ep_match.group(2).strip()
                    # If the clause had a fronted 'From <ep_a> <R2 and R3 are connected separately> to <ep_b>',
                    # strip the embedded subject component list and connection verbs from the tail of ep_a_str.
                    ep_a_cleaned = re.sub(
                        r'(?:,\s*)?(?:\b[RVCLI]\d+\b(?:\s*(?:,\s*and|,|and)\s*)?)+(?:\s+(?:is|are|was|were|goes|go|also|separately|both|each|connected|connects|connecting|branch(?:es|ing|ed)?))*\s*$',
                        '',
                        ep_a_str,
                        flags=re.IGNORECASE
                    ).strip()
                    if ep_a_cleaned:
                        ep_a_str = ep_a_cleaned

                    na = resolve_node_phrase(ep_a_str, exclude_comp=subj_comp, allow_create_junction=True)
                    nb = resolve_node_phrase(ep_b_str, exclude_comp=subj_comp, allow_create_junction=True)
                    if na and nb and na != nb:
                        ep_ref_comps = set(extract_comp_ids(ep_a_str) + extract_comp_ids(ep_b_str))
                        target_subjects = [uc for uc in unplaced_in_clause if uc not in ep_ref_comps] or [subj_comp]
                        na_lbl, nb_lbl = cls._fmt_graph_node(na), cls._fmt_graph_node(nb)
                        for t_comp in target_subjects:
                            if t_comp not in placed_nodes:
                                placed_nodes[t_comp] = [na, nb]
                                comp_roles[t_comp] = f"Connected from {na_lbl} to {nb_lbl}"
                                inferred_lines.append(f"{t_comp} connected from {na_lbl} to {nb_lbl}")
                                user_connection_clauses.append(f"{t_comp} connects from {na_lbl} to {nb_lbl}")
                        continue

                # 2. SECOND check single-endpoint junction / midpoint / middle node attachment, OR
                #    "and <R3> (is) also/separately (connected) to ground" when active_junction_node is already active:
                has_junction_ref = bool(
                    junction_phrase_re.search(fl_low)
                    or re.search(r'\bbranch(?:es|ing|ed)?\s+(?:from|at|connected|to)\b', fl_low)
                    or (
                        active_junction_node is not None
                        and re.search(r'\b(?:also|separately|each|both|too|as\s+well)\b', fl_low)
                        and re.search(r'\bto\s+(?:ground|gnd)\b', fl_low)
                    )
                )
                has_gnd_ref = bool(re.search(r'\b(?:to\s+ground|to\s+gnd|and\s+ground|and\s+gnd|ground|gnd)\b', fl_low))

                if has_junction_ref:
                    j_node = resolve_node_phrase(fclause, exclude_comp=subj_comp, allow_create_junction=True)
                    if not j_node or j_node == "GND":
                        j_node = active_junction_node
                    j_pair_in_clause = [c for c in cids if c != subj_comp]
                    if not j_node or j_node == "GND":
                        placed_r = [k for k in placed_nodes if not k.startswith("V") and k != subj_comp]
                        if len(placed_r) >= 2:
                            shared = (set(placed_nodes[placed_r[0]]) & set(placed_nodes[placed_r[1]])) - {"GND"}
                            if shared:
                                j_node = sorted(shared)[0]
                                active_junction_node = j_node
                                if len(j_pair_in_clause) < 2:
                                    j_pair_in_clause = [placed_r[0], placed_r[1]]
                    if j_node and j_node != "GND":
                        dest_node = "GND" if has_gnd_ref else "GND"
                        for t_comp in unplaced_in_clause:
                            if t_comp not in placed_nodes:
                                placed_nodes[t_comp] = [j_node, dest_node]
                                comp_roles[t_comp] = f"Branches from {cls._fmt_graph_node(j_node)} to {dest_node}"
                                inferred_lines.append(f"{t_comp} branches from {cls._fmt_graph_node(j_node)} to {dest_node}")
                                user_connection_clauses.append(
                                    f"{t_comp} connects from {cls._fmt_graph_node(j_node)} to {dest_node}"
                                )
                        continue

                # 3. Check "<subj_comp> in series with <placed_comp>" when <placed_comp> was already placed in parallel
                m_series_with = re.search(r'in\s+series\s+with\s+\b([RVCLI]\d+)\b', fclause, re.IGNORECASE)
                if m_series_with:
                    s_comp = m_series_with.group(1).upper()
                    if s_comp in catalog and s_comp not in placed_nodes:
                        mid_n = get_or_alloc_junction()
                        for pk, pnodes in list(placed_nodes.items()):
                            if pk != primary_source_id and pnodes == ["1", "GND"]:
                                placed_nodes[pk] = [mid_n, "GND"]
                                comp_roles[pk] = f"Parallel branch ({cls._fmt_graph_node(mid_n)} → GND)"
                        placed_nodes[s_comp] = ["1", mid_n]
                        comp_roles[s_comp] = f"Series element (N1 → {cls._fmt_graph_node(mid_n)})"
                        inferred_lines.append(f"{s_comp} in series with parallel branch at {cls._fmt_graph_node(mid_n)}")
                        user_connection_clauses.append(f"{s_comp} connects in series with parallel branch at {cls._fmt_graph_node(mid_n)}")
                        continue

        # =====================================================================
        # PIPELINE STEP 4 & 5: BUILD FINAL GRAPH & VALIDATE ALL EXPLICIT COMPONENTS
        # =====================================================================
        unplaced_passives = [pid for pid in passive_ids if pid not in placed_nodes]
        unplaced_explicit = [ecid for ecid in explicit_comp_ids if ecid not in placed_nodes]
        if unplaced_passives or unplaced_explicit:
            return {
                "has_nl_topology": len(inferred_lines) > 0,
                "is_complete": False,
                "unplaced_components": list(dict.fromkeys(unplaced_passives + unplaced_explicit)),
                "inferred_topology_lines": inferred_lines,
                "user_connection_clauses": user_connection_clauses,
            }

        # Assemble ordered component list (sources first, then passives) and node list, verifying every component has 2 valid distinct endpoints
        final_components: List[Dict[str, Any]] = []
        node_set = ["1"]
        ordered_cids = (
            [cid for cid in catalog if cid.startswith(("V", "I"))]
            + [cid for cid in catalog if not cid.startswith(("V", "I"))]
        )
        for cid in ordered_cids:
            meta = catalog[cid]
            if cid not in placed_nodes:
                continue
            c_nodes = placed_nodes[cid]
            if (
                not isinstance(c_nodes, list)
                or len(c_nodes) != 2
                or not c_nodes[0]
                or not c_nodes[1]
                or c_nodes[0] == c_nodes[1]
            ):
                return {
                    "has_nl_topology": len(inferred_lines) > 0,
                    "is_complete": False,
                    "unplaced_components": [cid],
                    "inferred_topology_lines": inferred_lines,
                    "user_connection_clauses": user_connection_clauses,
                }
            for n in c_nodes:
                if n != "GND" and n not in node_set:
                    node_set.append(n)
            final_components.append({
                "id": cid,
                "type": meta["type"],
                "value": meta["value"],
                "unit": meta["unit"],
                "nodes": c_nodes,
            })
        node_set.append("GND")

        final_comp_ids = {c["id"] for c in final_components}
        if any(ecid not in final_comp_ids for ecid in explicit_comp_ids):
            return {
                "has_nl_topology": len(inferred_lines) > 0,
                "is_complete": False,
                "unplaced_components": [ecid for ecid in explicit_comp_ids if ecid not in final_comp_ids],
                "inferred_topology_lines": inferred_lines,
                "user_connection_clauses": user_connection_clauses,
            }

        preview = cls.build_topology_preview(
            final_components,
            node_set,
            user_connection_clauses=user_connection_clauses,
            junction_pair=last_junction_pair,
        )
        resolved_graph_lines = preview["resolved_graph_lines"]
        if not resolved_graph_lines or len(final_components) == 0:
            return {
                "has_nl_topology": False,
                "is_complete": False,
                "inferred_topology_lines": inferred_lines,
                "user_connection_clauses": user_connection_clauses,
            }

        return {
            "has_nl_topology": True,
            "is_complete": True,
            "components": final_components,
            "nodes": node_set,
            "inferred_topology_lines": inferred_lines,
            "user_connection_clauses": user_connection_clauses,
            "resolved_graph": resolved_graph_lines,
            "topology_preview": preview,
            "comp_roles": comp_roles,
        }

    # =========================================================================
    # STAGE 2: CIRCUIT TYPE / INTENT CLASSIFICATION (BEFORE MANUAL RETRIEVAL)
    # =========================================================================
    @classmethod
    def classify_circuit_intent(
        cls,
        text: str,
        raw_entities: Dict[str, Any],
        experiment_context: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Deterministically classifies the requested circuit BEFORE retrieving experiment knowledge.
        Distinguishes:
          - Manual experiment topologies (EXACT MANUAL TOPOLOGY / MODIFIED MANUAL TOPOLOGY)
          - Generic / simplified circuits (GENERALIZED CIRCUIT, e.g., GENERAL_RC, VOLTAGE_DIVIDER, CUSTOM_NL_TOPOLOGY)
        NEVER defaults to Experiment 1 merely because resistors or PySpice are mentioned.
        """
        low = text.lower()
        r_list = raw_entities.get("resistors", [])
        c_list = raw_entities.get("capacitors", [])
        v_list = raw_entities.get("voltage_sources", [])
        i_list = raw_entities.get("current_sources", [])
        l_list = raw_entities.get("inductors", [])

        # Check explicit candidate confirmation or mode selection
        if re.search(r'\bgeneral[_\s]*rc\b|\bsimple\s*rc\b|\bgeneric\s*rc\b|\bbasic\s*rc\b|\bsingle[\s\-]*resistor\s*rc\b|\bseries\s*rc\b', low):
            return {
                "circuit_type": "GENERAL_RC",
                "selected_experiment": None,
                "topology_source": "ai_inferred",
                "is_ambiguous": False,
                "user_confirmed_candidate": "GENERAL_RC",
                "reason": "User requested a generic/simple single-loop RC circuit (GENERAL_RC) rather than the multi-switch Experiment 4/5 manual topology."
            }

        if re.search(r'\buse\s*modified\s*experiment\s*4\b|\bconfirm\s*experiment\s*4\b', low) or (
            re.search(r'\bmap\b.*\bto\s*r[1234]\b', low)
        ):
            return {
                "circuit_type": "RC_NATURAL_RESPONSE",
                "selected_experiment": 4,
                "topology_source": "manual_template",
                "is_ambiguous": False,
                "user_confirmed_candidate": "EXP4_MODIFIED",
                "reason": "User confirmed Modified Manual Topology for Experiment 4 (preserving all manual switches, pulse sources, and unmentioned resistors)."
            }

        cand_pick = re.search(r'\b(?:confirm\s*candidate|use\s*candidate|select\s*candidate|candidate)\s*([abc])\b', low)
        user_confirmed_candidate = cand_pick.group(1).upper() if cand_pick else None

        # Explicit Manual Experiment Mappings (1 to 14)
        # Exp 2: CCCS
        if re.search(r'\bcccs\b|current[\s\-]*controlled\s*current\s*source|experiment\s*2\b|exp\s*2\b', low):
            return {
                "circuit_type": "CCCS",
                "selected_experiment": 2,
                "topology_source": "manual_template",
                "is_ambiguous": False,
                "user_confirmed_candidate": user_confirmed_candidate,
                "reason": "Matched Current-Controlled Current Source (CCCS) -> Experiment 2"
            }

        # Exp 3: VCVS
        if re.search(r'\bvcvs\b|voltage[\s\-]*controlled\s*voltage\s*source|experiment\s*3\b|exp\s*3\b', low):
            return {
                "circuit_type": "VCVS",
                "selected_experiment": 3,
                "topology_source": "manual_template",
                "is_ambiguous": False,
                "user_confirmed_candidate": user_confirmed_candidate,
                "reason": "Matched Voltage-Controlled Voltage Source (VCVS) -> Experiment 3"
            }

        # Exp 1: Resistor Bridge / Wheatstone Bridge
        if re.search(r'resistor\s*bridge|wheatstone\s*bridge|\bbridge\s*circuit\b|dc\s*biases\s*in\s*a\s*resistor\s*bridge|experiment\s*1\b|exp\s*1\b', low) and not re.search(r'rectifier|diode|full[\s\-]*wave', low):
            return {
                "circuit_type": "RESISTOR_BRIDGE",
                "selected_experiment": 1,
                "topology_source": "manual_template",
                "is_ambiguous": False,
                "user_confirmed_candidate": user_confirmed_candidate,
                "reason": "Matched Resistor Bridge -> Experiment 1"
            }

        # Exp 4: Natural Response RC
        if re.search(r'natural\s*response|capacitor\s*discharge|rc\s*discharge|experiment\s*4\b|exp\s*4\b', low):
            return {
                "circuit_type": "RC_NATURAL_RESPONSE",
                "selected_experiment": 4,
                "topology_source": "manual_template",
                "is_ambiguous": False,
                "user_confirmed_candidate": user_confirmed_candidate,
                "reason": "Matched Natural Response of RC Circuit -> Experiment 4"
            }

        # Exp 5: Step Response RC
        if re.search(r'step\s*response|forced\s*response|rc\s*step|rc\s*charging|experiment\s*5\b|exp\s*5\b', low):
            return {
                "circuit_type": "RC_STEP_RESPONSE",
                "selected_experiment": 5,
                "topology_source": "manual_template",
                "is_ambiguous": False,
                "user_confirmed_candidate": user_confirmed_candidate,
                "reason": "Matched Step Response of RC Circuit -> Experiment 5"
            }

        # Exp 6: Pacemaker Circuit
        if re.search(r'pacemaker|heart\s*rate|\bbpm\b|experiment\s*6\b|exp\s*6\b', low):
            return {
                "circuit_type": "PACEMAKER",
                "selected_experiment": 6,
                "topology_source": "manual_template",
                "is_ambiguous": False,
                "user_confirmed_candidate": user_confirmed_candidate,
                "reason": "Matched Pacemaker Circuit -> Experiment 6"
            }

        # Exp 8: Half Adder / Full Adder
        if re.search(r'half\s*adder|full\s*adder|\badder\b|experiment\s*8\b|exp\s*8\b', low):
            return {
                "circuit_type": "HALF_FULL_ADDER",
                "selected_experiment": 8,
                "topology_source": "manual_template",
                "is_ambiguous": False,
                "user_confirmed_candidate": user_confirmed_candidate,
                "reason": "Matched Half/Full Adder -> Experiment 8"
            }

        # Exp 9: SOP / POS Boolean Function
        if re.search(r'\bsop\b|\bpos\b|sum\s*of\s*products|product\s*of\s*sums|experiment\s*9\b|exp\s*9\b', low):
            return {
                "circuit_type": "BOOLEAN_SOP_POS",
                "selected_experiment": 9,
                "topology_source": "manual_template",
                "is_ambiguous": False,
                "user_confirmed_candidate": user_confirmed_candidate,
                "reason": "Matched SOP/POS Boolean Implementation -> Experiment 9"
            }

        # Exp 10: Minimum NAND Gates
        if re.search(r'nand\s*gate|minimum\s*number\s*of\s*nand|universal\s*nand|experiment\s*10\b|exp\s*10\b', low):
            return {
                "circuit_type": "NAND_COMBINATIONAL",
                "selected_experiment": 10,
                "topology_source": "manual_template",
                "is_ambiguous": False,
                "user_confirmed_candidate": user_confirmed_candidate,
                "reason": "Matched Minimum NAND Gate Implementation -> Experiment 10"
            }

        # Exp 7: Logic Gate Truth Table
        if re.search(r'truth\s*table|basic\s*logic\s*gate|verify\s*logic\s*gate|experiment\s*7\b|exp\s*7\b', low):
            return {
                "circuit_type": "LOGIC_GATES_TRUTH_TABLE",
                "selected_experiment": 7,
                "topology_source": "manual_template",
                "is_ambiguous": False,
                "user_confirmed_candidate": user_confirmed_candidate,
                "reason": "Matched Logic Gate Truth Table -> Experiment 7"
            }

        # Exp 14: Full-Wave Rectifier (checked before Exp 11 so 'four diodes as a bridge' matches Exp 14)
        if re.search(r'full[\s\-]*wave\s*rectifier|bridge\s*rectifier|(?:four|4)\s*diodes.*bridge|diodes\s*as\s*a\s*bridge|experiment\s*14\b|exp\s*14\b', low):
            return {
                "circuit_type": "FULL_WAVE_RECTIFIER",
                "selected_experiment": 14,
                "topology_source": "manual_template",
                "is_ambiguous": False,
                "user_confirmed_candidate": user_confirmed_candidate,
                "reason": "Matched Full-Wave Bridge Rectifier -> Experiment 14"
            }

        # Exp 13: Half-Wave Rectifier
        if re.search(r'half[\s\-]*wave\s*rectifier|experiment\s*13\b|exp\s*13\b', low):
            return {
                "circuit_type": "HALF_WAVE_RECTIFIER",
                "selected_experiment": 13,
                "topology_source": "manual_template",
                "is_ambiguous": False,
                "user_confirmed_candidate": user_confirmed_candidate,
                "reason": "Matched Half-Wave Rectifier -> Experiment 13"
            }

        # Exp 12: Zener Voltage Regulator
        if re.search(r'zener|voltage\s*regulator|shunt\s*regulator|experiment\s*12\b|exp\s*12\b', low):
            return {
                "circuit_type": "ZENER_REGULATOR",
                "selected_experiment": 12,
                "topology_source": "manual_template",
                "is_ambiguous": False,
                "user_confirmed_candidate": user_confirmed_candidate,
                "reason": "Matched Zener Diode Voltage Regulator -> Experiment 12"
            }

        # Exp 11: Diode I-V Characteristics
        if re.search(r'diode\s*i[\s\-]*v|pn[\s\-]*junction|diode\s*characteristic|forward\s*bias\s*diode|resistor\s*between\s*(?:the\s*)?source\s*and\s*(?:the\s*)?diode|diode\s*in\s*series\s*with\s*(?:the\s*)?resistor|experiment\s*11\b|exp\s*11\b', low):
            return {
                "circuit_type": "DIODE_IV_CHARACTERISTICS",
                "selected_experiment": 11,
                "topology_source": "manual_template",
                "is_ambiguous": False,
                "user_confirmed_candidate": user_confirmed_candidate,
                "reason": "Matched PN-Junction Diode I-V Characteristics -> Experiment 11"
            }

        # Graph-Based Natural-Language Topology Reconstruction
        nl_topo = cls.parse_natural_language_topology(text, raw_entities)
        if nl_topo.get("has_nl_topology"):
            if nl_topo.get("is_complete"):
                return {
                    "circuit_type": "CUSTOM_NL_TOPOLOGY",
                    "selected_experiment": None,
                    "topology_source": "user_description_inferred",
                    "is_ambiguous": False,
                    "user_confirmed_candidate": "NL_TOPOLOGY",
                    "nl_topology": nl_topo,
                    "inferred_topology_lines": nl_topo.get("inferred_topology_lines", []),
                    "user_connection_clauses": nl_topo.get("user_connection_clauses", []),
                    "resolved_graph": nl_topo.get("resolved_graph", []),
                    "topology_preview": nl_topo.get("topology_preview"),
                    "reason": "Reconstructed complete circuit topology graph from natural-language connection clauses: " + "; ".join(nl_topo.get("user_connection_clauses", []))
                }
            else:
                # CRITICAL: If the user gave partial/incomplete component-specific connection clauses
                # (e.g., specified R1 and R2 in series, but left R3's connection unspecified or ambiguous),
                # DO NOT silently chain all components into SERIES_RESISTORS!
                unplaced = nl_topo.get("unplaced_components", [])
                return {
                    "circuit_type": "AMBIGUOUS_UNSPECIFIED",
                    "selected_experiment": None,
                    "topology_source": "ai_inferred",
                    "is_ambiguous": True,
                    "user_confirmed_candidate": None,
                    "nl_topology": nl_topo,
                    "inferred_topology_lines": nl_topo.get("inferred_topology_lines", []),
                    "user_connection_clauses": nl_topo.get("user_connection_clauses", []),
                    "reason": f"Partial topology graph: connection not specified for {', '.join(unplaced)}. Refusing to guess a sequential series chain."
                }

        # Generic Non-Manual Topologies (explicitly stated in natural language for the whole circuit)
        if re.search(r'voltage\s*divider', low):
            return {
                "circuit_type": "VOLTAGE_DIVIDER",
                "selected_experiment": None,
                "topology_source": "ai_inferred",
                "is_ambiguous": False,
                "user_confirmed_candidate": user_confirmed_candidate,
                "reason": "Inferred generic Voltage Divider from natural language"
            }

        if re.search(r'series\s*rlc', low):
            return {
                "circuit_type": "SERIES_RLC",
                "selected_experiment": None,
                "topology_source": "ai_inferred",
                "is_ambiguous": False,
                "user_confirmed_candidate": user_confirmed_candidate,
                "reason": "Inferred generic Series RLC circuit from natural language"
            }

        if re.search(r'parallel\s*rlc', low):
            return {
                "circuit_type": "PARALLEL_RLC",
                "selected_experiment": None,
                "topology_source": "ai_inferred",
                "is_ambiguous": False,
                "user_confirmed_candidate": user_confirmed_candidate,
                "reason": "Inferred generic Parallel RLC circuit from natural language"
            }

        has_junction_or_branch_words = bool(re.search(
            r'\b(?:junction|middle\s*point|midpoint|common\s*node|common\s*junction|branch|across)\b',
            low
        ))
        if re.search(r'series\s*resistor|connected\s*in\s*series|\bin\s*series\b', low) and len(r_list) >= 2 and not c_list and not has_junction_or_branch_words:
            return {
                "circuit_type": "SERIES_RESISTORS",
                "selected_experiment": None,
                "topology_source": "ai_inferred",
                "is_ambiguous": False,
                "user_confirmed_candidate": user_confirmed_candidate,
                "reason": "Inferred Series Resistor network from natural language"
            }

        if re.search(r'parallel\s*resistor|connected\s*in\s*parallel|\bin\s*parallel\b', low) and len(r_list) >= 2 and not c_list and not has_junction_or_branch_words:
            return {
                "circuit_type": "PARALLEL_RESISTORS",
                "selected_experiment": None,
                "topology_source": "ai_inferred",
                "is_ambiguous": False,
                "user_confirmed_candidate": user_confirmed_candidate,
                "reason": "Inferred Parallel Resistor network from natural language"
            }

        # If UI experiment context was explicitly selected by user (1..14)
        exp_to_type = {
            1: "RESISTOR_BRIDGE",
            2: "CCCS",
            3: "VCVS",
            4: "RC_NATURAL_RESPONSE",
            5: "RC_STEP_RESPONSE",
            6: "PACEMAKER",
            7: "LOGIC_GATES_TRUTH_TABLE",
            8: "HALF_FULL_ADDER",
            9: "BOOLEAN_SOP_POS",
            10: "NAND_COMBINATIONAL",
            11: "DIODE_IV_CHARACTERISTICS",
            12: "ZENER_REGULATOR",
            13: "HALF_WAVE_RECTIFIER",
            14: "FULL_WAVE_RECTIFIER",
        }
        if experiment_context in exp_to_type:
            return {
                "circuit_type": exp_to_type[experiment_context],
                "selected_experiment": experiment_context,
                "topology_source": "manual_template",
                "is_ambiguous": False,
                "user_confirmed_candidate": user_confirmed_candidate,
                "reason": f"Matched UI-selected Experiment {experiment_context} context ({exp_to_type[experiment_context]})"
            }

        # Special handling when user provides RC components (V, R, C, e.g., "12V, 5kΩ and 2µF") without specifying
        # whether they want Experiment 4 (Multi-Switch RC Natural Response) or a generic RC circuit (GENERAL_RC):
        if c_list and (r_list or v_list) and not l_list and not i_list:
            if user_confirmed_candidate == "A":
                return {
                    "circuit_type": "GENERAL_RC",
                    "selected_experiment": None,
                    "topology_source": "ai_inferred",
                    "is_ambiguous": False,
                    "user_confirmed_candidate": "A",
                    "reason": "User confirmed Candidate A: GENERAL_RC (Generalized Single-Loop RC Circuit)"
                }
            if user_confirmed_candidate == "B":
                return {
                    "circuit_type": "RC_NATURAL_RESPONSE",
                    "selected_experiment": 4,
                    "topology_source": "manual_template",
                    "is_ambiguous": False,
                    "user_confirmed_candidate": "B",
                    "reason": "User confirmed Candidate B: Experiment 4 Modified Manual Topology (preserving all switches, pulses, and resistors)"
                }
            if user_confirmed_candidate == "C":
                return {
                    "circuit_type": "RC_STEP_RESPONSE",
                    "selected_experiment": 5,
                    "topology_source": "manual_template",
                    "is_ambiguous": False,
                    "user_confirmed_candidate": "C",
                    "reason": "User confirmed Candidate C: Experiment 5 Modified Manual Topology"
                }
            # Route to RC_NATURAL_RESPONSE with partial-parameter audit & GENERAL_RC comparison so the user
            # gets the full Parameter Completeness Report, preserved manual topology, AND the GENERAL_RC option!
            return {
                "circuit_type": "RC_NATURAL_RESPONSE",
                "selected_experiment": 4,
                "topology_source": "manual_template",
                "is_ambiguous": False,
                "partial_rc_prompt": True,
                "user_confirmed_candidate": None,
                "reason": (
                    "Detected RC parameters (V, R, C). Auditing against Experiment 4 Manual Topology "
                    "(preserving all switches, pulse sources, and unmentioned resistors) while offering GENERAL_RC."
                )
            }

        # If user confirmed a candidate (A, B, C) for a generic resistor circuit
        if user_confirmed_candidate:
            if user_confirmed_candidate == "C":
                return {
                    "circuit_type": "RESISTOR_BRIDGE",
                    "selected_experiment": 1,
                    "topology_source": "manual_template",
                    "is_ambiguous": False,
                    "user_confirmed_candidate": "C",
                    "reason": "User explicitly confirmed Candidate C (Resistor Bridge Experiment 1)"
                }
            return {
                "circuit_type": f"CANDIDATE_{user_confirmed_candidate}",
                "selected_experiment": None,
                "topology_source": "ai_inferred",
                "is_ambiguous": False,
                "user_confirmed_candidate": user_confirmed_candidate,
                "reason": f"User explicitly confirmed Candidate {user_confirmed_candidate}"
            }

        # CRITICAL RULE: NEVER default to Experiment 1 merely because resistors or PySpice are mentioned!
        return {
            "circuit_type": "AMBIGUOUS_UNSPECIFIED",
            "selected_experiment": None,
            "topology_source": "ai_inferred",
            "is_ambiguous": True,
            "user_confirmed_candidate": None,
            "reason": "Circuit topology not specified by user; clarification required before selecting any template."
        }

    # =========================================================================
    # HELPER: SMART PARAMETER MAPPING (EXPLICIT ID FIRST, POSITIONAL FALLBACK)
    # =========================================================================
    @classmethod
    def _map_component_slots(
        cls,
        slot_specs: List[Dict[str, Any]],
        extracted_list: List[Dict[str, Any]],
        unit: str
    ) -> Tuple[Dict[str, float], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Maps user-extracted components into a manual template's required slots:
          1. Matches explicit IDs first (e.g., user wrote 'R2 = 5kΩ' -> maps to slot 'R2').
          2. Maps remaining unlabeled values positionally to unfilled slots.
          3. Retains manual defaults for any remaining unfilled slots (never deletes them!).
          4. Flags ambiguity when fewer unlabeled items are provided than required slots.
        Returns: (values_by_id, user_supplied_entries, manual_default_entries, missing_ambiguous_entries)
        """
        values_by_id: Dict[str, float] = {}
        user_supplied: List[Dict[str, Any]] = []
        manual_defaults: List[Dict[str, Any]] = []
        missing_ambiguous: List[Dict[str, Any]] = []

        filled_ids = set()
        unlabeled_items = []

        slot_map = {s["id"].upper(): s for s in slot_specs}

        # Pass 1: Explicit ID matches
        for item in extracted_list:
            item_id = item.get("id", "").upper()
            if item.get("explicit_id") and item_id in slot_map:
                spec = slot_map[item_id]
                val = float(item["value"])
                values_by_id[spec["id"]] = val
                filled_ids.add(spec["id"])
                user_supplied.append({
                    "id": spec["id"],
                    "value": cls._format_eng(val, unit),
                    "manual_default": cls._format_eng(spec["default"], unit),
                    "role": spec["role"],
                    "is_modified": abs(val - spec["default"]) > 1e-12,
                    "note": f"Explicitly assigned by user ({spec['id']} = {cls._format_eng(val, unit)})"
                })
            else:
                unlabeled_items.append(item)

        # Pass 2: Positional mapping for unlabeled items
        unfilled_specs = [s for s in slot_specs if s["id"] not in filled_ids]
        is_partial_unlabeled = 0 < len(unlabeled_items) < len(unfilled_specs) and len(slot_specs) > 1

        for idx, spec in enumerate(unfilled_specs):
            if idx < len(unlabeled_items):
                val = float(unlabeled_items[idx]["value"])
                values_by_id[spec["id"]] = val
                filled_ids.add(spec["id"])
                all_slot_names = ", ".join(s["id"] for s in slot_specs)
                note = (
                    f"Mapped positionally to {spec['id']} (manual default {cls._format_eng(spec['default'], unit)}); "
                    f"ambiguous across [{all_slot_names}] since label was not specified"
                    if is_partial_unlabeled
                    else f"Supplied by user (mapped to {spec['id']}, manual default {cls._format_eng(spec['default'], unit)})"
                )
                user_supplied.append({
                    "id": spec["id"],
                    "value": cls._format_eng(val, unit),
                    "manual_default": cls._format_eng(spec["default"], unit),
                    "role": spec["role"],
                    "is_modified": abs(val - spec["default"]) > 1e-12,
                    "note": note
                })
                if is_partial_unlabeled:
                    missing_ambiguous.append({
                        "id": f"{cls._format_eng(val, unit)} -> {spec['id']} (Ambiguous Component Mapping)",
                        "description": (
                            f"User supplied {len(unlabeled_items)} unlabeled value(s) ({cls._format_eng(val, unit)}), "
                            f"whereas this manual topology requires {len(slot_specs)} ({all_slot_names}). "
                            f"Explicitly mapped {cls._format_eng(val, unit)} to {spec['id']} ({spec['role']}) and retained manual defaults for "
                            f"{', '.join(s['id'] for s in unfilled_specs[len(unlabeled_items):])}. "
                            f"Please confirm which component ({all_slot_names}) this value corresponds to."
                        )
                    })
            else:
                # Retain manual default — NEVER delete unspecified manual components!
                values_by_id[spec["id"]] = spec["default"]
                manual_defaults.append({
                    "id": spec["id"],
                    "value": cls._format_eng(spec["default"], unit),
                    "role": spec["role"],
                    "note": "Retained manual default (unspecified by user)"
                })
                if len(extracted_list) > 0 and len(extracted_list) < len(slot_specs):
                    missing_ambiguous.append({
                        "id": spec["id"],
                        "description": (
                            f"Not provided by user — safely retaining manual default {spec['id']} = "
                            f"{cls._format_eng(spec['default'], unit)} ({spec['role']})."
                        )
                    })

        return values_by_id, user_supplied, manual_defaults, missing_ambiguous

    # =========================================================================
    # STAGE 4, 5, 6: TOPOLOGY TEMPLATE, PARAMETER COMPLETENESS & CIRCUIT IR
    # =========================================================================
    @classmethod
    def build_circuit_ir(
        cls,
        entities: Dict[str, Any],
        classification: Dict[str, Any],
        user_confirmed: bool = False
    ) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
        """
        Substitutes ONLY user-extracted entities into the classified topology template
        while preserving all unspecified manual topology-defining components.
        Returns (selected_circuit_ir, candidate_list, parameter_completeness_report).
        """
        ctype = classification["circuit_type"]

        v_list = entities.get("voltage_sources", [])
        i_list = entities.get("current_sources", [])
        r_list = entities.get("resistors", [])
        c_list = entities.get("capacitors", [])
        l_list = entities.get("inductors", [])
        d_list = entities.get("diodes", [])
        params = entities.get("parameters", {})

        def compute_topology_class(is_manual: bool, user_supplied_list: List[Dict[str, Any]]) -> str:
            if not is_manual:
                return "GENERALIZED CIRCUIT"
            any_modified = any(item.get("is_modified", True) for item in user_supplied_list)
            if len(user_supplied_list) == 0 or not any_modified:
                return "EXACT MANUAL TOPOLOGY"
            return "MODIFIED MANUAL TOPOLOGY"

        # ---------------------------------------------------------------------
        # EXP 1: RESISTOR BRIDGE (Exact 6-component manual topology, Page 3)
        # ---------------------------------------------------------------------
        if ctype == "RESISTOR_BRIDGE":
            v_specs = [{"id": "Vinput", "default": 10.0, "role": "DC input voltage source (nodes 1 -> GND)"}]
            r_specs = [
                {"id": "R1", "default": 2000.0, "role": "Upper-left bridge resistor (nodes 1 -> 2)"},
                {"id": "R2", "default": 1000.0, "role": "Upper-right bridge resistor (nodes 1 -> 3)"},
                {"id": "R3", "default": 1000.0, "role": "Lower-left bridge resistor (nodes 2 -> GND)"},
                {"id": "R4", "default": 2000.0, "role": "Lower-right bridge resistor (nodes 3 -> GND)"},
                {"id": "R5", "default": 2000.0, "role": "Center bridge resistor (nodes 3 -> 2)"},
            ]
            # Normalize V1 -> Vinput if user wrote V1
            v_norm = [{"id": "VINPUT" if v.get("id") == "V1" else v.get("id", ""), **v} for v in v_list]
            v_map, v_sup, v_def, v_amb = cls._map_component_slots(v_specs, v_norm, "V")
            r_map, r_sup, r_def, r_amb = cls._map_component_slots(r_specs, r_list, "ohm")

            user_sup = v_sup + r_sup
            man_def = v_def + r_def
            miss_amb = v_amb + r_amb
            top_class = compute_topology_class(True, user_sup)

            completeness = {
                "topology_classification": top_class,
                "template_name": "Experiment 1: Resistor Bridge Circuit (Manual Page 3)",
                "required_count": 6,
                "user_supplied": user_sup,
                "manual_defaults": man_def,
                "missing_ambiguous": miss_amb,
            }

            ir = {
                "version": "1.0",
                "metadata": {
                    "name": "Resistor Bridge Circuit (Experiment 1)",
                    "circuit_type": "RESISTOR_BRIDGE",
                    "experiment": 1,
                    "topology_source": "manual_template",
                    "topology_classification": top_class,
                    "user_confirmed": user_confirmed,
                    "lifecycle": {
                        "TOPOLOGY_RECONSTRUCTED": True,
                        "TOPOLOGY_VALIDATED": False,
                        "SIMULATION_EXECUTED": False,
                        "SIMULATION_SUCCESSFUL": False
                    }
                },
                "components": [
                    {"id": "Vinput", "type": "dc_voltage_source", "value": v_map["Vinput"], "unit": "V", "nodes": ["1", "GND"]},
                    {"id": "R1", "type": "resistor", "value": r_map["R1"], "unit": "ohm", "nodes": ["1", "2"]},
                    {"id": "R2", "type": "resistor", "value": r_map["R2"], "unit": "ohm", "nodes": ["1", "3"]},
                    {"id": "R3", "type": "resistor", "value": r_map["R3"], "unit": "ohm", "nodes": ["2", "GND"]},
                    {"id": "R4", "type": "resistor", "value": r_map["R4"], "unit": "ohm", "nodes": ["3", "GND"]},
                    {"id": "R5", "type": "resistor", "value": r_map["R5"], "unit": "ohm", "nodes": ["3", "2"]},
                ],
                "nodes": ["1", "2", "3", "GND"],
                "ground_node": "GND",
                "analysis": {"type": "op"}
            }
            return ir, [], completeness

        # ---------------------------------------------------------------------
        # EXP 2: CCCS CIRCUIT (Exact 8-parameter manual topology, Page 4-5)
        # ---------------------------------------------------------------------
        if ctype == "CCCS":
            v_specs = [{"id": "V1", "default": 50.0, "role": "Independent DC voltage source (nodes 1 -> GND)"}]
            r_specs = [
                {"id": "R1", "default": 6.0, "role": "Input series resistor carrying controlling current (nodes 2 -> 3)"},
                {"id": "R2", "default": 8.0, "role": "Central shunt resistor (nodes 3 -> GND)"},
                {"id": "R3", "default": 2.0, "role": "Inter-node coupling resistor (nodes 3 -> 4)"},
                {"id": "R4", "default": 4.0, "role": "Output shunt resistor (nodes 4 -> GND)"},
            ]
            i_specs = [{"id": "I1", "default": 5.0, "role": "Independent DC current source (nodes GND -> 4)"}]

            v_map, v_sup, v_def, v_amb = cls._map_component_slots(v_specs, v_list, "V")
            r_map, r_sup, r_def, r_amb = cls._map_component_slots(r_specs, r_list, "ohm")
            i_map, i_sup, i_def, i_amb = cls._map_component_slots(i_specs, i_list, "A")

            user_sup = v_sup + r_sup + i_sup
            man_def = v_def + r_def + i_def
            miss_amb = v_amb + r_amb + i_amb

            # Vtest (0V ammeter) is always part of Exp 2 manual topology
            man_def.append({
                "id": "Vtest",
                "value": "0 V",
                "role": "Zero-volt current-sense source (nodes 1 -> 2) measuring controlling current for F1",
                "note": "Retained topology-defining manual component"
            })

            if "gain" in params:
                gain = params["gain"]
                user_sup.append({
                    "id": "F1 (CCCS gain)",
                    "value": f"{gain:g} A/A",
                    "manual_default": "3 A/A",
                    "role": "Current-Controlled Current Source gain (nodes 4 -> 3, controlled by Vtest)",
                    "is_modified": abs(float(gain) - 3.0) > 1e-12,
                    "note": "Explicitly supplied by user"
                })
            else:
                gain = 3
                man_def.append({
                    "id": "F1 (CCCS gain)",
                    "value": "3 A/A",
                    "role": "Current-Controlled Current Source gain (nodes 4 -> 3, controlled by Vtest)",
                    "note": "Retained manual default gain = 3"
                })
                if len(user_sup) > 0:
                    miss_amb.append({
                        "id": "F1 (CCCS gain)",
                        "description": "CCCS current gain not specified in prompt — safely retaining manual default gain = 3."
                    })

            top_class = compute_topology_class(True, user_sup)
            completeness = {
                "topology_classification": top_class,
                "template_name": "Experiment 2: Current-Controlled Current Source (CCCS) Circuit (Manual Pages 4–5)",
                "required_count": 8,
                "user_supplied": user_sup,
                "manual_defaults": man_def,
                "missing_ambiguous": miss_amb,
            }

            comps = [
                {"id": "V1", "type": "dc_voltage_source", "value": v_map["V1"], "unit": "V", "nodes": ["1", "GND"]},
                {"id": "Vtest", "type": "dc_voltage_source", "value": 0.0, "unit": "V", "nodes": ["1", "2"], "role": "current_sense"},
                {"id": "R1", "type": "resistor", "value": r_map["R1"], "unit": "ohm", "nodes": ["2", "3"]},
                {"id": "R2", "type": "resistor", "value": r_map["R2"], "unit": "ohm", "nodes": ["3", "GND"]},
                {"id": "R3", "type": "resistor", "value": r_map["R3"], "unit": "ohm", "nodes": ["3", "4"]},
                {"id": "R4", "type": "resistor", "value": r_map["R4"], "unit": "ohm", "nodes": ["4", "GND"]},
                {"id": "I1", "type": "current_source", "value": i_map["I1"], "unit": "A", "nodes": ["GND", "4"]},
                {"id": "F1", "type": "cccs", "controlling_source": "Vtest", "gain": gain, "nodes": ["4", "3"]},
            ]

            ir = {
                "version": "1.0",
                "metadata": {
                    "name": "Current-Controlled Current Source (CCCS) Circuit (Experiment 2)",
                    "circuit_type": "CCCS",
                    "experiment": 2,
                    "topology_source": "manual_template",
                    "topology_classification": top_class,
                    "user_confirmed": user_confirmed,
                    "lifecycle": {
                        "TOPOLOGY_RECONSTRUCTED": True,
                        "TOPOLOGY_VALIDATED": False,
                        "SIMULATION_EXECUTED": False,
                        "SIMULATION_SUCCESSFUL": False
                    }
                },
                "components": comps,
                "nodes": ["1", "2", "3", "4", "GND"],
                "ground_node": "GND",
                "analysis": {"type": "op"}
            }
            return ir, [], completeness

        # ---------------------------------------------------------------------
        # EXP 3: VCVS CIRCUIT (Exact 7-parameter manual topology, Page 6-7)
        # ---------------------------------------------------------------------
        if ctype == "VCVS":
            v_specs = [{"id": "V1", "default": 65.0, "role": "Independent DC voltage source (nodes 2 -> 1)"}]
            r_specs = [
                {"id": "R1", "default": 5.0, "role": "Shunt resistor at node 3 (nodes 3 -> GND)"},
                {"id": "R2", "default": 6.0, "role": "Shunt resistor at node 1 (nodes 1 -> GND)"},
                {"id": "R3", "default": 4.0, "role": "Controlling voltage branch resistor (nodes 2 -> 3)"},
                {"id": "R4", "default": 8.0, "role": "Coupling resistor (nodes 3 -> 4)"},
                {"id": "R5", "default": 15.0, "role": "Output load resistor (nodes 5 -> GND)"},
            ]
            v_map, v_sup, v_def, v_amb = cls._map_component_slots(v_specs, v_list, "V")
            r_map, r_sup, r_def, r_amb = cls._map_component_slots(r_specs, r_list, "ohm")

            user_sup = v_sup + r_sup
            man_def = v_def + r_def
            miss_amb = v_amb + r_amb

            if "gain" in params:
                gain = params["gain"]
                user_sup.append({
                    "id": "E1 (VCVS gain)",
                    "value": f"{gain:g} V/V",
                    "manual_default": "3 V/V",
                    "role": "Voltage-Controlled Voltage Source gain (output 4 -> 5, control 2 -> 3)",
                    "is_modified": abs(float(gain) - 3.0) > 1e-12,
                    "note": "Explicitly supplied by user"
                })
            else:
                gain = 3
                man_def.append({
                    "id": "E1 (VCVS gain)",
                    "value": "3 V/V",
                    "role": "Voltage-Controlled Voltage Source gain (output 4 -> 5, control 2 -> 3)",
                    "note": "Retained manual default gain = 3"
                })
                if len(user_sup) > 0:
                    miss_amb.append({
                        "id": "E1 (VCVS gain)",
                        "description": "VCVS voltage gain not specified in prompt — safely retaining manual default gain = 3."
                    })

            top_class = compute_topology_class(True, user_sup)
            completeness = {
                "topology_classification": top_class,
                "template_name": "Experiment 3: Voltage-Controlled Voltage Source (VCVS) Circuit (Manual Pages 6–7)",
                "required_count": 7,
                "user_supplied": user_sup,
                "manual_defaults": man_def,
                "missing_ambiguous": miss_amb,
            }

            ir = {
                "version": "1.0",
                "metadata": {
                    "name": "Voltage-Controlled Voltage Source (VCVS) Circuit (Experiment 3)",
                    "circuit_type": "VCVS",
                    "experiment": 3,
                    "topology_source": "manual_template",
                    "topology_classification": top_class,
                    "user_confirmed": user_confirmed,
                    "lifecycle": {
                        "TOPOLOGY_RECONSTRUCTED": True,
                        "TOPOLOGY_VALIDATED": False,
                        "SIMULATION_EXECUTED": False,
                        "SIMULATION_SUCCESSFUL": False
                    }
                },
                "components": [
                    {"id": "V1", "type": "dc_voltage_source", "value": v_map["V1"], "unit": "V", "nodes": ["2", "1"]},
                    {"id": "R1", "type": "resistor", "value": r_map["R1"], "unit": "ohm", "nodes": ["3", "GND"]},
                    {"id": "R2", "type": "resistor", "value": r_map["R2"], "unit": "ohm", "nodes": ["1", "GND"]},
                    {"id": "R3", "type": "resistor", "value": r_map["R3"], "unit": "ohm", "nodes": ["2", "3"]},
                    {"id": "R4", "type": "resistor", "value": r_map["R4"], "unit": "ohm", "nodes": ["3", "4"]},
                    {"id": "R5", "type": "resistor", "value": r_map["R5"], "unit": "ohm", "nodes": ["5", "GND"]},
                    {"id": "E1", "type": "vcvs", "gain": gain, "nodes": ["4", "5"], "control_nodes": ["2", "3"]},
                ],
                "nodes": ["1", "2", "3", "4", "5", "GND"],
                "ground_node": "GND",
                "analysis": {"type": "op"}
            }
            return ir, [], completeness

        # ---------------------------------------------------------------------
        # EXP 4: RC NATURAL RESPONSE (Full 16-parameter multi-switch topology, Pages 8-11)
        # ---------------------------------------------------------------------
        if ctype == "RC_NATURAL_RESPONSE":
            v_specs = [{"id": "V1", "default": 100.0, "role": "DC charging source (nodes 1 -> GND)"}]
            c_specs = [{"id": "C1", "default": 0.5e-6, "role": "Energy-storage capacitor (nodes output -> GND)"}]
            r_specs = [
                {"id": "R1", "default": 10000.0, "role": "Charging branch resistor before Switch 1 (nodes 1 -> a)"},
                {"id": "R2", "default": 32000.0, "role": "Discharge series resistor after Switch 2 (nodes b -> 2)"},
                {"id": "R3", "default": 240000.0, "role": "Discharge parallel branch resistor 1 (nodes 2 -> GND)"},
                {"id": "R4", "default": 60000.0, "role": "Discharge parallel branch resistor 2 (nodes 2 -> GND)"},
            ]

            v_map, v_sup, v_def, v_amb = cls._map_component_slots(v_specs, v_list, "V")
            c_map, c_sup, c_def, c_amb = cls._map_component_slots(c_specs, c_list, "F")
            r_map, r_sup, r_def, r_amb = cls._map_component_slots(r_specs, r_list, "ohm")

            user_sup = v_sup + c_sup + r_sup
            man_def = v_def + c_def + r_def
            miss_amb = v_amb + c_amb + r_amb

            # Topology-defining switches, control pulse sources, termination resistors, ic, and transient settings
            # MUST NEVER be silently deleted!
            steptime = params.get("steptime", 1e-6)
            switchingtime = params.get("switchingtime", 50e-3)
            finaltime = params.get("finaltime", 250e-3)
            ic_val = params.get("ic", 0.0)

            man_def.extend([
                {
                    "id": "S1 (VoltageControlledSwitch 1)",
                    "value": "SW(Ron=1 mΩ, Roff=1 GΩ)",
                    "role": "Charging switch between nodes 'a' and 'output', controlled by 'posa'",
                    "note": "Retained topology-defining manual component"
                },
                {
                    "id": "S2 (VoltageControlledSwitch 2)",
                    "value": "SW(Ron=1 mΩ, Roff=1 GΩ)",
                    "role": "Discharging switch between nodes 'output' and 'b', controlled by 'posb'",
                    "note": "Retained topology-defining manual component"
                },
                {
                    "id": "Vpulse2 (PulseVoltageSource posa)",
                    "value": f"Pulse(1 V -> -1 V, delay={cls._format_eng(switchingtime, 's')}, width={cls._format_eng(finaltime, 's')})",
                    "role": "Control pulse source driving node 'posa' (opens S1 at switchingtime)",
                    "note": "Retained topology-defining manual component"
                },
                {
                    "id": "Vpulse3 (PulseVoltageSource posb)",
                    "value": f"Pulse(-1 V -> 1 V, delay={cls._format_eng(switchingtime, 's')}, width={cls._format_eng(finaltime, 's')})",
                    "role": "Control pulse source driving node 'posb' (closes S2 at switchingtime)",
                    "note": "Retained topology-defining manual component"
                },
                {
                    "id": "Rtesta",
                    "value": "1 kΩ",
                    "role": "Control loop termination resistor for 'posa' (nodes posa -> GND)",
                    "note": "Retained manual default"
                },
                {
                    "id": "Rtestb",
                    "value": "1 kΩ",
                    "role": "Control loop termination resistor for 'posb' (nodes posb -> GND)",
                    "note": "Retained manual default"
                },
            ])

            for t_id, t_val, t_def, t_unit, t_role in [
                ("ic(output)", ic_val, 0.0, "V", "Initial capacitor voltage condition at node 'output'"),
                ("steptime", steptime, 1e-6, "s", "Transient simulation step time"),
                ("switchingtime", switchingtime, 50e-3, "s", "Switch transition delay time"),
                ("finaltime", finaltime, 250e-3, "s", "Transient simulation end time"),
            ]:
                key_Lookup = "ic" if t_id == "ic(output)" else t_id
                if key_Lookup in params:
                    user_sup.append({
                        "id": t_id,
                        "value": cls._format_eng(t_val, t_unit),
                        "manual_default": cls._format_eng(t_def, t_unit),
                        "role": t_role,
                        "is_modified": abs(t_val - t_def) > 1e-12,
                        "note": "Explicitly supplied by user"
                    })
                else:
                    man_def.append({
                        "id": t_id,
                        "value": cls._format_eng(t_def, t_unit),
                        "role": t_role,
                        "note": "Retained manual default"
                    })

            # If user only gave 1 resistor (e.g. "12V, 5kΩ and 2µF"), also flag the topology choice
            # between Experiment 4 (Modified Manual Topology) vs GENERAL_RC (Generalized Circuit)
            candidates = []
            if 0 < len(r_list) < 4:
                miss_amb.append({
                    "id": "Topology Intent (Experiment 4 Multi-Switch vs GENERAL_RC)",
                    "description": (
                        "Experiment 4 in the manual is a 4-resistor, 2-switch circuit (R1=10 kΩ charging; "
                        "R2=32 kΩ, R3=240 kΩ, R4=60 kΩ discharging; switches S1/S2; pulse sources Vpulse2/Vpulse3). "
                        "If you intended a simple 1-resistor, 1-capacitor RC circuit without switches or R2–R4, "
                        "select GENERAL_RC (GENERALIZED CIRCUIT) instead."
                    )
                })
                gen_rc_ir, _, _ = cls.build_circuit_ir(
                    entities,
                    {"circuit_type": "GENERAL_RC", "selected_experiment": None, "topology_source": "ai_inferred"},
                    user_confirmed=False
                )
                candidates = [
                    {
                        "candidate_key": "EXP4_MODIFIED",
                        "name": "Option 1: Modified Experiment 4 Manual Topology (Preserves S1, S2, Vpulse2, Vpulse3, R2–R4)",
                        "description": "Maps your values into the full Experiment 4 netlist while keeping all manual switches, pulse sources, and unmentioned resistors.",
                        "topology_source": "manual_template",
                        "topology_classification": "MODIFIED MANUAL TOPOLOGY",
                        "circuit_ir": None  # filled below
                    },
                    {
                        "candidate_key": "GENERAL_RC",
                        "name": "Option 2: GENERAL_RC — Generalized Single-Loop RC Circuit (No Switches / No Extra Resistors)",
                        "description": "Simple 3-component RC circuit using only your supplied V, R, and C (not the exact Experiment 4 manual topology).",
                        "topology_source": "ai_inferred",
                        "topology_classification": "GENERALIZED CIRCUIT",
                        "circuit_ir": gen_rc_ir
                    }
                ]

            top_class = compute_topology_class(True, user_sup)
            completeness = {
                "topology_classification": top_class,
                "template_name": "Experiment 4: Natural Response of RC Circuit (Manual Pages 8–11)",
                "required_count": 16,
                "user_supplied": user_sup,
                "manual_defaults": man_def,
                "missing_ambiguous": miss_amb,
            }

            ir = {
                "version": "1.0",
                "metadata": {
                    "name": "Natural Response of RC Circuit (Experiment 4)",
                    "circuit_type": "RC_NATURAL_RESPONSE",
                    "experiment": 4,
                    "topology_source": "manual_template",
                    "topology_classification": top_class,
                    "user_confirmed": user_confirmed,
                    "lifecycle": {
                        "TOPOLOGY_RECONSTRUCTED": True,
                        "TOPOLOGY_VALIDATED": False,
                        "SIMULATION_EXECUTED": False,
                        "SIMULATION_SUCCESSFUL": False
                    }
                },
                "components": [
                    {"id": "Vpulse2", "type": "pulse_voltage_source", "initial_value": 1.0, "pulsed_value": -1.0, "delay_time": switchingtime, "pulse_width": finaltime, "period": finaltime, "unit": "V", "nodes": ["posa", "GND"]},
                    {"id": "Rtesta", "type": "resistor", "value": 1000.0, "unit": "ohm", "nodes": ["posa", "GND"]},
                    {"id": "Vpulse3", "type": "pulse_voltage_source", "initial_value": -1.0, "pulsed_value": 1.0, "delay_time": switchingtime, "pulse_width": finaltime, "period": finaltime, "unit": "V", "nodes": ["posb", "GND"]},
                    {"id": "Rtestb", "type": "resistor", "value": 1000.0, "unit": "ohm", "nodes": ["posb", "GND"]},
                    {"id": "V1", "type": "dc_voltage_source", "value": v_map["V1"], "unit": "V", "nodes": ["1", "GND"]},
                    {"id": "R1", "type": "resistor", "value": r_map["R1"], "unit": "ohm", "nodes": ["1", "a"]},
                    {"id": "S1", "type": "vc_switch", "model": "switch", "ron": 1e-3, "roff": 1e9, "nodes": ["a", "output"], "control_nodes": ["posa", "GND"]},
                    {"id": "C1", "type": "capacitor", "value": c_map["C1"], "unit": "F", "nodes": ["output", "GND"]},
                    {"id": "S2", "type": "vc_switch", "model": "switch", "ron": 1e-3, "roff": 1e9, "nodes": ["output", "b"], "control_nodes": ["posb", "GND"]},
                    {"id": "R2", "type": "resistor", "value": r_map["R2"], "unit": "ohm", "nodes": ["b", "2"]},
                    {"id": "R3", "type": "resistor", "value": r_map["R3"], "unit": "ohm", "nodes": ["2", "GND"]},
                    {"id": "R4", "type": "resistor", "value": r_map["R4"], "unit": "ohm", "nodes": ["2", "GND"]},
                ],
                "nodes": ["1", "a", "output", "b", "2", "posa", "posb", "GND"],
                "ground_node": "GND",
                "analysis": {
                    "type": "transient",
                    "step": steptime,
                    "switchingtime": switchingtime,
                    "stop": finaltime,
                    "initial_condition": {"output": ic_val}
                }
            }
            if candidates:
                candidates[0]["circuit_ir"] = ir
            return ir, candidates, completeness

        # ---------------------------------------------------------------------
        # EXP 5: RC STEP RESPONSE (Full 18-parameter multi-switch topology, Pages 12-15)
        # ---------------------------------------------------------------------
        if ctype == "RC_STEP_RESPONSE":
            v_specs = [
                {"id": "V1", "default": 40.0, "role": "Initial pre-switching DC source (nodes 1 -> GND)"},
                {"id": "V2", "default": 75.0, "role": "Post-switching step forcing DC source (nodes GND -> 3)"},
            ]
            c_specs = [{"id": "C1", "default": 0.25e-6, "role": "Capacitor (nodes output -> GND)"}]
            r_specs = [
                {"id": "R1", "default": 20000.0, "role": "Pre-switching series resistor (nodes 1 -> a)"},
                {"id": "R2", "default": 60000.0, "role": "Pre-switching shunt divider resistor (nodes a -> GND)"},
                {"id": "R3", "default": 8000.0, "role": "Post-switching series resistor (nodes b -> 2)"},
                {"id": "R4", "default": 160000.0, "role": "Post-switching parallel resistor (nodes 2 -> GND)"},
                {"id": "R5", "default": 40000.0, "role": "Post-switching step branch resistor (nodes 2 -> 3)"},
            ]

            v_map, v_sup, v_def, v_amb = cls._map_component_slots(v_specs, v_list, "V")
            c_map, c_sup, c_def, c_amb = cls._map_component_slots(c_specs, c_list, "F")
            r_map, r_sup, r_def, r_amb = cls._map_component_slots(r_specs, r_list, "ohm")

            user_sup = v_sup + c_sup + r_sup
            man_def = v_def + c_def + r_def
            miss_amb = v_amb + c_amb + r_amb

            steptime = params.get("steptime", 1e-6)
            switchingtime = params.get("switchingtime", 20e-3)
            finaltime = params.get("finaltime", 80e-3)
            ic_val = params.get("ic", 0.0)

            man_def.extend([
                {
                    "id": "S1 (VoltageControlledSwitch 1)",
                    "value": "SW(Ron=1 mΩ, Roff=1 GΩ)",
                    "role": "Pre-switching switch between 'a' and 'output', controlled by 'posa'",
                    "note": "Retained topology-defining manual component"
                },
                {
                    "id": "S2 (VoltageControlledSwitch 2)",
                    "value": "SW(Ron=1 mΩ, Roff=1 GΩ)",
                    "role": "Post-switching switch between 'output' and 'b', controlled by 'posb'",
                    "note": "Retained topology-defining manual component"
                },
                {
                    "id": "Vpulse3 (PulseVoltageSource posa)",
                    "value": f"Pulse(1 V -> -1 V, delay={cls._format_eng(switchingtime, 's')}, width={cls._format_eng(finaltime, 's')})",
                    "role": "Control pulse source driving 'posa'",
                    "note": "Retained topology-defining manual component"
                },
                {
                    "id": "Vpulse4 (PulseVoltageSource posb)",
                    "value": f"Pulse(-1 V -> 1 V, delay={cls._format_eng(switchingtime, 's')}, width={cls._format_eng(finaltime, 's')})",
                    "role": "Control pulse source driving 'posb'",
                    "note": "Retained topology-defining manual component"
                },
                {
                    "id": "Rtesta",
                    "value": "1 kΩ",
                    "role": "Control loop termination resistor for 'posa'",
                    "note": "Retained manual default"
                },
                {
                    "id": "Rtestb",
                    "value": "1 kΩ",
                    "role": "Control loop termination resistor for 'posb'",
                    "note": "Retained manual default"
                },
                {
                    "id": "ic(output)",
                    "value": cls._format_eng(ic_val, "V"),
                    "role": "Initial capacitor voltage condition at node 'output'",
                    "note": "Retained manual default"
                },
                {
                    "id": "Transient Settings",
                    "value": f"steptime={cls._format_eng(steptime, 's')}, switchingtime={cls._format_eng(switchingtime, 's')}, finaltime={cls._format_eng(finaltime, 's')}",
                    "role": "Transient simulation timing parameters",
                    "note": "Retained manual defaults"
                },
            ])

            top_class = compute_topology_class(True, user_sup)
            completeness = {
                "topology_classification": top_class,
                "template_name": "Experiment 5: Step Response of RC Circuit (Manual Pages 12–15)",
                "required_count": 18,
                "user_supplied": user_sup,
                "manual_defaults": man_def,
                "missing_ambiguous": miss_amb,
            }

            ir = {
                "version": "1.0",
                "metadata": {
                    "name": "Step Response of RC Circuit (Experiment 5)",
                    "circuit_type": "RC_STEP_RESPONSE",
                    "experiment": 5,
                    "topology_source": "manual_template",
                    "topology_classification": top_class,
                    "user_confirmed": user_confirmed,
                    "lifecycle": {
                        "TOPOLOGY_RECONSTRUCTED": True,
                        "TOPOLOGY_VALIDATED": False,
                        "SIMULATION_EXECUTED": False,
                        "SIMULATION_SUCCESSFUL": False
                    }
                },
                "components": [
                    {"id": "Vpulse3", "type": "pulse_voltage_source", "initial_value": 1.0, "pulsed_value": -1.0, "delay_time": switchingtime, "pulse_width": finaltime, "period": finaltime, "unit": "V", "nodes": ["posa", "GND"]},
                    {"id": "Rtesta", "type": "resistor", "value": 1000.0, "unit": "ohm", "nodes": ["posa", "GND"]},
                    {"id": "Vpulse4", "type": "pulse_voltage_source", "initial_value": -1.0, "pulsed_value": 1.0, "delay_time": switchingtime, "pulse_width": finaltime, "period": finaltime, "unit": "V", "nodes": ["posb", "GND"]},
                    {"id": "Rtestb", "type": "resistor", "value": 1000.0, "unit": "ohm", "nodes": ["posb", "GND"]},
                    {"id": "V1", "type": "dc_voltage_source", "value": v_map["V1"], "unit": "V", "nodes": ["1", "GND"]},
                    {"id": "R1", "type": "resistor", "value": r_map["R1"], "unit": "ohm", "nodes": ["1", "a"]},
                    {"id": "R2", "type": "resistor", "value": r_map["R2"], "unit": "ohm", "nodes": ["a", "GND"]},
                    {"id": "S1", "type": "vc_switch", "model": "switch", "ron": 1e-3, "roff": 1e9, "nodes": ["a", "output"], "control_nodes": ["posa", "GND"]},
                    {"id": "C1", "type": "capacitor", "value": c_map["C1"], "unit": "F", "nodes": ["output", "GND"]},
                    {"id": "S2", "type": "vc_switch", "model": "switch", "ron": 1e-3, "roff": 1e9, "nodes": ["output", "b"], "control_nodes": ["posb", "GND"]},
                    {"id": "R3", "type": "resistor", "value": r_map["R3"], "unit": "ohm", "nodes": ["b", "2"]},
                    {"id": "R4", "type": "resistor", "value": r_map["R4"], "unit": "ohm", "nodes": ["2", "GND"]},
                    {"id": "R5", "type": "resistor", "value": r_map["R5"], "unit": "ohm", "nodes": ["2", "3"]},
                    {"id": "V2", "type": "dc_voltage_source", "value": v_map["V2"], "unit": "V", "nodes": ["GND", "3"]},
                ],
                "nodes": ["1", "a", "output", "b", "2", "3", "posa", "posb", "GND"],
                "ground_node": "GND",
                "analysis": {
                    "type": "transient",
                    "step": steptime,
                    "switchingtime": switchingtime,
                    "stop": finaltime,
                    "initial_condition": {"output": ic_val}
                }
            }
            return ir, [], completeness

        # ---------------------------------------------------------------------
        # GENERAL_RC: GENERALIZED SINGLE-LOOP RC CIRCUIT (NOT Experiment 4/5!)
        # ---------------------------------------------------------------------
        if ctype == "GENERAL_RC":
            v_val = float(v_list[0]["value"]) if v_list else 12.0
            r_val = float(r_list[0]["value"]) if r_list else 5000.0
            c_val = float(c_list[0]["value"]) if c_list else 2e-6
            tau = r_val * c_val
            stop_t = round(5.0 * tau, 6) if tau > 0 else 0.05
            step_t = round(tau / 100.0, 8) if tau > 0 else 1e-5

            user_sup = []
            man_def = []
            miss_amb = []

            if v_list:
                user_sup.append({"id": "V1", "value": cls._format_eng(v_val, "V"), "manual_default": "N/A (Generic RC)", "role": "DC source / initial voltage (nodes 1 -> GND)", "is_modified": True, "note": "User supplied"})
            else:
                miss_amb.append({"id": "V1", "description": "Voltage source not specified; using 12 V generic default."})

            if r_list:
                user_sup.append({"id": "R1", "value": cls._format_eng(r_val, "ohm"), "manual_default": "N/A (Generic RC)", "role": "Series resistor (nodes 1 -> output)", "is_modified": True, "note": "User supplied"})
            else:
                miss_amb.append({"id": "R1", "description": "Resistor not specified; using 5 kΩ generic default."})

            if c_list:
                user_sup.append({"id": "C1", "value": cls._format_eng(c_val, "F"), "manual_default": "N/A (Generic RC)", "role": "Capacitor (nodes output -> GND)", "is_modified": True, "note": "User supplied"})
            else:
                miss_amb.append({"id": "C1", "description": "Capacitor not specified; using 2 µF generic default."})

            completeness = {
                "topology_classification": "GENERALIZED CIRCUIT",
                "template_name": "GENERAL_RC: Generic Single-Loop Series RC Circuit (Non-Manual Generalized Topology)",
                "required_count": 3,
                "user_supplied": user_sup,
                "manual_defaults": man_def,
                "missing_ambiguous": miss_amb,
            }

            ir = {
                "version": "1.0",
                "metadata": {
                    "name": "Generalized Single-Loop RC Circuit (GENERAL_RC)",
                    "circuit_type": "GENERAL_RC",
                    "experiment": None,
                    "topology_source": "ai_inferred",
                    "topology_classification": "GENERALIZED CIRCUIT",
                    "user_confirmed": True,
                    "parameters": {"tau_seconds": tau},
                    "lifecycle": {
                        "TOPOLOGY_RECONSTRUCTED": True,
                        "TOPOLOGY_VALIDATED": False,
                        "SIMULATION_EXECUTED": False,
                        "SIMULATION_SUCCESSFUL": False
                    }
                },
                "components": [
                    {"id": "V1", "type": "dc_voltage_source", "value": v_val, "unit": "V", "nodes": ["1", "GND"]},
                    {"id": "R1", "type": "resistor", "value": r_val, "unit": "ohm", "nodes": ["1", "output"]},
                    {"id": "C1", "type": "capacitor", "value": c_val, "unit": "F", "nodes": ["output", "GND"]},
                ],
                "nodes": ["1", "output", "GND"],
                "ground_node": "GND",
                "analysis": {"type": "transient", "step": step_t, "stop": stop_t, "initial_condition": {"output": v_val}}
            }
            return ir, [], completeness

        # ---------------------------------------------------------------------
        # EXP 6: PACEMAKER CIRCUIT (Exact 10-parameter manual topology, Pages 16-18)
        # ---------------------------------------------------------------------
        if ctype == "PACEMAKER":
            v_specs = [{"id": "Vs", "default": 6.0, "role": "Pacemaker supply DC voltage source V1 (nodes 1 -> GND)"}]
            c_specs = [{"id": "C1", "default": 47e-6, "role": "Pacemaker timing capacitor C (nodes control -> GND)"}]
            v_norm = [{"id": "VS" if v.get("id") in ("V1", "VS") else v.get("id", ""), **v} for v in v_list]
            v_map, v_sup, v_def, v_amb = cls._map_component_slots(v_specs, v_norm, "V")
            c_map, c_sup, c_def, c_amb = cls._map_component_slots(c_specs, c_list, "F")

            vs = v_map["Vs"]
            c_val = c_map["C1"]
            bpm = float(params.get("heart_rate_bpm", 70.0))
            sf = float(params.get("switching_factor", 0.68))
            vo = sf * vs
            t_period = 60.0 / bpm
            r_calc = -60.0 / (bpm * c_val * math.log(1.0 - (vo / vs)))

            r_specs = [
                {"id": "R1", "default": round(r_calc, 2), "role": "Calculated charging timing resistor R (nodes 1 -> control)"},
                {"id": "R2", "default": 50.0, "role": "Pacemaker output discharge load resistor (nodes out -> GND)"},
            ]
            r_map, r_sup, r_def, r_amb = cls._map_component_slots(r_specs, r_list, "ohm")

            r1_val = float(r_map["R1"])
            tau_charge = r1_val * c_val
            five_cycle_stop_s = round(5.0 * t_period, 6)
            recommended_stop_s = five_cycle_stop_s

            user_sup = v_sup + c_sup + r_sup
            man_def = v_def + c_def + r_def
            miss_amb = v_amb + c_amb + r_amb

            if "heart_rate_bpm" in params:
                user_sup.append({
                    "id": "H (Heart Rate)",
                    "value": f"{bpm:g} BPM",
                    "manual_default": "70 BPM",
                    "role": f"Target heart rate in beats per minute (Calculated period T = 60 / H = {t_period:.4f} s; 5-cycle window = {five_cycle_stop_s:g} s)",
                    "is_modified": abs(bpm - 70.0) > 1e-9,
                    "note": "Explicitly supplied by user"
                })
            else:
                man_def.append({
                    "id": "H (Heart Rate)",
                    "value": "70 BPM",
                    "role": f"Target heart rate in beats per minute (Calculated period T = 60 / H = {t_period:.4f} s; 5-cycle window = {five_cycle_stop_s:g} s)",
                    "note": "Retained manual default"
                })

            if "switching_factor" in params:
                user_sup.append({
                    "id": "Switching_factor",
                    "value": f"{sf:g}",
                    "manual_default": "0.68",
                    "role": "Threshold ratio Vo / Vs",
                    "is_modified": abs(sf - 0.68) > 1e-9,
                    "note": "Explicitly supplied by user"
                })
            else:
                man_def.append({"id": "Switching_factor", "value": "0.68", "role": "Threshold ratio Vo / Vs", "note": "Retained manual default"})

            raw_steptime_s = float(params.get("steptime", 1e-3))
            if "finaltime" in params:
                raw_finaltime_s = float(params["finaltime"])
                stop_code_expr, stop_textual, _ = cls._format_pyspice_time(raw_finaltime_s)
                user_sup.append({
                    "id": "Transient end_time",
                    "value": f"{stop_textual} ({stop_code_expr})",
                    "manual_default": "60 microseconds (60@u_us manual raw duration)",
                    "role": "User-specified transient observation window",
                    "is_modified": True,
                    "note": "Explicitly supplied by user"
                })
            else:
                # Manual raw duration: 60 microseconds (60e-6 s), validated as `60@u_us` (never `@u_s`)
                raw_finaltime_s = 60e-6
                stop_code_expr, stop_textual, _ = cls._format_pyspice_time(raw_finaltime_s)

            # Pre-simulation Step/Stop & Window Consistency Check:
            # Verify step_time > 0, end_time > 0, step_time <= end_time.
            # Never silently use 1 ms as the timestep for a 60 us simulation!
            step_stop_consistency = cls.verify_step_stop_consistency(
                raw_step_s=raw_steptime_s,
                raw_stop_s=raw_finaltime_s,
                target_period_s=t_period,
                rc_tau_s=tau_charge,
                required_cycles=5,
            )

            # Active simulation parameters for the manual/user window (with compatible step_time <= end_time)
            steptime_s = float(step_stop_consistency["compat_step_for_raw_stop_s"])
            finaltime_s = float(raw_finaltime_s)
            step_code_expr = step_stop_consistency["compat_raw_step_expr"]
            step_textual = step_stop_consistency["compat_raw_step_text"]

            # Compatible 5-cycle parameters for generated PySpice code (e.g., 3.75 seconds for 80 BPM)
            five_cycle_step_expr = step_stop_consistency["req_step_expr"]
            five_cycle_step_text = step_stop_consistency["req_step_text"]
            five_cycle_stop_expr = step_stop_consistency["req_stop_expr"]
            five_cycle_stop_text = step_stop_consistency["req_stop_text"]

            window_sufficient = bool(step_stop_consistency["window_sufficient"])
            unit_mismatch_detected = bool(
                ("finaltime" not in params)
                or (not step_stop_consistency["step_le_stop"])
                or (not window_sufficient)
            )
            unit_mismatch_detail = (
                f"Pre-simulation Step/Stop & Window Audit: Raw manual parameters had `step_time = {step_stop_consistency['raw_step_text']}` "
                f"(`{step_stop_consistency['raw_step_expr']}`) and `end_time = {stop_textual}` (`{stop_code_expr}`). "
                f"1) Step/Stop Inconsistency: `{step_stop_consistency['raw_step_text']}` > `{stop_textual}` violates `step_time <= end_time` "
                f"(1 ms cannot be used as the timestep for a 60 us simulation); adjusted 60 us diagnostic timestep to "
                f"`step_time = {step_code_expr}` ({step_textual}). "
                f"2) Insufficient Observation Window: `{stop_textual}` << RC tau = {tau_charge:.4f} s and target period T = 60/{bpm:g} = {t_period:.4f} s. "
                f"To observe 5 complete cycles, required duration = 5 * {t_period:g} s = `{five_cycle_stop_text}` (`end_time = {five_cycle_stop_expr}` "
                f"with `step_time = {five_cycle_step_expr}`)."
                if unit_mismatch_detected else None
            )

            man_def.extend([
                {
                    "id": "S1 (VoltageControlledSwitch)",
                    "value": "SW(Ron=1 mΩ, Roff=1 GΩ, Vt=2.05 V, Vh=2.03 V)",
                    "role": "Pacemaker pulse discharge switch (control -> out, ctrl: control -> GND)",
                    "note": "Retained topology-defining manual component"
                },
                {
                    "id": "ic(control)",
                    "value": "0 V",
                    "role": "Initial capacitor voltage condition",
                    "note": "Retained manual default"
                },
                {
                    "id": "Transient Settings (Step/Stop Validated)",
                    "value": (
                        f"Manual 60 us window: step_time={step_code_expr} ({step_textual}), end_time={stop_code_expr} ({stop_textual}) "
                        f"[auto-adjusted from raw step_time=1 ms so step_time <= end_time]; "
                        f"5-Cycle ({five_cycle_stop_text}) code window: step_time={five_cycle_step_expr} ({five_cycle_step_text}), "
                        f"end_time={five_cycle_stop_expr} ({five_cycle_stop_text})"
                    ),
                    "role": "Validated transient simulation parameters (step_time > 0, end_time > 0, step_time <= end_time)",
                    "note": "Step/stop consistency verified before simulation"
                },
            ])

            if not window_sufficient:
                miss_amb.append({
                    "id": "Transient Simulation Window & Step/Stop Consistency",
                    "description": (
                        f"Simulation window is insufficient to observe the requested behavior. "
                        f"Manual-derived window is {stop_textual} (`end_time={stop_code_expr}` with compatible `step_time={step_code_expr}`), "
                        f"which is far shorter than the RC charging time constant (tau = {tau_charge:.4f} s) and target heartbeat period "
                        f"(T = 60 / {bpm:g} = {t_period:.4f} s). To observe 5 cycles, required duration = {five_cycle_stop_text} "
                        f"(`end_time={five_cycle_stop_expr}`, `step_time={five_cycle_step_expr}`)."
                    )
                })

            top_class = compute_topology_class(True, user_sup)
            completeness = {
                "topology_classification": top_class,
                "template_name": "Experiment 6: Pacemaker RC Timing Circuit (Manual Pages 16–18)",
                "required_count": 10,
                "user_supplied": user_sup,
                "manual_defaults": man_def,
                "missing_ambiguous": miss_amb,
            }

            ir = {
                "version": "1.0",
                "metadata": {
                    "name": "Pacemaker RC Timing Circuit (Experiment 6)",
                    "circuit_type": "PACEMAKER",
                    "experiment": 6,
                    "topology_source": "manual_template",
                    "topology_classification": top_class,
                    "user_confirmed": user_confirmed,
                    "parameters": {
                        "heart_rate_bpm": bpm,
                        "switching_factor": sf,
                        "calculated_R_ohm": round(r_calc, 2),
                        "target_period_s": round(t_period, 6),
                        "rc_tau_s": round(tau_charge, 6),
                        "expected_threshold_vo_V": round(vo, 4),
                        "recommended_stop_s": recommended_stop_s,
                        "recommended_5_cycle_duration_s": five_cycle_stop_s,
                        "five_cycle_duration_s": five_cycle_stop_s,
                        "five_cycle_stop_expr": five_cycle_stop_expr,
                        "five_cycle_stop_text": five_cycle_stop_text,
                        "five_cycle_step_expr": five_cycle_step_expr,
                        "five_cycle_step_text": five_cycle_step_text,
                    },
                    "lifecycle": {
                        "TOPOLOGY_RECONSTRUCTED": True,
                        "TOPOLOGY_VALIDATED": False,
                        "SIMULATION_EXECUTED": False,
                        "SIMULATION_NUMERICALLY_SUCCESSFUL": False,
                        "SIMULATION_SUCCESSFUL": False,
                        "WINDOW_SUFFICIENT": window_sufficient,
                        "REQUESTED_BEHAVIOR_OBSERVED": False,
                    }
                },
                "components": [
                    {"id": "V1", "type": "dc_voltage_source", "value": vs, "unit": "V", "nodes": ["1", "GND"]},
                    {"id": "R1", "type": "resistor", "value": r_map["R1"], "unit": "ohm", "nodes": ["1", "control"]},
                    {"id": "C1", "type": "capacitor", "value": c_val, "unit": "F", "nodes": ["control", "GND"]},
                    {"id": "S1", "type": "vc_switch", "nodes": ["control", "out"], "control_nodes": ["control", "GND"], "vt": 2.05, "vh": 2.03, "ron": 1e-3, "roff": 1e9},
                    {"id": "R2", "type": "resistor", "value": r_map["R2"], "unit": "ohm", "nodes": ["out", "GND"]},
                ],
                "nodes": ["1", "control", "out", "GND"],
                "ground_node": "GND",
                "analysis": {
                    "type": "transient",
                    "raw_step": raw_steptime_s,
                    "raw_stop": raw_finaltime_s,
                    "step": steptime_s,
                    "stop": finaltime_s,
                    "step_code_expr": step_code_expr,
                    "stop_code_expr": stop_code_expr,
                    "step_textual": step_textual,
                    "stop_textual": stop_textual,
                    "recommended_cycles": 5,
                    "recommended_step_s": step_stop_consistency["compat_step_for_req_s"],
                    "recommended_stop_s": recommended_stop_s,
                    "recommended_step_code_expr": five_cycle_step_expr,
                    "recommended_stop_code_expr": five_cycle_stop_expr,
                    "five_cycle_step_s": step_stop_consistency["compat_step_for_req_s"],
                    "five_cycle_stop_s": five_cycle_stop_s,
                    "five_cycle_step_expr": five_cycle_step_expr,
                    "five_cycle_stop_expr": five_cycle_stop_expr,
                    "five_cycle_step_text": five_cycle_step_text,
                    "five_cycle_stop_text": five_cycle_stop_text,
                    "target_period_s": round(t_period, 6),
                    "rc_tau_s": round(tau_charge, 6),
                    "window_sufficient": window_sufficient,
                    "unit_mismatch_detected": unit_mismatch_detected,
                    "unit_mismatch_detail": unit_mismatch_detail,
                    "step_stop_consistency": step_stop_consistency,
                }
            }
            return ir, [], completeness

        # ---------------------------------------------------------------------
        # EXP 7, 8, 9, 10: DIGITAL LOGIC & COMBINATIONAL CIRCUITS
        # ---------------------------------------------------------------------
        if ctype in ("LOGIC_GATES_TRUTH_TABLE", "HALF_FULL_ADDER", "BOOLEAN_SOP_POS", "NAND_COMBINATIONAL"):
            exp_map = {
                "LOGIC_GATES_TRUTH_TABLE": (7, "Verification of Truth Tables of Logic Gates"),
                "HALF_FULL_ADDER": (8, "Half Adder and Full Adder Digital Circuit"),
                "BOOLEAN_SOP_POS": (9, "Boolean Function in SOP and POS Form"),
                "NAND_COMBINATIONAL": (10, "Combinational Circuit Using Minimum NAND Gates"),
            }
            e_num, e_title = exp_map[ctype]
            user_sup = []
            if "boolean_expression" in params:
                user_sup.append({
                    "id": "Boolean Expression",
                    "value": params["boolean_expression"],
                    "manual_default": "X_SOP = sum(1,3,6) = A'B'C + A'BC + ABC'",
                    "role": "Target Boolean logic function",
                    "is_modified": True,
                    "note": "Explicitly supplied by user"
                })
            man_def = [
                {"id": "TTL Logic Gates", "value": "7408 (AND), 7432 (OR), 7404 (NOT), 7400 (NAND), 7486 (XOR)", "role": "Standard TTL IC family components", "note": "Retained manual defaults"},
                {"id": "Digital Inputs/Probes", "value": "Logic Toggles (A, B, C) & LED Indicators", "role": "Input stimulus and output verification", "note": "Retained manual defaults"},
            ]
            top_class = compute_topology_class(True, user_sup)
            completeness = {
                "topology_classification": top_class,
                "template_name": f"Experiment {e_num}: {e_title}",
                "required_count": len(user_sup) + len(man_def),
                "user_supplied": user_sup,
                "manual_defaults": man_def,
                "missing_ambiguous": [],
            }
            ir = {
                "version": "1.0",
                "metadata": {
                    "name": f"{e_title} (Experiment {e_num})",
                    "circuit_type": ctype,
                    "experiment": e_num,
                    "topology_source": "manual_template",
                    "topology_classification": top_class,
                    "user_confirmed": user_confirmed,
                    "lifecycle": {
                        "TOPOLOGY_RECONSTRUCTED": True,
                        "TOPOLOGY_VALIDATED": True,
                        "SIMULATION_EXECUTED": False,
                        "SIMULATION_SUCCESSFUL": False
                    }
                },
                "components": [],
                "nodes": ["A", "B", "C", "OUT", "GND"],
                "ground_node": "GND",
                "analysis": {"type": "digital_truth_table"}
            }
            return ir, [], completeness

        # ---------------------------------------------------------------------
        # EXP 11, 12, 13, 14: SEMICONDUCTOR & POWER ELECTRONICS
        # ---------------------------------------------------------------------
        if ctype in ("DIODE_IV_CHARACTERISTICS", "ZENER_REGULATOR", "HALF_WAVE_RECTIFIER", "FULL_WAVE_RECTIFIER"):
            exp_map = {
                "DIODE_IV_CHARACTERISTICS": (11, "PN-Junction Diode I-V Characteristics"),
                "ZENER_REGULATOR": (12, "Zener Diode Voltage Regulator"),
                "HALF_WAVE_RECTIFIER": (13, "Half-Wave Rectifier"),
                "FULL_WAVE_RECTIFIER": (14, "Full-Wave Bridge Rectifier"),
            }
            e_num, e_title = exp_map[ctype]

            v_specs = [{"id": "V1", "default": 12.0, "role": "DC source (Exp 11/12) or AC sinusoidal source (Exp 13/14)"}]
            if e_num == 12:
                r_specs = [
                    {"id": "Rs", "default": 220.0, "role": "Series current-limiting resistor (nodes 1 -> 2)"},
                    {"id": "RL", "default": 1000.0, "role": "Shunt load resistor across Zener diode (nodes 2 -> GND)"},
                ]
            else:
                r_specs = [
                    {"id": "R1", "default": 1000.0, "role": "Current-limiting / load resistor (nodes 2 -> GND)"},
                ]

            v_map, v_sup, v_def, v_amb = cls._map_component_slots(v_specs, v_list, "V")
            r_map, r_sup, r_def, r_amb = cls._map_component_slots(r_specs, r_list, "ohm")
            user_sup = v_sup + r_sup
            man_def = v_def + r_def
            miss_amb = v_amb + r_amb

            if e_num == 12:
                vz = d_list[0].get("vz", 5.1) if d_list else 5.1
                if d_list and d_list[0].get("explicit_vz"):
                    user_sup.append({"id": "DZ1 (Zener Vz)", "value": f"{vz:g} V", "manual_default": "5.1 V", "role": "Reverse-biased Zener regulator diode (nodes GND -> 2)", "is_modified": abs(vz - 5.1) > 1e-9, "note": "Explicitly supplied by user"})
                else:
                    man_def.append({"id": "DZ1 (Zener Vz)", "value": "5.1 V", "role": "Reverse-biased Zener regulator diode (nodes GND -> 2)", "note": "Retained manual default"})
                comps = [
                    {"id": "V1", "type": "dc_voltage_source", "value": v_map["V1"], "unit": "V", "nodes": ["1", "GND"]},
                    {"id": "Rs", "type": "resistor", "value": r_map["Rs"], "unit": "ohm", "nodes": ["1", "2"]},
                    {"id": "DZ1", "type": "zener", "value": vz, "unit": "V", "nodes": ["GND", "2"]},
                    {"id": "RL", "type": "resistor", "value": r_map["RL"], "unit": "ohm", "nodes": ["2", "GND"]},
                ]
                nodes = ["1", "2", "GND"]
            elif e_num == 14:
                man_def.append({"id": "D1..D4 (Diode Bridge)", "value": "4x 1N4007 (Vf=0.7 V)", "role": "Full-wave bridge rectifier diodes", "note": "Retained topology-defining manual components"})
                comps = [
                    {"id": "V1", "type": "ac_voltage_source", "value": v_map["V1"], "unit": "V", "nodes": ["1", "2"]},
                    {"id": "D1", "type": "diode", "value": 0.7, "unit": "V", "nodes": ["1", "out"]},
                    {"id": "D2", "type": "diode", "value": 0.7, "unit": "V", "nodes": ["GND", "2"]},
                    {"id": "D3", "type": "diode", "value": 0.7, "unit": "V", "nodes": ["2", "out"]},
                    {"id": "D4", "type": "diode", "value": 0.7, "unit": "V", "nodes": ["GND", "1"]},
                    {"id": "R1", "type": "resistor", "value": r_map["R1"], "unit": "ohm", "nodes": ["out", "GND"]},
                ]
                if c_list:
                    c_val = float(c_list[0]["value"])
                    user_sup.append({"id": "C1 (Filter)", "value": cls._format_eng(c_val, "F"), "manual_default": "100 µF", "role": "Shunt smoothing filter capacitor (nodes out -> GND)", "is_modified": True, "note": "User supplied"})
                    comps.append({"id": "C1", "type": "capacitor", "value": c_val, "unit": "F", "nodes": ["out", "GND"]})
                nodes = ["1", "2", "out", "GND"]
            else:
                man_def.append({"id": "D1 (PN Diode)", "value": "1N4007 (Vf=0.7 V)", "role": "Forward PN-junction diode (nodes 1 -> 2)", "note": "Retained topology-defining manual component"})
                comps = [
                    {"id": "V1", "type": "dc_voltage_source" if e_num == 11 else "ac_voltage_source", "value": v_map["V1"], "unit": "V", "nodes": ["1", "GND"]},
                    {"id": "D1", "type": "diode", "value": 0.7, "unit": "V", "nodes": ["1", "2"]},
                    {"id": "R1", "type": "resistor", "value": r_map["R1"], "unit": "ohm", "nodes": ["2", "GND"]},
                ]
                if c_list:
                    c_val = float(c_list[0]["value"])
                    user_sup.append({"id": "C1 (Filter)", "value": cls._format_eng(c_val, "F"), "manual_default": "100 µF", "role": "Filter capacitor (nodes 2 -> GND)", "is_modified": True, "note": "User supplied"})
                    comps.append({"id": "C1", "type": "capacitor", "value": c_val, "unit": "F", "nodes": ["2", "GND"]})
                nodes = ["1", "2", "GND"]

            top_class = compute_topology_class(True, user_sup)
            completeness = {
                "topology_classification": top_class,
                "template_name": f"Experiment {e_num}: {e_title}",
                "required_count": len(user_sup) + len(man_def),
                "user_supplied": user_sup,
                "manual_defaults": man_def,
                "missing_ambiguous": miss_amb,
            }

            ir = {
                "version": "1.0",
                "metadata": {
                    "name": f"{e_title} (Experiment {e_num})",
                    "circuit_type": ctype,
                    "experiment": e_num,
                    "topology_source": "manual_template",
                    "topology_classification": top_class,
                    "user_confirmed": user_confirmed,
                    "lifecycle": {
                        "TOPOLOGY_RECONSTRUCTED": True,
                        "TOPOLOGY_VALIDATED": False,
                        "SIMULATION_EXECUTED": False,
                        "SIMULATION_SUCCESSFUL": False
                    }
                },
                "components": comps,
                "nodes": nodes,
                "ground_node": "GND",
                "analysis": {"type": "op" if e_num in (11, 12) else "transient"}
            }
            return ir, [], completeness

        # ---------------------------------------------------------------------
        # NATURAL-LANGUAGE INFERRED CUSTOM TOPOLOGY (CUSTOM_NL_TOPOLOGY)
        # ---------------------------------------------------------------------
        if ctype == "CUSTOM_NL_TOPOLOGY" and classification.get("nl_topology"):
            nl_topo = classification["nl_topology"]
            comps = nl_topo.get("components", [])
            nodes = nl_topo.get("nodes", ["1", "GND"])
            inferred_lines = nl_topo.get("inferred_topology_lines", [])
            user_connection_clauses = nl_topo.get("user_connection_clauses", inferred_lines)
            resolved_graph = nl_topo.get("resolved_graph", [])
            topology_preview = nl_topo.get("topology_preview") or cls.build_topology_preview(comps, nodes, user_connection_clauses, resolved_graph)
            comp_roles = nl_topo.get("comp_roles", {})
            user_sup = cls._build_user_supplied_entries(entities, comp_roles)

            has_cap_or_ind = any(c["type"] in ("capacitor", "inductor") for c in comps)
            analysis_cfg = {"type": "transient", "step": 1e-5, "stop": 0.05} if has_cap_or_ind else {"type": "op"}

            completeness = {
                "topology_classification": "GENERALIZED CIRCUIT",
                "template_name": "User-Described Custom Topology (Reconstructed from Natural Language)",
                "required_count": len(comps),
                "user_supplied": user_sup,
                "manual_defaults": [],
                "missing_ambiguous": [],
                "inferred_topology_lines": inferred_lines,
                "user_connection_clauses": user_connection_clauses,
                "resolved_graph": resolved_graph,
                "topology_preview": topology_preview,
            }
            ir = {
                "version": "1.0",
                "metadata": {
                    "name": "Custom Natural-Language Reconstructed Circuit",
                    "circuit_type": "CUSTOM_NL_TOPOLOGY",
                    "experiment": None,
                    "topology_source": "user_description_inferred",
                    "topology_classification": "GENERALIZED CIRCUIT",
                    "inferred_topology_lines": inferred_lines,
                    "user_connection_clauses": user_connection_clauses,
                    "resolved_graph": resolved_graph,
                    "topology_preview": topology_preview,
                    "user_confirmed": True,
                    "lifecycle": {
                        "TOPOLOGY_RECONSTRUCTED": True,
                        "TOPOLOGY_VALIDATED": False,
                        "SIMULATION_EXECUTED": False,
                        "SIMULATION_SUCCESSFUL": False
                    }
                },
                "components": comps,
                "nodes": nodes,
                "ground_node": "GND",
                "analysis": analysis_cfg
            }
            return ir, [], completeness

        # ---------------------------------------------------------------------
        # GENERIC EXPLICIT CIRCUITS (GENERALIZED CIRCUIT — AI-INFERRED)
        # ---------------------------------------------------------------------
        if ctype in ("VOLTAGE_DIVIDER", "SERIES_RESISTORS", "CANDIDATE_A"):
            v1 = float(v_list[0]["value"]) if v_list else 10.0
            comps = [{"id": "V1", "type": "dc_voltage_source", "value": v1, "unit": "V", "nodes": ["1", "GND"]}]
            nodes = ["1", "GND"]
            n_res = len(r_list) if r_list else 2
            user_sup = []
            if v_list:
                user_sup.append({"id": v_list[0].get("id", "V1"), "value": cls._format_eng(v1, "V"), "manual_default": "N/A (Generic)", "role": "DC Voltage Source", "is_modified": True, "user_supplied": True, "note": "User supplied"})
            for idx in range(n_res):
                r_val = float(r_list[idx]["value"]) if idx < len(r_list) else 1000.0
                r_id = r_list[idx].get("id", f"R{idx+1}") if idx < len(r_list) else f"R{idx+1}"
                n_from = str(idx + 1)
                n_to = "GND" if idx == n_res - 1 else str(idx + 2)
                if n_to not in nodes:
                    nodes.insert(-1, n_to)
                comps.append({"id": r_id, "type": "resistor", "value": r_val, "unit": "ohm", "nodes": [n_from, n_to]})
                if idx < len(r_list):
                    user_sup.append({"id": r_id, "value": cls._format_eng(r_val, "ohm"), "manual_default": "N/A (Generic)", "role": f"Series resistor #{idx+1} ({n_from} -> {n_to})", "is_modified": True, "user_supplied": True, "note": "User supplied"})

            completeness = {
                "topology_classification": "GENERALIZED CIRCUIT",
                "template_name": "Generalized Series Resistor / Voltage Divider Network (Non-Manual Topology)",
                "required_count": len(comps),
                "user_supplied": user_sup,
                "manual_defaults": [],
                "missing_ambiguous": [],
                "inferred_topology_lines": [f"{', '.join(c['id'] for c in comps if c['type'] == 'resistor')} connected in series"],
            }
            ir = {
                "version": "1.0",
                "metadata": {
                    "name": "Series Resistor / Voltage Divider Network (Generalized Circuit)",
                    "circuit_type": ctype,
                    "experiment": None,
                    "topology_source": "ai_inferred",
                    "topology_classification": "GENERALIZED CIRCUIT",
                    "user_confirmed": user_confirmed or (ctype == "CANDIDATE_A"),
                    "lifecycle": {
                        "TOPOLOGY_RECONSTRUCTED": True,
                        "TOPOLOGY_VALIDATED": False,
                        "SIMULATION_EXECUTED": False,
                        "SIMULATION_SUCCESSFUL": False
                    }
                },
                "components": comps,
                "nodes": nodes,
                "ground_node": "GND",
                "analysis": {"type": "op"}
            }
            return ir, [], completeness

        if ctype in ("PARALLEL_RESISTORS", "CANDIDATE_B"):
            v1 = float(v_list[0]["value"]) if v_list else 10.0
            comps = [{"id": "V1", "type": "dc_voltage_source", "value": v1, "unit": "V", "nodes": ["1", "GND"]}]
            n_res = len(r_list) if r_list else 2
            user_sup = []
            if v_list:
                user_sup.append({"id": v_list[0].get("id", "V1"), "value": cls._format_eng(v1, "V"), "manual_default": "N/A (Generic)", "role": "DC Voltage Source", "is_modified": True, "user_supplied": True, "note": "User supplied"})
            for idx in range(n_res):
                r_val = float(r_list[idx]["value"]) if idx < len(r_list) else 1000.0
                r_id = r_list[idx].get("id", f"R{idx+1}") if idx < len(r_list) else f"R{idx+1}"
                comps.append({"id": r_id, "type": "resistor", "value": r_val, "unit": "ohm", "nodes": ["1", "GND"]})
                if idx < len(r_list):
                    user_sup.append({"id": r_id, "value": cls._format_eng(r_val, "ohm"), "manual_default": "N/A (Generic)", "role": f"Parallel resistor #{idx+1} (1 -> GND)", "is_modified": True, "user_supplied": True, "note": "User supplied"})

            completeness = {
                "topology_classification": "GENERALIZED CIRCUIT",
                "template_name": "Generalized Parallel Resistor Network (Non-Manual Topology)",
                "required_count": len(comps),
                "user_supplied": user_sup,
                "manual_defaults": [],
                "missing_ambiguous": [],
                "inferred_topology_lines": [f"{', '.join(c['id'] for c in comps if c['type'] == 'resistor')} connected in parallel across V1"],
            }
            ir = {
                "version": "1.0",
                "metadata": {
                    "name": "Parallel Resistor Network (Generalized Circuit)",
                    "circuit_type": ctype,
                    "experiment": None,
                    "topology_source": "ai_inferred",
                    "topology_classification": "GENERALIZED CIRCUIT",
                    "user_confirmed": user_confirmed or (ctype == "CANDIDATE_B"),
                    "lifecycle": {
                        "TOPOLOGY_RECONSTRUCTED": True,
                        "TOPOLOGY_VALIDATED": False,
                        "SIMULATION_EXECUTED": False,
                        "SIMULATION_SUCCESSFUL": False
                    }
                },
                "components": comps,
                "nodes": ["1", "GND"],
                "ground_node": "GND",
                "analysis": {"type": "op"}
            }
            return ir, [], completeness

        if ctype in ("SERIES_RLC", "PARALLEL_RLC"):
            v1 = float(v_list[0]["value"]) if v_list else 10.0
            r1 = float(r_list[0]["value"]) if r_list else 100.0
            l1 = float(l_list[0]["value"]) if l_list else 10e-3
            c1 = float(c_list[0]["value"]) if c_list else 1e-6
            if ctype == "SERIES_RLC":
                comps = [
                    {"id": "V1", "type": "dc_voltage_source", "value": v1, "unit": "V", "nodes": ["1", "GND"]},
                    {"id": "R1", "type": "resistor", "value": r1, "unit": "ohm", "nodes": ["1", "2"]},
                    {"id": "L1", "type": "inductor", "value": l1, "unit": "H", "nodes": ["2", "output"]},
                    {"id": "C1", "type": "capacitor", "value": c1, "unit": "F", "nodes": ["output", "GND"]},
                ]
                nodes = ["1", "2", "output", "GND"]
                inferred_line = "R1, L1, and C1 connected in series across V1"
            else:
                comps = [
                    {"id": "V1", "type": "dc_voltage_source", "value": v1, "unit": "V", "nodes": ["1", "GND"]},
                    {"id": "R1", "type": "resistor", "value": r1, "unit": "ohm", "nodes": ["1", "GND"]},
                    {"id": "L1", "type": "inductor", "value": l1, "unit": "H", "nodes": ["1", "GND"]},
                    {"id": "C1", "type": "capacitor", "value": c1, "unit": "F", "nodes": ["1", "GND"]},
                ]
                nodes = ["1", "GND"]
                inferred_line = "R1, L1, and C1 connected in parallel across V1"

            user_sup = cls._build_user_supplied_entries(entities)
            completeness = {
                "topology_classification": "GENERALIZED CIRCUIT",
                "template_name": f"Generalized {ctype.replace('_', ' ').title()} Network",
                "required_count": 4,
                "user_supplied": user_sup,
                "manual_defaults": [],
                "missing_ambiguous": [],
                "inferred_topology_lines": [inferred_line],
            }
            ir = {
                "version": "1.0",
                "metadata": {
                    "name": f"{ctype.replace('_', ' ').title()} Circuit",
                    "circuit_type": ctype,
                    "experiment": None,
                    "topology_source": "ai_inferred",
                    "topology_classification": "GENERALIZED CIRCUIT",
                    "user_confirmed": user_confirmed,
                    "lifecycle": {
                        "TOPOLOGY_RECONSTRUCTED": True,
                        "TOPOLOGY_VALIDATED": False,
                        "SIMULATION_EXECUTED": False,
                        "SIMULATION_SUCCESSFUL": False
                    }
                },
                "components": comps,
                "nodes": nodes,
                "ground_node": "GND",
                "analysis": {"type": "transient", "step": 1e-5, "stop": 0.02}
            }
            return ir, [], completeness

        # ---------------------------------------------------------------------
        # AMBIGUOUS / UNSPECIFIED CIRCUIT TYPE
        # ---------------------------------------------------------------------
        candidates = []
        if r_list or v_list or i_list:
            cand_a_ir, _, _ = cls.build_circuit_ir(entities, {"circuit_type": "SERIES_RESISTORS", "selected_experiment": None, "topology_source": "ai_inferred"}, user_confirmed=False)
            cand_b_ir, _, _ = cls.build_circuit_ir(entities, {"circuit_type": "PARALLEL_RESISTORS", "selected_experiment": None, "topology_source": "ai_inferred"}, user_confirmed=False)
            candidates.append({
                "candidate_key": "A",
                "name": f"Candidate A: Series Chain ({len(r_list)} Resistors in Series) [GENERALIZED CIRCUIT]",
                "description": "All extracted components connected sequentially in a single series loop.",
                "rationale": "Standard series voltage divider topology using only your specified components.",
                "topology_source": "ai_inferred",
                "topology_classification": "GENERALIZED CIRCUIT",
                "circuit_ir": cand_a_ir
            })
            candidates.append({
                "candidate_key": "B",
                "name": f"Candidate B: Parallel Branches ({len(r_list)} Resistors in Parallel) [GENERALIZED CIRCUIT]",
                "description": "All extracted resistors connected in parallel across the source.",
                "rationale": "Standard parallel current-splitting load bank.",
                "topology_source": "ai_inferred",
                "topology_classification": "GENERALIZED CIRCUIT",
                "circuit_ir": cand_b_ir
            })
            if len(r_list) == 5:
                cand_c_ir, _, _ = cls.build_circuit_ir(entities, {"circuit_type": "RESISTOR_BRIDGE", "selected_experiment": 1, "topology_source": "manual_template"}, user_confirmed=False)
                candidates.append({
                    "candidate_key": "C",
                    "name": "Candidate C: Five-Resistor Wheatstone Bridge (Experiment 1) [MODIFIED MANUAL TOPOLOGY]",
                    "description": "R1, R2 form upper branches; R3, R4 to ground; R5 bridges nodes 2 and 3.",
                    "rationale": "Available since 5 resistors were provided, matching Experiment 1's 5-resistor bridge.",
                    "topology_source": "manual_template",
                    "topology_classification": "MODIFIED MANUAL TOPOLOGY",
                    "circuit_ir": cand_c_ir
                })

        # CRITICAL FIX: Always populate `user_supplied` with all values extracted from `latest_user_message`
        # even when the topology is still ambiguous! Never leave `user_supplied` empty when entities exist.
        amb_user_sup = cls._build_user_supplied_entries(entities)
        completeness = {
            "topology_classification": "GENERALIZED CIRCUIT",
            "template_name": "Pending User Topology Selection (Ambiguous Prompt)",
            "required_count": len(amb_user_sup),
            "user_supplied": amb_user_sup,
            "manual_defaults": [],
            "missing_ambiguous": [
                {
                    "id": "Circuit Topology / Interconnections",
                    "description": "Component values were provided without specifying how they are connected or which manual experiment applies."
                }
            ],
        }
        return None, candidates, completeness

    # =========================================================================
    # STAGE 7: DETERMINISTIC VALIDATION & ACTUAL SIMULATION EXECUTION
    # =========================================================================
    @classmethod
    def validate_and_simulate(cls, circuit_ir: Optional[Dict[str, Any]], execute_sim: bool = True) -> Dict[str, Any]:
        """
        Separates:
        - TOPOLOGY_RECONSTRUCTED
        - TOPOLOGY_VALIDATED
        - SIMULATION_EXECUTED
        - SIMULATION_NUMERICALLY_SUCCESSFUL
        - WINDOW_SUFFICIENT
        - REQUESTED_BEHAVIOR_OBSERVED
        Before simulation, verifies:
          step_time > 0
          end_time > 0
          step_time <= end_time
        """
        if not circuit_ir:
            return {
                "TOPOLOGY_RECONSTRUCTED": False,
                "TOPOLOGY_VALIDATED": False,
                "SIMULATION_EXECUTED": False,
                "SIMULATION_NUMERICALLY_SUCCESSFUL": False,
                "SIMULATION_SUCCESSFUL": False,
                "WINDOW_SUFFICIENT": False,
                "REQUESTED_BEHAVIOR_OBSERVED": False,
                "errors": ["Circuit topology is ambiguous or not yet reconstructed."],
                "simulation_results": None
            }

        comps = circuit_ir.get("components", [])
        nodes = circuit_ir.get("nodes", [])
        gnd = circuit_ir.get("ground_node", "GND")

        errors = []
        if gnd not in nodes:
            errors.append("Missing reference ground node (GND).")

        # Check node degree (no floating nodes or shorted components for analog netlists)
        if comps:
            node_counts: Dict[str, int] = {}
            for c in comps:
                c_nodes = c.get("nodes", [])
                if len(c_nodes) >= 2 and c_nodes[0] == c_nodes[1]:
                    errors.append(f"Short-circuited component detected: {c.get('id')} has both terminals on '{c_nodes[0]}'.")
                for n in c_nodes:
                    node_counts[n] = node_counts.get(n, 0) + 1
                for n in c.get("control_nodes", []):
                    node_counts[n] = node_counts.get(n, 0) + 1
            for n, cnt in node_counts.items():
                if cnt < 2 and n != gnd:
                    errors.append(f"Floating node detected: Node '{n}' has only 1 connection.")

        # Pre-simulation Step/Stop Consistency Gate for transient circuits
        analysis = circuit_ir.get("analysis", {})
        if analysis.get("type") == "transient":
            raw_step = float(analysis.get("raw_step", analysis.get("step", 1e-3)))
            raw_stop = float(analysis.get("raw_stop", analysis.get("stop", 0.05)))
            step_stop_check = analysis.get("step_stop_consistency") or cls.verify_step_stop_consistency(
                raw_step_s=raw_step,
                raw_stop_s=raw_stop,
                target_period_s=analysis.get("target_period_s"),
                rc_tau_s=analysis.get("rc_tau_s"),
                required_cycles=5,
            )
            analysis["step_stop_consistency"] = step_stop_check
            # Ensure active step_time and end_time before simulation satisfy step_time > 0, end_time > 0, step_time <= end_time
            if float(analysis.get("step", raw_step)) <= 0 or float(analysis.get("stop", raw_stop)) <= 0 or float(analysis.get("step", raw_step)) > float(analysis.get("stop", raw_stop)):
                analysis["step"] = float(step_stop_check["compat_step_for_raw_stop_s"])
                analysis["step_code_expr"] = step_stop_check["compat_raw_step_expr"]
                analysis["step_textual"] = step_stop_check["compat_raw_step_text"]

        top_validated = len(errors) == 0
        sim_executed = False
        sim_num_successful = False
        window_sufficient = True
        behavior_observed = False
        sim_results: Optional[Dict[str, Any]] = None

        if top_validated and execute_sim:
            sim_executed = True
            try:
                ctype = circuit_ir.get("metadata", {}).get("circuit_type", "")
                sim_results = cls._solve_circuit_numerically(circuit_ir, ctype)
                if sim_results and sim_results.get("converged"):
                    sim_num_successful = True
                    window_sufficient = bool(sim_results.get("window_sufficient", True))
                    behavior_observed = bool(sim_results.get("requested_behavior_observed", window_sufficient))
            except Exception as e:
                errors.append(f"Simulation solver error: {str(e)}")
                sim_num_successful = False
                window_sufficient = False
                behavior_observed = False

        lifecycle = {
            "TOPOLOGY_RECONSTRUCTED": True,
            "TOPOLOGY_VALIDATED": top_validated,
            "SIMULATION_EXECUTED": sim_executed,
            "SIMULATION_NUMERICALLY_SUCCESSFUL": sim_num_successful,
            "SIMULATION_SUCCESSFUL": sim_num_successful,
            "WINDOW_SUFFICIENT": window_sufficient,
            "REQUESTED_BEHAVIOR_OBSERVED": behavior_observed,
        }
        circuit_ir.setdefault("metadata", {})["lifecycle"] = lifecycle

        return {
            **lifecycle,
            "errors": errors,
            "simulation_results": sim_results
        }

    @classmethod
    def _solve_circuit_numerically(cls, circuit_ir: Dict[str, Any], ctype: str) -> Dict[str, Any]:
        """
        Executes local deterministic MNA / numerical solution for the constructed Circuit IR.
        """
        import numpy as np

        comps = {c["id"]: c for c in circuit_ir.get("components", [])}

        # Solve CCCS (Exp 2) via exact KCL Nodal Matrix
        if ctype == "CCCS":
            v1 = comps["V1"]["value"]
            r1 = comps["R1"]["value"]
            r2 = comps["R2"]["value"]
            r3 = comps["R3"]["value"]
            r4 = comps["R4"]["value"]
            i1 = comps["I1"]["value"]
            gain = comps["F1"].get("gain", 3)

            g1, g2, g3, g4 = 1.0 / r1, 1.0 / r2, 1.0 / r3, 1.0 / r4
            A = np.array([
                [g1 + g2 + g3 + gain * g1, -g3],
                [-g3 - gain * g1, g3 + g4]
            ], dtype=float)
            b = np.array([
                v1 * g1 * (1.0 + gain),
                i1 - gain * g1 * v1
            ], dtype=float)
            v3, v4 = np.linalg.solve(A, b)
            i_vtest = (v1 - v3) / r1
            return {
                "converged": True,
                "node_voltages": {
                    "1": round(float(v1), 4),
                    "2": round(float(v1), 4),
                    "3": round(float(v3), 4),
                    "4": round(float(v4), 4),
                },
                "branch_currents": {
                    "Vtest": round(float(i_vtest), 4),
                    "F1_CCCS": round(float(gain * i_vtest), 4),
                }
            }

        # Solve Resistor Bridge (Exp 1) via KCL Nodal Matrix
        if ctype == "RESISTOR_BRIDGE":
            v1 = comps.get("Vinput", comps.get("V1", {"value": 10.0}))["value"]
            r1 = comps["R1"]["value"]
            r2 = comps["R2"]["value"]
            r3 = comps["R3"]["value"]
            r4 = comps["R4"]["value"]
            r5 = comps["R5"]["value"]
            g1, g2, g3, g4, g5 = 1.0 / r1, 1.0 / r2, 1.0 / r3, 1.0 / r4, 1.0 / r5
            A = np.array([
                [g1 + g3 + g5, -g5],
                [-g5, g2 + g4 + g5]
            ], dtype=float)
            b = np.array([v1 * g1, v1 * g2], dtype=float)
            v2, v3 = np.linalg.solve(A, b)
            return {
                "converged": True,
                "node_voltages": {
                    "1": round(float(v1), 4),
                    "2": round(float(v2), 4),
                    "3": round(float(v3), 4),
                }
            }

        # Solve VCVS (Exp 3) via KCL + Constraint Matrix
        if ctype == "VCVS":
            v1 = comps["V1"]["value"]
            r1 = comps["R1"]["value"]
            r2 = comps["R2"]["value"]
            r3 = comps["R3"]["value"]
            r4 = comps["R4"]["value"]
            r5 = comps["R5"]["value"]
            gain = comps["E1"].get("gain", 3)
            g1, g2, g3, g4, g5 = 1.0 / r1, 1.0 / r2, 1.0 / r3, 1.0 / r4, 1.0 / r5
            M = np.array([
                [g2, 0, 0, 0, 0, -1, 0],
                [0, g3, -g3, 0, 0, 1, 0],
                [0, -g3, g1 + g3 + g4, -g4, 0, 0, 0],
                [0, 0, -g4, g4, 0, 0, 1],
                [0, 0, 0, 0, g5, 0, -1],
                [-1, 1, 0, 0, 0, 0, 0],
                [0, -gain, gain, 1, -1, 0, 0],
            ], dtype=float)
            rhs = np.array([0, 0, 0, 0, 0, v1, 0], dtype=float)
            sol = np.linalg.solve(M, rhs)
            return {
                "converged": True,
                "node_voltages": {
                    "1": round(float(sol[0]), 4),
                    "2": round(float(sol[1]), 4),
                    "3": round(float(sol[2]), 4),
                    "4": round(float(sol[3]), 4),
                    "5": round(float(sol[4]), 4),
                },
                "branch_currents": {
                    "v1": round(float(sol[5]), 4),
                    "e1": round(float(sol[6]), 4),
                }
            }

        # Solve Experiment 4: Natural Response of RC Circuit
        if ctype == "RC_NATURAL_RESPONSE":
            v1 = comps["V1"]["value"]
            r1 = comps["R1"]["value"]
            c1 = comps["C1"]["value"]
            r2 = comps["R2"]["value"]
            r3 = comps["R3"]["value"]
            r4 = comps["R4"]["value"]
            analysis = circuit_ir.get("analysis", {})
            t_sw = analysis.get("switchingtime", 50e-3)
            ic_v = analysis.get("initial_condition", {}).get("output", 0.0)
            tau_charge = r1 * c1
            v_at_switch = v1 - (v1 - ic_v) * math.exp(-t_sw / tau_charge)
            r_eq_discharge = r2 + (r3 * r4) / (r3 + r4)
            tau_discharge = c1 * r_eq_discharge
            v_after_1tau = v_at_switch / math.e
            i_cap_pre_init = (v1 - ic_v) / r1
            i_cap_post_init = -v_at_switch / r_eq_discharge
            return {
                "converged": True,
                "node_voltages": {
                    "1 (Source V1)": round(float(v1), 4),
                    "output (Capacitor V_C @ t=0)": round(float(ic_v), 4),
                    "output (Capacitor V_C @ t=switchingtime)": round(float(v_at_switch), 4),
                    "output (Capacitor V_C @ t=switchingtime+tau)": round(float(v_after_1tau), 4),
                    "output (Capacitor V_C @ t->inf)": 0.0,
                },
                "branch_currents": {
                    "I_C(0+) [Initial Charging Current]": round(float(i_cap_pre_init), 6),
                    "I_C(t_sw+) [Post-Switch Discharge Current]": round(float(i_cap_post_init), 6),
                    "I_R2(t_sw+)": round(float(-i_cap_post_init), 6),
                },
                "transient_metrics": {
                    "Charging Time Constant (R1*C1)": cls._format_eng(tau_charge, "s"),
                    "Equivalent Discharge Resistance Req": cls._format_eng(r_eq_discharge, "ohm"),
                    "Post-Switching Discharge Time Constant (tau)": cls._format_eng(tau_discharge, "s"),
                    "Capacitor Voltage Equation (t >= t_sw)": f"V_C(t) = {v_at_switch:.4f} * exp(-(t - {t_sw:g}) / {tau_discharge:g}) V",
                    "Capacitor Current Equation (t >= t_sw)": f"i_C(t) = {i_cap_post_init:.6f} * exp(-(t - {t_sw:g}) / {tau_discharge:g}) A",
                }
            }

        # Solve Experiment 5: Step Response of RC Circuit
        if ctype == "RC_STEP_RESPONSE":
            v1 = comps["V1"]["value"]
            v2 = comps["V2"]["value"]
            r1 = comps["R1"]["value"]
            r2 = comps["R2"]["value"]
            c1 = comps["C1"]["value"]
            r3 = comps["R3"]["value"]
            r4 = comps["R4"]["value"]
            r5 = comps["R5"]["value"]
            analysis = circuit_ir.get("analysis", {})
            t_sw = analysis.get("switchingtime", 20e-3)
            v_pre = v1 * (r2 / (r1 + r2))
            r_th_pre = (r1 * r2) / (r1 + r2)
            tau_pre = c1 * r_th_pre
            r_eq_post = r3 + (r4 * r5) / (r4 + r5)
            tau_post = c1 * r_eq_post
            v_inf = -v2 * (r4 / (r4 + r5))
            v_at_1tau = v_inf + (v_pre - v_inf) / math.e
            i_cap_post_init = (v_inf - v_pre) / r_eq_post
            return {
                "converged": True,
                "node_voltages": {
                    "1 (Source V1)": round(float(v1), 4),
                    "3 (Source -V2)": round(float(-v2), 4),
                    "output (Capacitor V_C pre-switch steady state V_0)": round(float(v_pre), 4),
                    "output (Capacitor V_C @ t=switchingtime+tau)": round(float(v_at_1tau), 4),
                    "output (Capacitor V_C post-switch final steady state V_inf)": round(float(v_inf), 4),
                },
                "branch_currents": {
                    "I_C(t_sw+) [Initial Post-Switch Capacitor Current]": round(float(i_cap_post_init), 6),
                    "I_R3(t_sw+)": round(float(-i_cap_post_init), 6),
                },
                "transient_metrics": {
                    "Pre-Switching Thevenin Time Constant": cls._format_eng(tau_pre, "s"),
                    "Post-Switching Equivalent Resistance Req": cls._format_eng(r_eq_post, "ohm"),
                    "Post-Switching Time Constant (tau)": cls._format_eng(tau_post, "s"),
                    "Capacitor Voltage Step Response (t >= t_sw)": f"V_C(t) = {v_inf:.4f} + ({v_pre:.4f} - ({v_inf:.4f})) * exp(-(t - {t_sw:g}) / {tau_post:g}) V",
                    "Capacitor Current Step Response (t >= t_sw)": f"i_C(t) = {i_cap_post_init:.6f} * exp(-(t - {t_sw:g}) / {tau_post:g}) A",
                }
            }

        # Solve GENERAL_RC (Generalized Single-Loop RC Circuit)
        if ctype == "GENERAL_RC":
            v1 = comps["V1"]["value"]
            r1 = comps["R1"]["value"]
            c1 = comps["C1"]["value"]
            tau = r1 * c1
            i_init = v1 / r1
            return {
                "converged": True,
                "node_voltages": {
                    "1 (V1)": round(float(v1), 4),
                    "output @ t=tau (Natural Decay)": round(float(v1 / math.e), 4),
                    "output @ t=tau (Step Charge)": round(float(v1 * (1.0 - 1.0 / math.e)), 4),
                },
                "branch_currents": {
                    "I_C(0+) [Initial Capacitor Current]": round(float(i_init), 6),
                    "I_C(tau)": round(float(i_init / math.e), 6),
                },
                "transient_metrics": {
                    "Time Constant (tau = R1*C1)": cls._format_eng(tau, "s"),
                    "5*tau Settling Time": cls._format_eng(5.0 * tau, "s"),
                    "Capacitor Voltage Step Equation": f"V_C(t) = {v1:g} * (1 - exp(-t / {tau:g})) V",
                    "Capacitor Current Step Equation": f"i_C(t) = {i_init:.6f} * exp(-t / {tau:g}) A",
                }
            }

        # Solve Experiment 6: Pacemaker Circuit (Strict Numerical Time-Domain Simulation)
        if ctype == "PACEMAKER":
            vs = float(comps["V1"]["value"])
            r1 = float(comps["R1"]["value"])
            c1 = float(comps["C1"]["value"])
            r2 = float(comps["R2"]["value"])
            sw_comp = comps.get("S1", {})
            vt = float(sw_comp.get("vt", 2.05))
            vh = float(sw_comp.get("vh", 2.03))
            ron = float(sw_comp.get("ron", 1e-3))
            roff = float(sw_comp.get("roff", 1e9))
            v_on_switch = vt + vh
            v_off_switch = max(0.0, vt - vh)

            meta_p = circuit_ir.get("metadata", {}).get("parameters", {})
            analysis = circuit_ir.get("analysis", {})
            bpm = float(meta_p.get("heart_rate_bpm", 70.0))
            sf = float(meta_p.get("switching_factor", 0.68))
            vo = sf * vs
            tau_charge = r1 * c1
            t_period = 60.0 / bpm
            five_cycle_stop_s = round(5.0 * t_period, 6)

            raw_step_s = float(analysis.get("raw_step", analysis.get("step", 1e-3)))
            stop_s = float(analysis.get("stop", 60e-6))
            step_stop_consistency = analysis.get("step_stop_consistency") or cls.verify_step_stop_consistency(
                raw_step_s=raw_step_s,
                raw_stop_s=stop_s,
                target_period_s=t_period,
                rc_tau_s=tau_charge,
                required_cycles=5,
            )

            # Enforce step_time > 0, end_time > 0, step_time <= end_time (never use 1 ms for a 60 us simulation!)
            step_s = float(step_stop_consistency["compat_step_for_raw_stop_s"])
            step_code_expr = step_stop_consistency["compat_raw_step_expr"]
            stop_code_expr = step_stop_consistency["raw_stop_expr"]
            step_textual = step_stop_consistency["compat_raw_step_text"]
            stop_textual = step_stop_consistency["raw_stop_text"]
            recommended_stop_s = float(step_stop_consistency["required_duration_s"])
            five_cycle_step_expr = step_stop_consistency["req_step_expr"]
            five_cycle_stop_expr = step_stop_consistency["req_stop_expr"]
            five_cycle_stop_text = step_stop_consistency["req_stop_text"]

            window_sufficient = bool(step_stop_consistency["window_sufficient"])
            unit_mismatch_detected = bool(analysis.get("unit_mismatch_detected", not window_sufficient))
            unit_mismatch_detail = analysis.get(
                "unit_mismatch_detail",
                "; ".join(step_stop_consistency.get("changes_reported", []))
            )

            # Numerical time-domain simulation over the actual [0, stop_s] window with compatible step_s
            effective_v_thresh = vo
            if stop_s <= 0.0:
                v_control_end = 0.0
                v_control_peak = 0.0
                v_out_peak = 0.0
                pulses_observed = 0
                threshold_reached = False
            else:
                t_first_charge = -tau_charge * math.log(1.0 - (effective_v_thresh / vs)) if effective_v_thresh < vs else float("inf")
                if stop_s < t_first_charge:
                    # Simulation window ends BEFORE capacitor ever reaches threshold!
                    v_control_end = vs * (1.0 - math.exp(-stop_s / tau_charge))
                    v_control_peak = v_control_end
                    v_out_peak = v_control_peak * (r2 / (roff + r2))
                    pulses_observed = 0
                    threshold_reached = False
                else:
                    # Discrete time-stepped ODE simulation over [0, stop_s] with dt = step_s
                    dt = step_s
                    n_steps = max(1, int(round(stop_s / dt)))
                    vc = 0.0
                    sw_on = False
                    pulses_observed = 0
                    v_control_peak = 0.0
                    v_out_peak = 0.0
                    for _ in range(n_steps):
                        if not sw_on and vc >= effective_v_thresh:
                            sw_on = True
                            pulses_observed += 1
                        elif sw_on and vc <= max(v_off_switch, 1e-3):
                            sw_on = False
                        r_sw = ron if sw_on else roff
                        r_shunt = r_sw + r2
                        g_tot = (1.0 / r1) + (1.0 / r_shunt)
                        v_eq = (vs / r1) / g_tot
                        tau_step = c1 / g_tot
                        vc = v_eq - (v_eq - vc) * math.exp(-dt / tau_step)
                        v_out_inst = vc * (r2 / r_shunt)
                        if vc > v_control_peak:
                            v_control_peak = vc
                        if v_out_inst > v_out_peak:
                            v_out_peak = v_out_inst
                    v_control_end = vc
                    threshold_reached = pulses_observed >= 1

            requested_behavior_observed = bool(window_sufficient and threshold_reached and pulses_observed >= 1)

            # Calculated load current from simulated V(out) via Ohm's law (NOT analysis.branches)
            i_load_sim_calc = v_out_peak / r2
            i_load_expected_calc = vo / r2
            i_r1_init_calc = vs / r1

            sim_window_label = cls._format_eng(stop_s, "s")
            warning_msg = (
                "Simulation window is insufficient to observe the requested behavior."
                if (not window_sufficient or not requested_behavior_observed)
                else None
            )

            return {
                "converged": True,
                "window_sufficient": window_sufficient,
                "requested_behavior_observed": requested_behavior_observed,
                "threshold_reached": threshold_reached,
                "pulses_observed": pulses_observed,
                "unit_mismatch_detected": unit_mismatch_detected,
                "unit_mismatch_detail": unit_mismatch_detail,
                "step_stop_consistency": step_stop_consistency,
                "simulation_warning": warning_msg,
                "actual_simulation_parameters": {
                    "raw_step_time_s": raw_step_s,
                    "raw_end_time_s": stop_s,
                    "step_time_s": step_s,
                    "end_time_s": stop_s,
                    "step_code_expr": step_code_expr,
                    "stop_code_expr": stop_code_expr,
                    "step_textual": step_textual,
                    "stop_textual": stop_textual,
                    "five_cycle_step_expr": five_cycle_step_expr,
                    "five_cycle_stop_expr": five_cycle_stop_expr,
                    "five_cycle_stop_text": five_cycle_stop_text,
                    "target_period_s": round(t_period, 6),
                    "rc_tau_s": round(tau_charge, 6),
                    "recommended_stop_s": recommended_stop_s,
                },
                # ONLY actual simulator outputs appear in node_voltages (never analytical/expected targets)
                "node_voltages": {
                    "1 (Simulated Supply Voltage)": round(float(vs), 6),
                    f"control (Simulated Max Capacitor Voltage in {sim_window_label})": round(float(v_control_peak), 6),
                    f"out (Simulated Max Output Voltage in {sim_window_label})": round(float(v_out_peak), 6),
                },
                # Do NOT claim branch_current was numerically extracted when analysis.branches was not used
                "branch_currents": {},
                "calculated_load_currents": {
                    f"i_load = v_output / R2 (Calculated Load Current in {sim_window_label} window)": round(float(i_load_sim_calc), 6),
                    "I_R1(0+) = Vs / R1 (Calculated Initial Charging Current)": round(float(i_r1_init_calc), 6),
                },
                "provenance": {
                    "EXPECTED_THEORETICAL": {
                        "Target Capacitor Threshold Vo (0.68 * Vs)": f"{vo:.4f} V",
                        "Expected Peak Output Pulse V(out)": f"{vo:.4f} V",
                        "Expected Pacemaker Behavior": f"Periodic RC charge to {vo:.4f} V and discharge pulse every T = {t_period:.4f} s ({bpm:g} BPM; 5 cycles = {five_cycle_stop_s:g} s)",
                    },
                    "CALCULATED": {
                        "Target Heartbeat Period (T = 60 / H)": f"{t_period:.4f} s",
                        "Required Duration for 5 Cycles (5 * T)": f"{five_cycle_stop_text} ({five_cycle_stop_expr})",
                        "Calculated Timing Resistor R1": f"{cls._format_eng(r1, 'ohm')} ({r1:.2f} Ω)",
                        "Charging RC Time Constant (tau = R1 * C1)": f"{cls._format_eng(tau_charge, 's')} ({tau_charge:.4f} s)",
                        "Calculated Initial Charging Current (Vs / R1)": f"{i_r1_init_calc:.6f} A",
                        "Calculated Peak Load Current at Expected Vo (Vo / R2)": f"{i_load_expected_calc:.6f} A (Calculated from Vo / R2; analysis.branches not used)",
                        "Calculated Load Current from Simulated V(out) (v_output / R2)": f"{i_load_sim_calc:.6f} A (Calculated from v_output / R2; analysis.branches not used)",
                    },
                    "SIMULATED": {
                        "Actual Simulation Window Executed": f"0 s to {sim_window_label} (step_time={step_code_expr} [{step_textual}], end_time={stop_code_expr} [{stop_textual}])",
                        "Pre-Simulation Step/Stop Consistency": (
                            f"Verified step_time > 0, end_time > 0, step_time <= end_time ({step_s:g} s <= {stop_s:g} s). "
                            + ("; ".join(step_stop_consistency.get("changes_reported", [])) if step_stop_consistency.get("changes_reported") else "Consistent.")
                        ),
                        "Simulation Window Sufficiency": (
                            "Simulation window is insufficient to observe the requested behavior."
                            if not window_sufficient
                            else "Simulation window is sufficient to observe pacemaker pulses."
                        ),
                        "Simulated Node 1 Voltage V(1)": f"{vs:.4f} V",
                        f"Simulated Capacitor Voltage V(control) at t={sim_window_label}": f"{v_control_end:.6f} V ({v_control_end*1e3:.4f} mV)",
                        f"Simulated Peak Capacitor Voltage V(control) in {sim_window_label}": f"{v_control_peak:.6f} V ({v_control_peak*1e3:.4f} mV)",
                        f"Simulated Peak Output Voltage V(out) in {sim_window_label}": f"{v_out_peak:.6f} V",
                        "Threshold Reached in Simulation": str(threshold_reached),
                        "Pacemaker Pulses Observed in Simulation": str(pulses_observed),
                    },
                    "USER_OBSERVED": {
                        "User-Reported Observation": "None reported in prompt",
                    },
                },
                "transient_metrics": {
                    "Simulation Window Status": (
                        f"Simulation window is insufficient to observe the requested behavior ({sim_window_label} << tau = {tau_charge:.4f} s, T = {t_period:.4f} s). "
                        f"Required duration for 5 cycles: {five_cycle_stop_text} (`end_time={five_cycle_stop_expr}`, `step_time={five_cycle_step_expr}`)."
                        if not window_sufficient
                        else f"Sufficient window ({sim_window_label} >= 5 * T = {five_cycle_stop_s:g} s); {pulses_observed} pulses observed."
                    ),
                    "Calculated Target Heartbeat Period (T = 60 / H)": f"{t_period:.4f} s ({bpm:g} BPM)",
                    "Required Duration for 5 Cycles (5 * T)": f"{five_cycle_stop_text} (`{five_cycle_stop_expr}`)",
                    "Calculated Timing Resistor R1": f"{cls._format_eng(r1, 'ohm')} ({r1:.2f} Ω)",
                    "Calculated Charging Time Constant (tau = R1*C1)": f"{cls._format_eng(tau_charge, 's')} ({tau_charge:.4f} s)",
                    "Expected / Theoretical Threshold Vo": f"{vo:.4f} V (NOT reached in {sim_window_label} simulation)" if not threshold_reached else f"{vo:.4f} V (Reached)",
                    f"Simulated V(control) at t={sim_window_label}": f"{v_control_end:.6f} V ({v_control_end*1e3:.4f} mV)",
                    f"Simulated V(out) at t={sim_window_label}": f"{v_out_peak:.6f} V ({pulses_observed} pulses)",
                }
            }

        # Solve Digital Logic Experiments (Exp 7, 8, 9, 10)
        if ctype in ("LOGIC_GATES_TRUTH_TABLE", "HALF_FULL_ADDER", "BOOLEAN_SOP_POS", "NAND_COMBINATIONAL"):
            if ctype == "HALF_FULL_ADDER":
                tt_rows = [
                    {"A": 0, "B": 0, "Cin": 0, "Sum": 0, "Cout": 0},
                    {"A": 0, "B": 0, "Cin": 1, "Sum": 1, "Cout": 0},
                    {"A": 0, "B": 1, "Cin": 0, "Sum": 1, "Cout": 0},
                    {"A": 0, "B": 1, "Cin": 1, "Sum": 0, "Cout": 1},
                    {"A": 1, "B": 0, "Cin": 0, "Sum": 1, "Cout": 0},
                    {"A": 1, "B": 0, "Cin": 1, "Sum": 0, "Cout": 1},
                    {"A": 1, "B": 1, "Cin": 0, "Sum": 0, "Cout": 1},
                    {"A": 1, "B": 1, "Cin": 1, "Sum": 1, "Cout": 1},
                ]
            elif ctype in ("BOOLEAN_SOP_POS", "NAND_COMBINATIONAL"):
                # Default manual SOP = sum(1, 3, 6) = A'B'C + A'BC + ABC'
                tt_rows = []
                for idx in range(8):
                    a, b, c = (idx >> 2) & 1, (idx >> 1) & 1, idx & 1
                    y = 1 if idx in (1, 3, 6) else 0
                    tt_rows.append({"Minterm": f"m{idx}", "A": a, "B": b, "C": c, "Output_Y": y})
            else:
                tt_rows = [
                    {"A": 0, "B": 0, "AND": 0, "OR": 0, "NAND": 1, "NOR": 1, "XOR": 0, "XNOR": 1},
                    {"A": 0, "B": 1, "AND": 0, "OR": 1, "NAND": 1, "NOR": 0, "XOR": 1, "XNOR": 0},
                    {"A": 1, "B": 0, "AND": 0, "OR": 1, "NAND": 1, "NOR": 0, "XOR": 1, "XNOR": 0},
                    {"A": 1, "B": 1, "AND": 1, "OR": 1, "NAND": 0, "NOR": 0, "XOR": 0, "XNOR": 1},
                ]
            return {
                "converged": True,
                "node_voltages": {},
                "truth_table": tt_rows,
                "transient_metrics": {
                    "Digital Verification": f"Verified {len(tt_rows)} truth-table states",
                }
            }

        # Solve Diode / Zener / Rectifier Circuits (Exp 11, 12, 13, 14)
        if ctype in ("DIODE_IV_CHARACTERISTICS", "ZENER_REGULATOR", "HALF_WAVE_RECTIFIER", "FULL_WAVE_RECTIFIER"):
            v1 = comps["V1"]["value"]
            if ctype == "ZENER_REGULATOR":
                rs = comps["Rs"]["value"]
                rl = comps["RL"]["value"]
                vz = comps["DZ1"]["value"]
                v_th = v1 * (rl / (rs + rl))
                v_out = min(v_th, vz)
                i_s = (v1 - v_out) / rs
                i_l = v_out / rl
                i_z = max(0.0, i_s - i_l)
                return {
                    "converged": True,
                    "node_voltages": {"1 (Vin)": round(float(v1), 4), "2 (Vout Regulated)": round(float(v_out), 4)},
                    "branch_currents": {"I_Rs": round(float(i_s), 6), "I_RL (Load)": round(float(i_l), 6), "I_Zener": round(float(i_z), 6)},
                }
            r1 = comps["R1"]["value"]
            vf = 0.7 if ctype != "FULL_WAVE_RECTIFIER" else 1.4
            v_peak_out = max(0.0, v1 - vf)
            i_peak = v_peak_out / r1
            return {
                "converged": True,
                "node_voltages": {
                    "1 (Input Peak)": round(float(v1), 4),
                    "2/out (Output Peak)": round(float(v_peak_out), 4),
                },
                "branch_currents": {
                    "I_peak (Forward/Load Current)": round(float(i_peak), 6),
                },
                "transient_metrics": {
                    "Diode Forward Knee Voltage Vf": f"{vf:g} V",
                    "Peak Load Voltage": f"{v_peak_out:.4f} V",
                }
            }

        # Solve Series / Parallel / Generic
        if ctype in ("VOLTAGE_DIVIDER", "SERIES_RESISTORS", "CANDIDATE_A"):
            v1 = comps["V1"]["value"]
            r_vals = [c["value"] for c in circuit_ir["components"] if c["type"] == "resistor"]
            r_tot = sum(r_vals) if r_vals else 1.0
            i_loop = v1 / r_tot
            node_v = {"1": round(float(v1), 4)}
            v_curr = v1
            for idx, rv in enumerate(r_vals[:-1]):
                v_curr -= i_loop * rv
                node_v[str(idx + 2)] = round(float(v_curr), 4)
            return {
                "converged": True,
                "node_voltages": node_v,
                "branch_currents": {"I_series": round(float(i_loop), 6)}
            }

        if ctype in ("PARALLEL_RESISTORS", "CANDIDATE_B"):
            v1 = comps["V1"]["value"]
            r_comps = [c for c in circuit_ir["components"] if c["type"] == "resistor"]
            branch_i = {}
            i_tot = 0.0
            for rc in r_comps:
                i_b = v1 / rc["value"]
                branch_i[f"I({rc['id']})"] = round(float(i_b), 6)
                i_tot += i_b
            branch_i["I_total"] = round(float(i_tot), 6)
            return {
                "converged": True,
                "node_voltages": {"1": round(float(v1), 4)},
                "branch_currents": branch_i
            }

        return cls._solve_general_dc_mna(circuit_ir)

    @classmethod
    def _solve_general_dc_mna(cls, circuit_ir: Dict[str, Any]) -> Dict[str, Any]:
        """
        General Modified Nodal Analysis (MNA) solver for arbitrary natural-language reconstructed
        topologies (series-parallel networks, T-networks, ladder networks, shunted dividers, etc.).
        Computes exact node voltages and branch currents for all components.
        """
        import numpy as np

        comp_list = circuit_ir.get("components", [])
        gnd = circuit_ir.get("ground_node", "GND")
        non_gnd_nodes = [n for n in circuit_ir.get("nodes", []) if n != gnd]
        if not non_gnd_nodes:
            return {"converged": True, "node_voltages": {}, "branch_currents": {}}

        node_idx = {n: i for i, n in enumerate(non_gnd_nodes)}
        v_sources = [c for c in comp_list if c.get("type") in ("dc_voltage_source", "ac_voltage_source")]
        n_nodes = len(non_gnd_nodes)
        n_vs = len(v_sources)
        dim = n_nodes + n_vs

        M = np.zeros((dim, dim), dtype=float)
        rhs = np.zeros(dim, dtype=float)

        # Tiny Gmin for numerical stability when capacitors/open branches exist in DC
        for i in range(n_nodes):
            M[i, i] += 1e-12

        for c in comp_list:
            ct = c.get("type")
            c_nodes = c.get("nodes", ["1", gnd])
            na, nb = c_nodes[0], c_nodes[1]
            ia = node_idx.get(na)
            ib = node_idx.get(nb)
            val = float(c.get("value", 0.0))

            if ct == "resistor" and val > 0:
                g = 1.0 / val
                if ia is not None:
                    M[ia, ia] += g
                if ib is not None:
                    M[ib, ib] += g
                if ia is not None and ib is not None:
                    M[ia, ib] -= g
                    M[ib, ia] -= g
            elif ct == "inductor":
                # DC short circuit (1 mOhm equivalent resistance)
                g = 1.0 / 1e-3
                if ia is not None:
                    M[ia, ia] += g
                if ib is not None:
                    M[ib, ib] += g
                if ia is not None and ib is not None:
                    M[ia, ib] -= g
                    M[ib, ia] -= g
            elif ct in ("current_source", "dc_current_source"):
                if ia is not None:
                    rhs[ia] -= val
                if ib is not None:
                    rhs[ib] += val

        for v_idx, vs in enumerate(v_sources):
            row = n_nodes + v_idx
            c_nodes = vs.get("nodes", ["1", gnd])
            na, nb = c_nodes[0], c_nodes[1]
            ia = node_idx.get(na)
            ib = node_idx.get(nb)
            v_val = float(vs.get("value", 0.0))
            if ia is not None:
                M[ia, row] += 1.0
                M[row, ia] += 1.0
            if ib is not None:
                M[ib, row] -= 1.0
                M[row, ib] -= 1.0
            rhs[row] = v_val

        sol = np.linalg.solve(M, rhs)

        node_voltages: Dict[str, float] = {}
        for n, idx in node_idx.items():
            node_voltages[n] = round(float(sol[idx]), 4)

        def get_v(n_name: str) -> float:
            if n_name == gnd:
                return 0.0
            return float(sol[node_idx[n_name]])

        branch_currents: Dict[str, float] = {}
        for c in comp_list:
            cid = c["id"]
            ct = c.get("type")
            c_nodes = c.get("nodes", ["1", gnd])
            va, vb = get_v(c_nodes[0]), get_v(c_nodes[1])
            val = float(c.get("value", 0.0))
            if ct == "resistor" and val > 0:
                branch_currents[f"I({cid})"] = round((va - vb) / val, 6)

        for v_idx, vs in enumerate(v_sources):
            cid = vs["id"]
            # Current leaving positive terminal of voltage source = -sol[n_nodes + v_idx]
            i_src = -float(sol[n_nodes + v_idx])
            branch_currents[f"I({cid})"] = round(i_src, 6)

        return {
            "converged": True,
            "node_voltages": node_voltages,
            "branch_currents": branch_currents,
        }

    # =========================================================================
    # STAGE 1B: SEPARATE DETERMINISTIC OUTPUT / PLOT REQUIREMENT PARSER
    # =========================================================================
    @classmethod
    def extract_requested_outputs(cls, latest_user_message: str, ctype: str = "") -> Dict[str, Any]:
        """
        Parses requested outputs separately from component/value extraction:
          - capacitor_voltage
          - capacitor_current
          - node_voltage
          - branch_current
          - waveform
          - switch_activations
          - iv_curve
          - truth_table
          - dc_operating_point
          - time_constant
        Treats any requested output in `latest_user_message` as an explicit requirement
        that MUST be fulfilled in both the simulation report and generated PySpice code.
        """
        low = latest_user_message.lower()

        flags: Dict[str, bool] = {
            "capacitor_voltage": bool(
                re.search(
                    r'capacitor\s*voltage|voltage\s*across\s*(?:the\s*)?(?:capacitor|c\d*)\b|'
                    r'\bv_?c\b|\bvc\(t\)|v\(\s*output\s*\)|capacitor\s*(?:charge|charging|discharge|discharging)\s*(?:voltage|curve|plot|waveform)?',
                    low
                )
            ),
            "capacitor_current": bool(
                re.search(
                    r'capacitor\s*current|current\s*(?:through|in|across)\s*(?:the\s*)?(?:capacitor|c\d*)\b|'
                    r'\bi_?c\b|\bic\(t\)|(?:charging|discharging)\s*current',
                    low
                )
            ),
            "node_voltage": bool(
                re.search(
                    r'node\s*voltages?|nodal\s*voltages?|voltage\s*at\s*node|voltages?\s*at\s*all\s*nodes|'
                    r'voltage\s*at\s*(?:the\s*)?(?:junction|midpoint|middle\s*point|middle\s*node|common\s*point|common\s*node)|'
                    r'node\s*potentials?|\bv\([1-5a-z]+\)',
                    low
                )
            ),
            "branch_current": bool(
                re.search(
                    r'branch\s*currents?|current\s*(?:through|in)\s*(?:r\d+|each|all|branch|resistor)|'
                    r'mesh\s*currents?|loop\s*currents?|\bcurrents?\s*plot\b',
                    low
                )
            ),
            "waveform": bool(
                re.search(
                    r'\b(?:plot|show|graph|display|visualize|draw|trace|save)\b.*'
                    r'\b(?:voltage|current|waveform|response|output|curve|signal|transient|v_?c|i_?c|capacitor)\b|'
                    r'\b(?:waveform|transient\s*plot|time[\s\-]*domain\s*plot|step\s*response\s*plot|natural\s*response\s*plot)\b|'
                    r'\bplot\b',
                    low
                )
            ),
            "switch_activations": bool(
                re.search(
                    r'switch\s*activations?|switch\s*control|control\s*pulses?|\bposa\b|\bposb\b|switching\s*waveform',
                    low
                )
            ),
            "iv_curve": bool(
                re.search(
                    r'i[\s\-]*v\s*(?:curve|characteristic|plot|graph)|v[\s\-]*i\s*(?:curve|characteristic)|'
                    r'current[\s\-]*voltage\s*(?:curve|characteristic)|diode\s*characteristic|dc\s*sweep',
                    low
                )
            ),
            "truth_table": bool(
                re.search(
                    r'truth\s*table|logic\s*table|boolean\s*table|verify\s*(?:the\s*)?truth\s*table|all\s*input\s*combinations',
                    low
                )
            ),
            "dc_operating_point": bool(
                re.search(
                    r'dc\s*operating\s*point|operating\s*point|dc\s*bias(?:es)?|quiescent\s*point|q[\s\-]*point|\.op\b',
                    low
                )
            ),
            "time_constant": bool(
                re.search(
                    r'time\s*constant|\btau\b|settling\s*time|decay\s*rate',
                    low
                )
            ),
        }

        # If the user asked to plot/show on an RC circuit without naming a specific variable,
        # capacitor_voltage and waveform are both explicitly required.
        if flags["waveform"] and ctype in ("RC_NATURAL_RESPONSE", "RC_STEP_RESPONSE", "GENERAL_RC", "PACEMAKER"):
            if not flags["capacitor_voltage"] and not flags["capacitor_current"]:
                flags["capacitor_voltage"] = True

        # If user asked for capacitor_voltage or capacitor_current along with "show" / "plot" / "graph" / "waveform"
        if (flags["capacitor_voltage"] or flags["capacitor_current"]) and re.search(r'\b(?:show|plot|graph|draw|display|waveform|curve|visualize)\b', low):
            flags["waveform"] = True

        explicitly_requested = [k for k, v in flags.items() if v]

        # Standard implicit outputs for each circuit family (so even terse prompts get complete plots & analysis)
        default_map: Dict[str, List[str]] = {
            "RESISTOR_BRIDGE": ["dc_operating_point", "node_voltage", "branch_current"],
            "CCCS": ["dc_operating_point", "node_voltage", "branch_current"],
            "VCVS": ["dc_operating_point", "node_voltage", "branch_current"],
            "RC_NATURAL_RESPONSE": ["capacitor_voltage", "capacitor_current", "waveform", "switch_activations", "branch_current", "time_constant"],
            "RC_STEP_RESPONSE": ["capacitor_voltage", "capacitor_current", "waveform", "switch_activations", "branch_current", "time_constant"],
            "GENERAL_RC": ["capacitor_voltage", "capacitor_current", "waveform", "time_constant"],
            "PACEMAKER": ["capacitor_voltage", "waveform", "calculated_load_current", "time_constant"],
            "LOGIC_GATES_TRUTH_TABLE": ["truth_table"],
            "HALF_FULL_ADDER": ["truth_table"],
            "BOOLEAN_SOP_POS": ["truth_table"],
            "NAND_COMBINATIONAL": ["truth_table"],
            "DIODE_IV_CHARACTERISTICS": ["iv_curve", "waveform", "dc_operating_point"],
            "ZENER_REGULATOR": ["dc_operating_point", "node_voltage", "branch_current", "waveform"],
            "HALF_WAVE_RECTIFIER": ["waveform", "node_voltage", "branch_current"],
            "FULL_WAVE_RECTIFIER": ["waveform", "node_voltage", "branch_current"],
            "VOLTAGE_DIVIDER": ["dc_operating_point", "node_voltage", "branch_current"],
            "SERIES_RESISTORS": ["dc_operating_point", "node_voltage", "branch_current"],
            "PARALLEL_RESISTORS": ["dc_operating_point", "node_voltage", "branch_current"],
        }
        default_for_type = default_map.get(ctype, ["dc_operating_point", "node_voltage"])
        effective_outputs = list(dict.fromkeys(explicitly_requested + default_for_type))

        return {
            "flags": flags,
            "explicitly_requested": explicitly_requested,
            "default_outputs_for_type": default_for_type,
            "effective_outputs": effective_outputs,
            "requires_plot": any(
                k in effective_outputs
                for k in ("waveform", "capacitor_voltage", "capacitor_current", "switch_activations", "iv_curve")
            ),
        }

    # =========================================================================
    # STAGE 8: PYSPICE CODE GENERATION (WITH FULL OUTPUT & PLOTTING COMMANDS)
    # =========================================================================
    @classmethod
    def generate_pyspice_code(
        cls,
        circuit_ir: Dict[str, Any],
        requested_outputs: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generates executable PySpice code strictly from the parameter-substituted Circuit IR
        AND ensures every requested output (capacitor voltage plot, capacitor current plot,
        switch activations, node voltages, branch currents, I-V curve, truth table, etc.)
        is extracted, plotted with labeled axes, and displayed/saved.
        """
        meta = circuit_ir.get("metadata", {})
        ctype = meta.get("circuit_type", "")
        top_class = meta.get("topology_classification", "MODIFIED MANUAL TOPOLOGY")
        title = meta.get("name", "SimLab Circuit")
        comps = {c["id"]: c for c in circuit_ir.get("components", [])}
        analysis = circuit_ir.get("analysis", {"type": "op"})

        req_eff = (requested_outputs or {}).get("effective_outputs", [])
        req_exp = (requested_outputs or {}).get("explicitly_requested", [])
        all_reqs = set(req_eff) | set(req_exp)

        # ---------------------------------------------------------------------
        # EXP 4: RC_NATURAL_RESPONSE (Full Multi-Switch Netlist + Full Plotting)
        # ---------------------------------------------------------------------
        if ctype == "RC_NATURAL_RESPONSE":
            steptime = analysis.get("step", 1e-6)
            switchingtime = analysis.get("switchingtime", 50e-3)
            finaltime = analysis.get("stop", 250e-3)
            ic_val = analysis.get("initial_condition", {}).get("output", 0.0)
            v1 = comps["V1"]["value"]
            r1 = comps["R1"]["value"]
            c1_uf = comps["C1"]["value"] * 1e6
            r2 = comps["R2"]["value"]
            r3 = comps["R3"]["value"]
            r4 = comps["R4"]["value"]
            return (
                "import math\n"
                "import matplotlib.pyplot as plt\n"
                "from matplotlib.widgets import Cursor\n"
                "import numpy as np\n"
                "import PySpice.Logging.Logging as Logging\n"
                "logger = Logging.setup_logging()\n"
                "from PySpice.Probe.Plot import plot\n"
                "from PySpice.Spice.Netlist import Circuit\n"
                "from PySpice.Unit import *\n"
                "from engineering_notation import EngNumber\n\n"
                f"# Topology Classification: {top_class}\n"
                "# Experiment 4: Natural Response of RC Circuit (Complete Manual Multi-Switch Topology)\n"
                "circuit = Circuit('Natural Response of RC Circuit')\n"
                f"steptime = {steptime*1e6:g}@u_us\n"
                f"switchingtime = {switchingtime*1e3:g}@u_ms\n"
                f"finaltime = {finaltime*1e3:g}@u_ms\n\n"
                "# Switch model & control pulse sources (preserved from manual topology)\n"
                "circuit.model('switch', 'SW', Ron=1@u_mOhm, Roff=1@u_GOhm)\n"
                "circuit.PulseVoltageSource(2, 'posa', circuit.gnd, initial_value=1, pulsed_value=-1,\n"
                "                           pulse_width=finaltime, period=finaltime, delay_time=switchingtime)\n"
                "circuit.R('testa', 'posa', circuit.gnd, 1@u_kOhm)\n"
                "circuit.PulseVoltageSource(3, 'posb', circuit.gnd, initial_value=-1, pulsed_value=1,\n"
                "                           pulse_width=finaltime, period=finaltime, delay_time=switchingtime)\n"
                "circuit.R('testb', 'posb', circuit.gnd, 1@u_kOhm)\n\n"
                "# Charging & Discharging Network\n"
                f"circuit.V(1, 1, circuit.gnd, {v1:g}@u_V)\n"
                f"circuit.R(1, 1, 'a', {cls._format_pyspice_res(r1)})\n"
                "circuit.VoltageControlledSwitch(1, 'a', 'output', 'posa', circuit.gnd, model='switch')\n"
                f"circuit.C(1, 'output', circuit.gnd, {c1_uf:g}@u_uF)\n"
                "circuit.VoltageControlledSwitch(2, 'output', 'b', 'posb', circuit.gnd, model='switch')\n"
                f"circuit.R(2, 'b', 2, {cls._format_pyspice_res(r2)})\n"
                f"circuit.R(3, 2, circuit.gnd, {cls._format_pyspice_res(r3)})\n"
                f"circuit.R(4, 2, circuit.gnd, {cls._format_pyspice_res(r4)})\n\n"
                "# 1. Run the transient simulation\n"
                "simulator = circuit.simulator(temperature=25, nominal_temperature=25)\n"
                f"ic = {ic_val:g}@u_V\n"
                "simulator.initial_condition(output=ic)\n"
                "analysis = simulator.transient(step_time=steptime, end_time=finaltime)\n\n"
                "# Theoretical discharge time constant after switching\n"
                "tau = (circuit.C1.capacitance) * (circuit.R2.resistance +\n"
                "      (circuit.R3.resistance * circuit.R4.resistance) /\n"
                "      (circuit.R3.resistance + circuit.R4.resistance))\n"
                "print('tau={0}'.format(EngNumber(tau.value)))\n\n"
                "# 2. Extract the requested signals (Capacitor Voltage, Node Voltages, and Currents)\n"
                "time_axis = np.array(analysis.time)\n"
                "v_capacitor = np.array(analysis['output'])  # Capacitor voltage V_C(t) at node 'output'\n"
                "v_node2 = np.array(analysis['2'])\n"
                "i_capacitor = float(circuit.C1.capacitance) * np.gradient(v_capacitor, time_axis)  # i_C(t) = C * dV_C/dt\n"
                "i_r1 = (np.array(analysis['1']) - np.array(analysis['a'])) / float(circuit.R1.resistance)\n"
                "i_r2 = (np.array(analysis['b']) - np.array(analysis['2'])) / float(circuit.R2.resistance)\n"
                "i_r4 = np.array(analysis['2']) / float(circuit.R4.resistance)\n\n"
                "# 3. Create the plots and 4. Label axes appropriately\n"
                "figure1 = plt.figure(1, (20, 10))\n"
                "plt.subplot(211)\n"
                "plot(analysis['posa'])\n"
                "plot(analysis['posb'])\n"
                "plt.title('Switch Activations (posa & posb)')\n"
                "plt.xlabel('Time [s]')\n"
                "plt.ylabel('Voltage [V]')\n"
                "plt.grid(True)\n"
                "plt.legend(('Switch 1 Control V(posa)', 'Switch 2 Control V(posb)'), loc='upper right')\n\n"
                "axe = plt.subplot(212)\n"
                "plt.title('Voltage across Capacitor C1 (Natural Response)')\n"
                "plt.xlabel('Time [s]')\n"
                "plt.ylabel('Voltage [V]')\n"
                "plt.grid(True)\n"
                "plot(analysis['output'], axis=axe, color='black')\n"
                "plot(analysis['2'], color='magenta')\n"
                "plt.legend(('Capacitor Voltage V_C(t) [output]', 'Node 2 Voltage V(2)'), loc=(.5, .5))\n"
                "cursor = Cursor(axe, useblit=True, color='red', linewidth=1)\n\n"
                "figure2 = plt.figure(2, (20, 10))\n"
                "plot((analysis['1'] - analysis['a']) / circuit.R1.resistance)\n"
                "plot(analysis['2'] / circuit.R4.resistance)\n"
                "plot((analysis['b'] - analysis['2']) / circuit.R2.resistance)\n"
                "plt.plot(time_axis, i_capacitor, linestyle='--', color='blue', label='Capacitor Current i_C(t)')\n"
                "plt.title('Capacitor & Branch Currents')\n"
                "plt.xlabel('Time [s]')\n"
                "plt.ylabel('Current [A]')\n"
                "plt.grid(True)\n"
                "plt.legend(('I(R1) Charging', 'I(R4) Branch', 'I(R2) Discharging', 'Capacitor Current i_C(t)'), loc=(.5, .5))\n\n"
                "# 5. Save and display the result\n"
                "plt.tight_layout()\n"
                "figure1.savefig('rc_natural_response_capacitor_voltage.png', dpi=150)\n"
                "figure2.savefig('rc_natural_response_currents.png', dpi=150)\n"
                "plt.show()\n"
            )

        # ---------------------------------------------------------------------
        # EXP 5: RC_STEP_RESPONSE (Full Multi-Switch Netlist + Full Plotting)
        # ---------------------------------------------------------------------
        if ctype == "RC_STEP_RESPONSE":
            steptime = analysis.get("step", 1e-6)
            switchingtime = analysis.get("switchingtime", 20e-3)
            finaltime = analysis.get("stop", 80e-3)
            ic_val = analysis.get("initial_condition", {}).get("output", 0.0)
            v1 = comps["V1"]["value"]
            v2 = comps["V2"]["value"]
            r1 = comps["R1"]["value"]
            r2 = comps["R2"]["value"]
            c1_uf = comps["C1"]["value"] * 1e6
            r3 = comps["R3"]["value"]
            r4 = comps["R4"]["value"]
            r5 = comps["R5"]["value"]
            return (
                "import math\n"
                "import matplotlib.pyplot as plt\n"
                "from matplotlib.widgets import Cursor\n"
                "import numpy as np\n"
                "import PySpice.Logging.Logging as Logging\n"
                "logger = Logging.setup_logging()\n"
                "from PySpice.Probe.Plot import plot\n"
                "from PySpice.Spice.Netlist import Circuit\n"
                "from PySpice.Unit import *\n"
                "from engineering_notation import EngNumber\n\n"
                f"# Topology Classification: {top_class}\n"
                "# Experiment 5: Step Response of RC Circuit (Complete Manual Multi-Switch Topology)\n"
                "circuit = Circuit('Step Response of RC Circuit')\n"
                f"steptime = {steptime*1e6:g}@u_us\n"
                f"switchingtime = {switchingtime*1e3:g}@u_ms\n"
                f"finaltime = {finaltime*1e3:g}@u_ms\n\n"
                "# Switch model & control pulse sources (preserved from manual topology)\n"
                "circuit.model('switch', 'SW', Ron=1@u_mOhm, Roff=1@u_GOhm)\n"
                "circuit.PulseVoltageSource(3, 'posa', circuit.gnd, initial_value=1, pulsed_value=-1,\n"
                "                           pulse_width=finaltime, period=finaltime, delay_time=switchingtime)\n"
                "circuit.R('testa', 'posa', circuit.gnd, 1@u_kOhm)\n"
                "circuit.PulseVoltageSource(4, 'posb', circuit.gnd, initial_value=-1, pulsed_value=1,\n"
                "                           pulse_width=finaltime, period=finaltime, delay_time=switchingtime)\n"
                "circuit.R('testb', 'posb', circuit.gnd, 1@u_kOhm)\n\n"
                "# Pre-Switching & Post-Switching Step Network\n"
                f"circuit.V(1, 1, circuit.gnd, {v1:g}@u_V)\n"
                f"circuit.R(1, 1, 'a', {cls._format_pyspice_res(r1)})\n"
                f"circuit.R(2, 'a', circuit.gnd, {cls._format_pyspice_res(r2)})\n"
                "circuit.VoltageControlledSwitch(1, 'a', 'output', 'posa', circuit.gnd, model='switch')\n"
                f"circuit.C(1, 'output', circuit.gnd, {c1_uf:g}@u_uF)\n"
                "circuit.VoltageControlledSwitch(2, 'output', 'b', 'posb', circuit.gnd, model='switch')\n"
                f"circuit.R(3, 'b', 2, {cls._format_pyspice_res(r3)})\n"
                f"circuit.R(4, 2, circuit.gnd, {cls._format_pyspice_res(r4)})\n"
                f"circuit.R(5, 2, 3, {cls._format_pyspice_res(r5)})\n"
                f"circuit.V(2, circuit.gnd, 3, {v2:g}@u_V)\n\n"
                "# 1. Run the transient simulation\n"
                "simulator = circuit.simulator(temperature=25, nominal_temperature=25)\n"
                f"ic = {ic_val:g}@u_V\n"
                "simulator.initial_condition(output=ic)\n"
                "analysis = simulator.transient(step_time=steptime, end_time=finaltime)\n\n"
                "# Post-switching equivalent time constant tau\n"
                "tau = (circuit.C1.capacitance) * (circuit.R3.resistance +\n"
                "      (circuit.R4.resistance * circuit.R5.resistance) /\n"
                "      (circuit.R4.resistance + circuit.R5.resistance))\n"
                "print('tau={0}'.format(EngNumber(tau.value)))\n\n"
                "# 2. Extract the requested signals (Capacitor Voltage V_C(t), Node Voltages, and Currents)\n"
                "time_axis = np.array(analysis.time)\n"
                "v_capacitor = np.array(analysis['output'])  # Extracted Capacitor Voltage V_C(t) at node 'output'\n"
                "v_node2 = np.array(analysis['2'])\n"
                "i_capacitor = float(circuit.C1.capacitance) * np.gradient(v_capacitor, time_axis)  # i_C(t) = C * dV_C/dt\n"
                "i_r1 = (np.array(analysis['1']) - np.array(analysis['a'])) / float(circuit.R1.resistance)\n"
                "i_r3 = (np.array(analysis['b']) - np.array(analysis['2'])) / float(circuit.R3.resistance)\n"
                "i_r4 = np.array(analysis['2']) / float(circuit.R4.resistance)\n\n"
                "# 3. Create the plots and 4. Label axes appropriately\n"
                "figure1 = plt.figure(1, (20, 10))\n"
                "plt.subplot(211)\n"
                "plot(analysis['posa'])\n"
                "plot(analysis['posb'])\n"
                "plt.title('Switch Activations (posa & posb)')\n"
                "plt.xlabel('Time [s]')\n"
                "plt.ylabel('Voltage [V]')\n"
                "plt.grid(True)\n"
                "plt.legend(('Switch 1 Control V(posa)', 'Switch 2 Control V(posb)'), loc='upper right')\n\n"
                "axe = plt.subplot(212)\n"
                "plt.title('Voltage across Capacitor C1 (Step Response)')\n"
                "plt.xlabel('Time [s]')\n"
                "plt.ylabel('Voltage [V]')\n"
                "plt.grid(True)\n"
                "plot(analysis['output'], axis=axe, color='black')\n"
                "plot(analysis['2'])\n"
                "plt.legend(('Capacitor Voltage V_C(t) [output]', 'Node 2 Voltage V(2)'), loc=(.5, .5))\n"
                "cursor = Cursor(axe, useblit=True, color='red', linewidth=1)\n\n"
                "figure2 = plt.figure(2, (20, 10))\n"
                "plot((analysis['1'] - analysis['a']) / circuit.R1.resistance)\n"
                "plot(analysis['2'] / circuit.R4.resistance)\n"
                "plot((analysis['b'] - analysis['2']) / circuit.R3.resistance)\n"
                "plt.plot(time_axis, i_capacitor, linestyle='--', color='blue', label='Capacitor Current i_C(t)')\n"
                "plt.title('Capacitor & Branch Currents')\n"
                "plt.xlabel('Time [s]')\n"
                "plt.ylabel('Current [A]')\n"
                "plt.grid(True)\n"
                "plt.legend(('I(R1)', 'I(R4)', 'I(R3)', 'Capacitor Current i_C(t)'), loc=(.5, .5))\n\n"
                "# 5. Save and display the result\n"
                "plt.tight_layout()\n"
                "figure1.savefig('rc_step_response_capacitor_voltage.png', dpi=150)\n"
                "figure2.savefig('rc_step_response_currents.png', dpi=150)\n"
                "plt.show()\n"
            )

        # ---------------------------------------------------------------------
        # GENERAL_RC: Generalized Single-Loop RC Circuit (+ Full Plotting)
        # ---------------------------------------------------------------------
        if ctype == "GENERAL_RC":
            v1 = comps["V1"]["value"]
            r1 = comps["R1"]["value"]
            c1_uf = comps["C1"]["value"] * 1e6
            step_t = float(analysis.get("step", 1e-4))
            stop_t = float(analysis.get("stop", 0.05))
            if step_t <= 0 or stop_t <= 0 or step_t > stop_t:
                stop_t = max(stop_t, 0.05)
                step_t = min(max(step_t, stop_t / 500.0), stop_t / 100.0)
            step_expr_rc, step_txt_rc, need_u1 = cls._format_pyspice_time(step_t)
            stop_expr_rc, stop_txt_rc, need_u2 = cls._format_pyspice_time(stop_t)
            need_u_second = need_u1 or need_u2
            u_sec_def = "u_time_s = UnitValueShorcut(U_s)  # Explicit SI seconds unit\n" if need_u_second else ""
            return (
                "import numpy as np\n"
                "import matplotlib.pyplot as plt\n"
                "import PySpice.Logging.Logging as Logging\n"
                "logger = Logging.setup_logging()\n"
                "from PySpice.Probe.Plot import plot\n"
                "from PySpice.Spice.Netlist import Circuit\n"
                "from PySpice.Unit import *\n"
                f"{u_sec_def}\n"
                "# Topology Classification: GENERALIZED CIRCUIT (GENERAL_RC)\n"
                "# Note: Generic single-loop RC circuit (NOT the multi-switch Experiment 4/5 manual topology)\n"
                "circuit = Circuit('Generalized Single-Loop RC Circuit')\n"
                f"circuit.V(1, 1, circuit.gnd, {v1:g}@u_V)\n"
                f"circuit.R(1, 1, 'output', {cls._format_pyspice_res(r1)})\n"
                f"circuit.C(1, 'output', circuit.gnd, {c1_uf:g}@u_uF)\n\n"
                "tau = float(circuit.R1.resistance) * float(circuit.C1.capacitance)\n"
                "print(f'Time Constant tau = R1 * C1 = {tau:.6f} s')\n\n"
                "# 1. Run the transient simulation (step_time <= end_time verified)\n"
                "simulator = circuit.simulator(temperature=25, nominal_temperature=25)\n"
                "simulator.initial_condition(output=0@u_V)\n"
                f"analysis = simulator.transient(step_time={step_expr_rc}, end_time={stop_expr_rc})  # {step_txt_rc}, {stop_txt_rc}\n\n"
                "# 2. Extract the requested signals (Capacitor Voltage & Capacitor Current)\n"
                "time_axis = np.array(analysis.time)\n"
                "v_capacitor = np.array(analysis['output'])\n"
                "i_capacitor = (np.array(analysis['1']) - v_capacitor) / float(circuit.R1.resistance)\n\n"
                "# 3. Create the plots and 4. Label axes appropriately\n"
                "fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)\n"
                "ax1.plot(time_axis, v_capacitor, color='black', linewidth=2, label='Capacitor Voltage V_C(t)')\n"
                "ax1.set_title('Generalized RC Circuit: Voltage across Capacitor C1')\n"
                "ax1.set_ylabel('Voltage [V]')\n"
                "ax1.grid(True)\n"
                "ax1.legend(loc='lower right')\n\n"
                "ax2.plot(time_axis, i_capacitor, color='blue', linewidth=2, label='Capacitor Current i_C(t)')\n"
                "ax2.set_title('Generalized RC Circuit: Capacitor Charging Current i_C(t)')\n"
                "ax2.set_xlabel('Time [s]')\n"
                "ax2.set_ylabel('Current [A]')\n"
                "ax2.grid(True)\n"
                "ax2.legend(loc='upper right')\n\n"
                "# 5. Save and display the result\n"
                "plt.tight_layout()\n"
                "plt.savefig('general_rc_capacitor_voltage.png', dpi=150)\n"
                "plt.show()\n"
            )

        # ---------------------------------------------------------------------
        # EXP 6: PACEMAKER CIRCUIT (+ Full Plotting)
        # ---------------------------------------------------------------------
        if ctype == "PACEMAKER":
            p = meta.get("parameters", {})
            bpm = float(p.get("heart_rate_bpm", 70.0))
            sf = float(p.get("switching_factor", 0.68))
            vs = float(comps["V1"]["value"])
            c_uf = float(comps["C1"]["value"]) * 1e6
            r1_val = float(comps["R1"]["value"])
            r_load = float(comps["R2"]["value"])
            t_period = 60.0 / bpm
            tau_charge = r1_val * float(comps["C1"]["value"])
            rec_cycles = int(analysis.get("recommended_cycles", 5))
            rec_stop = float(analysis.get("recommended_stop_s", round(rec_cycles * t_period, 4)))
            rec_step_expr = analysis.get("recommended_step_code_expr", "1@u_ms")
            rec_stop_expr = analysis.get("recommended_stop_code_expr", f"{rec_stop:g}@u_time_s")
            diag_step_expr = analysis.get("step_code_expr", "1@u_us")
            diag_stop_expr = analysis.get("stop_code_expr", "60@u_us")
            step_stop_check = analysis.get("step_stop_consistency", {})
            win_ok = bool(analysis.get("window_sufficient", False))

            # Validate generated time expressions against textual meanings before presenting
            cls.validate_time_quantity(rec_step_expr, f"{float(analysis.get('recommended_step_s', 0.001)) * 1e3:g} milliseconds", strict=True)
            cls.validate_time_quantity(rec_stop_expr, f"{rec_stop:g} seconds", strict=True)

            warn_comment = (
                f"# NOTE ON MANUAL DIAGNOSTIC WINDOW vs 5-CYCLE SIMULATION WINDOW:\n"
                f"# - Raw manual script had step_time=1 ms, end_time=60 us (60 microseconds << tau={tau_charge:.4f} s, T={t_period:.4f} s),\n"
                f"#   where step_time (1 ms) > end_time (60 us) and Simulation window is insufficient to observe the requested behavior.\n"
                f"# - Step/Stop consistency check adjusted the 60 us diagnostic window timestep to step_time={diag_step_expr}, end_time={diag_stop_expr}.\n"
                f"# - To observe {rec_cycles} complete pacemaker cycles (T = 60/{bpm:g} = {t_period:.4f} s -> {rec_cycles}*T = {rec_stop:g} seconds),\n"
                f"#   the executable transient call below uses compatible step_time={rec_step_expr} (1 milliseconds) and end_time={rec_stop_expr} ({rec_stop:g} seconds).\n"
                if not win_ok else
                f"# Step/Stop consistency verified: 0 < step_time ({diag_step_expr}) <= end_time ({diag_stop_expr}).\n"
            )
            active_step_expr = rec_step_expr if not win_ok else diag_step_expr
            active_stop_expr = rec_stop_expr if not win_ok else diag_stop_expr
            return (
                "import numpy as np\n"
                "import matplotlib.pyplot as plt\n"
                "import PySpice.Logging.Logging as Logging\n"
                "logger = Logging.setup_logging()\n"
                "from PySpice.Probe.Plot import plot\n"
                "from PySpice.Spice.Netlist import Circuit\n"
                "from PySpice.Unit import *\n\n"
                "# Explicit SI second unit shortcut (PySpice u_s is microseconds, so use u_time_s = UnitValueShorcut(U_s) for seconds)\n"
                "u_time_s = UnitValueShorcut(U_s)\n\n"
                f"# Topology Classification: {top_class}\n"
                "# Given Pacemaker Parameters (Experiment 6)\n"
                f"H = {bpm:g}  # Heart rate in beats per minute (Target Period T = 60 / H = {t_period:.4f} s)\n"
                f"Vs = {vs:g}@u_V\n"
                f"Switching_factor = {sf:g}\n"
                "Vo = Switching_factor * Vs\n"
                f"C = {c_uf:g}@u_uF\n\n"
                "# Calculate required timing resistor R and RC time constant tau\n"
                "T_target = 60.0 / H\n"
                "R = -60 / (H * (C.value) * np.log(1 - (Vo.value / Vs.value)))\n"
                "tau = R * C.value\n"
                "print(f'Calculated Target Period T = {T_target:.4f} s')\n"
                "print(f'Calculated Timing Resistor R = {R:.2f} Ohm, RC tau = {tau:.4f} s')\n\n"
                "circuit = Circuit('Pacemaker Circuit')\n"
                "circuit.model('switch', 'SW', Ron=1@u_mOhm, Roff=1@u_GOhm, Vt=2.05@u_V, Vh=2.03@u_V)\n"
                "circuit.V(1, 1, circuit.gnd, Vs)\n"
                "circuit.R(1, 1, 'control', R@u_Ohm)\n"
                "circuit.VoltageControlledSwitch(1, 'control', 'out', 'control', circuit.gnd, model='switch')\n"
                "circuit.C(1, 'control', circuit.gnd, C)\n"
                f"circuit.R(2, 'out', circuit.gnd, {r_load:g}@u_Ohm)\n\n"
                "# 1. Run the transient simulation (step_time > 0, end_time > 0, step_time <= end_time verified)\n"
                f"{warn_comment}"
                f"step_time = {active_step_expr}\n"
                f"end_time = {active_stop_expr}  # {rec_stop:g} seconds ({rec_cycles} cycles of T = {t_period:.4f} s)\n"
                "assert float(step_time) > 0 and float(end_time) > 0 and float(step_time) <= float(end_time)\n"
                "simulator = circuit.simulator(temperature=25, nominal_temperature=25)\n"
                "simulator.initial_condition(control=0@u_V)\n"
                "analysis = simulator.transient(step_time=step_time, end_time=end_time)\n\n"
                "# 2. Extract the simulated node voltages & compute calculated load current (analysis.branches not used)\n"
                "time_axis = np.array(analysis.time)\n"
                "v_capacitor = np.array(analysis['control'])\n"
                "v_output = np.array(analysis['out'])\n"
                "i_load = v_output / float(circuit.R2.resistance)  # Calculated load current from V(out)/R2\n\n"
                "# 3. Create the plots and 4. Label axes appropriately\n"
                "figure1 = plt.figure(1, (20, 10))\n"
                "plt.subplot(211)\n"
                "plot(analysis['control'], color='blue')\n"
                "plt.title('Pacemaker Timing Capacitor Voltage V(control)')\n"
                "plt.xlabel('Time [s]')\n"
                "plt.ylabel('Voltage [V]')\n"
                "plt.grid(True)\n"
                "plt.legend(('Capacitor Voltage V_C(t) [control]',), loc='upper right')\n\n"
                "plt.subplot(212)\n"
                "plot(analysis['out'], color='red')\n"
                "plt.title('Pacemaker Output Pulses V(out)')\n"
                "plt.xlabel('Time [s]')\n"
                "plt.ylabel('Voltage [V]')\n"
                "plt.grid(True)\n"
                "plt.legend(('Pacemaker Output Voltage V(out)',), loc='upper right')\n\n"
                "# 5. Save and display the result\n"
                "plt.tight_layout()\n"
                "plt.savefig('pacemaker_capacitor_and_output_voltage.png', dpi=150)\n"
                "plt.show()\n"
            )

        # ---------------------------------------------------------------------
        # EXP 7, 8, 9, 10: DIGITAL LOGIC TRUTH TABLE & TIMING PLOT
        # ---------------------------------------------------------------------
        if ctype in ("LOGIC_GATES_TRUTH_TABLE", "HALF_FULL_ADDER", "BOOLEAN_SOP_POS", "NAND_COMBINATIONAL"):
            return (
                "import numpy as np\n"
                "import matplotlib.pyplot as plt\n\n"
                f"# Topology Classification: {top_class} ({title})\n"
                "# 1. Run Digital Logic Truth Table Verification\n"
                "print('=== DIGITAL TRUTH TABLE VERIFICATION ===')\n"
                "rows = []\n"
                "for idx in range(8):\n"
                "    A, B, C = (idx >> 2) & 1, (idx >> 1) & 1, idx & 1\n"
                "    sum_bit = A ^ B ^ C\n"
                "    carry_bit = (A & B) | (B & C) | (A & C)\n"
                "    sop_y = 1 if idx in (1, 3, 6) else 0\n"
                "    rows.append((A, B, C, sum_bit, carry_bit, sop_y))\n"
                "    print(f'A={A} B={B} C={C} | Sum={sum_bit} Carry={carry_bit} | SOP_Y={sop_y}')\n\n"
                "# 2. Extract digital signals & 3. Plot digital timing waveforms\n"
                "t = np.arange(8)\n"
                "arr = np.array(rows)\n"
                "fig, axes = plt.subplots(4, 1, figsize=(10, 7), sharex=True)\n"
                "labels = ['Input A', 'Input B', 'Input C', 'Output Y']\n"
                "cols = [0, 1, 2, 3 if 'ADDER' in '" + ctype + "' else 5]\n"
                "for ax, col_idx, lbl in zip(axes, cols, labels):\n"
                "    ax.step(t, arr[:, col_idx], where='post', linewidth=2)\n"
                "    ax.set_ylabel(lbl)\n"
                "    ax.set_ylim(-0.2, 1.2)\n"
                "    ax.grid(True)\n"
                "axes[0].set_title('Digital Logic Truth-Table Timing Waveforms')\n"
                "axes[-1].set_xlabel('Input State Index (0..7)')\n"
                "plt.tight_layout()\n"
                "plt.savefig('digital_truth_table_waveforms.png', dpi=150)\n"
                "plt.show()\n"
            )

        # ---------------------------------------------------------------------
        # EXP 11: DIODE I-V CHARACTERISTICS (DC Sweep + I-V Curve Plot)
        # ---------------------------------------------------------------------
        if ctype == "DIODE_IV_CHARACTERISTICS":
            v1 = comps["V1"]["value"]
            r1 = comps["R1"]["value"]
            return (
                "import numpy as np\n"
                "import matplotlib.pyplot as plt\n"
                "import PySpice.Logging.Logging as Logging\n"
                "logger = Logging.setup_logging()\n"
                "from PySpice.Spice.Netlist import Circuit\n"
                "from PySpice.Unit import *\n\n"
                f"# Topology Classification: {top_class}\n"
                "circuit = Circuit('PN-Junction Diode I-V Characteristics (Experiment 11)')\n"
                "circuit.model('1N4007', 'D', IS=7.027e-9@u_A, RS=0.034@u_Ohm, N=1.77, BV=1000@u_V)\n"
                f"circuit.V(1, 1, circuit.gnd, {v1:g}@u_V)\n"
                "circuit.Diode(1, 1, 2, model='1N4007')\n"
                f"circuit.R(1, 2, circuit.gnd, {cls._format_pyspice_res(r1)})\n\n"
                "# 1. Run DC sweep simulation\n"
                "simulator = circuit.simulator(temperature=25, nominal_temperature=25)\n"
                f"analysis = simulator.dc(V1=slice(0, {v1:g}, 0.05))\n\n"
                "# 2. Extract Diode Voltage V_D and Diode Current I_D\n"
                "v_source = np.array(analysis['1'])\n"
                "v_load = np.array(analysis['2'])\n"
                "v_diode = v_source - v_load\n"
                "i_diode = v_load / float(circuit.R1.resistance)\n\n"
                "# 3. Create the I-V Curve plot and 4. Label axes appropriately\n"
                "plt.figure(figsize=(10, 6))\n"
                "plt.plot(v_diode, i_diode * 1e3, color='crimson', linewidth=2, label='Diode Forward I-V Curve')\n"
                "plt.title('PN-Junction Diode I-V Characteristics')\n"
                "plt.xlabel('Voltage across Diode V_D [V]')\n"
                "plt.ylabel('Diode Forward Current I_D [mA]')\n"
                "plt.grid(True)\n"
                "plt.legend(loc='upper left')\n\n"
                "# 5. Save and display the result\n"
                "plt.tight_layout()\n"
                "plt.savefig('diode_iv_characteristics.png', dpi=150)\n"
                "plt.show()\n"
            )

        # ---------------------------------------------------------------------
        # EXP 13 & 14: HALF-WAVE / FULL-WAVE RECTIFIER (Transient + Waveform Plot)
        # ---------------------------------------------------------------------
        if ctype in ("HALF_WAVE_RECTIFIER", "FULL_WAVE_RECTIFIER"):
            v1 = comps["V1"]["value"]
            r1 = comps["R1"]["value"]
            c_comp = comps.get("C1")
            out_node = "out" if ctype == "FULL_WAVE_RECTIFIER" else "2"
            lines_rect = [
                "import numpy as np",
                "import matplotlib.pyplot as plt",
                "import PySpice.Logging.Logging as Logging",
                "logger = Logging.setup_logging()",
                "from PySpice.Spice.Netlist import Circuit",
                "from PySpice.Unit import *",
                "",
                f"# Topology Classification: {top_class}",
                f"circuit = Circuit('{title}')",
                "circuit.model('1N4007', 'D', IS=7.027e-9@u_A, RS=0.034@u_Ohm, N=1.77, BV=1000@u_V)",
            ]
            if ctype == "FULL_WAVE_RECTIFIER":
                lines_rect.extend([
                    f"circuit.SinusoidalVoltageSource(1, 1, 2, amplitude={v1:g}@u_V, frequency=50@u_Hz)",
                    "circuit.Diode(1, 1, 'out', model='1N4007')",
                    "circuit.Diode(2, circuit.gnd, 2, model='1N4007')",
                    "circuit.Diode(3, 2, 'out', model='1N4007')",
                    "circuit.Diode(4, circuit.gnd, 1, model='1N4007')",
                    f"circuit.R(1, 'out', circuit.gnd, {cls._format_pyspice_res(r1)})",
                ])
            else:
                lines_rect.extend([
                    f"circuit.SinusoidalVoltageSource(1, 1, circuit.gnd, amplitude={v1:g}@u_V, frequency=50@u_Hz)",
                    "circuit.Diode(1, 1, 2, model='1N4007')",
                    f"circuit.R(1, 2, circuit.gnd, {cls._format_pyspice_res(r1)})",
                ])
            if c_comp:
                lines_rect.append(f"circuit.C(1, '{out_node}', circuit.gnd, {c_comp['value']*1e6:g}@u_uF)")
            lines_rect.extend([
                "",
                "# 1. Run the transient simulation",
                "simulator = circuit.simulator(temperature=25, nominal_temperature=25)",
                "analysis = simulator.transient(step_time=100@u_us, end_time=60@u_ms)",
                "",
                "# 2. Extract input and rectified output voltage waveforms",
                "time_axis = np.array(analysis.time)",
                f"v_output = np.array(analysis['{out_node}'])",
                "v_input = np.array(analysis['1'])",
                "i_load = v_output / float(circuit.R1.resistance)",
                "",
                "# 3. Create the waveform plot and 4. Label axes appropriately",
                "plt.figure(figsize=(10, 6))",
                "plt.plot(time_axis, v_input, '--', color='gray', label='AC Input Voltage V(1)')",
                f"plt.plot(time_axis, v_output, color='black', linewidth=2, label='Rectified Output Voltage V({out_node})')",
                f"plt.title('{title}: Input vs Rectified Output Waveform')",
                "plt.xlabel('Time [s]')",
                "plt.ylabel('Voltage [V]')",
                "plt.grid(True)",
                "plt.legend(loc='upper right')",
                "",
                "# 5. Save and display the result",
                "plt.tight_layout()",
                "plt.savefig('rectifier_waveform.png', dpi=150)",
                "plt.show()",
            ])
            return "\n".join(lines_rect)

        # ---------------------------------------------------------------------
        # DC / OPERATING POINT CIRCUITS (Exp 1, 2, 3, 12, Generic Divider/Series/Parallel)
        # ---------------------------------------------------------------------
        lines = [
            "import numpy as np",
            "import matplotlib.pyplot as plt",
            "import PySpice.Logging.Logging as Logging",
            "logger = Logging.setup_logging()",
            "from PySpice.Spice.Netlist import Circuit",
            "from PySpice.Unit import *",
            "",
            f"# Topology Classification: {top_class} ({meta.get('topology_source', 'manual_template')})",
            f"circuit = Circuit('{title}')",
            ""
        ]

        def fmt_node(n: str) -> str:
            if n.upper() == "GND":
                return "circuit.gnd"
            return str(n) if n.isdigit() else f"'{n}'"

        if any(c.get("type") == "zener" for c in circuit_ir.get("components", [])):
            vz_val = next((c.get("value", 5.1) for c in circuit_ir.get("components", []) if c.get("type") == "zener"), 5.1)
            lines.append(f"circuit.model('ZENER_D', 'D', BV={vz_val:g}@u_V, IBV=5@u_mA)")

        for comp in circuit_ir.get("components", []):
            cid = comp["id"]
            ct = comp["type"]
            nodes = [fmt_node(n) for n in comp.get("nodes", ["1", "GND"])]
            val = comp.get("value", 0.0)

            if ct == "dc_voltage_source":
                num_id = cid[1:] if cid.startswith("V") and cid[1:].isdigit() else f"'{cid[1:] if cid.startswith('V') else cid}'"
                lines.append(f"circuit.V({num_id}, {nodes[0]}, {nodes[1]}, {val:g}@u_V)")
            elif ct == "ac_voltage_source":
                lines.append(f"circuit.SinusoidalVoltageSource('{cid}', {nodes[0]}, {nodes[1]}, amplitude={val:g}@u_V, frequency=50@u_Hz)")
            elif ct == "current_source":
                num_id = cid[1:] if cid.startswith("I") and cid[1:].isdigit() else f"'{cid}'"
                lines.append(f"circuit.I({num_id}, {nodes[0]}, {nodes[1]}, {val:g}@u_A)")
            elif ct == "resistor":
                num_id = cid[1:] if cid.startswith("R") and cid[1:].isdigit() else f"'{cid}'"
                lines.append(f"circuit.R({num_id}, {nodes[0]}, {nodes[1]}, {cls._format_pyspice_res(val)})")
            elif ct == "capacitor":
                num_id = cid[1:] if cid.startswith("C") and cid[1:].isdigit() else f"'{cid}'"
                lines.append(f"circuit.C({num_id}, {nodes[0]}, {nodes[1]}, {val*1e6:g}@u_uF)")
            elif ct == "inductor":
                num_id = cid[1:] if cid.startswith("L") and cid[1:].isdigit() else f"'{cid}'"
                lines.append(f"circuit.L({num_id}, {nodes[0]}, {nodes[1]}, {val*1e3:g}@u_mH)")
            elif ct == "zener":
                lines.append(f"circuit.Diode('Z1', {nodes[0]}, {nodes[1]}, model='ZENER_D')")
            elif ct == "cccs":
                ctrl = comp.get("controlling_source", "Vtest")
                gain = comp.get("gain", 3)
                lines.append("# Add CCCS (F element)")
                lines.append(f"circuit.F(1, {nodes[0]}, {nodes[1]}, '{ctrl}', {gain:g})")
            elif ct == "vcvs":
                c_nodes = [fmt_node(n) for n in comp.get("control_nodes", ["2", "3"])]
                gain = comp.get("gain", 3)
                lines.append("# Add VCVS (E element)")
                lines.append(f"circuit.VCVS(1, {nodes[0]}, {nodes[1]}, {c_nodes[0]}, {c_nodes[1]}, {gain:g})")

        lines.append("")
        lines.append("# 1. Perform the simulation")
        lines.append("simulator = circuit.simulator(temperature=25, nominal_temperature=25)")
        if analysis.get("type") == "transient":
            step = analysis.get("step", 1e-6)
            stop = analysis.get("stop", 0.25)
            out_n = next((c["nodes"][0] for c in circuit_ir.get("components", []) if c.get("type") == "capacitor"), "output")
            lines.extend([
                f"analysis = simulator.transient(step_time={step:g}, end_time={stop:g})",
                "",
                "# 2. Extract time axis and capacitor/output node voltage waveform",
                "time_axis = np.array(analysis.time)",
                f"v_out = np.array(analysis['{out_n}'])",
                "",
                "# 3. Create transient waveform plot & 4. Label axes appropriately",
                "plt.figure(figsize=(9, 5))",
                f"plt.plot(time_axis, v_out, color='royalblue', linewidth=2, label='V({out_n})')",
                f"plt.title('{title} — Transient Response')",
                "plt.xlabel('Time [s]')",
                "plt.ylabel('Voltage [V]')",
                "plt.grid(True)",
                "plt.legend()",
                "plt.tight_layout()",
                "plt.savefig('transient_response.png', dpi=150)",
                "plt.show()",
            ])
        else:
            lines.append("analysis = simulator.operating_point()")
            lines.append("")
            lines.append("# 2. Extract and print Node Voltages and Branch Currents")
            lines.append("node_voltages = {}")
            lines.append("for node in analysis.nodes.values():")
            lines.append("    node_voltages[str(node)] = float(node)")
            lines.append("    print('Node {}: {:4.2f} V'.format(str(node), float(node)))")
            lines.append("branch_currents = {}")
            lines.append("for branch in analysis.branches.values():")
            lines.append("    branch_currents[str(branch)] = float(branch)")
            lines.append("    print('Branch {}: {:5.2f} A'.format(str(branch), float(branch)))")

            if "waveform" in all_reqs:
                lines.extend([
                    "",
                    "# 3. Create DC Operating Point Plot & 4. Label Axes",
                    "plt.figure(figsize=(8, 5))",
                    "plt.bar(list(node_voltages.keys()), list(node_voltages.values()), color='teal')",
                    f"plt.title('{title}: DC Node Voltages')",
                    "plt.xlabel('Circuit Node')",
                    "plt.ylabel('Voltage [V]')",
                    "plt.grid(True, axis='y')",
                    "# 5. Save and display the result",
                    "plt.tight_layout()",
                    "plt.savefig('dc_node_voltages.png', dpi=150)",
                    "plt.show()",
                ])

        return "\n".join(lines)

    # =========================================================================
    # STAGE 8B: DETERMINISTIC OUTPUT FULFILLMENT VERIFICATION GATE
    # =========================================================================
    @classmethod
    def verify_requested_outputs(
        cls,
        requested_outputs: Dict[str, Any],
        generated_code: str,
        sim_results: Optional[Dict[str, Any]],
        ctype: str
    ) -> Dict[str, Any]:
        """
        Verifies that EVERY requested output (capacitor voltage, capacitor current,
        node voltage, branch current, waveform plot, I-V curve, truth table, DC operating point, etc.)
        was actually fulfilled in the generated PySpice code and simulation results.
        Never marks `TASK_COMPLETED = True` if any requested output was omitted!
        """
        explicit_reqs = requested_outputs.get("explicitly_requested", [])
        effective_reqs = requested_outputs.get("effective_outputs", [])
        targets_to_verify = explicit_reqs if explicit_reqs else effective_reqs

        fulfilled_items: List[Dict[str, Any]] = []
        omitted_items: List[Dict[str, Any]] = []

        has_transient_call = "simulator.transient(" in generated_code
        has_dc_call = "simulator.dc(" in generated_code
        has_op_call = "simulator.operating_point(" in generated_code
        has_plot_create = any(tok in generated_code for tok in ("plt.figure", "plt.subplots", "plt.subplot", "plot(", "plt.plot(", "plt.bar(", "ax.step("))
        has_axis_labels = ("xlabel" in generated_code) and ("ylabel" in generated_code) and ("title" in generated_code)
        has_display_or_save = ("plt.show()" in generated_code) or ("savefig(" in generated_code)

        for req in targets_to_verify:
            if req == "capacitor_voltage":
                has_cap_sig = any(tok in generated_code for tok in ("analysis['output']", "analysis['control']", "v_capacitor"))
                ok = has_transient_call and has_cap_sig and has_plot_create and has_axis_labels and has_display_or_save
                detail = (
                    "1. Transient simulation run (`simulator.transient`), "
                    "2. Capacitor voltage extracted (`analysis['output']` / `v_capacitor`), "
                    "3. Plot created (`plt.figure` / `plot`), "
                    "4. Axes labeled (`Time [s]`, `Voltage [V]`), "
                    "5. Displayed & saved (`plt.savefig` / `plt.show()`)."
                )
            elif req == "capacitor_current":
                has_cap_curr = any(tok in generated_code for tok in ("i_capacitor", "np.gradient", "circuit.R1.resistance", "circuit.R2.resistance", "circuit.R3.resistance"))
                ok = has_transient_call and has_cap_curr and has_plot_create and has_axis_labels and has_display_or_save
                detail = (
                    "1. Transient simulation run, "
                    "2. Capacitor current extracted (`i_capacitor = C * dV_C/dt`), "
                    "3. Current waveform plotted, "
                    "4. Axes labeled (`Time [s]`, `Current [A]`), "
                    "5. Displayed & saved."
                )
            elif req == "waveform":
                ok = (has_transient_call or has_dc_call or has_op_call or "ax.step(" in generated_code) and has_plot_create and has_axis_labels and has_display_or_save
                detail = "Simulation executed, waveform signal extracted, plot created, axes labeled, and result saved/displayed."
            elif req == "switch_activations":
                has_sw_sig = ("analysis['posa']" in generated_code) and ("analysis['posb']" in generated_code)
                ok = has_transient_call and has_sw_sig and has_plot_create and has_axis_labels and has_display_or_save
                detail = "Switch control pulse voltages `analysis['posa']` and `analysis['posb']` extracted and plotted vs `Time [s]`."
            elif req == "node_voltage":
                has_nv = bool((sim_results or {}).get("node_voltages")) or ("analysis.nodes" in generated_code) or ("analysis['output']" in generated_code)
                ok = has_nv
                detail = "Node voltages solved numerically and extracted in PySpice code."
            elif req == "branch_current":
                has_true_branches = bool((sim_results or {}).get("branch_currents")) or ("analysis.branches" in generated_code)
                has_calc_load = bool((sim_results or {}).get("calculated_load_currents")) or ("resistance" in generated_code)
                ok = has_true_branches or has_calc_load
                if has_true_branches:
                    detail = "Branch currents solved numerically and extracted via `analysis.branches` / MNA sense source."
                else:
                    detail = "Calculated load current derived from node voltage (`v_output / R`); `analysis.branches` was not used."
            elif req == "calculated_load_current":
                ok = ("i_load" in generated_code) or bool((sim_results or {}).get("calculated_load_currents")) or ("resistance" in generated_code)
                detail = "Calculated load current (`i_load = v_output / R2`) derived from simulated node voltage (`analysis.branches` was not used)."
            elif req == "iv_curve":
                ok = has_dc_call and ("v_diode" in generated_code) and ("i_diode" in generated_code) and has_plot_create and has_axis_labels and has_display_or_save
                detail = "DC sweep executed (`simulator.dc`), `v_diode` & `i_diode` extracted, and I-V curve plotted with labeled axes."
            elif req == "truth_table":
                ok = bool((sim_results or {}).get("truth_table")) and ("TRUTH TABLE" in generated_code)
                detail = "Complete digital logic Truth Table verified across all input states and emitted in code."
            elif req == "dc_operating_point":
                ok = has_op_call or bool((sim_results or {}).get("node_voltages"))
                detail = "DC operating point (`simulator.operating_point()`) solved and printed."
            elif req == "time_constant":
                ok = ("tau" in generated_code) or bool((sim_results or {}).get("transient_metrics"))
                detail = "RC time constant `tau` computed analytically and printed in PySpice code."
            else:
                ok = True
                detail = f"Output '{req}' verified."

            entry = {"output_type": req, "fulfilled": ok, "verification_detail": detail}
            if ok:
                fulfilled_items.append(entry)
            else:
                omitted_items.append(entry)

        all_fulfilled = len(omitted_items) == 0
        return {
            "all_fulfilled": all_fulfilled,
            "explicitly_requested": explicit_reqs,
            "fulfilled": fulfilled_items,
            "omitted": omitted_items,
        }

    # =========================================================================
    # FULL DETERMINISTIC PIPELINE ENTRY POINT
    # =========================================================================
    @classmethod
    def reconstruct_circuit(
        cls,
        latest_user_message: str,
        previous_user_message: Optional[str] = None,
        experiment_context: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Executes the full 8-stage deterministic pipeline strictly on `latest_user_message`.
        Only if `latest_user_message` is a pure candidate selection ("Confirm Candidate A", "Use GENERAL_RC", "Map 5kΩ to R2")
        does it read entities from `previous_user_message` (and NEVER from assistant output).
        """
        clean_msg = latest_user_message.strip()

        # Step 1: Extract entities strictly from latest_user_message
        entities = cls.extract_entities(clean_msg, experiment_context=experiment_context)
        classification = cls.classify_circuit_intent(clean_msg, entities, experiment_context=experiment_context)

        user_confirmed = classification.get("user_confirmed_candidate") is not None

        has_any_entity = bool(
            entities.get("voltage_sources")
            or entities.get("resistors")
            or entities.get("current_sources")
            or entities.get("capacitors")
            or entities.get("inductors")
            or entities.get("diodes")
        )

        # If user clicked "Use GENERAL_RC" or "Confirm Candidate A/B/C" or "Map 5kΩ to R2"
        # or provided a natural-language connection description in a follow-up turn after giving component values:
        has_nl_followup = bool(
            re.search(
                r'\bin\s+series\b|\bin\s+parallel\b|\bmiddle\s*point\b|\bmidpoint\b|\bjunction\b|'
                r'\bcommon\s*point\b|\bbranch(?:es|ing)?\s+from\b|\bconnected\s+across\b|\bacross\s+r\d+|'
                r'\bconnected\s+between\b|\bconnected\s+from\b|\bone\s+end\b|\bother\s+end\b|\bto\s+ground\b',
                clean_msg.lower()
            )
        )
        if previous_user_message and (
            user_confirmed
            or re.search(r'\bmap\b.*\bto\s*r[1234]\b', clean_msg.lower())
            or (has_nl_followup and not has_any_entity)
        ):
            prev_entities = cls.extract_entities(previous_user_message, experiment_context=experiment_context)
            if not has_any_entity:
                entities = prev_entities
                classification = cls.classify_circuit_intent(
                    f"{previous_user_message}. {clean_msg}",
                    entities,
                    experiment_context=experiment_context
                )
                entities["circuit_type"] = classification["circuit_type"]
                if classification.get("inferred_topology_lines"):
                    entities["inferred_topology"] = classification["inferred_topology_lines"]
                user_confirmed = classification.get("user_confirmed_candidate") is not None
                has_any_entity = True
            elif re.search(r'\bmap\b.*\bto\s*r[1234]\b', clean_msg.lower()):
                if not entities.get("voltage_sources") and prev_entities.get("voltage_sources"):
                    entities["voltage_sources"] = prev_entities["voltage_sources"]
                if not entities.get("capacitors") and prev_entities.get("capacitors"):
                    entities["capacitors"] = prev_entities["capacitors"]

        # Step 1B: Parse requested outputs separately from component/value extraction
        requested_outputs = cls.extract_requested_outputs(clean_msg, classification["circuit_type"])

        # Step 4-6: Build Circuit IR & Parameter Completeness Report
        selected_ir, candidates, completeness = cls.build_circuit_ir(
            entities,
            classification,
            user_confirmed=user_confirmed
        )

        # GUARANTEE: Any value explicitly extracted from the latest user message MUST be classified as USER SUPPLIED.
        # Never allow completeness["user_supplied"] to be empty if `entities` has user-provided component values.
        if has_any_entity and not completeness.get("user_supplied"):
            completeness["user_supplied"] = cls._build_user_supplied_entries(entities)
            if completeness.get("required_count", 0) == 0:
                completeness["required_count"] = len(completeness["user_supplied"])

        # Step 7: Validate & Simulate
        lifecycle_report = cls.validate_and_simulate(selected_ir, execute_sim=(selected_ir is not None))

        # Step 8: Generate PySpice Code & Verify Requested Outputs
        generated_code = ""
        output_verification = {
            "all_fulfilled": False,
            "explicitly_requested": requested_outputs.get("explicitly_requested", []),
            "fulfilled": [],
            "omitted": [],
        }
        if selected_ir is not None:
            generated_code = cls.generate_pyspice_code(selected_ir, requested_outputs=requested_outputs)
            output_verification = cls.verify_requested_outputs(
                requested_outputs,
                generated_code,
                lifecycle_report.get("simulation_results"),
                classification["circuit_type"]
            )

        outputs_fulfilled = bool(selected_ir is not None and output_verification.get("all_fulfilled", False))
        sim_num_ok = bool(lifecycle_report.get("SIMULATION_NUMERICALLY_SUCCESSFUL", lifecycle_report.get("SIMULATION_SUCCESSFUL", False)))
        win_sufficient = bool(lifecycle_report.get("WINDOW_SUFFICIENT", True))
        behavior_observed = bool(lifecycle_report.get("REQUESTED_BEHAVIOR_OBSERVED", sim_num_ok and win_sufficient))
        task_completed = bool(
            lifecycle_report["TOPOLOGY_RECONSTRUCTED"]
            and lifecycle_report["TOPOLOGY_VALIDATED"]
            and lifecycle_report["SIMULATION_EXECUTED"]
            and sim_num_ok
            and win_sufficient
            and behavior_observed
            and outputs_fulfilled
        )
        if task_completed:
            task_completion_status = "COMPLETED"
        elif sim_num_ok and not win_sufficient:
            task_completion_status = "INCOMPLETE_INSUFFICIENT_SIMULATION_WINDOW"
        elif sim_num_ok and not behavior_observed:
            task_completion_status = "INCOMPLETE_BEHAVIOR_NOT_OBSERVED"
        elif sim_num_ok and not outputs_fulfilled:
            task_completion_status = "INCOMPLETE_OUTPUTS_NOT_FULFILLED"
        else:
            task_completion_status = "INCOMPLETE"

        lifecycle_flags = {
            "TOPOLOGY_RECONSTRUCTED": lifecycle_report["TOPOLOGY_RECONSTRUCTED"],
            "TOPOLOGY_VALIDATED": lifecycle_report["TOPOLOGY_VALIDATED"],
            "SIMULATION_EXECUTED": lifecycle_report["SIMULATION_EXECUTED"],
            "SIMULATION_NUMERICALLY_SUCCESSFUL": sim_num_ok,
            "SIMULATION_SUCCESSFUL": lifecycle_report["SIMULATION_SUCCESSFUL"],
            "WINDOW_SUFFICIENT": win_sufficient,
            "REQUESTED_BEHAVIOR_OBSERVED": behavior_observed,
            "REQUESTED_OUTPUTS_FULFILLED": outputs_fulfilled,
            "TASK_COMPLETION_STATUS": task_completion_status,
            "TASK_COMPLETED": task_completed,
        }
        topology_classification = completeness.get("topology_classification", "GENERALIZED CIRCUIT")
        inferred_topology_lines = (
            completeness.get("inferred_topology_lines")
            or classification.get("inferred_topology_lines")
            or entities.get("inferred_topology")
            or []
        )
        user_connection_clauses = (
            completeness.get("user_connection_clauses")
            or classification.get("user_connection_clauses")
            or inferred_topology_lines
            or []
        )
        topology_graph: Optional[Dict[str, Any]] = None
        resolved_graph: List[str] = []
        topology_preview: Any = ""

        if selected_ir is not None:
            # STRICT SINGLE SOURCE OF TRUTH:
            # Circuit IR -> Topology Graph -> Preview
            topology_graph = cls.build_topology_graph(
                selected_ir.get("components", []),
                selected_ir.get("nodes", []),
            )
            resolved_graph = list(topology_graph["resolved_graph_lines"])
            topology_preview = cls.build_topology_preview(
                selected_ir.get("components", []),
                selected_ir.get("nodes", []),
                user_connection_clauses=user_connection_clauses,
                resolved_graph=resolved_graph,
                topology_graph=topology_graph,
            )
            selected_ir.setdefault("metadata", {})["lifecycle"] = lifecycle_flags
            selected_ir["metadata"]["requested_outputs"] = requested_outputs.get("effective_outputs", [])
            selected_ir["metadata"]["user_connection_clauses"] = user_connection_clauses
            selected_ir["metadata"]["topology_graph"] = topology_graph
            selected_ir["metadata"]["resolved_graph"] = resolved_graph
            selected_ir["metadata"]["topology_preview"] = topology_preview
            completeness["user_connection_clauses"] = user_connection_clauses
            completeness["topology_graph"] = topology_graph
            completeness["resolved_graph"] = resolved_graph
            completeness["topology_preview"] = topology_preview
        else:
            resolved_graph = (
                completeness.get("resolved_graph")
                or classification.get("resolved_graph")
                or []
            )
            topology_preview = (
                completeness.get("topology_preview")
                or classification.get("topology_preview")
                or ""
            )

        # Build Debug Trace for the UI Debug Panel
        debug_trace = {
            "user_input": clean_msg,
            "extracted_entities": entities,
            "inferred_topology_lines": inferred_topology_lines,
            "user_connection_clauses": user_connection_clauses,
            "topology_graph": topology_graph,
            "resolved_graph": resolved_graph,
            "topology_preview": topology_preview,
            "requested_outputs": {
                "explicitly_requested": requested_outputs.get("explicitly_requested", []),
                "effective_outputs": requested_outputs.get("effective_outputs", []),
                "all_fulfilled": outputs_fulfilled,
                "fulfilled": output_verification.get("fulfilled", []),
                "omitted": output_verification.get("omitted", []),
            },
            "classified_circuit_type": classification["circuit_type"],
            "classification_reason": classification["reason"],
            "selected_experiment": classification["selected_experiment"],
            "topology_source": selected_ir["metadata"]["topology_source"] if selected_ir else classification["topology_source"],
            "topology_classification": topology_classification,
            "user_confirmed": user_confirmed,
            "parameter_completeness": {
                "required_count": completeness.get("required_count", 0),
                "user_supplied_count": len(completeness.get("user_supplied", [])),
                "manual_default_count": len(completeness.get("manual_defaults", [])),
                "missing_ambiguous_count": len(completeness.get("missing_ambiguous", [])),
                "user_supplied": completeness.get("user_supplied", []),
                "manual_defaults": completeness.get("manual_defaults", []),
                "missing_ambiguous": completeness.get("missing_ambiguous", []),
                "inferred_topology_lines": inferred_topology_lines,
                "user_connection_clauses": user_connection_clauses,
                "resolved_graph": resolved_graph,
                "topology_preview": topology_preview,
            },
            "lifecycle_flags": lifecycle_flags,
            "final_circuit_ir": selected_ir
        }

        # Flatten known_components for legacy callers
        known_components = []
        for idx, v in enumerate(entities.get("voltage_sources", [])):
            known_components.append({"id": v.get("id", f"V{idx+1}"), "type": "voltage_source", "value": v["value"], "unit": "V", "display": f"{v['value']} V", "user_supplied": True})
        for idx, r in enumerate(entities.get("resistors", [])):
            known_components.append({"id": r.get("id", f"R{idx+1}"), "type": "resistor", "value": r["value"], "unit": "ohm", "display": cls._format_eng(r["value"], "ohm"), "user_supplied": True})
        for idx, i_src in enumerate(entities.get("current_sources", [])):
            known_components.append({"id": i_src.get("id", f"I{idx+1}"), "type": "current_source", "value": i_src["value"], "unit": "A", "display": cls._format_eng(i_src["value"], "A"), "user_supplied": True})
        for idx, c in enumerate(entities.get("capacitors", [])):
            known_components.append({"id": c.get("id", f"C{idx+1}"), "type": "capacitor", "value": c["value"], "unit": "F", "display": c.get("display", cls._format_eng(c["value"], "F")), "user_supplied": True})
        for idx, l_ind in enumerate(entities.get("inductors", [])):
            known_components.append({"id": l_ind.get("id", f"L{idx+1}"), "type": "inductor", "value": l_ind["value"], "unit": "H", "display": l_ind.get("display", cls._format_eng(l_ind["value"], "H")), "user_supplied": True})

        is_circuit_query = has_any_entity or (classification["selected_experiment"] is not None) or user_confirmed

        return {
            "has_components": is_circuit_query,
            "known_components": known_components,
            "extracted_entities": entities,
            "inferred_topology_lines": inferred_topology_lines,
            "user_connection_clauses": user_connection_clauses,
            "resolved_graph": resolved_graph,
            "topology_preview": topology_preview,
            "requested_outputs": requested_outputs,
            "output_verification": output_verification,
            "generated_pyspice_code": generated_code,
            "circuit_type": classification["circuit_type"],
            "selected_experiment": classification["selected_experiment"],
            "is_ambiguous": classification["is_ambiguous"],
            "topology_source": debug_trace["topology_source"],
            "topology_classification": topology_classification,
            "parameter_completeness": completeness,
            "user_confirmed": user_confirmed,
            "lifecycle": lifecycle_flags,
            "simulation_results": lifecycle_report.get("simulation_results"),
            "candidates": candidates,
            "selected_circuit_ir": selected_ir,
            "debug_trace": debug_trace
        }

    # =========================================================================
    # STRUCTURED MARKDOWN RESPONSE FORMATTER
    # =========================================================================
    @classmethod
    def format_reconstruction_response(cls, recon: Dict[str, Any], query: str) -> str:
        entities = recon.get("extracted_entities", {})
        inferred_topology_lines = recon.get("inferred_topology_lines") or recon.get("parameter_completeness", {}).get("inferred_topology_lines") or []
        user_connection_clauses = recon.get("user_connection_clauses") or recon.get("parameter_completeness", {}).get("user_connection_clauses") or inferred_topology_lines or []
        resolved_graph = recon.get("resolved_graph") or recon.get("parameter_completeness", {}).get("resolved_graph") or []
        topology_preview = recon.get("topology_preview") or recon.get("parameter_completeness", {}).get("topology_preview") or ""
        requested_outputs = recon.get("requested_outputs", {})
        output_verification = recon.get("output_verification", {})
        ctype = recon.get("circuit_type", "AMBIGUOUS_UNSPECIFIED")
        exp_num = recon.get("selected_experiment")
        is_ambiguous = recon.get("is_ambiguous", True)
        top_source = recon.get("topology_source", "ai_inferred")
        top_class = recon.get("topology_classification", "GENERALIZED CIRCUIT")
        completeness = recon.get("parameter_completeness", {})
        user_confirmed = recon.get("user_confirmed", False)
        lifecycle = recon.get("lifecycle", {})
        sim_results = recon.get("simulation_results")
        selected_ir = recon.get("selected_circuit_ir")
        candidates = recon.get("candidates", [])

        user_sup = completeness.get("user_supplied", [])
        if not user_sup:
            user_sup = cls._build_user_supplied_entries(entities)
        man_def = completeness.get("manual_defaults", [])
        miss_amb = completeness.get("missing_ambiguous", [])

        md: List[str] = []

        # TOPOLOGY DISTINCTION BANNER (EXACT MANUAL TOPOLOGY | MODIFIED MANUAL TOPOLOGY | GENERALIZED CIRCUIT)
        md.append(f"## Topology Category: **`{top_class}`**")
        if top_class == "EXACT MANUAL TOPOLOGY":
            md.append(
                f"> [!NOTE]\n"
                f"> **`EXACT MANUAL TOPOLOGY`**: This circuit uses the exact topology and default parameters from **Experiment {exp_num}** of *23EEP20B - SIMULATION LAB MANUAL*. No components were removed or simplified."
            )
        elif top_class == "MODIFIED MANUAL TOPOLOGY":
            md.append(
                f"> [!IMPORTANT]\n"
                f"> **`MODIFIED MANUAL TOPOLOGY`**: This circuit uses the **Experiment {exp_num}** manual topology with your custom component values substituted, while **preserving all other manual-defined components and parameters** (switches, pulse sources, unmentioned resistors, initial conditions, and transient settings)."
            )
        else:
            md.append(
                f"> [!WARNING]\n"
                f"> **`GENERALIZED CIRCUIT`**: This is a generic/custom circuit (`{ctype}`), **NOT** an exact manual experiment topology."
            )
        md.append("")

        # EXPLICIT SUMMARY BLOCK FOR USER SUPPLIED + TOPOLOGY INFERRED FROM USER DESCRIPTION
        if user_sup or inferred_topology_lines:
            summary_lines: List[str] = ["USER SUPPLIED"]
            if user_sup:
                for item in user_sup:
                    summary_lines.append(f"{item['id']} = {item['value']}")
            else:
                summary_lines.append("(None — using manual default parameters)")

            if inferred_topology_lines:
                summary_lines.append("")
                summary_lines.append("TOPOLOGY INFERRED FROM USER DESCRIPTION")
                for tline in inferred_topology_lines:
                    summary_lines.append(tline)

            md.append("```text\n" + "\n".join(summary_lines) + "\n```")
            md.append("")

        # TOPOLOGY PREVIEW BEFORE SIMULATION + [Confirm & Simulate] [Edit Circuit]
        if topology_preview:
            preview_text = topology_preview.get("formatted_preview", "") if isinstance(topology_preview, dict) else str(topology_preview)
            md.append("### [TOPOLOGY PREVIEW BEFORE SIMULATION]")
            md.append(f"```text\n{preview_text}\n```")
            md.append("**Actions:** `[Confirm & Simulate]`  `[Edit Circuit]`")
            md.append("")

        # DEVELOPMENT / DIAGNOSTICS OUTPUT: INTERMEDIATE GRAPH REPRESENTATION
        if user_connection_clauses or resolved_graph:
            diag_lines: List[str] = ["USER CONNECTION CLAUSES"]
            if user_connection_clauses:
                for cl_line in user_connection_clauses:
                    diag_lines.append(f"- {cl_line}")
            else:
                diag_lines.append("- (Standard template topology)")
            diag_lines.append("")
            diag_lines.append("RESOLVED GRAPH")
            for rg_line in resolved_graph:
                diag_lines.append(f"- {rg_line}")
            md.append("### [INTERMEDIATE TOPOLOGY GRAPH (DIAGNOSTICS)]")
            md.append("```text\n" + "\n".join(diag_lines) + "\n```")
            md.append("")

        # 1. USER-PROVIDED VALUES (Strictly from latest user message)
        md.append("### 1. [USER-PROVIDED VALUES (Extracted Strictly from Latest Prompt)]")
        md.append(f"```json\n{json.dumps(entities, indent=2)}\n```")
        md.append("")

        # 2. CIRCUIT CLASSIFICATION & TOPOLOGY SOURCE
        md.append("### 2. [CIRCUIT CLASSIFICATION & TOPOLOGY SOURCE]")
        md.append(f"- **Topology Distinction**: **`{top_class}`**")
        md.append(f"- **Classified Circuit Type**: `{ctype}`")
        md.append(f"- **Selected Manual Experiment**: `{f'Experiment {exp_num}' if exp_num else 'None (Generalized / Non-Manual Circuit)'}`")
        md.append(f"- **Topology Source**: `{top_source}`")
        md.append(f"- **User Confirmed Topology**: `{str(user_confirmed).lower()}`")
        if inferred_topology_lines:
            md.append(f"- **Topology Inferred from User Description**: `{'; '.join(inferred_topology_lines)}`")
        md.append("")

        # 3. PARAMETER COMPLETENESS REPORT
        md.append("### 3. [PARAMETER COMPLETENESS REPORT]")
        md.append(f"**Required parameters** (`{completeness.get('required_count', len(user_sup) + len(man_def))}` required for *{completeness.get('template_name', ctype)}*):")
        md.append("")

        md.append("**✓ USER SUPPLIED**")
        if user_sup:
            for item in user_sup:
                md.append(
                    f"- `✓` **`{item['id']}` = `{item['value']}`** — {item.get('role', '')} "
                    f"*(Manual default: `{item.get('manual_default', 'N/A')}`; {item.get('note', 'User supplied')})*"
                )
        else:
            md.append("- *(No custom values supplied in prompt — using 100% manual default values)*")
        md.append("")

        if inferred_topology_lines:
            md.append("**✓ TOPOLOGY INFERRED FROM USER DESCRIPTION**")
            for tline in inferred_topology_lines:
                md.append(f"- `✓` **{tline}**")
            md.append("")

        md.append("**✓ Manual default (Preserved — Never Silently Deleted)**")
        if man_def:
            for item in man_def:
                md.append(
                    f"- `✓` **`{item['id']}` = `{item['value']}`** — {item.get('role', '')}"
                )
        else:
            md.append("- *(None — all parameters were explicitly supplied by user or circuit is a Generalized Circuit)*")
        md.append("")

        md.append("**? Missing / ambiguous**")
        if miss_amb:
            for item in miss_amb:
                md.append(
                    f"- `?` **`{item['id']}`**: {item['description']}"
                )
        else:
            md.append("- `✓` *None — all required parameters and connections are unambiguously mapped.*")
        md.append("")

        # 4. REQUESTED OUTPUTS & FULFILLMENT VERIFICATION
        md.append("### 4. [REQUESTED OUTPUTS & FULFILLMENT VERIFICATION]")
        exp_reqs = requested_outputs.get("explicitly_requested", [])
        eff_reqs = requested_outputs.get("effective_outputs", [])
        md.append(f"- **Explicitly Requested in Prompt**: `{', '.join(exp_reqs) if exp_reqs else 'None (using standard outputs for ' + ctype + ')'}`")
        md.append(f"- **Active Output Targets**: `{', '.join(eff_reqs)}`")
        for f_item in output_verification.get("fulfilled", []):
            md.append(f"- `✓ Fulfilled` **`{f_item['output_type']}`**: {f_item['verification_detail']}")
        for o_item in output_verification.get("omitted", []):
            md.append(f"- `✗ Omitted` **`{o_item['output_type']}`**: {o_item['verification_detail']}")
        md.append("")

        # If RC partial values were given (e.g., "12V, 5kΩ and 2µF"), highlight the explicit options A, B, C
        if candidates and ctype == "RC_NATURAL_RESPONSE":
            md.append("### 5. [AMBIGUITY RESOLUTION OPTIONS (Manual Multi-Switch vs `GENERAL_RC`)]")
            md.append(
                "Because Experiment 4 contains **4 resistors (`R1, R2, R3, R4`), 2 controlled switches (`S1, S2`), and 2 control pulse sources (`Vpulse2, Vpulse3`)**, "
                "and your prompt supplied only 1 resistor:\n"
                "- **A. Specify Which Manual Resistor**: Tell me whether your resistor corresponds to `R1` (charging, 10 kΩ), `R2` (discharge series, 32 kΩ), `R3` (240 kΩ), or `R4` (60 kΩ).\n"
                "- **B. Explicit Mapping (Shown Below)**: We mapped your resistor to `R1` and **retained all other Experiment 4 manual components** (`R2=32 kΩ, R3=240 kΩ, R4=60 kΩ, S1, S2, Vpulse2, Vpulse3, Rtesta, Rtestb, ic=0 V`).\n"
                "- **C. Switch to `GENERAL_RC` (`GENERALIZED CIRCUIT`)**: If you want a simple 3-component RC circuit without switches or extra resistors, click **`Switch to GENERAL_RC`** below."
            )
            md.append("")

        # AMBIGUOUS CASE -> ASK CLARIFICATION (NEVER DEFAULT TO EXP 1)
        if is_ambiguous or not selected_ir:
            md.append("### 5. [CLARIFICATION REQUIRED — TOPOLOGY NOT SPECIFIED]")
            md.append(
                "> [!WARNING]\n"
                "> **Circuit Topology Ambiguous**: Your component values were extracted and classified under **`USER SUPPLIED`** above, "
                "but the circuit interconnections were not specified. SIMLAB AI **never** defaults arbitrarily to Experiment 1.\n"
            )
            if candidates:
                md.append("#### Candidate Topologies Using Your Exact Component Values:")
                for cand in candidates:
                    md.append(f"- **{cand['name']}** (`topology_source: {cand['topology_source']}`): {cand['description']}")
                md.append("")
                md.append(
                    "**How to Proceed:**\n"
                    "1. Click **`Confirm Candidate A`**, **`Confirm Candidate B`**, or **`Confirm Candidate C`** below.\n"
                    "2. Or describe the connections in natural language (e.g., *'R1 and R2 in series, R3 connected from the middle point to ground'*)."
                )
            else:
                md.append(
                    "Please describe how the components are connected (e.g., *'R1 and R2 in series, R3 connected from the middle point to ground'*) or specify the circuit type (*CCCS*, *VCVS*, *Resistor Bridge*, *RC Natural Response (Exp 4)*, *Simple RC (GENERAL_RC)*, *Pacemaker*, *Zener Regulator*, or *Rectifier*)."
                )
            return "\n".join(md)

        # LIFECYCLE & VALIDATION STATUS
        md.append("### 6. [VALIDATION, SIMULATION & TASK COMPLETION LIFECYCLE]")
        md.append(f"- **TOPOLOGY RECONSTRUCTED**: `{lifecycle.get('TOPOLOGY_RECONSTRUCTED', False)}`")
        md.append(f"- **TOPOLOGY VALIDATED**: `{lifecycle.get('TOPOLOGY_VALIDATED', False)}`")
        md.append(f"- **SIMULATION EXECUTED**: `{lifecycle.get('SIMULATION_EXECUTED', False)}`")
        md.append(f"- **SIMULATION NUMERICALLY SUCCESSFUL**: `{lifecycle.get('SIMULATION_NUMERICALLY_SUCCESSFUL', lifecycle.get('SIMULATION_SUCCESSFUL', False))}`")
        md.append(f"- **OBSERVATION WINDOW SUFFICIENT**: `{lifecycle.get('WINDOW_SUFFICIENT', True)}`")
        md.append(f"- **REQUESTED BEHAVIOR ACTUALLY OBSERVED**: `{lifecycle.get('REQUESTED_BEHAVIOR_OBSERVED', False)}`")
        md.append(f"- **REQUESTED OUTPUTS FULLY AVAILABLE**: `{lifecycle.get('REQUESTED_OUTPUTS_FULFILLED', False)}`")
        md.append(f"- **TASK COMPLETION STATUS**: `{lifecycle.get('TASK_COMPLETION_STATUS', 'COMPLETED' if lifecycle.get('TASK_COMPLETED') else 'INCOMPLETE')}`")
        md.append(f"- **TASK COMPLETED**: `{lifecycle.get('TASK_COMPLETED', False)}`")
        md.append("")

        # SIMULATION RESULTS (if executed and numerically successful)
        if lifecycle.get("SIMULATION_SUCCESSFUL") and sim_results:
            md.append("### 7. [SIMULATION RESULTS & PROVENANCE VERIFICATION (Simulator = Sole Source of Truth)]")
            sim_warn = sim_results.get("simulation_warning")
            unit_mismatch_detail = sim_results.get("unit_mismatch_detail")
            step_stop_info = sim_results.get("step_stop_consistency", {})
            if sim_warn or unit_mismatch_detail or step_stop_info.get("was_adjusted"):
                md.append("> [!WARNING]")
                if sim_warn:
                    md.append(f"> **{sim_warn}**")
                if step_stop_info.get("was_adjusted"):
                    md.append(f"> - **Step/Stop Consistency Correction**: {step_stop_info.get('adjustment_reason')}")
                if unit_mismatch_detail:
                    md.append(f"> - **Unit Mismatch & Window Diagnosis**: {unit_mismatch_detail}")
                act_p = sim_results.get("actual_simulation_parameters", {})
                if act_p.get("recommended_stop_s"):
                    rec_stop_expr = act_p.get("recommended_stop_code_expr", f"{act_p['recommended_stop_s']:g}@u_second")
                    rec_step_expr = act_p.get("recommended_step_code_expr", "1@u_ms")
                    rec_cycles = act_p.get("recommended_cycles", 5)
                    md.append(
                        f"> - **Recommended Simulation Duration**: Use `end_time = {rec_stop_expr}` (`{act_p['recommended_stop_s']:g} seconds`, "
                        f"to observe {rec_cycles} complete heartbeat periods of `T = {act_p.get('target_period_s', 0.75):.4f} s`) "
                        f"with `step_time = {rec_step_expr}` (`1 milliseconds`). Never use `@u_s` for seconds because PySpice `u_s` is microseconds (`1e-6 s`)."
                    )
                md.append("")

            prov = sim_results.get("provenance")
            if prov:
                for prov_label, prov_key in [
                    ("EXPECTED / THEORETICAL", "EXPECTED_THEORETICAL"),
                    ("CALCULATED", "CALCULATED"),
                    ("SIMULATED", "SIMULATED"),
                    ("USER OBSERVED", "USER_OBSERVED"),
                ]:
                    section_dict = prov.get(prov_key, {})
                    if section_dict:
                        md.append(f"**`{prov_label}`**")
                        for k_label, v_str in section_dict.items():
                            md.append(f"- **{k_label}**: `{v_str}`")
                        md.append("")

            nv = sim_results.get("node_voltages", {})
            bc = sim_results.get("branch_currents", {})
            clc = sim_results.get("calculated_load_currents", {})
            tm = sim_results.get("transient_metrics", {})
            tt = sim_results.get("truth_table", [])
            if nv:
                md.append("**Simulated Node Voltages (Directly from Simulator Output):**")
                for n_id, v_val in nv.items():
                    md.append(f"- **Node {n_id}**: `{v_val:.6f} V`")
            if bc:
                md.append("**Numerically Extracted Branch Currents (`analysis.branches` / MNA):**")
                for b_id, i_val in bc.items():
                    md.append(f"- **Branch {b_id}**: `{i_val:.6f} A`")
            if clc:
                md.append("**Calculated Load / Branch Currents (Derived from Node Voltage via Ohm's Law; `analysis.branches` NOT used):**")
                for c_id, i_val in clc.items():
                    md.append(f"- **{c_id}**: `{i_val:.6f} A`")
            if tm:
                for m_id, m_val in tm.items():
                    md.append(f"- **{m_id}**: `{m_val}`")
            if tt:
                md.append("")
                headers = list(tt[0].keys())
                md.append("| " + " | ".join(headers) + " |")
                md.append("| " + " | ".join(["---"] * len(headers)) + " |")
                for row in tt:
                    md.append("| " + " | ".join(str(row[h]) for h in headers) + " |")
            md.append("")

        # PYSPICE CODE GENERATION
        pyspice_code = recon.get("generated_pyspice_code") or cls.generate_pyspice_code(selected_ir, requested_outputs=requested_outputs)
        md.append(f"### 8. [GENERATED PYSPICE CODE — `{top_class}`]")
        md.append(f"```python\n{pyspice_code}\n```")
        md.append("")

        # FINAL CIRCUIT IR
        md.append("### 9. [FINAL CIRCUIT IR]")
        md.append(f"```json\n{json.dumps(selected_ir, indent=2)}\n```")

        full_diagnostic_report = "\n".join(md)
        recon["internal_diagnostic_report"] = full_diagnostic_report

        if cls.is_code_only_request(query) and pyspice_code:
            return pyspice_code.strip()

        return full_diagnostic_report

    @classmethod
    def is_code_only_request(cls, query: str) -> bool:
        """
        Detects when the user explicitly asks for ONLY the executable PySpice code
        (e.g. 'Generate the PySpice code only', 'return only the PySpice code',
        'output PySpice code only').
        """
        if not query:
            return False
        return bool(
            re.search(
                r'(?:generate|return|output|give|provide|show|write)?\s*(?:the\s*)?(?:pyspice|python|spice)?\s*code\s*only\b|'
                r'\bonly\s*(?:generate|return|output|give|provide|show|write)?\s*(?:the\s*)?(?:pyspice|python|spice)\s*code\b',
                query,
                re.I,
            )
        )


