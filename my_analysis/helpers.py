import os
import yaml
import sys
from functools import reduce

from importlib import reload
from datetime import datetime

import numpy as np
from numpy import isnan

import pandas as pd
from pandas import DataFrame, isnull

from scipy.stats import zscore


def reload_modules(modnames=[]):
    for modname in modnames:
        __import__(modname)
        reload(sys.modules[modname])


def pick(cond, x, y):
    return x if cond else y


def filepath(p, f):
    return p['datapath'] + p[f]


def load_yaml(fname):
    """Load a YAML file."""
    with open(fname, 'r') as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as e:
            print(e)


def count_unique_values(column):
    """Return unique column values as dataframe with the values and counts"""
    return DataFrame(np.transpose(np.unique(column,
                                            return_counts=True)),
                     columns=('value', 'n'))


def make_row_codes(df_or_column):
    """Generate row codes for an n x p or n matrix"""
    return df_or_column.index + 1


def expand_range(v):
    """Generate all integers in the range between two tuple values"""
    return tuple(range(int(v[0]), int(v[1]) + 1))


def join_range(pfx, sep, v):
    """Join a series of numbers into variable names, essentially"""
    if (len(v) == 0):
        return [pfx]
    return (pfx + sep + str(i) for i in v)


def mean_prefix(var):
    """Return variable name with prefix indicating its a mean score"""
    return 'm_' + var


def grade_prefix(var):
    """Return variable name with prefix indicating its a grade score"""
    return 'g_' + var


def scale_var_names(rm):
    """Return all scale names for all scores in research model. As of currently,
    these are mean scores and grade scores."""
    return list(rm.mean_name) + list(rm.grade_name)


def scale_positive_var_names(rm):
    """Return all variable names that have a positive direction as indicated in
    the research model."""
    return list(rm[rm.direction == 'positive']
                [['mean_name', 'grade_name']].melt().value)


def scale_negative_var_names(rm):
    """Return all variable names that have a negative direction as indicated in
    the research model."""
    return list(rm[rm.direction == 'negative']
                [['mean_name', 'grade_name']].melt().value)


def scale_iv_var_names(rm):
    """Return all variable names that are of type iv in the research model."""
    return rm[rm.type == 'iv'][['mean_name', 'grade_name']]


def scale_dv_var_names(rm):
    """Return all variable names that are of dv in the research model."""
    return rm[rm.type == 'dv'][['mean_name', 'grade_name']]


def items_range(value):
    """Expand special range syntax to a tuple of numeric value.

    Use ',' to separate numbers, and '-' to indicate a range of numbers.

    Examples:
    '10' -> ( 10, )
    '10,11,12' -> ( 10, 11, 12 )
    '5-7' -> ( 5, 6, 7 )
    '1, 3-5, 8' -> ( 1, 3, 4, 5, 8 )
    """
    stack = (value,) if ',' not in value else value.split(',')

    if len(value) == 1:
        if int(value[0]) == 0:
            return []

    stack = map(lambda v: (v,) if '-' not in v else expand_range(tuple(v.split('-'
                                                                               ))), stack)
    return list(reduce(lambda a, b: a + b, stack))


def scale_names(rm, prefix=None):
    """Get the names of all the used scales. If prefix parameter provided,
    concatenate scale names with prefix.
    """
    names = rm['var']
    if prefix is None:
        return names
    elif callable(prefix):
        return list(map(prefix, names))
    elif isinstance(prefix, str):
        return [prefix + n for n in names]


def items_scale_means(df, rm):
    """Calculate means per row per scale items as defined in research model."""
    subdfs = rm.apply(lambda row: df[list(row['items_names'])], axis='columns')
    varnames = scale_var_names(rm)
    means = pd.DataFrame(dict(zip(varnames, list(map(lambda subdf: subdf.mean(
        axis='columns'), subdfs)))))
    return(means)


