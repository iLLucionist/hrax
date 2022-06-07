from nowpipes import pipe
from box import Box
from helpers import filepath
from copy import deepcopy

import pandas as pd


def has_prev(results, nesting):
    return nesting in results.prev


def has_prev_for_nesting_no(prev, no):
    return no in list(prev.no)


def remap_prev(mapping, df):
    return df.rename(columns=mapping)


def mappable_prev_varnames(research_model):
    mappable = research_model[research_model.prevname.isnull() == False]
    return dict(zip(mappable.prevname, mappable.meanname))


def prev_only_keep_existing_nesting_values(nesting, prev):
    exist = nesting[nesting.value.isin(prev.value)]
    exist = deepcopy(exist)
    exist['no'] = exist.index
    existing_df = exist.merge(prev, left_on="value",
                              right_on="value", how="inner")
    return existing_df


@pipe
def prev(research_model, nesting, **p):
    """
    Load and transform scores from previous (hence prev) years to
    """
    r = Box()

    mapping = mappable_prev_varnames(research_model)

    if 'prev_aggregate_org' in p:
        r.org = pd.read_csv(filepath(p, 'prev_aggregate_org'))
        r.org = remap_prev(mapping, r.org)

    for n in p['nestings']:
        key = 'prev_aggregate_' + n
        if key not in p:
            continue
        r[n] = pd.read_csv(filepath(p, key))
        r[n] = remap_prev(mapping, r[n])
        r[n] = prev_only_keep_existing_nesting_values(nesting[n], r[n])

    return r
