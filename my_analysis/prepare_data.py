import numpy as np
import pandas as pd

from pandas import DataFrame
from box import Box
from queue import Queue
from copy import deepcopy

from nowpipes import pipe

from helpers import (filepath, make_row_codes, count_unique_values, join_range,
                     items_range, mean_prefix, grade_prefix, items_scale_means,
                     grade10, scale_var_names)


@pipe
def data(**p):
    """Load datasets, merge them, apply requirements, and make unique codes"""
    # R PORT: Implements (portions of) <prepare_data.R/data()>,
    # <prepare_data.R/data.model()>
    r = Box()

    # Load hrdata, survey data, and the research model, respectively
    r.hr = pd.read_csv(filepath(p, 'hrfile'))
    r.sv = pd.read_csv(filepath(p, 'svfile'))
    r.rm = pd.read_csv(filepath(p, 'rmfile'))

    print(r.hr.columns)

    # Merge hrdata columns with survey data and only keep cases
    # where both dataframes have data
    r.all = r.sv.merge(r.hr, how='inner', left_on=p['merge_on_sv'],
                       right_on=p['merge_on_hr'])

    # Make identifier codes for rows for merged data and research model
    r.all['code'] = make_row_codes(r.all)
    r.rm['code'] = make_row_codes(r.rm)

    # Only retain survey respondents that gave consent and who finished
    r.use = r.all[r.all[p['finished_column']] == p['finished_value']]
    r.use = r.use[r.use[p['consent_column']] == p['consent_value']]

    return r


@pipe
def nesting(data, **p):
    """Verify that nesting columns exist, count unqique values, and make unique
    codes"""
    # R PORT: Implements (portions of) <prepare_data.R/data()>
    r = dict()

    for column in p['nestings']:
        if column not in data.use.columns:
            raise ValueError(f'Nesting column {column} missing.')

        r[column] = count_unique_values(data.all[column])
        r[column]['code'] = make_row_codes(r[column])

        nesting_size = count_unique_values(data.hr[column])
        nesting_size = nesting_size.rename(columns={'n': 'size'})

        r[column] = r[column].merge(nesting_size, how='inner',
                                    left_on='value', right_on='value')

        r[column]['respons'] = (r[column]['n'] / r[column]['size']) * 100

    return r


@pipe
def research_model(data, **p):
    """Process research model: determine which items to use per defined scale,
    determine their item names in the dataset, and only retain entries that
    should be used in the research model."""
    # R PORT: Implements (portions of) <prepare_data.R/data()>,
    # <prepare_data.R/vars()>

    # Copy original research model and add columns for the range of items and
    # respective column names in the dataset
    r = data.rm[['var', 'meanname', 'prevname', 'direction', 'code',
                 'use', 'subcluster', 'type', 'scalemax']].copy()

    r['items_range'] = data.rm['items'].apply(items_range)
    r['items_names'] = r.apply(lambda row: join_range(row['var'], '_',
                                                      row['items_range']),
                               axis='columns')

    # Determine which items should be reversed from the reserach model
    r['items_reverse_range'] = data.rm['reverse'].apply(items_range)
    r['items_reverse_names'] = r.apply(lambda row: join_range(row['var'], '_',
                                       row['items_reverse_range']),
                                       axis='columns')
    update_rows = r['items_reverse_names'].apply(lambda x: isinstance(x, list))
    r.items_reverse_names.where(update_rows != True, None, inplace=True)

    # Cannot use same name twice.
    # That's why now the "meanname" columns should specify unique
    # names
    # TODO: check unique names same length as rmod
    r['mean_name'] = r['meanname'].apply(mean_prefix)
    r['grade_name'] = r['meanname'].apply(grade_prefix)

    # Only retain entries in research model that should be used
    r['use'] = r['use'].astype('bool')
    r = r[r['use'].eq(True)]

    return r


@pipe
def scale_means(data, research_model, **p):
    """Calculate scale means for scales defined in research model."""
    # Reverse items
    # TODO: put in seperate helper function and call that
    reverse = research_model[['scalemax', 'items_reverse_names']]
    reverse = reverse[reverse.items_reverse_names.apply(lambda x: x != None)]

    for index, rev in reverse.iterrows():
        scalemax, items = rev
        for item in items:
            data.use[item] = (scalemax + 1) - data.use[item]

    # Verify inter-item correlations do not include negative signs
    # ensure_inter_item_corrs(deepcopy(data.use), deepcopy(research_model))

    # Calculate scale means
    means = items_scale_means(data.use, research_model)

    varnames = means.columns
    rm = research_model[research_model['mean_name'].isin(varnames)]
    oldmax = list(DataFrame(rm['scalemax']).iloc[:, 0])

    # Transform scale means to grade scores. Oldmax contains the old
    # scale maximum. Thus, every variable (column in means) will be
    # transformed from its original measurement scale to a 10-point scale.
    q = Queue()
    for x in oldmax:
        q.put(x)

    def grade10_for_column(col, q):
        return col.apply(grade10, oldmax=q.get())

    grades = means.apply(grade10_for_column, args=(q, ), axis='rows')
    grades.columns = research_model['grade_name']

    # Add scale means and grade scores to the survey dataset
    means = pd.concat([means, grades], axis='columns')
    means['code'] = data.use['code']
    data['use'] = data['use'].merge(means, how='left', on='code')
    data['all'] = data['all'].merge(means, how='left', on='code')

    return means


@pipe
def aggregate(data, research_model, nesting, scale_means, **p):
    """Aggregate scale means per nesting column."""
    # R PORT: Implements (portions of) <prepare_data.R/agg()>
    r = dict(nesting={})

    # Get variable names for scale means and grade scores
    varnames = scale_var_names(research_model)

    # Calculate organization-level (grand) scale means and grade scores
    # Add sample size as column 'n'
    r['org'] = DataFrame(data.use[varnames].mean(axis='rows')).transpose()
    r['org']['n'] = len(data.use.index)

    # Calculate aggregated scale means and grade scores for each nesting
    # variable
    for n in p['nestings']:
        subdf = data.use.groupby(n)[varnames].mean()
        subdf['value'] = subdf.index
        subdf = subdf.merge(nesting[n], on='value', how='left')
        r[n] = subdf

    return r
