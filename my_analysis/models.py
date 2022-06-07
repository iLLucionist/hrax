import numpy as np
from pandas import DataFrame
from copy import deepcopy
import pandas as pd

import semopy as sp

from nowpipes import pipe

from helpers import rm_subcluster_vars, grade_prefix


def sem_regression_formula(dvs, ivs):
    """Make a (multivariate) semopy regression formula based on dvs and ivs"""
    return ', '.join(dvs) + ' ~ ' + ' + '.join(ivs)


def sem_regression(dvs, ivs, df, debug=False):
    """Use semopy to perform a (multivariate) regression with manifest
    variables on specified dataframe."""

    if debug:
        print(" Model with dvs:", ' '.join(dvs))
        print(" Model with ivs:", ' '.join(ivs))
        print()

    # Define the sem model
    formula = sem_regression_formula(dvs, ivs)

    # Make subset of data with only variables defined in sem model
    varss = list(ivs) + list(dvs)
    df = df[varss]

    # Calculate model, fit, estimates, and fit statistics, respectively
    model = sp.Model(formula)
    fit = model.fit(df)
    estimates = model.inspect()
    stats = sp.calc_stats(model).transpose()

    return dict(formula=formula, vars=vars, model=model, fit=fit,
                estimates=estimates, stats=stats)


def model_table(sem, pval, dvcluster, ivcluster, modname):
    """Make a model table based on a sem regression (sem_regression)"""
    # R PORT: Implements (portions of) <regressions.R/calc_model()>

    # Copy input sem to prevent accidentally modifying original
    modt = sem['estimates'].copy()

    # Delete op column (we do not need it) and redefine column names
    del modt['op']
    modt.columns = ('dv', 'iv', 'est', 'sdterr', 'z', 'p')

    # Drop covariances
    modt = modt.drop(modt[modt['dv'] == modt['iv']].index)

    # Replace non-significant estimates with 0
    modt['est'] = modt['est'].where(modt['p'] < pval, 0)

    # Make column with absolute estimate values
    modt['estabs'] = modt['est'].abs()

    # Column indicating True when estimate significant, False otherwise
    modt['issig'] = modt['est'].where(modt['est'] == 0, 1).astype(bool)

    # Column indicating estimate positive (+1), negative (-1) or zero (0)
    modt['direction'] = np.sign(modt['est'])

    # Rank absolute estimates per dependent variable
    modt['rank'] = modt.groupby('dv')['estabs'].rank('dense',
                                                     ascending=False)

    # Add dvcluster, ivcluster, and model names
    modt['dvcluster'] = dvcluster
    modt['ivcluster'] = ivcluster
    modt['model'] = modname

    # Sort the table per rank per dependent variable
    modt.sort_values(['dv', 'rank'], inplace=True)

    return modt


def model_iv_stats(modt, dvcluster, ivcluster, modname):
    """Gather some summary information about how the independent variables
    perform across all dependent variables in the model table."""

    # Mean_rank: Average rank of ivs across all dvs
    # Max_est: Maximum estimate across all dvs
    # Mean_est: Average estimate across all dvs
    stats = DataFrame([modt.groupby('iv')['rank'].mean(),
                       modt.groupby('iv')['estabs'].max(),
                       modt.groupby('iv')['estabs'].mean()],
                      index=('mean_rank', 'max_est', 'mean_est')).transpose()

    # Add dvcluster, ivcluster, and model names
    stats['dvcluster'] = dvcluster
    stats['ivcluster'] = ivcluster
    stats['model'] = modname

    return stats


def relative_df(df, divide_by):
    """Make every value in every row relative by dividing it with every row in
    divide_by. Thus, every value in the n-th row is divided by the value in the
    n-th row of dividy_by"""
    return df.div(divide_by, 0)


def sort_and_cutoff_pos(df, cutoff):
    """Per row, sort column values from low to high and return the n-th row that
    is higher than the specified cutoff value"""
    # Sort numbers per row from high to low
    hi_to_lo = DataFrame(-np.sort(-df))
    # Calculate cumulative scores
    cumulative = hi_to_lo.cumsum(axis='columns')
    # Count number of times that number is greater than cutoff per row
    bools = DataFrame(cutoff > cumulative)
    # Count that number of occurences and add 1.
    # That is, the cutoff should include the first value that exceeds cutoff
    cutoffs = bools.sum(axis='columns') + 1
    # Correct cutoffs that exceed number of variables
    cutoffs.loc[cutoffs > bools.shape[1]] = bools.shape[1]
    # Get the 'proportion explained variance' for the collection of
    # scores that fall under the cutoff
    explained = cumulative.to_numpy()[np.arange(len(cumulative)), cutoffs - 1]

    return DataFrame({'cutoff': cutoffs, 'explained': explained})


