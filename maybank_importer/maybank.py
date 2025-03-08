"""Example importer for PDF statements from ACME Bank.

This importer identifies the file from its contents and only supports
filing, it cannot extract any transactions from the PDF conversion to
text.  This is common, and I figured I'd provide an example for how
this works.

"""
__copyright__ = "Copyright (C) 2016  Martin Blais"
__license__ = "GNU GPLv2"

import csv
from datetime import datetime
import re
import logging
import subprocess as sp
from decimal import ROUND_DOWN

from os import path
from io import StringIO
from dateutil.parser import parse
from collections import defaultdict
from dateutil.parser import parse as parse_datetime

from beancount.core import account
from beancount.core import amount
from beancount.core import data
from beancount.core import flags
from beancount.core import position
from beancount.core.number import D
from beancount.core.number import ZERO

import beangulp
from beangulp import mimetypes
from beangulp.cache import cache
from beangulp.testing import main


@cache

def pdf_to_text(path, password=None):
    """
    Generate a text rendering of a PDF file in the form of a list of lines.
    If the PDF is password-protected, the password can be provided.
    The function first tries with the password (if provided) and,
    if it fails, tries without the password.
    """
    def run_pdftotext(args):
        return sp.run(
            args, stdout=sp.PIPE, stderr=sp.PIPE, check=True, text=True
        )

    # First attempt with the password (if provided)
    if password:
        try:
            args_with_password = ['pdftotext', '-layout', '-upw', password, path, '-']
            return run_pdftotext(args_with_password).stdout
        except sp.CalledProcessError as e:
            # If the password is incorrect, try without password
            print("Password failed or incorrect, trying without password...")

    # Try without password
    try:
        args_without_password = ['pdftotext', '-layout', path, '-']
        return run_pdftotext(args_without_password).stdout
    except sp.CalledProcessError as e:
        raise RuntimeError(f"Failed to extract text from the PDF: {e}")

class Importer(beangulp.Importer):
    """An importer for Maybank Bank PDF statements."""

    def __init__(self,account, currency, account_number, password=None, flag='*'):
        self.importer_account = account
        self.currency = currency
        self.flag = flag
        self.account_number = account_number
        self.password = password

    def identify(self, filepath):
        mimetype, encoding = mimetypes.guess_type(filepath)
        if mimetype != 'application/pdf':
            return False

        # Look for some words in the PDF file to figure out if it's a statement
        # from ACME. The filename they provide (Statement.pdf) isn't useful.
        text = pdf_to_text(filepath)
        if text:
            return re.search(self.account_number, text) is not None

    def filename(self, filepath):
        # Normalize the name to something meaningful.
        return 'maybank.pdf'

    def account(self, filepath):
        return self.importer_account

    def date(self, filepath):
        # Get the actual statement's date from the contents of the file.
        text = pdf_to_text(filepath)
        match = re.search(':\s+(\d{2}/\d{2}/\d{2})', text)
        if match:
            return parse_datetime(match.group(1)).date()

    def extract(self,filepath, existing):
        """
        Process a single PDF file: extract text, parse transactions, 
        and save them as CSV and OFX files.
        """
        statement_text = pdf_to_text(filepath, self.password)
        default_account = self.account(filepath)
        currency = self.currency
        current_year = datetime.now().year

        # Regular expression to match the main transaction line
        transaction_pattern = re.compile(r'''
            (\d{2}/\d{2}(?:/\d{2})?)\s+
            (.+?)\s+
            ([0-9,\.]+[+-])\s+
            ([0-9,\.]+)
        ''', re.VERBOSE)

        # Regular expression to match the next line that ends with a '*'
        continuation_pattern = re.compile(r'''
            ^\s*(.{0,40})\*\s*$                     # Line ending with an asterisk
        ''', re.VERBOSE | re.MULTILINE)

        # Split the statement into lines for easier processing
        lines = statement_text.splitlines()

        entries = []
        i = 0
        while i < len(lines):
            line = lines[i]

            # Check for a main transaction line
            match = transaction_pattern.search(line)
            if match:
                entry_date, notes, amount_raw, statement_balance = match.groups()

                # Look ahead for any lines ending in a '*'
                j = i + 1
                continuation_description = ''
                while j < len(lines):
                    next_line = lines[j]
                    continuation_match = continuation_pattern.match(next_line)
                    if continuation_match:
                        continuation_description = continuation_match.group(1).strip()
                        break  # Stop looking once a line ending in '*' is found
                    j += 1

                # Determine if the amount is credit or debit
                amount_raw = amount_raw.replace(',', '')
                if amount_raw.endswith('-'):
                    amount_raw = -float(amount_raw[:-1])  # Debit transactions have a minus sign
                else:
                    amount_raw = float(amount_raw[:-1])  # Credit transactions have a plus sign

                amount_rounded = D(amount_raw).quantize(D('0.00'))
                
                amt = amount.Amount(amount_rounded, currency)
 

                # Check if the date already contains a year (assuming the format is like 'dd/mm' or 'dd/mm/yy')
                if len(entry_date.split('/')) == 2:  # If the year part is missing
                    entry_date += f'/{str(current_year)[-2:]}'  # Append the current year (last two digits)

                entry = data.Transaction(
                    data.new_metadata(filepath, 0, ()),
                    datetime.strptime(entry_date,'%d/%m/%y').date(), "*",
                    continuation_description,
                    notes,
                    data.EMPTY_SET,
                    data.EMPTY_SET,
                    [
                        data.Posting(default_account, amt, None, None, None, None),
                    ],
                )
                entries.append(entry)
            i += 1
        return entries 

if __name__ == '__main__':
    importer = Importer("Assets:MY:Maybank:Checking", "MYR")
    main(importer)
