"""Training-only preprocessing pipeline, parameter serialization, and transform execution."""

import json
from pathlib import Path

import numpy as np
import polars as pl


class PreprocessorNotFittedError(Exception):
    """Raised when transform() is called before fit()."""


class TrainingOnlyPreprocessor:
    """
    Executes training-only statistical fitting and transform application.
    STRICT DATA LEAKAGE RULE:
        fit() consumes ONLY the training split.
        Validation and test splits are strictly evaluated via transform(),
        never contributing to mean, median, standard deviation, or scaling boundaries.
    """

    def __init__(
        self,
        scaling_method: str = "robust",  # 'robust' (median/IQR) or 'standard' (mean/std)
        features_to_scale: list[str] | None = None,
    ) -> None:
        self.scaling_method = scaling_method
        self.features_to_scale = features_to_scale
        self.is_fitted = False
        self.imputation_medians: dict[str, float] = {}
        self.scale_center: dict[str, float] = {}
        self.scale_dispersion: dict[str, float] = {}
        self.feature_columns: list[str] = []

    def fit(self, train_df: pl.DataFrame) -> "TrainingOnlyPreprocessor":
        """Fit preprocessing parameters strictly on the training partition."""
        if len(train_df) == 0:
            raise ValueError("Cannot fit preprocessor on empty training dataframe")

        # Select numeric feature columns
        numeric_cols = [
            col
            for col, dtype in train_df.schema.items()
            if dtype in (pl.Float32, pl.Float64, pl.Int32, pl.Int64)
            and col not in ("Label", "label", "binary_label")
        ]
        self.feature_columns = numeric_cols

        cols_to_scale = self.features_to_scale or [
            c for c in numeric_cols
            if any(k in c for k in ["BYTES", "PKTS", "DURATION", "THROUGHPUT", "TTL"])
        ]

        # Learn median imputations
        for col in numeric_cols:
            series = train_df[col].drop_nulls().drop_nans()
            med = series.median()
            if isinstance(med, (int, float)):
                self.imputation_medians[col] = float(med)
            else:
                self.imputation_medians[col] = 0.0

        # Learn scaling centers and dispersions
        for col in cols_to_scale:
            if col in train_df.columns:
                arr = train_df[col].to_numpy()
                arr = arr[~np.isnan(arr)]
                if len(arr) == 0:
                    continue

                if self.scaling_method == "robust":
                    q25 = float(np.percentile(arr, 25))
                    q50 = float(np.median(arr))
                    q75 = float(np.percentile(arr, 75))
                    iqr = q75 - q25
                    dispersion = iqr if iqr > 1e-6 else 1.0
                    self.scale_center[col] = q50
                    self.scale_dispersion[col] = dispersion
                else:  # standard
                    mean_val = float(np.mean(arr))
                    std_val = float(np.std(arr))
                    dispersion = std_val if std_val > 1e-6 else 1.0
                    self.scale_center[col] = mean_val
                    self.scale_dispersion[col] = dispersion

        self.is_fitted = True
        return self

    def transform(self, df: pl.DataFrame) -> pl.DataFrame:
        """Apply learned imputations and scalers to a partition (train, val, or test)."""
        if not self.is_fitted:
            raise PreprocessorNotFittedError("Preprocessor must be fitted on training data before calling transform().")

        transformed_df = df
        exprs: list[pl.Expr] = []

        for col in self.feature_columns:
            if col in transformed_df.columns:
                med_val = self.imputation_medians.get(col, 0.0)
                expr = pl.col(col).fill_nan(med_val).fill_null(med_val)

                if col in self.scale_center and col in self.scale_dispersion:
                    center = self.scale_center[col]
                    disp = self.scale_dispersion[col]
                    expr = (expr.cast(pl.Float32) - center) / disp

                exprs.append(expr.alias(col))

        if exprs:
            transformed_df = transformed_df.with_columns(exprs)

        return transformed_df

    def save_state(self, output_path: Path | str) -> None:
        """Serialize fitted parameters to JSON for Phase 3 model training and inference."""
        if not self.is_fitted:
            raise PreprocessorNotFittedError("Cannot serialize unfitted preprocessor state.")
        state = {
            "version": "1.2.0",
            "scaling_method": self.scaling_method,
            "feature_columns": self.feature_columns,
            "imputation_medians": self.imputation_medians,
            "scale_center": self.scale_center,
            "scale_dispersion": self.scale_dispersion,
        }
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, sort_keys=True)

    @classmethod
    def load_state(cls, input_path: Path | str) -> "TrainingOnlyPreprocessor":
        """Restore fitted preprocessor state from serialized JSON artifact."""
        p = Path(input_path)
        with p.open("r", encoding="utf-8") as f:
            state = json.load(f)

        preprocessor = cls(scaling_method=state.get("scaling_method", "robust"))
        preprocessor.feature_columns = state.get("feature_columns", [])
        preprocessor.imputation_medians = state.get("imputation_medians", {})
        preprocessor.scale_center = state.get("scale_center", {})
        preprocessor.scale_dispersion = state.get("scale_dispersion", {})
        preprocessor.is_fitted = True
        return preprocessor
