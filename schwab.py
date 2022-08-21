# Copyright Google

# BSD License

import argparse
import csv
import datetime
import lot

def parse_schwab_1099b(fileobj):
  reader = csv.reader(fileobj)
  ret = []
  i = 0
  for row in reader:
    if i % 3 == 0:
      description = row[1].strip()
      buydate = datetime.datetime.strptime(row[2].strip(), "%m/%d/%Y").date()
      proceeds = float(row[3].replace(',', ''))
      basis = float(row[4].replace(',', ''))
      code = 'W' if row[5].startswith('W') else ""
      count = 0
      symbol = ''
      selldate = None
      adjustment = 0.0
    if i % 3 == 1:
      count = int(row[0].split()[0])
      symbol = row[0].split()[3]
    if i % 3 == 2:
      selldate = datetime.datetime.strptime(row[2].strip(), "%m/%d/%Y").date()
      if len(row) > 6 and row[6] != '':
        adjustment = float(row[6].replace(',', ''))
      ret.append(lot.Lot(count, symbol, description, buydate, basis,
                        selldate, code, adjustment, proceeds,
                        'Line %d' % int(i / 3 + 1)))
      print(ret[-1])
    i = i + 1
  return ret

def parse_schwab_statement(fileobj):
  reader = csv.reader(fileobj)
  ret = []
  for row in reader:
    rowKind = row[2].strip()
    count = int(row[7].strip("() "))
    if rowKind == 'Sale':
      ret.append(lot.Lot(
        count,
        row[0].strip(),
        row[3].strip(),
        datetime.datetime.strptime(row[4].strip(), "%m/%d/%Y").date(),
        lot.Lot.str_to_float(row[5]) * count,
        datetime.datetime.strptime(row[1].strip(), "%m/%d/%Y").date(),
        '', 0.0,
        lot.Lot.str_to_float(row[8]) * float(count)))
    elif rowKind == 'Deposit':
      ret.append(lot.Lot(
        count,
        row[0].strip(),
        row[3].strip(),
        datetime.datetime.strptime(row[4].strip(), "%m/%d/%Y").date(),
        lot.Lot.str_to_float(row[5]) * float(count)))
  return ret

def remove_sold_buys(lots):
  # WARNING: if you sold part of a lot, this won't catch it
  buys = [lot for lot in lots if not lot.has_sell()]
  sells = [lot for lot in lots if lot.has_sell()]
  ret = []
  for buy in buys:
    found = False
    for idx, sell in enumerate(sells):
      if buy.acquition_match(sell):
        found = True
        ret.append(sells.pop(idx))
        break
    if not found:
      print("No match for", buy)
      ret.append(buy)
  for sell in sells:
    print("No match for", sell)
  ret.extend(sells)
  return ret

def match_lots_to_1099(lots, t1099):
  # Matches lots from statement w/ those from 1099b.
  # The idea is the 1099b has the correct sale date and proceeds, while
  # the raw lots have the real acquition date and basis.
  # We assume the 1099b may have incorrect basis info if wash sales were
  # computed (incorrectly) by the broker.
  # Return value is list of lots with real acquition date and basis
  # (from 'lots') and real proceeds and sale date (from 't1099').
  # Algorithm:
  # For each set of lots that were sold on the same day:
  #   If they have the same count and acquition date, they match. easy.
  #   For lots from statement that don't have matches from 1099,
  #   see how many ways they could match. If just one, do that.
  #   If more than one, then it's a failure and you'd prompt the user.

  def pop_lots_with_selldate(lots, selldate):
    return ([lot for lot in lots if lot.selldate == selldate],
            [lot for lot in lots if lot.selldate != selldate])

  def match_lots(raw, from1099):
    # match will be the same len as from1099, and will indicate for each
    # corresponding lot in from1099, which element in raw it corresponds to.
    print('match_lots:', len(raw), len(from1099))
    match = [-1] * len(from1099)
    for fromidx in range(len(from1099) - 1, -1, -1):
      fromlot = from1099[fromidx]
      found = False
      print('looking for match for', fromlot)
      for rawidx in range(len(raw)):
        rawlot = raw[rawidx]
        print('  try:', rawlot)
        if rawidx in match:
          print('  already matched.')
          continue
        if (rawlot.count == fromlot.count and
            rawlot.buydate == fromlot.buydate):
          found = True
          print('match found')
          match[fromidx] = rawidx
          break
      if not found:
        print("can't find match", fromlot)
    if -1 not in match:
      return match
    print("Need assistance matching.")
    for rawidx in range(len(raw)):
      if rawidx in match:
        continue
      print('%d: %s' % (rawidx, raw[rawidx]))
    print("Pick indexes above for each of these lots from 1099b:")
    for i in range(len(match)):
      if match[i] != -1:
        continue
      print(from1099[i])
    print("Now, you can give your input:")
    for i in range(len(match)):
      if match[i] != -1:
        continue
      print(from1099[i])
      print("For this lot, which index is corresponding?")
      match[i] = int(input("idx:"))
    return match

  def set_basis(good, bad):
    # Applies basis from good to bad and clears adjustment
    bad.buydate = good.buydate
    bad.basis = bad.count * good.basis / good.count
    bad.code = ''
    bad.adjustment = 0.0

  # First, move over the buy-only lots, as they don't factor in
  ret = [lot for lot in lots if not lot.has_sell()]
  lots = [lot for lot in lots if lot.has_sell()]
  while lots:
    date = lots[0].selldate
    print('selldate', date)
    (lotsraw, lots) = pop_lots_with_selldate(lots, date)
    (lots1099, t1099) = pop_lots_with_selldate(t1099, date)
    matches = match_lots(lotsraw, lots1099)
    for i in range(len(matches)):
      set_basis(lotsraw[matches[i]], lots1099[i])
    ret.extend(lots1099)
  return ret

def main():
  parser = argparse.ArgumentParser(
    description=
    "Parses output from TabulaPDF. You must supply both a 1099b and\n"
    "corresponding statements with the same lots. This script will\n"
    "match lots so that you get the correct purchase date and basis\n"
    "for all lots on the 1099b.\n"
    "The output is a clean csv file that can be fed into the wash sale\n"
    "calculator.\n"
    "WARNING: Doesn't handle the case where you sold part of a lot.")
  parser.add_argument('--in1099b', help="1099b input file as output from TabulaPDF")
  parser.add_argument('--statements',
                      help="statement input files output from TabulaPDF",
                      nargs='+')
  parser.add_argument('-o', '--out_file')
  parsed = parser.parse_args()

  lots = []
  print(parsed.statements)
  for csvfile in parsed.statements:
    print('parsing statement', csvfile)
    lots.extend(parse_schwab_statement(open(csvfile)))
  lot.print_lots(lots)
  lots = remove_sold_buys(lots)

  from1099 = parse_schwab_1099b(open(parsed.in1099b))
  lot.print_lots(from1099)

  from1099 = match_lots_to_1099(lots, from1099)
  print("1099b final:")
  for outlot in from1099:
    print(outlot)
  lot.save_lots(from1099, parsed.out_file)

if __name__ == "__main__":
    main()
