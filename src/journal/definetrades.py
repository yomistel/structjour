'''
Created on Sep 5, 2018

@author: Mike Petersen
'''
import sys
import datetime
import pandas as pd
from journal.dfutil import DataFrameUtil
# pylint: disable = C0103

class FinReqCol(object):
    '''
    Intended to serve as the adapter class for multiple input files. FinReqCol manages the column
    names for the output file. It includes some of the input columns and additional columns  to
    identify seprate trades and sorting. The columns we add are tix, start, bal, sum, dur, and name
    :SeeAlso: journal.thetradeobject.SumReqFields
    '''

    def __init__(self, source='DAS'):

        if source not in ['DAS', 'IB_HTML']:
            print("Only DAS and IB_HTML are implemented")
            raise ValueError

        # frcvals are the actual column titles (to be abstracted when we add new input files)
        # frckeys are the abstracted names for use with all file types
        frcvals = ['Tindex', 'Start', 'Time', 'Symb', 'Side', 'Price', 'Qty', 'Balance', 'Account',
                   "P / L", 'Sum', 'Duration', 'Name', 'Date', 'O/C']
        frckeys = ['tix', 'start', 'time', 'ticker', 'side', 'price', 'shares', 'bal', 'acct',
                   'PL', 'sum', 'dur', 'name', 'date', 'oc']
        frc = dict(zip(frckeys, frcvals))

        # Address the columns with these attributes instead of strings in frc.
        self.tix = frc['tix']
        self.start = frc['start']
        self.time = frc['time']
        self.ticker = frc['ticker']
        self.side = frc['side']
        self.price = frc['price']
        self.shares = frc['shares']
        self.bal = frc['bal']
        self.acct = frc['acct']
        self.PL = frc['PL']
        self.sum = frc['sum']
        self.dur = frc['dur']
        self.name = frc['name']
        self.date = frc['date']
        self.oc = frc['oc']

        # provided for methods that need a list of columns (using e.g. frc.values())
        self.frc = frc
        self.columns = list(frc.values())


class ReqCol(object):
    '''
    Intended as an adapter class for multiple input types. ReqCol are the columns for the original
    input file All of these are required.
    '''

    def __init__(self, source="DAS"):
        '''Set the required columns in the import file.'''

        if source != 'DAS':
            print("Only DAS is currently supported")
            raise ValueError

        # rcvals are the actual column titles (to be abstracted when we add new input files)
        # rckeys are the abstracted names for use with all file types
        rckeys = ['time', 'ticker', 'side', 'price', 'shares', 'acct', 'PL', 'date']
        rcvals = ['Time', 'Symb', 'Side', 'Price', 'Qty', 'Account', 'P / L', 'Date']
        rc = dict(zip(rckeys, rcvals))

        # Suggested way to address the columns for the main input DataFrame.
        self.time = rc['time']
        self.ticker = rc['ticker']
        self.side = rc['side']
        self.price = rc['price']
        self.shares = rc['shares']
        self.acct = rc['acct']
        self.PL = rc['PL']
        self.date = rc['date']

        self.rc = rc
        self.columns = list(rc.values())


