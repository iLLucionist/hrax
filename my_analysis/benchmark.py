import pandas as pd

from pandas import DataFrame

from nowpipes import pipe

from helpers import (scale_var_names, scale_negative_var_names, df_standardize,
                     score_percentage_multiply)


def r10_quantiles(df, varnames, lo, hi, pfx=''):
    """Calculate quantiles for specified variables in provided dataframe based
    on the specified low and high quantiles. Optional postfix can be provided
    that will be appended to the resulting dataframe's column names.

    WARNING: pandas.quantile automatically orders results from lowest to
    highest quantile. For example, q = (0.1, 0.9) and q = (0.9, 0.1) will both
    return quantile scores with two columns[0.1, 0.9].
    """
    q = df[varnames].quantile((lo, hi)).transpose()
    q.columns = ('low10' + pfx, 'high10' + pfx)
    return q


def r10_from_quantiles_and_direction(row):
    """Select the correct r10 comparison standard depending on the direction of
    a specified variable, typically specified in the research model. When the
    direction is positive, return the higher r10 comparison standard value.
    When the direction is negative, return the lower r10 comparison standard.
    This function returns these values for both the scale mean and grade
    scores."""

    if row.direction == 'positive':
        return pd.Series([row.high10_mean,
                          row.high10_grade])
    elif row.direction == 'negative':
        return pd.Series([row.low10_mean,
                          row.low10_grade])


def r10_nesting_comparison_values(nesting, r10, research_model):
    """Returns the r10 comparison values for the specified nesting variable."""
    n = nesting
    # Get r10 comparison values for scale means and grade scores
    g = r10[n][['mean_name', 'r10_mean', 'grade_name', 'r10_grade']]
    # Reshape them into one long list
    g = g.melt(id_vars=['mean_name', 'grade_name'],
               var_name='var', value_name='growth')
    # Add their respective variable column names from the research model
    g['var_name'] = scale_var_names(research_model)
    # Retain only the necessary columns
    g = g[['var_name', 'growth']]
    # Use the variable column name as index for easy calculations further on
    g.set_index('var_name', inplace=True)
    return g


def make_r10_df(df, scores, q_lo, q_hi):
    """
    Make an r10 dataframe based on the base df in r10() and using provided
    scores.
    """
    df = df.copy()

    # Quantiles for mean scores and grade scores, respectively
    # NOTE: These use the nesting's aggregate scores.
    df = df.merge(r10_quantiles(scores, df.mean_name, q_lo, q_hi,
                                pfx='_mean'),
                  left_on='mean_name', right_index=True, how='left')

    df = df.merge(r10_quantiles(scores, df.grade_name, q_lo, q_hi,
                                pfx='_grade'),
                  left_on='grade_name', right_index=True, how='left')

    # Select r10 value based on the direction in basedf
    r10_values = df.apply(r10_from_quantiles_and_direction,
                          axis='columns')
    df[['r10_mean', 'r10_grade']] = r10_values

    # Convert low10 and high10 grade to percentages
    df['low10_grade_per'] = df['low10_grade'].apply(
            score_percentage_multiply, args=(10.0, True))
    df['high10_grade_per'] = df['high10_grade'].apply(
            score_percentage_multiply, args=(10.0, True))
    return df


@pipe
def r10(research_model, data, nesting, aggregate, **p):
    """Calculate r10 benchmark comparison values."""
    # R PORT: Implements (portions of) <r10.R/r10()>
    r = dict()

    # Get high and low r10 quantiles from the analysis parameters. These values
    # are used to determine the high and low r10 comparison standard values.
    q_hi = p['r10_quantile']
    q_lo = 1 - q_hi

    # Get organization-level means
    org_scores = aggregate.org.transpose()
    org_scores.columns = ['score', ]

    # Make basis dataframe that holds all values needed to calculate r10
    # for all nestings. This dataframe contains the organization-level
    # descriptives for the r10 benchmark.
    basedf = DataFrame(research_model[['var', 'mean_name', 'grade_name',
                                       'direction', 'code']])

    mean_vars = org_scores.index.isin(basedf.mean_name)
    grade_vars = org_scores.index.isin(basedf.grade_name)

    basedf['score_mean'] = list(org_scores[mean_vars]['score'])
    basedf['score_grade'] = list(org_scores[grade_vars]['score'])

    r['org'] = make_r10_df(basedf, data.use, q_lo, q_hi)

    for n in p['nestings']:
        df = make_r10_df(basedf, aggregate[n], q_lo, q_hi)

        # NOTE: In porting this function from the equivalent R-code, it was
        # discovered that no code relies on these 'absolute growth potential'
        # values. It is uncertain why this is calculated. As for now, it is
        # commented out as it prevents unnecessary computation.
        # Calculate r10 benchmark and absolute growth potential
        # growth = df.apply(r10_calculate_growth_potential, axis='columns')
        # df[['growth_mean', 'growth_grade']] = growth

        r[n] = df

    return r


