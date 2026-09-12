from ml_features import (
    load_telemetry,
    build_features,
    FEATURES,
    TARGET
)


df = load_telemetry()

print("\nRaw telemetry:")
print(df.head())

print("\nRaw shape:")
print(df.shape)


ml_df = build_features(df)

print("\nML dataset:")
print(ml_df.head())


print("\nML shape:")
print(ml_df.shape)


print("\nFeatures:")
print(ml_df[FEATURES].head())


print("\nTarget:")
print(ml_df[TARGET].head())


print("\nMissing values:")
print(
    ml_df[
        FEATURES + [TARGET]
    ].isnull().sum()
)


print("\nTime range:")

print(
    "Start:",
    ml_df["datetime"].min()
)

print(
    "End:",
    ml_df["datetime"].max()
)