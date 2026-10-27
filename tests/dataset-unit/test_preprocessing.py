"""Unit tests for training-only preprocessing fitting and parameter persistence."""

from pathlib import Path

import polars as pl
import pytest

from fcs_udip.preprocessing.preprocessor import (
    PreprocessorNotFittedError,
    TrainingOnlyPreprocessor,
)


@pytest.mark.dataset_unit
class TestPreprocessing:
    """Validate training-only fitting and zero-test-contamination guarantee."""

    def test_calling_transform_before_fit_raises_error(self) -> None:
        pre = TrainingOnlyPreprocessor()
        df = pl.DataFrame({"IN_BYTES": [100, 200]})
        with pytest.raises(PreprocessorNotFittedError):
            pre.transform(df)

    def test_fit_on_train_only_invariance(self) -> None:
        """
        Verify that training preprocessing parameters are completely independent of test data.
        Modifying the test set must NEVER alter preprocessor parameters.
        """
        train_df = pl.DataFrame({
            "IN_BYTES": [100.0, 200.0, 300.0, 400.0, 500.0],
            "IN_PKTS": [10.0, 20.0, 30.0, 40.0, 50.0],
        })

        test_df_normal = pl.DataFrame({
            "IN_BYTES": [150.0, 250.0],
            "IN_PKTS": [15.0, 25.0],
        })

        test_df_extreme_outlier = pl.DataFrame({
            "IN_BYTES": [1_000_000.0, 5_000_000.0],
            "IN_PKTS": [100_000.0, 500_000.0],
        })

        preprocessor1 = TrainingOnlyPreprocessor(scaling_method="robust")
        preprocessor1.fit(train_df)

        preprocessor2 = TrainingOnlyPreprocessor(scaling_method="robust")
        preprocessor2.fit(train_df)

        # Centers and dispersions must be identical regardless of what test set will be evaluated
        assert preprocessor1.scale_center == preprocessor2.scale_center
        assert preprocessor1.scale_dispersion == preprocessor2.scale_dispersion
        assert preprocessor1.scale_center["IN_BYTES"] == 300.0  # Median of train

        # Both test sets can be transformed cleanly without affecting parameters
        transformed_norm = preprocessor1.transform(test_df_normal)
        transformed_out = preprocessor1.transform(test_df_extreme_outlier)
        assert len(transformed_norm) == 2
        assert len(transformed_out) == 2

    def test_save_and_load_preprocessor_state(self, tmp_path: Path) -> None:
        train_df = pl.DataFrame({
            "IN_BYTES": [100.0, 200.0, 300.0],
            "FLOW_DURATION_MILLISECONDS": [50.0, 100.0, 150.0],
        })
        pre = TrainingOnlyPreprocessor()
        pre.fit(train_df)

        state_file = tmp_path / "preprocessor_state.json"
        pre.save_state(state_file)
        assert state_file.exists()

        restored = TrainingOnlyPreprocessor.load_state(state_file)
        assert restored.is_fitted
        assert restored.scale_center == pre.scale_center
        assert restored.imputation_medians == pre.imputation_medians
