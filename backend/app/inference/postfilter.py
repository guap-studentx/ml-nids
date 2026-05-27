import pandas as pd


def apply_postfilter(df: pd.DataFrame) -> pd.DataFrame:
    required = {"bidirectional_packets", "bidirectional_rst_packets", "bidirectional_fin_packets"}
    if not required.issubset(df.columns):
        return df.copy()

    return df[
        ~(
            (df["bidirectional_packets"] == 1)
            & (
                (df["bidirectional_rst_packets"] == 1)
                | (df["bidirectional_fin_packets"] == 1)
            )
        )
    ].copy()
