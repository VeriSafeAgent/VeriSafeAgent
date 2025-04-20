import re
import z3


def parse_expression(expression) -> tuple[str, str, str]:
    expr_pattern = r"([\w\W\d]+)\s?(<=|>=|!=|==|<|>)\s?([\w\W\d]+)"
    expr_match = re.match(expr_pattern, expression)
    if not expr_match:
        raise ValueError(f"Invalid expression: {expression}")
    lexpr, op, rexpr = expr_match.groups()
    return lexpr, op, rexpr


def parse_chc(chc: str) -> tuple[str, str]:
    chc_pattern = r"(.+)\s?(→|->)\s?(.+)"
    chc_match = re.match(chc_pattern, chc)
    if not chc_match:
        raise ValueError(f"Invalid CHC: {chc}")
    cond, _, reached = chc_match.groups()
    return cond.strip(), reached.strip()


def signature_to_z3_const(signature: str) -> z3.ArithRef:
    float_pattern = r"^[0-9]+\.[0-9]+$"
    int_pattern = r"^[0-9]+$"
    if re.match(float_pattern, signature):
        return z3.RealVal(float(signature))
    elif re.match(int_pattern, signature):
        return z3.RealVal(int(signature))
    else:
        return z3.Real(signature.strip())


def expression_to_z3(signature: str) -> z3.BoolRef | bool:
    lexpr, op, rexpr = parse_expression(signature)
    lexpr_z3 = signature_to_z3_const(lexpr)
    rexpr_z3 = signature_to_z3_const(rexpr)
    if op == "<":
        return lexpr_z3 < rexpr_z3
    elif op == ">":
        return lexpr_z3 > rexpr_z3
    elif op == "<=":
        return lexpr_z3 <= rexpr_z3
    elif op == ">=":
        return lexpr_z3 >= rexpr_z3
    elif op == "!=":
        return lexpr_z3 != rexpr_z3
    elif op == "=" or op == "==":
        return lexpr_z3 == rexpr_z3
    else:
        raise ValueError(f"Invalid operator: {op}")


def is_valid(chc: str) -> bool:
    cond, reached = parse_chc(chc)
    cond_z3 = expression_to_z3(cond)
    reached_z3 = expression_to_z3(reached)

    # Check if cond -> reached is valid by checking if !(cond -> reached) is unsatisfiable
    solver = z3.Solver()
    solver.add(z3.Not(z3.Implies(cond_z3, reached_z3)))
    is_unsat = solver.check()
    result = True
    if is_unsat == z3.unsat:
        result = True
    else:
        result = False
    return result
