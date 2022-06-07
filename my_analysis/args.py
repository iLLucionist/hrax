import argparse

parser = argparse.ArgumentParser(description='Run analysis and generate reports.')

# Switch whether to make an excel data dump or not
parser.add_argument('-p', '--dump', dest='dodump', action='store_true',
                    help='Write an excel data dump of the results',
                    default=False)

# Switch where to output a dataset file or not
parser.add_argument('-d', '--dataset', dest='dodataset', action='store_true',
                    help='Write the dataset with results of analyses',
                    default=False)

# List of nestin values for which to generate reports
parser.add_argument('-n', '--nestings', dest='nestings', nargs='+',
                    help='Nestings to generate reports for',
                    default=['org', 'team', 'functie'])