def model_weighted_growth_stats(wg, cutoff):
    # Rank weighted growths per nesting entry
    rank = wg.rank(ascending=False, axis=1)

    # Calculate growth relative to each nesting entry's sum
    relative = relative_df(wg, wg.sum(axis='columns'))

    # Get the position at which the cumulative sum exceeds cutoff.
    # This is later used to determine on how many independent variables
    # an entry in a nesting can 'grow' substantially. In other words, it's
    # a way of establishing the proportion explained 'variance' of each iv
    # For instance, a number of 4 with cutoff 0.7 means that for this
    # specific nesting's entry, the 4 cumulative weighed growth potentials
    # together account for about 70% of the influence on all dependent
    # variables specified in the models.
    cutoff = sort_and_cutoff_pos(relative, cutoff)

    # Get overall statistics for the ranks. Mean rank reflects the weighted
    # growth rank on average. For instance, a mean rank of 4 indicates that
    # randomly drawing the respective variable from a nesting entry should
    # reveal about weighted rank 4 in 50% of the cases.
    stats = DataFrame({'mean_rank': rank.mean(axis='rows'),
                       'sd_rank': rank.std(axis='rows')})

    return dict(rank=rank, relative=relative,
                cutoff=cutoff, stats=stats)


@pipe
def models(data, research_model, **p):
    """Run SEM multivariate manifest regression models for every model specified
    in the model file (modfile parameter). Next, transform the results into
    model tables that are later used for statistical / inferential decisions"""
    # R PORT: Implements (portions of) <regressions.R/regressions()>,
    # <rankings.R/rankshort.model()>
    r = dict()

    # Load model specifications from file
    y = pd.read_csv(p['modfile'])
    rm = research_model
    # P-value used as cut-off in model_table
    pval = p['models_p_value']
    df = data.use

    # Make an empty dataframe to concatenate all model tables and ivstats
    all_table, all_ivstats = DataFrame(), DataFrame()

    for index, model in y.iterrows():
        name = model['name']
        dvcluster, ivcluster = model['dvs'], model['ivs']
        dvs = rm_subcluster_vars(dvcluster, rm, grade_prefix)
        ivs = rm_subcluster_vars(ivcluster, rm, grade_prefix)

        # Run the regression model using sem (semopy)
        sem = sem_regression(dvs, ivs, df)
        # Transform results into a model table
        modt = model_table(sem, pval, dvcluster, ivcluster, name)
        # Gather summary iv stats
        ivstats = model_iv_stats(modt, dvcluster, ivcluster, name)

        all_table = all_table.append(modt)
        all_ivstats = all_ivstats.append(ivstats)

        r[name] = sem | {'table': modt, 'ivstats': ivstats}

    # Sort ivstats by ivcluster, dvcluster, finally iv (index).
    # Handy to have everything in order for further processing
    # weighted_growth.
    all_ivstats = all_ivstats.sort_values(['ivcluster', 'dvcluster', 'iv'])
    all_ivstats_bymodel = all_ivstats.groupby('model')
    rel_est = all_ivstats_bymodel.apply(lambda df: round(df['mean_est'].divide(sum(df['mean_est'])) * 100, 1))
    all_ivstats = all_ivstats.merge(rel_est, left_on=['model', 'iv'],
                                    right_index=True)
    all_ivstats = all_ivstats.rename(columns={'mean_est_x': 'mean_est',
                                              'mean_est_y': 'rel_est'})


    r['all'] = {'table': all_table, 'ivstats': all_ivstats}

    # Agreggate means for ivstats by iv
    overall_ivstats = all_ivstats.groupby('iv').mean()
    r['overall'] = dict(ivstats=overall_ivstats)

    # Strongest effects by dvcluster
    all_bydvclus = all_table.groupby('dvcluster')
    dvclusters = all_bydvclus.groups.keys()
    r['by_dvcluster'] = {dvclus: {} for dvclus in dvclusters}
    for dvcluster in dvclusters:
        effects = all_bydvclus.get_group(dvcluster)
        effects = effects.sort_values('estabs', ascending=False)
        r['by_dvcluster'][dvcluster] = effects

    return r


