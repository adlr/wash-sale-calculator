# Copyright Google

# BSD License

import argparse
import csv
import datetime

class Lot(object):
  """Represents a buy with optional sell."""
  def __init__(self, count, symbol, description,
               buydate, basis,
               selldate = None,
               code = None,
               adjustment = None,
               proceeds = None,
               form_position = ''):
    self.count = count
    self.symbol = symbol
    self.description = description
    self.buydate = buydate
    self.basis = basis
    # These may be None if it's just a buy:
    self.selldate = selldate
    self.code = code
    self.adjustment = adjustment
    self.proceeds = proceeds
    self.form_position = form_position
  @staticmethod
  def create_from_csv_row(row):
    lot = Lot(int(row[0]), row[1], row[2],
              datetime.datetime.strptime(row[3].strip(), "%m/%d/%Y").date(),
              float(row[4]))
    if row[5]:
      lot.selldate = \
        datetime.datetime.strptime(row[5].strip(), "%m/%d/%Y").date()
      lot.proceeds = float(row[6])
      lot.code = row[7]
      lot.adjustment = float(row[8])
    lot.form_position = row[9]
    return lot
  def acquition_match(self, that):
    return (self.count == that.count and
            self.symbol == that.symbol and
            self.description == that.description and
            self.buydate == that.buydate and
            self.basis == that.basis)
  def has_sell(self):
    return self.selldate is not None
  @staticmethod
  def csv_headers():
    return ['Cnt', 'Sym', 'Desc', 'BuyDate',
            'Basis', 'SellDate', 'Proceeds', 'AdjCode',
            'Adj', 'FormPosition']
  def csv_row(self):
    return [self.count, self.symbol, self.description,
            self.buydate.strftime('%m/%d/%Y'),
            self.basis,
            None if self.selldate is None else \
            self.selldate.strftime('%m/%d/%Y'),
            self.proceeds, self.code,
            self.adjustment, self.form_position]
  def __eq__(self, that):
    return (isinstance(that, self.__class__)
                       and self.__dict__ == that.__dict__)
  def __ne__(self, that):
    return not self.__eq__(that)
  def __str__(self):
    front = ("%2d %s (%s) acq: %s %8.02f" %
             (self.count, self.symbol, self.description,
              self.buydate, self.basis))
    sell = ""
    code = ""
    if self.selldate:
      sell = (" sell: %s %8.02f" %
              (self.selldate, self.proceeds))
    if self.code or self.adjustment:
      if self.adjustment:
        code = " [%1s %6.02f]" % (self.code, self.adjustment)
      else:
        code = " [%1s]" % (self.code)
    position = ''
    if self.form_position:
      position = " " + self.form_position
    return front + sell + code + position
  __repr__ = __str__

def save_lots(lots, filepath):
  # Write the lots out to the given file
  fd = open(filepath, 'w')
  writer = csv.writer(fd)
  writer.writerow(Lot.csv_headers())
  for lot in lots:
    writer.writerow(lot.csv_row())

def load_lots(filepath):
  reader = csv.reader(open(filepath))
  ret = []
  for row in reader:
    if row[0] and row[0] == Lot.csv_headers()[0]:
      continue
    ret.append(Lot.create_from_csv_row(row))
  return ret

def print_lots(lots):
  print "Printing %d lots:" % len(lots)
  basis = 0
  proceeds = 0
  days = 0
  adjustment = 0
  # make sure all elements are unique
  id_list = [id(lot) for lot in lots]
  assert len(id_list) == len(set(id_list))
  # go through all lots
  for lot in lots:
    print lot
    basis += lot.basis
    if lot.proceeds:
      proceeds += lot.proceeds
    if lot.adjustment:
      adjustment += lot.adjustment
      if lot.adjustment != 0:
        assert(lot.adjustment == lot.basis - lot.proceeds)
  print "Totals: Basis %.2f Proceeds %.2f Adj: %.2f (basis-adj: %.2f)" % (basis, proceeds, adjustment, basis - adjustment)
