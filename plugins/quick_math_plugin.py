"""Quick Math Quiz Plugin - Practice mental math."""

from plugins.plugin_loader import PluginBase
import random


class QuickMathPlugin(PluginBase):
    name = "quick_math"
    description = "Practice mental math with random quizzes"
    triggers = ["math quiz", "practice math", "times table", "mental math",
                 "math test", "arithmetic"]

    async def execute(self, command: str, context: dict = None) -> str:
        lower = command.lower()

        if "times table" in lower:
            import re
            n_match = re.search(r'(\d+)', lower)
            n = int(n_match.group(1)) if n_match else random.randint(2, 12)
            result = f"Times table for {n}:\n"
            for i in range(1, 13):
                result += f"  {n} x {i} = {n * i}\n"
            return result

        ops = [('+', lambda a, b: a + b), ('-', lambda a, b: a - b),
               ('x', lambda a, b: a * b)]
        op_name, op_func = random.choice(ops)
        if op_name == 'x':
            a, b = random.randint(2, 12), random.randint(2, 12)
        else:
            a, b = random.randint(10, 99), random.randint(10, 99)
            if op_name == '-' and a < b:
                a, b = b, a

        answer = op_func(a, b)
        return f"Quick Math!\n\n  {a} {op_name} {b} = ?\n\n(Answer: {answer})"
