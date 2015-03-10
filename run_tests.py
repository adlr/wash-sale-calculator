# Copyright Google

# BSD License

import inspect
import lot
import os
import progress_logger
import wash

def run_test(input_csv, expected_out_csv):
  lots = lot.load_lots(input_csv)
  out = wash.perform_wash(lots, progress_logger.NullLogger())
  expected = lot.load_lots(expected_out_csv)
  out.sort(cmp=wash.cmp_by_buy_date)
  expected.sort(cmp=wash.cmp_by_buy_date)
  if out != expected:
    print "Test failed:", input_csv
    print "Got result:"
    lot.print_lots(out)
    print "\nExpected:"
    lot.print_lots(expected)
  else:
    print "Test passed:", input_csv

def main():
  test_dir = os.path.join(
    os.path.dirname(inspect.getfile(inspect.currentframe())),
    'tests')
  tests = [name for name in os.listdir(test_dir) \
           if (name.endswith(".csv") and not name.endswith("_out.csv"))]
  for test in tests:
    run_test(os.path.join(test_dir, test),
             os.path.join(test_dir, test.rsplit('.', 1)[0] + "_out.csv"))

if __name__ == "__main__":
  main()

