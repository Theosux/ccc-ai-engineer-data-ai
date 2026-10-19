# Resources

## Installed / required (see `requirements.txt`; verified on Windows + Python 3.14 on 2026-10-19)
pandas 3.0, numpy, scipy, scikit-learn 1.9.1, LightGBM 4.7.0, XGBoost 3.4.1, ortools, networkx; plus requests,
playwright, pypdf, pypdfium2 for the CLI. All have Python 3.14 Windows wheels (research report B §5.1).

## Optional (install BEFORE contest day if wanted; never mid-contest)
| Package | When |
|---|---|
| `pyarrow` | parquet caching of big tables |
| `catboost` | categorical-heavy tabular data |
| `matplotlib` | looking at hidden pictures / scatter plots (Spy Mission) |
| `optuna` | RMSE "improve" ladders |
| `imbalanced-learn` | imbalanced macro-F1 levels |
| `statsmodels` | classical time series |
| `torch` + `torchvision` (CUDA build from `https://download.pytorch.org/whl/cu126` if you have an NVIDIA GPU) | images |
| `sentence-transformers`, `timm` | text / image embeddings (insurance only) |

Pre-download weights (venue Wi-Fi insurance, ~0.4 GB):
```
python -c "import torchvision.models as m; m.resnet18(weights='DEFAULT'); m.resnet50(weights='DEFAULT'); m.efficientnet_b0(weights='DEFAULT')"
```

## References
- scikit-learn model selection (KFold, GroupKFold, TimeSeriesSplit): https://scikit-learn.org/stable/modules/cross_validation.html
- HistGradientBoosting (native NaN + categoricals): https://scikit-learn.org/stable/modules/ensemble.html#histogram-based-gradient-boosting
- LightGBM parameters: https://lightgbm.readthedocs.io/en/latest/Parameters.html
- Past statements: [datasets.md](datasets.md)