#TODO: What is going on here?
def get_inter_item_corrs(df, rm):
    subdfs = rm.apply(lambda row: df[list(row['items_names'])], axis='columns')
    varnames = scale_var_names(rm)
    corrs = dict(zip(varnames, list(map(lambda subdf: subdf.corr(), subdfs))))

    problems = []

    for varname, subdf in corrs.items():
        test = subdf.values < 0
        if True in test:
            problems.append(varname)

    if len(problems) > 0:
        raise ValueError('There are negative inter-item corrs for scales: ' +
                         ' '.join(problems))

    return True


def rm_subcluster_vars(clus, rm, op):
    """Return variable names from a subcluster from the research model and apply
    specified operation to the variable names (e.g., scale name or grade name)."""
    return list(rm[rm.subcluster == clus]['meanname'].apply(op))


def scale_quantiles(df, rm, q):
    """Calculate quantiles for all scales in research model based on specified
    quantiles in q tuple.

    WARNING: pandas.quantile automatically orders results from lowest to highest
    quantile. For example, q = (0.1, 0.9) and q = (0.9, 0.1) will both return
    quantile scores with two columns [0.1, 0.9].
    """
    varnames = scale_var_names(rm)
    return df[varnames].apply(lambda col: col.quantile(q), axis='rows')


def score_percentage(score, oldmax=7):
    """Convert score to percentage"""
    if isnan(score):
        return 0
    percentage = (float(score) - 1) / (oldmax - 1)
    return percentage


def score_percentage_multiply(score, oldmax=7, doround=False):
    percentage = score_percentage(score, oldmax) * 100
    if doround and not isnull(percentage):
        percentage = round(percentage)
    return percentage


def score_transform(score, oldmin=1, oldmax=7, newmin=1, newmax=10):
    """Apply linear transformation to a score to realign it from and old range
    to a new range."""
    percentage = score_percentage(score, oldmax)
    return (percentage * (newmax - newmin)) + 1


def grade10(score, oldmin=1, oldmax=7):
    """Transform the old score to a grade score, ranging from 1 to 10."""
    # print(f"grade10: [{oldmin}, {oldmax}] => {score}")
    return score_transform(score, oldmin, oldmax, 1, 10)


def df_standardize(df, axis='rows'):
    """Calculate standardized (z) scores per column or rows in specified
    dataframe."""

    # Apply zscore over axis
    return df.apply(zscore, axis=axis)


def delete_file_if_exists(fname):
    if os.path.exists(fname):
        os.remove(fname)


def df_to_list(df, rename=None, keep=None):
    df.reset_index(inplace=True, drop=True)
    df.index = df.index + 1
    df['number'] = df.index

    if rename is not None:
        df = df.rename(columns=rename)
    if keep is not None:
        df = df[keep]

    return df.transpose().to_dict().values()


def sanitize_filename(f):
    f = f.replace(" ", '-')
    f = f.replace("/", '-')
    f = f.replace("&", 'en')
    f = f.replace("+", 'en')
    f = f.replace(".", ' ')
    return f


def make_str_date(fmt="%Y-%m-%d_%I-%M-%S"):
    return datetime.now().strftime(fmt)


def make_report_fname(nesting, no, value, sanitize=sanitize_filename):
    fname = nesting + '_' + str(no) + '_' + sanitize(value)
    return(fname)


def make_org_report_fname(name):
    dt = make_str_date()
    fname = name + '_' + str(dt)
    return fname


def isinteractive():
    import sys
    return bool(getattr(sys, 'ps1', sys.flags.interactive))


def make_correlation_table(df, names=None, round=2):
    corrs = df.corr().round(round)

    if names is not None:
        names = names.set_index(corrs.index)
        corrs.insert(0, 'name', names.name)

    return corrs


def top_effects(results, model_name, n=5):
    effects = results.models[model_name].ivstats
    effects = effects.sort_values('mean_est', ascending=False).head(n)
    return effects


def top_effects_table(results, n=5):
    modnames = list(results.models.all.table.model.unique())
    top_effects_table = list(map(lambda x: top_effects(results, x), modnames))
    top_effects_table = pd.concat(top_effects_table)
    return top_effects_table
