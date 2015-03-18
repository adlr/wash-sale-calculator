# Copyright Google

# BSD License

import argparse
import copy
import lot
import progress_logger

def remove_lot_from_list(lots, lot):
  lots[:] = [elt for elt in lots if id(elt) != id(lot)]

# Ways to sort lots
def cmp_by_buy_date(lot_a, lot_b):
  if lot_a.buydate != lot_b.buydate:
    return (lot_a.buydate - lot_b.buydate).days
  if lot_a.selldate != lot_b.selldate:
    if lot_a.selldate is None:
      return 1
    if lot_b.selldate is None:
      return -1
    return (lot_a.selldate - lot_b.selldate).days
  if lot_a.form_position != lot_b.form_position:
    if lot_a.form_position < lot_b.form_position:
      return -1
    return 1
  return 0

def cmp_by_sell_date(lot_a, lot_b):
  # Sort puts the buys without sells at the end
  if lot_a.selldate != lot_b.selldate:
    if lot_a.selldate is None:
      return 1
    if lot_b.selldate is None:
      return -1
    return (lot_a.selldate - lot_b.selldate).days
  if lot_a.buydate != lot_b.buydate:
    return (lot_a.buydate - lot_b.buydate).days
  if lot_a.form_position != lot_b.form_position:
    if lot_a.form_position < lot_b.form_position:
      return -1
    return 1
  return 0

def buy_lots_match(lot_a, lot_b):
  a_buys = lot_a.buy_lot.split(',')
  b_buys = lot_b.buy_lot.split(',')
  return bool(set(a_buys).intersection(b_buys))

def merge_buy_lots(merge_from, merge_to):
  # Move all buy lots from 'from' into 'to'. Assume there is no intersection
  assert(not buy_lots_match(merge_from, merge_to))
  merge_to.buy_lot += ',' + merge_from.buy_lot

def buy_lots_within_window(lots, loss):
  # Returns an array of lots that were bought within 30 days of the loss,
  # but were not sold on this date
  return [lot for lot in lots if \
          (abs((lot.buydate - loss.selldate).days) <= 30 and 
           not buy_lots_match(lot, loss) and 
           not lot.is_replacement)]

def earliest_wash_loss(lots):
  lots.sort(cmp=cmp_by_sell_date)
  ret = []
  for i, lot in enumerate(lots):
    if not lot.has_sell():
      return None  # We're done
    if lot.proceeds >= lot.basis:
      continue
    buys = buy_lots_within_window(lots, lot)
    if not buys:
      continue
    ret.append(lot)
    # Pull all the next lots w/ the same sell-date into ret if they have losses
    i = i + 1
    while i < len(lots):
      if (lots[i].has_sell() and lots[i].proceeds < lots[i].basis and
          lots[i].selldate == ret[0].selldate):
        ret.append(lots[i])
        i = i + 1
        continue
      break
    return ret

def split_head_lot(lots, ideal_head_count):
  # returns the new lot that was created
  new_lot = copy.copy(lots[0])
  new_lot.count = ideal_head_count
  lots[0].count = lots[0].count - ideal_head_count
  # adjust prices
  total_cnt = new_lot.count + lots[0].count
  new_lot.basis = new_lot.basis * new_lot.count / total_cnt
  lots[0].basis = lots[0].basis * lots[0].count / total_cnt
  if new_lot.has_sell():
    new_lot.proceeds = new_lot.proceeds * new_lot.count / total_cnt
    lots[0].proceeds = lots[0].proceeds * lots[0].count / total_cnt
  lots[0].form_position += '.2'
  new_lot.form_position += '.1'
  lots.insert(0, new_lot)
  return new_lot

def perform_wash(lots, logger):
  removed = []
  while True:
    loss_lots = earliest_wash_loss(lots)
    if not loss_lots:
      break
    logger.print_progress(lots, "Found the following losses", loss_lots)
    buy_lots = buy_lots_within_window(lots, loss_lots[0])
    logger.print_progress(lots, "Here are the replacements", buy_lots)
    if not buy_lots:
      print "Error: no buy lots"
      raise
    # Pair them off, splitting as necessary
    buy_lots.sort(cmp=cmp_by_buy_date)
    loss_lots.sort(cmp=cmp_by_buy_date)
    while buy_lots and loss_lots:
      if buy_lots[0].count > loss_lots[0].count:
        # split buy
        logger.print_progress(lots, "Splitting buy", [buy_lots[0]])
        new_buy = split_head_lot(buy_lots, loss_lots[0].count)
        lots.append(new_buy)
        logger.print_progress(lots, "into these", [buy_lots[0],
                                                            buy_lots[1]])
      elif buy_lots[0].count < loss_lots[0].count:
        # split loss
        logger.print_progress(lots, "Splitting loss", [loss_lots[0]])
        new_loss = split_head_lot(loss_lots, buy_lots[0].count)
        lots.append(new_loss)
        logger.print_progress(lots, "into these", [loss_lots[0],
                                                            loss_lots[1]])
      assert buy_lots[0].count == loss_lots[0].count
      buy = buy_lots[0]
      loss = loss_lots[0]
      logger.print_progress(lots, "pairing these", [buy, loss])
      remove_lot_from_list(buy_lots, buy)
      remove_lot_from_list(loss_lots, loss)
      remove_lot_from_list(lots, loss)
      removed.append(loss)
      buy.basis = buy.basis + loss.basis - loss.proceeds
      buy.buydate = buy.buydate - (loss.selldate - loss.buydate)
      buy.is_replacement = True
      merge_buy_lots(loss, buy)
      logger.print_progress(lots, "pair complete", [buy])
      loss.code = 'W'
      loss.adjustment = loss.basis - loss.proceeds
  removed.extend(lots)
  removed.sort(cmp=cmp_by_sell_date)
  return removed

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('-o', '--out_file')
  parser.add_argument('-w', '--do_wash', metavar='in_file')
  parser.add_argument('-q', '--quiet', action="store_true")
  parsed = parser.parse_args()

  if parsed.do_wash:
    lots = lot.load_lots(parsed.do_wash)
    lot.print_lots(lots)
    if parsed.quiet:
      logger = progress_logger.NullLogger()
    else:
      logger = progress_logger.TermLogger()
    out = perform_wash(lots, logger)
    print 'output:'
    lot.print_lots(out)
    if parsed.out_file:
      print 'Saving final lots to', parsed.out_file
      lot.save_lots(out, parsed.out_file)

if __name__ == "__main__":
  main()
