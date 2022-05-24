#!/usr/bin/env python3
# (c) 2022 The Danish National Genome Center / Nationalt Genom Center
# Author: KHO@NGC.DK
# Last updated: 21-03-2022 by KHO@NGC.DK

import json

# loading of jsons


def load_json(fname):
    with open(fname) as json_data:
        try:
            return json.load(json_data)
        except:
            return {}

# rounding function


def normal_round(num, ndigits=0):
    """Rounds a float to the specified number of decimal places.
    num: the value to round
    ndigits: the number of digits to round to
    """
    if ndigits == 0:
        return int(num + 0.5)
    else:
        digit_value = 10 ** ndigits
        return int(num * digit_value + 0.5) / digit_value
