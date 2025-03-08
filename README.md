# maybank-importer
An importer for maybank PDF Card Statements to beancount.

At the moment only checking/saving accounts and MAE. No support for credit cards at the moment.

Based on the beangulp framework: https://github.com/beancount/beangulp.


## Installation
``` pip install git+https://github.com/AmmarShaqeel/maybank-importer.git```

Requires popplertools (specifically pdftotext): https://poppler.freedesktop.org/

For OpenSuse, run:
```sudo zypper install poppler-tools```

## Usage
Create a setup.py file as below.
Substitute the account/card number with your own.

You can also optionally include a password, if your files are password protected.

Then run:

```python import.py extract YourCardStatement.PDF```


###  Example Setup.py:


```python
from maybank_importer import maybank

importers = [

    maybank.Importer("Assets:Maybank:MAE", "MYR", "164324-550652"),
]

def clean_up_descriptions(extracted_entries):
    """Example filter function; clean up cruft from narrations.

    Args:
      extracted_entries: A list of directives.
    Returns:
      A new list of directives with possibly modified payees and narration
      fields.
    """
    clean_entries = []
    for entry in extracted_entries:
        if isinstance(entry, data.Transaction):
            if entry.narration and " / " in entry.narration:
                left_part, _ = entry.narration.split(" / ")
                entry = entry._replace(narration=left_part)
            if entry.payee and " / " in entry.payee:
                left_part, _ = entry.payee.split(" / ")
                entry = entry._replace(payee=left_part)
        clean_entries.append(entry)
    return clean_entries


def process_extracted_entries(extracted_entries_list, ledger_entries):
    """Example filter function; clean up cruft from narrations.

    Args:
      extracted_entries_list: A list of (filename, entries) pairs, where
        'entries' are the directives extract from 'filename'.
      ledger_entries: If provided, a list of directives from the existing
        ledger of the user. This is non-None if the user provided their
        ledger file as an option.
    Returns:
      A possibly different version of extracted_entries_list, a list of
      (filename, entries), to be printed.
    """
    return [(filename, clean_up_descriptions(entries), account, importer)
            for filename, entries, account, importer in extracted_entries_list]


hooks = [process_extracted_entries]

if __name__ == '__main__':
    ingest = beangulp.Ingest(importers, hooks)
    ingest()
```

