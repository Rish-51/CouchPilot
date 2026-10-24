def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(factor_one, factor_two):
    result = factor_one * factor_two
    return result

def divide(dividend, divisor):
    if divisor == 0:
        raise ValueError("Cannot divide by zero")
    return dividend / divisor

def quick_square(x): return x * x

async def async_compute_sum(numbers):
    total = sum(numbers)
    return total
