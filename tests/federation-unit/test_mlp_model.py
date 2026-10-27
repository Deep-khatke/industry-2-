"""Unit tests for TabularMLPNet model, parameter serialization, and digests."""

import numpy as np
import pytest
import torch

from fcs_pfl.models.mlp import TabularMLPNet, compute_model_digest, get_parameters, set_parameters


def test_mlp_model_forward() -> None:
    model = TabularMLPNet(input_dim=14, hidden_dims=[64, 32], num_classes=2, use_group_norm=False)
    x = torch.randn(8, 14)
    out = model(x)
    assert out.shape == (8, 2)


def test_mlp_group_norm_compatibility() -> None:
    # Opacus-compatible normalization
    model = TabularMLPNet(input_dim=14, hidden_dims=[64, 32], num_classes=2, use_group_norm=True)
    x = torch.randn(8, 14)
    out = model(x)
    assert out.shape == (8, 2)
    # Check that GroupNorm is present in layers
    has_gn = any(isinstance(m, torch.nn.GroupNorm) for m in model.modules())
    assert has_gn


def test_parameter_serialization_roundtrip() -> None:
    model1 = TabularMLPNet(input_dim=14, hidden_dims=[32], num_classes=2)
    model2 = TabularMLPNet(input_dim=14, hidden_dims=[32], num_classes=2)

    params = model1.get_parameters()
    model2.set_parameters(params)
    model1.eval()
    model2.eval()

    # Verify identical output on same input
    x = torch.randn(5, 14)
    with torch.no_grad():
        out1 = model1(x)
        out2 = model2(x)
    np.testing.assert_allclose(out1.numpy(), out2.numpy(), atol=1e-6)


def test_model_digest_deterministic() -> None:
    torch.manual_seed(42)
    model1 = TabularMLPNet(input_dim=14, hidden_dims=[32], num_classes=2)
    torch.manual_seed(42)
    model2 = TabularMLPNet(input_dim=14, hidden_dims=[32], num_classes=2)

    digest1 = model1.compute_model_digest()
    digest2 = model2.compute_model_digest()
    assert digest1 == digest2
    assert len(digest1) == 64  # SHA-256 hex string
