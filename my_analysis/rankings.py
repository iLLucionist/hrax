from nowpipes import pipe

from helpers import scale_var_names
from pandas import DataFrame

import numpy as np


def stars_categorize(df, one=1, two=2, three=3):
    """Categorize values in df into stars."""
    # NOTE: Reimplemented categorization using np.digitize, which is immensely
    # faster. Left old implementation for reference.

    # def nstars(x):
    #     if x > three:
    #         return 3
    #     elif x > two:
    #         return 2
    #     elif x > one:
    #         return 1
    #     else:
    #         return 0

    # Calculate number of stars by applying all classification functions and
    # summating their results
    # OLD:
    # return df.apply(np.vectorize(nstars))

    #: NEW
    categories = (float('-inf'), one, two, three, float('inf'))
    return DataFrame(np.digitize(df.values, categories, right=False) - 1,
                     columns=df.columns)


def scores_categorize(df, categories, labels, right=True):
    return DataFrame(np.digitize(df.values, categories, right=right),
                     columns=df.columns)


@pipe
def rankings(weighted_growth, **p):
    """Make one large table where every row represents the weighted growth rank
    per nesting per model per variable."""
    # R PORT: Implements (portions of) <teams.R/teamrankings()>,
    # <teams.R/teamtopall()>

    # TODO: add nesting growth and nesting relative growth as columns

    r = dict()

    for n in p['nestings']:
        # Get weighted growth ranks for nesting per model
        rank = weighted_growth.by_model.rank[n]
        # Reset index so that multi-index becomes columns
        rank.reset_index(inplace=True)
        # Melt variables in columns to rows and repeat multi-index
        df = rank.melt(id_vars=['model', 'level_1'], var_name='var',
                       value_name='rank')
        # Rename level_1 column which reflects nesting entity:
        df.rename(columns={'level_1': 'value'}, inplace=True)
        # Sort values for ease of reading and locality
        df = df.sort_values(['value', 'model', 'rank'])
        # Remove rows where the ranking is NaN
        df = df.dropna()
        # Reset index now that NAs are removed
        df.reset_index(drop=True, inplace=True)

        r[n] = df

    return r


@pipe
def stars(zgrowth, research_model, **p):
    """Categorize nesting growth potentials into stars. This is done by
    transforming a nesting's growth potentials into z-values per variable (as
    every variable has a different distribution), and then assigning stars
    based on cutoff z-values. These z-values can be specified in the analysis
    config."""
    # R PORT: Implements (portions of) <teams.R/teamgrowthdesc()>,
    # <stars.R/teamstars()>
    r = dict(zgrowth=dict())

    varnames = scale_var_names(research_model)

    for n in p['nestings']:
        r[n] = stars_categorize(zgrowth[n][varnames],
                                p.get('one_star_sd'),
                                p.get('two_stars_sd'),
                                p.get('three_stars_sd'))

    return r


@pipe
def highlights(stars, research_model, **p):
    """Highlights are the inverse of stars. That is, highlights indicate
    variables for which entities in a nesting score relatively well in terms of
    their relatively low growth potential."""
    # R PORT: Implements (portions of) <stars.R/teampositive()>

    r = dict()

    for n in p['nestings']:

        r[n] = 1 - stars[n].where(stars[n] == 0, 1)

    return r


@pipe
def frequencies(aggregate, research_model, scale_means, **p):
    r = dict()

    categories = p.get('score_categories', (1, 5, 7, 10))
    labels = p.get('score_category_names', ('low', 'neutral', 'high'))
    varnames = list(research_model.grade_name)

    for n in p['nestings']:
        scores = aggregate[n][varnames]
        r[n] = scores_categorize(scores, categories, labels, right=True)

    return r