@pipe
def growth(research_model, nesting, aggregate, r10, **p):
    """Calculate absolute growth potential scores per nesting variable. Growth
    scores indicate how much room there is to improve for a particular
    agregation level in a nesting (e.g., team, job). This is calculated by
    comparing the aggregation score against the r10 benchmark, taking into account 
    the direction of a variable. When a variable has a positive direction, the
    aggregation score is subtracted from the higher r10 benchmark score. When a
    variable has a negative direction, the lower r10 benchmark is effectively
    subtracted from the aggregation score. The larger this difference between
    the aggregation score and the r10 comparison standard, the more absolute
    room there is to improve on that specific variable."""

    r = dict()
    varnames = scale_var_names(research_model)

    for n in p['nestings']:
        # See whether custom r10 comparison standard is specified
        # NOTE: by default, the r10 scores of the nesting itself will be used
        # to calculate growth potentials. For example, if we were to
        # compare growth for teams, every team will be compared against
        # the team's r10-benchmark.
        cstd = p.get(f'r10_{n}_comparison', n)

        # Ensure that the r10 comparison standard exists
        if cstd not in r10:
            raise ValueError(f'Cannot calculate growth potentials for {n} ' +
                             'nesting because specified r10 comparison ' +
                             f'standard {cstd} does not exist')

        # Retrieve the r10 comparison values for specified nesting using
        # specified r10 comparison standard.
        g = r10_nesting_comparison_values(cstd, r10, research_model)

        # Subtract the aggregation scores from the r10 comparison values
        g = g.transpose().squeeze()
        r[n] = g - aggregate[n][varnames]

        # Correct scores with a negative direction by reversing them
        neg_names = scale_negative_var_names(research_model)
        negg = r[n][neg_names] * -1
        r[n].update(negg)

        # Correct growth scores that are lower than zero.
        # Lower than zero indicates that an aggregation score has exceeded
        # its respective r10 comparison value. In other words, this
        # aggregation score falls within the quantile range that the
        # r10 comparison value is based on. For those aggregation scores
        # that fall in this range, there is no room left to grow.
        r[n] = r[n].where(r[n] > 0, 0)

        # Previous implementation -- relatively slow
        # Not removed before unit testing:
        # r[n].update(r[n][varnames].where(r[n][varnames] > 0, 0))

        r[n] = r[n].merge(aggregate[n][['value', 'code']],
                          left_index=True, right_index=True)

    return r


@pipe
def zgrowth(growth, research_model, **p):
    """Calculate standardized (z) scores per variable per nesting. This is done
    per variable, as every variable has its own statistical distribution with a
    different mean and standard deviation."""
    r = dict(zgrowth=dict())

    varnames = scale_var_names(research_model)

    for n in p['nestings']:
        r[n] = df_standardize(growth[n][varnames], axis='rows')

    return r


@pipe
def growth_descriptives(growth, zgrowth, research_model, **p):
    """Calculate overall growth descriptives per nesting variable."""
    r = dict()
    varnames = scale_var_names(research_model)

    # Of course, mean and sd of zgrowth are theoretically known to be 0 and 1.
    # They are included to verify correctness of computation.
    for n in p['nestings']:
        r[n] = DataFrame({'mean_growth': growth[n][varnames].mean(),
                          'sd_growth': growth[n][varnames].std(),
                          'mean_zgrowth': zgrowth[n][varnames].mean(),
                          'sd_zgrowth': zgrowth[n][varnames].std()})
        r[n]['var_name'] = r[n].index

    return r


@pipe
def excellent(growth, research_model, **p):
    """Determine which aggregation scores are excellent, which are those that
    have no growth potential and, hence, are in the r10 quantile range"""
    r = dict(count=dict())
    varnames = scale_var_names(research_model)

    # TODO ADD COUNTS IN SEP DICT FOR NUMBER TIMES EXCELLENT

    for n in p['nestings']:
        # non-zero: there is growth == not excellent
        # zero: there is no growth == excellent
        # (1) Change non-zero into 1
        # (2) Subtract 1 to get 0 for non-excellent, -1 for excellent
        # (3) Make absolute values [0, -1] -> [0, 1]
        # (4) Make booleans

        r[n] = abs((growth[n][varnames].where(growth[n][varnames] <=
                                              0, 1) - 1)).astype(bool)

    return r
