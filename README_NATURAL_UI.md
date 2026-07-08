# BlueCarbonCell OS - Natural UI Edition

This version removes the visible Streamlit multipage list such as:

- Previous Main v3 App Preserved
- Original v1 Classic Feasibility
- Original v2 Research Dashboard
- Original v3 Advanced MVP

The app now opens naturally as one unified interface through `app.py`.

## How to run

```bat
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Or double-click:

```bat
RUN_BLUECARBONCELL_OS.bat
```

## Important

All previous code is still kept, but it is no longer shown in the Streamlit sidebar.

Preserved code is stored in:

```text
preserved_previous_code_not_in_ui/
original_versions_do_not_delete/
```

So nothing was deleted; it was only hidden from the app navigation.