class DefineTrades(object):
    '''
    DefineTrades moves the data from DataFrame representing the input file transactions to a
    dataframe with added columns sorted into trades, showing trade start time, share balance for
    each trade, and the duration of each trade.
    '''

    def __init__(self, source='DAS'):
        '''
        Constructor
        '''
        self.sources = {'das': 'DAS', 'ib': 'IB_HTML'}
        self.source = source
        assert self.source in self.sources.values()

        self._frc = FinReqCol(source)

    def processOutputDframe(self, trades):
        '''
        Run the methods to create the new DataFrame and fill in the data for the new trade-
        centric DataFrame.
        '''
        c = self._frc

        # Process the output file DataFrame
        trades = self.addFinReqCol(trades)
        newTrades = trades[c.columns]
        newTrades.copy()
        nt = newTrades.sort_values([c.ticker, c.acct, c.time])
        nt = self.writeShareBalance(nt)
        nt = self.addStartTime(nt)
        nt.Date = pd.to_datetime(nt.Date)
        nt = nt.sort_values([c.ticker, c.acct, c.start, c.date, c.time], ascending=True)
        nt = self.addTradeIndex(nt)
        nt = self.addTradePL(nt)
        nt = self.addTradeDuration(nt)
        nt = self.addTradeName(nt)
        # ldf is a list of DataFrames, one per trade
        ldf = self.getTradeList(nt)
        ldf, nt = self.postProcessing(ldf)
        nt = DataFrameUtil.addRows(nt, 2)
        nt = self.addSummaryPL(nt)

        # Get the length of the original input file before adding rows for processing Workbook
        # later (?move this out a level)
        inputlen = len(nt)
        dframe = DataFrameUtil.addRows(nt, 2)
        return inputlen, dframe, ldf

    def writeShareBalance(self, dframe):
        '''
        Create the data for share balance for a ticker. Note that for overnight holds after, the
        amount entered here is incorrect. It is corrected in postProcessing(). (for before trades,
        the amount entered hereis correct)
        :params dframe: The DataFrame representing the initial input file plus a bit.
        :return: The same dframe with updated balance entries.
        '''
        prevBal = 0
        c = self._frc

        for i, row in dframe.iterrows():
            qty = (dframe.at[i, c.shares])

            # This sets the after holds to 0 and leaves the before holds to set the proper balance
            if row[c.side] == "HOLD-" or row[c.side] == "HOLD+":
                dframe.at[i, c.bal] = 0
                newBalance = 0
            else:
                newBalance = qty + prevBal

            dframe.at[i, c.bal] = newBalance
            prevBal = newBalance
        return dframe

    def addStartTime(self, dframe):
        '''
        Add the start time to the new column labeled Start or frc.start. Each transaction in each
        trade will share a start time.
        :params dframe: The output df to place the data
        :return dframe: The same dframe but with the new start data.
        '''

        c = self._frc

        newTrade = True
        for i, row in dframe.iterrows():
            if newTrade:
                if row[c.side].startswith('HOLD') and i < len(dframe):
                    oldTime = dframe.at[i+1, c.time]
                    # print("     :Index: {0},  Side: {1}, Time{2}, setting {3}".format(i, row['Side'], row['Time'], oldTime))
                    dframe.at[i, c.start] = oldTime

                else:
                    oldTime = dframe.at[i, c.time]
                    dframe.at[i, c.start] = oldTime

                newTrade = False
            else:
                #             print("      Finally :Index: {0},  Side: {1}, Time{2}, setting {3}".format(i, row['Side'], row['Time'], oldTime))
                dframe.at[i, c.start] = oldTime
            if row[c.bal] == 0:
                newTrade = True
        return dframe

    def addTradeIndex(self, dframe):
        '''
        Labels and numbers the trades by populating the TIndex column. 'Trade 1' for example includes the transactions 
        between the initial purchase or short of a stock and its subsequent 0 position. (If the stock is held overnight, 
        non-transaction rows have been inserted to account for todays' activities.)
        '''

        c = self._frc

        TCount = 1
        prevEndTrade = -1

        for i, row in dframe.iterrows():
            if len(row[c.ticker]) < 1:
                break
            tradeIndex = "Trade " + str(TCount)
            if prevEndTrade == 0:
                TCount = TCount + 1
                prevEndTrade = -1
            tradeIndex = "Trade " + str(TCount)
            dframe.at[i, c.tix] = tradeIndex
            if row[c.bal] == 0:
                prevEndTrade = 0
        return dframe

    def addTradePL(self, dframe):
        ''' Add a trade summary P/L. That is total the transaction P/L and write a summary P/L for the trade in the c.sum column '''

        c = self._frc

        tradeTotal = 0.0
        for i, row in dframe.iterrows():
            if row[c.bal] != 0:
                tradeTotal = tradeTotal + row[c.PL]
            else:
                sumtotal = tradeTotal + row[c.PL]
                dframe.at[i, c.sum] = sumtotal
                tradeTotal = 0
        return dframe

    def addTradeDuration(self, dframe):
        ''' Get a time delta beween the time of the first and last transaction. Place it in the c.dur column'''

        c = self._frc

        for i, row in dframe.iterrows():
            if row[c.bal] == 0:
                timeEnd = pd.Timestamp(row[c.time])
                timeStart = pd.Timestamp(row[c.start])
                assert timeEnd.date() == timeStart.date()
                diff = timeEnd - timeStart

                # end = timeEnd.split(":")
                # start = timeStart.split(":")
                # diff = datetime.datetime(1, 1, 1, int(end[0]), int(end[1]), int(
                #     end[2])) - datetime.datetime(1, 1, 1, int(start[0]), int(start[1]), int(start[2]))
                dframe.at[i, c.dur] = diff
        return dframe

    def addTradeName(self, dframe):
        '''
        Create a name for this trade like 'AMD Short'. Place it in the c.name column. If this is
        not an overnight hold, then the last transaction is an exit so B indicates short. This
        could still be a flipped position. We need the initial transactions- which are processed
        later.
        '''

        c = self._frc

        for i, row in dframe.iterrows():

            longShort = " Long"
            if row[c.bal] == 0:
                # this is the last tx of the trade today. B or HOLD- are shorts
                if row[c.side] == 'B' or row[c.side].startswith('HOLD-'):
                    longShort = " Short"
                dframe.at[i, c.name] = row[c.ticker] + longShort
        return dframe

    def addSummaryPL(self, dframe):
        ''' 
        Create a summary of the P/L for the day, place it in new row. 
        Sum up the transactions in c.PL for Live and Sim Seperately.
        We rely on the account number starting with 'U' or 'TR' to determine
        live or SIM. These two columns should add to the same amount. '''
        # Note that .sum() should work on this but it failed when I tried it.
        c = self._frc

        count = 0
        tot = 0.0
        tot2 = 0.0
        totLive = 0.0
        totSim = 0.0
        for i, row in dframe.iterrows():
            count = count+1
            if count < len(dframe)-1:
                tot = tot+row[c.PL]
                if row[c.bal] == 0:
                    tot2 = tot2 + row[c.sum]
                    if row[c.acct].startswith('TR'):
                        totSim = totSim + row[c.sum]
                    else:
                        assert(row[c.acct].startswith('U'))
                        totLive = totLive + row[c.sum]
                # if count == len(dframe) -2 :
                #     lastCol = row[c.PL]

            elif count == len(dframe) - 1:
                # print(dframe)
                dframe.at[i, c.PL] = tot
                dframe.at[i, c.sum] = totSim
            else:
                assert (count == len(dframe))
                dframe.at[i, c.sum] = totLive

        return dframe



    def getTradeList(self, dframe):
        '''
        Creates a python list of DataFrames for each trade. It relies on addTradeIndex successfully creating the 
        trade index in the format Trade 1, Trade 2 etc.
        :param:dframe: A dataframe with the column Tindex filled in.
        '''
        # Now  we are going to add each trade and insert space to put in pictures with circles and
        # arrows and paragraph on the back of each one to be used as evidence against you in a court
        # of law (or court of bb opionion)
        # insertsize=25
        # dframe = nt
        c = self._frc
        try:
            if not dframe[c.tix].unique()[0].startswith('Trade'):
                raise(NameError(
                    "Cannot make a trade list. You must first create the TIndex column using addTradeIndex()."))
        except NameError as ex:
            print(ex, 'Bye!')
            sys.exit(-1)

        ldf = list()
        count = 1
        while True:
            tradeStr = "Trade " + str(count)
            count = count + 1
            tdf = dframe[dframe.Tindex == tradeStr]
            if len(tdf) > 0:
                ldf.append(tdf)
            else:
                break
        # print("Got {0} trades".format(len(ldf)))
        return ldf

    def postProcessing(self, ldf):
        '''
        A few items that need fixing up in names and initial HOLD entries. This method is called
        after the creation of the DataFrameList (ldf). We locate flipped positions and overnight
        holds and change the name appropriately. Also update initial HOLD prices, and balance with
        the calculated average price of pre owned shares and initial shares respectively.
        :params ldf: A ist of DataFrames, each DataFrame represents a trade defined by the initial
                     purchase or short of a stock, and all transactions until the transaction which
                     returns the share balance to 0. Last entry may be a HOLD indicating shares
                     were held overnight in the amount of the previous transaction share balance.
                     After HOLDs are nontransactions. shares are listed as 0 indicating the
                     number of shares owned is in the previous transaction. Before HOLDs attempt to
                     show the current status of previous transctions not given explicity.
        :return (ldf, nt): The updated versions of the list of DataFrames, and the updated single DataFrame.

        '''
        c = self._frc
        dframe = pd.DataFrame()
        for count, tdf in enumerate(ldf):
            if tdf.iloc[-1][c.bal] == 0:
                x0 = tdf.index[0]
                xl = tdf.index[-1]
                if tdf.at[x0, c.side].startswith('HOLD') or tdf.at[xl, c.side].startswith('HOLD'):
                    # Apparent double testing to cover trades with holds both before and after
                    if tdf.at[xl, c.side].startswith('HOLD'):
                        tdf.at[xl, c.name] = tdf.at[xl, c.name] + " OVERNIGHT"
                        tdf.at[xl, c.bal] = 0
                    if tdf.at[x0, c.side].startswith('HOLD'):
                        sharelist = list()
                        pricelist = list()
                        for dummy, row in tdf.iterrows():
                            # Here we set initial entries' average price of shares previously held
                            # based on the P/L of the first exit. The math gets complicated if
                            # there are more than 2 entrances before # the first exit. This
                            # currently only works without extra opens before the first close.
                            # TODO Send in some SIM trades to model it.
                            sharelist.append(row[c.shares])
                            pricelist.append(row[c.price])
                            if row[c.PL] != 0:
                                # TODO This does not cover the possibilities-- still have no models
                                originalPrice = row[c.price] + (row[c.PL] / row[c.shares])
                                tdf.at[x0, c.price] = originalPrice
                                break
                        # print()
                elif tdf.at[x0, c.side].startswith('B') and tdf.at[xl, c.side].startswith('B'):
                    # Still not sure how IB deals with flipped trades. I think they break down the
                    # shares to figure, for ex, PL from shares sold closed to 0 balance, and avg
                    # price change from Shares sold Open to bal
                    # TODO: Get a an IB Statement with a flipped position 
                    tdf.at[xl, c.name] = tdf.at[xl, c.name] + " FLIPPED"

                    msg = '\nFound a flipper long to short.\n'
                    msg = msg + "Use this file for devel and testing if this is an IB statement\n"
                    print(msg)
                    for i, row in tdf.iterrows():
                        print(i, row)
                        print()
                elif not tdf.at[x0, c.side].startswith('B') and not tdf.at[xl, c.side].startswith('B'):
                    # print("found a flipper short to long")
                    tdf.iloc[-1][c.name] = tdf.iloc[-1][c.name] + " FLIPPED"
                    msg = '\nFound a flipper short to long.\n'
                    msg = msg + "Use this file for devel and testing if this is an IB statement\n"
                    print(msg)
                    for i, row in tdf.iterrows():
                        print(i, row)
                        print()





                #     for i, row in tdf.iterrows():
                #         print(i, row)
                #         print()

                # print()
            else:
                print('This should never run. What happned in postProcessing?',
                      'It means we have a non 0 balance at the end of a trade.(!?!)',
                      tdf.iloc[-1][c.bal], tdf.iloc[-1][c.name])
            if count == 0:
                dframe = tdf
            else:
                dframe = dframe.append(tdf)
        return ldf, dframe

    def addFinReqCol(self, dframe):
        '''
        Add the columns from FinReqCol that are not already in dframe. These are columns to determine the
        trade in which a  transaction belongs. It will probably include the FinReqCol dict values for the 
        keys: tix, start, bal, sum, dur, name
        :params dframe: The original DataFrame with the columns of the input file and including at least
                        all of the columns in ReqCol.columns
        :return dframe: A DataFrame that includes at least all of the columns in FinReqCol.columns 
        '''
        c = self._frc
        for l in c.columns:
            if l not in dframe.columns:
                dframe[l] = ''
        return dframe
