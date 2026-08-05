"""Synthetic benchmarks for Laxate's Benched workflow."""

import json
import math

import pytest


@pytest.fixture
def config_data(num_keys):
    data = {f"key_{index}": f"value_{index}" for index in range(num_keys)}
    return data, json.dumps(data)


@pytest.mark.benchmark(group="config")
@pytest.mark.parametrize("num_keys", [10, 100, 1000])
@pytest.mark.parametrize("operation", ["roundtrip", "parse", "merge"])
def test_config_operation(benchmark, config_data, num_keys, operation):
    """Benchmark one configuration-processing operation."""
    data, serialized = config_data

    if operation == "roundtrip":
        benchmark(lambda: json.loads(json.dumps(data)))
    elif operation == "parse":
        benchmark(json.loads, serialized)
    else:
        base = {f"base_{index}": index for index in range(num_keys)}
        override = {f"key_{index}": f"override_{index}" for index in range(num_keys // 2)}
        benchmark(lambda: {**base, **override})


def _math_operations(iterations):
    total = 0.0
    for index in range(1, iterations + 1):
        total += math.sqrt(index) * math.log(index + 1)
    return total


def _list_comprehension(iterations):
    data = [index * index for index in range(iterations)]
    return sum(data)


def _string_formatting(iterations):
    result = ""
    for index in range(iterations):
        result = f"benchmark-runner-{index:06d}-result"
    return result


@pytest.mark.benchmark(group="compute")
@pytest.mark.parametrize("iterations", [100, 1000, 10000])
@pytest.mark.parametrize(
    "operation",
    [_math_operations, _list_comprehension, _string_formatting],
    ids=["math", "list", "format"],
)
def test_compute_operation(benchmark, iterations, operation):
    """Benchmark one synthetic compute operation."""
    benchmark(operation, iterations)
