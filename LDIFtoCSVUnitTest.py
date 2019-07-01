import unittest
import LDIFtoCSV

import os


class LDIFAttributeChecks(unittest.TestCase):
  sampleLDIFLocation = "./TestLDIFs"  

  def testBasic(self):
    attributeDictionary = LDIFtoCSV.parseLDIFAttributes(os.path.join (self.sampleLDIFLocation, "Root.ldif"))
    print("Parsed attribute dictionary: " + repr(attributeDictionary))
    
    self.assertEqual(4, len(attributeDictionary))

    self.assertTrue("objectClass" in attributeDictionary)
    self.assertTrue("dc" in attributeDictionary)
    self.assertTrue("o" in attributeDictionary)
    self.assertTrue("dn" in attributeDictionary)

    self.assertEqual(2, attributeDictionary["objectClass"])
    self.assertEqual(1, attributeDictionary["dc"])
    self.assertEqual(1, attributeDictionary["o"])
    self.assertEqual(1, attributeDictionary["dn"])


  def testThreeEntries(self):
    attributeDictionary = LDIFtoCSV.parseLDIFAttributes(os.path.join (self.sampleLDIFLocation, "ThreeEntries.ldif"))

    self.assertEqual(4, len(attributeDictionary))

    self.assertTrue("objectclass" in attributeDictionary)
    self.assertTrue("cn" in attributeDictionary)
    self.assertTrue("sn" in attributeDictionary)

    self.assertEqual(1, attributeDictionary["objectclass"])
    self.assertEqual(2, attributeDictionary["cn"])
    self.assertEqual(1, attributeDictionary["sn"])

    print("Parsed attribute dictionary: " + repr(attributeDictionary))
    

if __name__ == "__main__":
  LDIFtoCSV.setupLogging()
  unittest.main()
