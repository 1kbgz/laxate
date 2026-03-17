"""
Synthetic benchmarks for laxate.

These benchmarks exercise basic Python operations to verify
the ASV benchmark infrastructure is working end-to-end.
"""

import json
import math


class ConfigParseSuite:
    """Benchmarks for configuration parsing operations."""

    params = ([10, 100, 1000],)
    param_names = ["num_keys"]

    def setup(self, num_keys):
        self.data = {f"key_{i}": f"value_{i}" for i in range(num_keys)}
        self.json_str = json.dumps(self.data)

    def time_json_roundtrip(self, num_keys):
        """Time JSON serialization and deserialization."""
        json.loads(json.dumps(self.data))

    def time_json_parse(self, num_keys):
        """Time JSON deserialization."""
        json.loads(self.json_str)

    def time_dict_merge(self, num_keys):
        """Time dictionary merge (config override pattern)."""
        base = {f"base_{i}": i for i in range(num_keys)}
        override = {f"key_{i}": f"override_{i}" for i in range(num_keys // 2)}
        {**base, **override}


class ComputeSuite:
    """Simple compute benchmarks to track runner performance."""

    params = ([100, 1000, 10000],)
    param_names = ["iterations"]

    def time_math_operations(self, iterations):
        """Time basic math operations."""
        total = 0.0
        for i in range(1, iterations + 1):
            total += math.sqrt(i) * math.log(i + 1)

    def time_list_comprehension(self, iterations):
        """Time list creation and processing."""
        data = [i * i for i in range(iterations)]
        sum(data)

    def time_string_formatting(self, iterations):
        """Time string formatting operations."""
        for i in range(iterations):
            f"benchmark-runner-{i:06d}-result"
