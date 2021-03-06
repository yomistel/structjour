'''
Created on Aug 30, 2018

@author: Mike Petersen
'''
import unittest
import datetime as dt
import os
import types
import pandas as pd
from journalfiles import JournalFiles
# pylint: disable = C0103, W0703, E1121


def itsTheWeekend():
    '''
    This is a hacky thing to take care of (most) non trading days aka Saturday and Sunday and
    solely for my development environment. (if its a holiday you shouldn't be working anyway so it
    serves you right). Errors occur because on the weekend no trades.csv file was created. I don't
    want to alter the code to test the dynamic file selection on weekends so I will change the day.
    :return: The date of the last weekday to have occurred. AKA Friday if today is a weekend day.
            Otherwise returns today
    '''
    d = dt.date.today()
    idow = int(d.strftime("%w"))
    subtract = 1 if idow == 6 else 2 if idow == 0 else 0
    td = dt.timedelta(subtract)
    newdate = d - td
    return newdate
# itsTheWeekend().strftime("%A, %B %d, %y")


class TestJF(unittest.TestCase):
    '''
    Test the methods in JournalFiles
    '''

    def __init__(self, *args, **kwargs):
        '''
        When we initialze the object, ensure that we always run from src as the cwd
        '''
        super(TestJF, self).__init__(*args, **kwargs)
        ddiirr = os.path.dirname(__file__)
        theDir, dummy = os.path.split(ddiirr)
        os.chdir(theDir)

    def test_DefaultCreate(self):
        '''
        The succes of the default case relies on running it from the right directory
        '''
        cwd = os.getcwd()
        os.chdir("..")
        print("cwd:", os.getcwd())
        try:
            JournalFiles()
        except NameError:
            pass
        except Exception as ex:
            self.fail("Unexpected exception ", ex)
        else:
            self.fail("Failed to throw expected exception")

        #Go back to the original location for all the other tests
        os.chdir(cwd)

    def test_IndirCreate(self):
        '''
        Test JournalFiles. Explicit setting of an infile
        '''
        f = "Trades.8.ExcelEdited.csv"
        jf = JournalFiles(indir="data/", infile=f)

        self.assertEqual(os.path.realpath(os.path.join('data/', f)), os.path.realpath(
            jf.inpathfile), "Structjour failed to correctly set the input file")

    def testDevelDefaultCreate(self):
        '''
        Tests the default creation if its Monday to Friday.  Tests the previus Friday's date
        using param theDate otherwise. This will fail if you neglected to export the trades file
        on the given date
        '''
        if dt.date.today() == itsTheWeekend():
            #             jf=JournalFiles(mydevel=True)
            jf = JournalFiles(theDate=dt.date(2018, 8, 31), mydevel=True)
        else:
            try:
                FAIL = False
                theDate = itsTheWeekend()
                jf = JournalFiles(theDate=theDate, mydevel=True)
            except NameError:

                self.assertTrue(FAIL, 'Did you not export your DAS file on ' + theDate.strftime("%A, %B %d?"))


        self.assertTrue(os.path.exists(jf.indir),
                        "Have you reset the code the tnormal non-holiday code?")
        self.assertIsInstance(jf.theDate, dt.date,
                              "Failed to instantiate a the date object")
        #If no exceptions were created we passed
        self.assertIsInstance(
            jf, JournalFiles, "Failed to create instance of journalFile")

    def testDevelOutdirCreate(self):
        '''
        Tests the default creation of my development environment on a day that I created a trades
        file. Specifically test that the outdir exists in this environment.
        '''
        dout = "out/"
        din = "data/"

        if dt.date.today() == itsTheWeekend():
            jf = JournalFiles(indir=din, outdir=dout, mydevel=True)
        else:
            jf = JournalFiles(theDate=itsTheWeekend(),
                              indir=din, outdir=dout, mydevel=True)

        self.assertEqual(os.path.realpath('out/'), os.path.realpath(
            jf.outdir), "Structjour failed to correctly set the output directory")
        self.assertTrue(os.path.exists(jf.indir))
        self.assertIsInstance(jf.theDate, dt.date,
                              "Failed to instantiate a the date object")
        #If no exceptions were created we passed
        self.assertIsInstance(
            jf, JournalFiles, "Failed to create instance of journalFile")

    def testDevelIndirCreate(self):
        '''
        Tests the default creation of my development environment on a day that I created a trades
        file.  If its the weekend, it tests for Friday. If its a weekday holiday it will fail to
        find an input file and JournalFiles will raise NameError. (Go play, its a holiday).
        '''
        din = "data/"

        if dt.date.today() == itsTheWeekend():
            jf = JournalFiles(indir=din, mydevel=True)
        else:
            jf = JournalFiles(theDate=itsTheWeekend(), indir=din, mydevel=True)

        self.assertEqual(os.path.realpath(din),
                         os.path.realpath(jf.indir),
                         "Structjour failed to correctly set the input directory")
        self.assertTrue(os.path.exists(jf.indir))
        self.assertIsInstance(jf.theDate, dt.date,
                              "Failed to instantiate a the date object")
        #If no exceptions were created we passed
        self.assertIsInstance(
            jf, JournalFiles, "Failed to create instance of journalFile")

    def testDevelIndirOutdirCreate(self):
        '''
        Tests the default creation of my development environment with an explicit infile.
        Tests the explicit indir parameter
        '''
        dout = "out/"
        din = "data/"
        fin = 'Trades.8.WithBothHolds.csv'
        try:
            jf = JournalFiles(indir=din, infile=fin, outdir=dout, mydevel=True)
        except NameError as ex:
            print(ex)
            print("testDevelIndirOutdirCreat  requires ../{0}".format(fin))
            print("Do you have files in the right locations for this test?")

            # If we are here, This one or both should fail
            self.assertTrue(os.path.exists(jf.infile))
            self.assertTrue(os.path.exists(jf.outdir))

        self.assertEqual(os.path.realpath(dout),
                         os.path.realpath(jf.outdir),
                         "Structjour failed to correctly set the output directory")
        self.assertTrue(os.path.exists(jf.indir))
        self.assertIsInstance(jf.theDate, dt.date,
                              "Failed to instantiate a the date object")
        #If no exceptions were created we passed
        self.assertIsInstance(
            jf, JournalFiles, "Failed to create instance of journalFile")

    def testDevelInfileFail(self):
        '''
        Tests the default creation of my development environment on a day that I created a trades
        file. Explicitly tests that it fails if the infile does not exist
        '''
        dout = 'out/'
        din = 'data/'
        fin = 'SchmorgalStein.csv'

        # with self.assertRaises(NameError) :   This is method unreliable
        try:
            JournalFiles(indir=din, infile=fin, outdir=dout, mydevel=True)
        except NameError as ex:
            pass
        except Exception as ex:
            print(ex)
            self.fail("Unexpected exception ")
        else:
            self.fail("Failed to throw expected exception")

    def testDevelInDirFail(self):
        '''
        Tests JournalFile. Test explictitly for failure when the input file given does not exist
        '''
        din = r"..\monkeysPaw"


#         with self.assertRaises(NameError) :
        try:
            JournalFiles(indir=din, mydevel=True)
        except NameError:
            pass
        except Exception:
            self.fail("Unexpected exception from testDevelInDirFail")

        else:
            self.fail("Failed to throw expected exception")

    # def test_infile2Create(self):



def main():
    '''
    Run code outside of unittest framework
    Then run cl python -m unittest discovery
    '''
    f = TestJF()
    for name in dir(f):
        if name.startswith('test'):
            attr = getattr(f, name)

            if isinstance(attr, types.MethodType):
                attr()


def notmain():
    '''Run some local code'''
    t = TestJF()
    t.test_DefaultCreate()

def clstyle():
    '''Run unittests cl style. Can debug'''
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()

if __name__ == "__main__":
    # notmain()
    # main()
    clstyle()
