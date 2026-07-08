
# BlueCarbonCell OS v3 - All Versions Preserved

This package keeps **all code from all previous versions** and uses Version 3 as the main app.

## What is inside

- `app.py`  
  The main BlueCarbonCell OS v3 app.

- `pages/01_Original_v1_Classic_Feasibility.py`  
  The full original v1 app code, preserved as a Streamlit page.

- `pages/02_Original_v2_Research_Dashboard.py`  
  The full original v2 app code, preserved as a Streamlit page.

- `pages/03_Original_v3_Advanced_MVP.py`  
  The full original v3 app code, preserved as a Streamlit page.

- `original_versions_do_not_delete/`  
  A complete archive of the original v1, v2 and v3 folders exactly as extracted from the uploaded ZIP files.

- `requirements.txt`  
  Combined requirements from all versions.

- `INSTALL_REQUIREMENTS.bat`  
  Windows helper for installing packages.

- `RUN_BLUECARBONCELL_OS.bat`  
  Windows helper for launching the app.

## How to run on Windows

First install requirements:

```bat
python -m pip install -r requirements.txt
```

Then run the app:

```bat
python -m streamlit run app.py
```

Or double-click:

```bat
RUN_BLUECARBONCELL_OS.bat
```

## Why `python -m streamlit`?

On Windows, the command `streamlit run app.py` may fail with:

```text
'streamlit' is not recognized as an internal or external command
```

This happens when Streamlit is installed but its command-line shortcut is not in PATH.

Use this instead:

```bat
python -m streamlit run app.py
```

## Important research disclaimer

BlueCarbonCell OS is a research MVP. It is for preliminary feasibility assessment, scenario comparison, uncertainty analysis and PhD/spin-off demonstration.

It does **not** replace:
- MCFC experiments;
- detailed electrochemical stack modelling;
- CFD;
- naval engineering design;
- safety assessment;
- classification approval;
- real pilot validation.
