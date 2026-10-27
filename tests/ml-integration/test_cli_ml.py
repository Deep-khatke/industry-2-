"""Integration tests for the fcs-ml command-line interface."""

import pytest

from fcs_ml.cli import main


@pytest.mark.ml_integration
class TestMLCliIntegration:
    """Validate fcs-ml CLI subcommands execution and return codes."""

    def test_cli_inspect_data(self) -> None:
        exit_code = main(["inspect-data"])
        assert exit_code == 0

    def test_cli_verify_data(self) -> None:
        exit_code = main(["verify-data"])
        assert exit_code == 0

    def test_cli_train_logistic(self) -> None:
        exit_code = main(["train", "--model", "logistic", "--track", "deployable"])
        assert exit_code == 0

    def test_cli_evaluate_model(self) -> None:
        exit_code = main(["evaluate", "--model-id", "logisticregression_deployable_subset"])
        assert exit_code == 0

    def test_cli_verify_artifact(self) -> None:
        exit_code = main(["verify-artifact", "--model-id", "logisticregression_deployable_subset"])
        assert exit_code == 0

    def test_cli_predict(self) -> None:
        exit_code = main(["predict", "--model-id", "logisticregression_deployable_subset"])
        assert exit_code == 0

    def test_cli_experiments_list(self) -> None:
        exit_code = main(["experiments", "list"])
        assert exit_code == 0
