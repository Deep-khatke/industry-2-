"""Performance and resource limits verification tests for FCS-PFL."""

import os
import psutil
import pytest
import torch

from fcs_pfl.models.mlp import TabularMLPNet


def test_cpu_compatibility_without_gpu() -> None:
    # Model forward and backward must work completely on CPU
    model = TabularMLPNet(input_dim=14, hidden_dims=[64, 32], num_classes=2)
    model.to("cpu")
    x = torch.randn(16, 14, device="cpu")
    out = model(x)
    loss = out.sum()
    loss.backward()
    assert all(p.grad is not None for p in model.parameters())


def test_model_size_under_limit() -> None:
    model = TabularMLPNet(input_dim=14, hidden_dims=[64, 32], num_classes=2)
    param_count = model.get_parameter_count()
    # 14 -> 64 -> 32 -> 2: parameter count should be ~3.2K params
    assert param_count < 100000, f"Model parameter count {param_count} exceeds lightweight tabular threshold"

    # Size in bytes
    size_bytes = sum(p.numel() * p.element_size() for p in model.parameters())
    assert size_bytes < 500 * 1024, "Model parameter footprint exceeds 500KB budget"


def test_memory_usage_bounded() -> None:
    process = psutil.Process(os.getpid())
    rss_mb = process.memory_info().rss / (1024 * 1024)
    # Process memory should be well within standard system RAM (< 2048 MB)
    assert rss_mb < 2048, f"Process memory {rss_mb}MB exceeds 2048MB resource limit"