@pipe
def signs(research_model, models, **p):

    dvclusters = models.by_dvcluster.keys()
    r = {'by_dvcluster': {dvclus: {} for dvclus in dvclusters}}

    for dvcluster in dvclusters:
        signs = models.all.table
        signs = signs[signs.dvcluster == dvcluster]
        signs = signs[signs['issig'] == True]
        signs_df = pd.DataFrame(signs.groupby('model').apply(lambda col: pd.crosstab(col.iv, col.direction)))
        signs_df = signs_df.rename(columns={-1.0: 'negative', 1.0: 'positive'})
        signs_df['model'] = signs_df.index.get_level_values('model')
        signs_df['grade_name'] = signs_df.index.get_level_values('iv')
        signs_df = signs_df.fillna(0)
        signs_df['majority'] = 1
        signs_df['majority'] = signs_df['majority'].mask(signs_df.negative > signs_df.positive, -1)
        signs_df['majority'] = signs_df['majority'].mask(signs_df.negative == signs_df.positive, 0)
        

        rm = research_model[['grade_name', 'direction']]
        signs_df = signs_df.merge(rm, left_on='grade_name', right_on='grade_name',
                                  how='inner')
        r['by_dvcluster'][dvcluster] = signs_df

    return r


@pipe
def weighted_growth(growth, models, nesting, research_model, **p):
    """Weigh growth potentials by multiplying the absolute growth potentials of
    every entity in every nesting with corrected regression estimates /
    weights. These are derived from ivstats from the models() analysis."""
    # R PORT: Implements (portions of) <ranking.R/rankshortteam()>,
    # <ranking.R/rankshort()>

    r = dict(rank=dict(), relative=dict(), cutoff=dict(),
             stats=dict())
    r['by_model'] = deepcopy(r)

    # The names of columns in ivstats can be used as weighing method
    weigh_by = p.get('weigh_growth_by', 'mean_est')

    # Get the weights for ivs over all models
    ivstats_overall = models.overall.ivstats
    weights_overall = ivstats_overall[weigh_by].squeeze()

    # Get the weights for ivs per model
    ivstats_per_model = models.all.ivstats
    weights_per_model = ivstats_per_model.groupby('model')[weigh_by]

    # Get the weights for ivs per dvcluster
    weights_per_dvclus = models.all.ivstats.groupby('dvcluster')
    dvclusters = weights_per_dvclus.groups.keys()
    r['by_dvcluster'] = {dvclus: {} for dvclus in dvclusters}

    # Weighted growth can only be calculated for those ivs that are present
    # in computated models
    varnames_overall = ivstats_overall.index

    # The cutoff value beyond which cumulative growth has reached diminishing
    # returns and provides marginal benefits.
    cumcut = p.get('cumulative_growth_cutoff', 0.7)

    for n in p['nestings']:
        # Get growth scores for nesting
        g = growth[n][varnames_overall]
        # Weigh these scores by multiplying them with weights from ivstats
        wg = g * weights_overall
        r[n] = wg

        # Weight growth scores per dvcluster
        for dvcluster in dvclusters:
            weights_dvclus = weights_per_dvclus.get_group(dvcluster)
            weights_dvclus = weights_dvclus[weigh_by].squeeze()
            wg_dvclus = g * weights_dvclus
            r['by_dvcluster'][dvcluster][n] = wg_dvclus

        # Calculate additional statistics for the weighted growth potentials
        wg_stats = model_weighted_growth_stats(wg, cumcut)
        # Rank position of the weighted growth potential
        r['rank'][n] = wg_stats['rank']
        # Relative potential compared to sum (e.g., all sum to 1 = 100%)
        r['relative'][n] = wg_stats['relative']
        # N-th variable cutoff
        r['cutoff'][n] = wg_stats['cutoff']
        # Additional statistics (like mean and sd of rank). These reflect how
        # often, on average, an iv reaches that rank
        r['stats'][n] = wg_stats['stats']

        # Weigh growth potentials for nesting per model
        wgm = weights_per_model.apply(lambda w: w * g)
        r['by_model'][n] = wgm

        wgm_stats = model_weighted_growth_stats(wgm, cumcut)
        wgm_stats['cutoff'].index = wgm_stats['relative'].index
        r['by_model']['rank'][n] = wgm_stats['rank']
        r['by_model']['relative'][n] = wgm_stats['relative']
        r['by_model']['cutoff'][n] = wgm_stats['cutoff']
        r['by_model']['stats'][n] = wgm_stats['stats']

    return r
