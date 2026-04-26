from telnetlib import DO
import os
import ROOT
ROOT.gSystem.Load("libRooFit")
ROOT.gSystem.Load("libRooFitCore")

# Critical line — ROOT does NOT autoload this header!
#ROOT.gInterpreter.Declare('#include "RooChi2Var.h"')
import re
from ROOT import TCanvas, TFile, TH1F, TPaveText, RooRealVar, RooDataSet, RooWorkspace, RooDataHist, RooArgSet, RooChi2Var
from ROOT import gPad, gROOT
from utils.plot_library import DoResidualPlot, DoPullPlot, DoCorrMatPlot, DoAlicePlot, LoadStyle



from utils.plot_library import DoPullPlot, DoCorrMatPlot, DoAlicePlot, LoadStyle

class DQFitter:
    def __init__(self, fInName, fFolderName, fInputName, fOutPath, fitMethod, minDatasetRange, maxDatasetRange):
        self.fPdfDict          = {}
        self.fOutPath          = fOutPath
        self.fFileOutName      = "{}{}_{}_{}.root".format(fOutPath, fInputName, minDatasetRange, maxDatasetRange)
        self.fFileOut          = TFile(self.fFileOutName, "RECREATE")
        self.fFileIn           = TFile.Open(fInName)
        self.fFolderName       = fFolderName
        self.fInputName        = fInputName
        self.fInput            = 0
        self.fRooWorkspace     = RooWorkspace('w','workspace')
        self.fParNames         = []
        self.fFitMethod        = fitMethod
        self.fFitRangeMin      = []
        self.fFitRangeMax      = []
        self.fTrialName        = ""
        self.fTailsUsed        = ""
        self.fMCwidth          = ""
        self.fMinDatasetRange  = minDatasetRange
        self.fMaxDatasetRange  = maxDatasetRange
        self.fRooMass          = RooRealVar("m", "#it{M} (GeV/#it{c}^{2})", self.fMinDatasetRange, self.fMaxDatasetRange)
        self.fDoResidualPlot   = False
        self.fDoPullPlot       = False
        self.fDoCorrMatPlot    = False

    def SetFitConfig(self, pdfDict):
        '''
        Method set the configuration of the fit
        '''
        self.fPdfDict = pdfDict
        folderName = self.fFolderName.strip()  # from config; assume you assign it earlier
        
        if folderName:
           folder = self.fFileIn.Get(folderName)
           if not folder:
            raise RuntimeError(f"Folder '{folderName}' not found in ROOT file.")
           self.fInput = folder.Get(self.fInputName )
        else:
          self.fInput = self.fFileIn.Get(self.fInputName )

        if not self.fInput:
          raise RuntimeError(f"Histogram '{self.fInputName }' not found in ROOT file.")


      #  self.fInput = self.fFileIn.Get(self.fInputName)
        if not "TTree" in self.fInput.ClassName():
            self.fInput.Sumw2()
        self.fFitRangeMin = pdfDict["fitRangeMin"]
        self.fFitRangeMax = pdfDict["fitRangeMax"]
        self.fDoResidualPlot = pdfDict["doResidualPlot"]
        self.fDoPullPlot = pdfDict["doPullPlot"]
        self.fDoCorrMatPlot = pdfDict["doCorrMatPlot"]
        pdfList = []
        # 🔸 Prompt user to enter the systematics subfolder name interactively
        Tails_Used = input("Which tails did you use for the fitting(Data/MC):")
        self.fTailsUsed=Tails_Used.upper()
        MC_width= input("Enter the MC width ratio:")
        self.fMCwidth=MC_width
        for pdf in self.fPdfDict["pdf"][:-1]:
            self.fTrialName = self.fTrialName + pdf + "_"
        
        for i in range(0, len(self.fPdfDict["pdf"])):
            if not self.fPdfDict["pdf"][i] == "SUM":
                gROOT.ProcessLineSync(".x ../fit_library/{}Pdf.cxx+".format(self.fPdfDict["pdf"][i]))
        
        for i in range(0, len(self.fPdfDict["pdf"])):
            parVal = self.fPdfDict["parVal"][i]
            parLimMin = self.fPdfDict["parLimMin"][i]
            parLimMax = self.fPdfDict["parLimMax"][i]
            parName = self.fPdfDict["parName"][i]

            if not len(parVal) == len(parLimMin) == len(parLimMax) == len(parName):
                print("WARNING! Different size if the input parameters in the configuration")
                print(parVal)
                print(parLimMin)
                print(parLimMax)
                print(parName)
                exit()

            if not self.fPdfDict["pdf"][i] == "SUM":
                # Filling parameter list
                for j in range(0, len(parVal)):
                    if ("sum" in parName[j]) or ("prod" in parName[j]):
                        self.fRooWorkspace.factory("{}".format(parName[j]))
                        # Replace the exression of the parameter with the name of the parameter
                        r1 = parName[j].find("::") + 2 # give the index start :: which is 3 for sum::mean_Psi2s(mean_Jpsi, 0.584)
                        r2 = parName[j].find("(", r1) # this will give 16
                        parName[j] = parName[j][r1:r2]# this is slicing give mean_Psi2s
                        self.fRooWorkspace.factory("{}[{}]".format(parName[j], parVal[j]))
                    else:
                        if (parLimMin[j] == parLimMax[j]):
                            self.fRooWorkspace.factory("{}[{}]".format(parName[j], parVal[j]))
                        else:
                            self.fRooWorkspace.factory("{}[{},{},{}]".format(parName[j], parVal[j], parLimMin[j], parLimMax[j]))

                        self.fParNames.append(parName[j]) # only free parameters will be reported in the histogram of results

                # Define the pdf associating the parametes previously defined
                nameFunc = self.fPdfDict["pdf"][i]
                #nameFunc += "Pdf::{}Pdf(m[{},{}]".format(self.fPdfDict["pdfName"][i],self.fPdfDict["fitRangeMin"][0],self.fPdfDict["fitRangeMax"][0])
                nameFunc += "Pdf::{}Pdf(m[{},{}]".format(self.fPdfDict["pdfName"][i], self.fMinDatasetRange, self.fMaxDatasetRange)
                pdfList.append(self.fPdfDict["pdfName"][i])
                for j in range(0, len(parVal)):
                    #if "frac" in parName[j]:
                        #continue
                    nameFunc += ",{}".format(parName[j])
                nameFunc += ")"
                self.fRooWorkspace.factory(nameFunc)
            else:
                nameFunc = self.fPdfDict["pdf"][i]
                nameFunc += "::sum("
                for j in range(0, len(pdfList)):
                    #if ("prod" in parName[j]):
                        #self.fRooWorkspace.factory("{}".format(parName[j]))
                        # Replace the exression of the parameter with the name of the parameter
                        #r1 = parName[j].find("::") + 2
                        #r2 = parName[j].find("(", r1)
                        #parName[j] = parName[j][r1:r2]
                        #print("par name -> ", parName[j])
                        #nameFunc += "{}[{},{},{}]*{}Pdf".format(parName[j], parVal[j], parLimMin[j], parLimMax[j], pdfList[j])
                        #self.fParNames.append(parName[j])
                    #else:
                    nameFunc += "{}[{},{},{}]*{}Pdf".format(parName[j], parVal[j], parLimMin[j], parLimMax[j], pdfList[j])
                    self.fParNames.append(parName[j])
                    if not j == len(pdfList) - 1:
                        nameFunc += ","
                nameFunc += ")"
                #print(nameFunc)
                self.fRooWorkspace.factory(nameFunc)

    def CheckSignalTails(self, fitRangeMin, fitRangeMax):
        '''
        Method to plot the signal tail parameters
        '''
        self.fRooWorkspace.Print()
        self.fRooWorkspace.writeToFile("{}_tails.root".format(self.fTrialName))
        ROOT.gDirectory.Add(self.fRooWorkspace)

    def FitInvMassSpectrum(self, fitMethod, fitRangeMin, fitRangeMax):
        '''
        Method to perform the fit to the invariant mass spectrum
        '''
        LoadStyle()
        # Extract ME_2-8 pattern (general version)
        match = re.search(r"(ME_\d+-\d+)", self.fInputName)
        self.fRegion = match.group(1) if match else "UNKNOWN"

       # parName = self.fPdfDict["parName"]
       # if "prod::" in parName[2]:
        #    r_close = parName[2].rfind(")")
        #    r_comma = parName[2].rfind(",", 0, r_close)
        #    value_str = parName[2][r_comma+1:r_close].strip()
        trialName = self.fTrialName + "_" + str(fitRangeMin) + "_" + str(fitRangeMax)+"_"+ self.fTailsUsed+" tails_"+ self.fMCwidth +" width_" + self.fRegion
      #  trialName = self.fTrialName + "_" + str(fitRangeMin) + "_" + str(fitRangeMax)+ "_MC tails_"+"1.05 width_" + self.fRegion
        self.fRooWorkspace.Print()
        pdf = self.fRooWorkspace.pdf("sum")
        self.fRooMass.setRange("range", fitRangeMin, fitRangeMax)
        fRooPlot = self.fRooMass.frame(ROOT.RooFit.Title(trialName), ROOT.RooFit.Range("range"))
        fRooPlotExtra = self.fRooMass.frame(ROOT.RooFit.Title(trialName), ROOT.RooFit.Range("range"))
        fRooPlotOff = self.fRooMass.frame(ROOT.RooFit.Title(trialName))
        if "TTree" in self.fInput.ClassName():
            print("########### Perform unbinned fit ###########")
            rooDs = RooDataSet("data", "data", RooArgSet(self.fRooMass), ROOT.RooFit.Import(self.fInput))
        else:
            print("########### Perform binned fit ###########")
            rooDs = RooDataHist("data", "data", RooArgSet(self.fRooMass), ROOT.RooFit.Import(self.fInput))

        # Select the fit method
        if fitMethod == "likelyhood":
            print("########### Perform likelyhood fit ###########")
            rooFitRes = ROOT.RooFitResult(pdf.fitTo(rooDs, ROOT.RooFit.Range(fitRangeMin,fitRangeMax), ROOT.RooFit.Save()))
        if fitMethod == "chi2":
            print("########### Perform X2 fit ###########")
            rooFitRes = ROOT.RooFitResult(pdf.chi2FitTo(rooDs, ROOT.RooFit.Range(fitRangeMin,fitRangeMax),ROOT.RooFit.PrintLevel(-1), ROOT.RooFit.Save()))

        rooDs.plotOn(fRooPlot, ROOT.RooFit.MarkerStyle(20), ROOT.RooFit.MarkerSize(0.6), ROOT.RooFit.Range(fitRangeMin, fitRangeMax))
        pdf.plotOn(fRooPlot, ROOT.RooFit.LineColor(ROOT.kRed+1), ROOT.RooFit.LineWidth(2), ROOT.RooFit.Range(fitRangeMin, fitRangeMax))
        #pdf.plotOn(fRooPlot, ROOT.RooFit.VisualizeError(rooFitRes, 1), ROOT.RooFit.FillColor(ROOT.kRed-10), ROOT.RooFit.Range(fitRangeMin, fitRangeMax))
        rooDs.plotOn(fRooPlot, ROOT.RooFit.MarkerStyle(20), ROOT.RooFit.MarkerSize(0.6), ROOT.RooFit.Range(fitRangeMin, fitRangeMax))
        pdf.plotOn(fRooPlot, ROOT.RooFit.LineColor(ROOT.kRed+1), ROOT.RooFit.LineWidth(2), ROOT.RooFit.Range(fitRangeMin, fitRangeMax))
        for i in range(0, len(self.fPdfDict["pdf"])):
            if not self.fPdfDict["pdfName"][i] == "SUM":
                pdf.plotOn(fRooPlot, ROOT.RooFit.Components("{}Pdf".format(self.fPdfDict["pdfName"][i])), ROOT.RooFit.LineColor(self.fPdfDict["pdfColor"][i]), ROOT.RooFit.LineStyle(self.fPdfDict["pdfStyle"][i]), ROOT.RooFit.LineWidth(2), ROOT.RooFit.Range(fitRangeMin, fitRangeMax))
        
        reduced_chi2 = 0
        if "TTree" in self.fInput.ClassName():
            #Fit with RooChi2Var
            # To Do : Find a way to get the number of bins differently. The following is a temparary solution.
            # WARNING : The largest fit range has to come first in the config file otherwise it does not work
            # Convert unbinned dataset into binned dataset
            rooDsBinned = RooDataHist("rooDsBinned","binned version of rooDs",RooArgSet(self.fRooMass),rooDs)
            nbinsperGev = rooDsBinned.numEntries() / (self.fPdfDict["fitRangeMax"][0] - self.fPdfDict["fitRangeMin"][0])
            nBins = (fitRangeMax - fitRangeMin) * nbinsperGev
           # nBins = (fitRangeMax - fitRangeMin)/0.02
            print("number of bins={}".format(nBins))

            chi2 = ROOT.RooChi2Var("chi2", "chi2", pdf, rooDsBinned)
         #   chi2 = ROOT.RooChi2Var("chi2",                   # Parname
          #                         "chi2",                   # title
           #                         pdf,                      # RooAbsReal (typically a RooAbsPdf)
           #                         rooDsBinned,                    # RooDataHist
            #                        True,                     # extended (True/False)
             #                       ROOT.RooAbsData.SumW2     # error type
             #                          )

            nPars = rooFitRes.floatParsFinal().getSize()
            ndof = nBins - nPars
            reduced_chi2 = chi2.getVal() / ndof
        else:
            #Fit with RooChi2Var
            # To Do : Find a way to get the number of bins differently. The following is a temparary solution.
            # WARNING : The largest fit range has to come first in the config file otherwise it does not work
            rooDsBinned = RooDataHist("rooDsBinned","binned version of rooDs",RooArgSet(self.fRooMass),rooDs)
            nbinsperGev = rooDs.numEntries() / (self.fPdfDict["fitRangeMax"][0] - self.fPdfDict["fitRangeMin"][0])
            print("bin width={}".format(1/nbinsperGev))
            nBins = (fitRangeMax - fitRangeMin) * nbinsperGev
            print("number of bins={}".format(nBins))
          #  nBins = (fitRangeMax - fitRangeMin)/0.02
          #  chi2 = ROOT.RooChi2Var("chi2", "chi2", pdf, rooDsBinned)
            
            chi2 = pdf.createChi2(rooDs, 
                                   ROOT.RooFit.Extended(False),
                                   ROOT.RooFit.DataError(ROOT.RooAbsData.SumW2))

       #     chi2 = ROOT.RooChi2Var("chi2",                    # nameParName
            #                       "chi2",                    # title
            #                       pdf,                      # RooAbsReal (typically a RooAbsPdf)
            #                       rooDsBinned,              # RooDataHist
             #                      True,                     # extended (True/False)
              #                     ROOT.RooAbsData.SumW2     # error type
                #               )
                                       
            nPars = rooFitRes.floatParsFinal().getSize()
            ndof = nBins - nPars
            reduced_chi2 = chi2.getVal() / ndof

        index = 1
        nbins = len(self.fParNames) + 1  # one extra for chi2
        histResults = TH1F("fit_results_{}".format(trialName), "fit_results_{}".format(trialName), nbins, 0., nbins)

        for parName in self.fParNames:
          histResults.GetXaxis().SetBinLabel(index, parName)
          histResults.SetBinContent(index, self.fRooWorkspace.var(parName).getVal())
          histResults.SetBinError(index, self.fRooWorkspace.var(parName).getError())
          index += 1

        # Add chi2 in the last bin
        histResults.GetXaxis().SetBinLabel(index, "chi2")
        histResults.SetBinContent(index, reduced_chi2)


     # The part to calculate the Jpsi yield by integration
     # Access the signal PDF and mass variable
        mean = self.fRooWorkspace.var("mean_Jpsi").getVal()
        sigma = self.fRooWorkspace.var("width_Jpsi").getVal()

        low = mean - 3 * sigma
        high = mean + 3 * sigma
        
        # Get signal and background PDFs
        signal_pdf = self.fRooWorkspace.pdf("JpsiPdf")  
        bkg_pdf = self.fRooWorkspace.pdf("BkgPdf")
        
        mass = self.fRooWorkspace.var("m")

      # Define the mass range over which to integrate
        mass.setRange("sigRange", low , high)  # example range for J/ψ

        # Compute integrals in the 3σ window (normalized to unity)
        signal_frac = signal_pdf.createIntegral(mass, ROOT.RooFit.NormSet(mass), ROOT.RooFit.Range("sigRange")).getVal()
        bkg_frac = bkg_pdf.createIntegral(mass, ROOT.RooFit.NormSet(mass), ROOT.RooFit.Range("sigRange")).getVal()
        # Get the fitted values
        sig_norm = self.fRooWorkspace.var("sig_Jpsi").getVal()
        bkg_norm = self.fRooWorkspace.var("bkg").getVal()


      # Get the normalization (yield) parameter
        sig_Jpsi_val = sig_norm * signal_frac
        bkg_val = bkg_norm * bkg_frac
        
        print("fractional Yield of J/ψ in signal region = {:.2f}".format(signal_frac))
        print("fractional Yield of Background in signal region = {:.2f}".format(bkg_frac))

        print("Yield of J/ψ in signal region = {:.2f}".format(sig_Jpsi_val))
        print("Yield of Background in signal region = {:.2f}".format(bkg_val))
       
       


        extraText=[]
     #   extraText = TPaveText(0.6,0.55,0.95,0.75) # extra text for "propaganda" plots
      #  extraText.SetTextFont(42)
      #  extraText.SetTextSize(0.025)
       # extraText.SetFillColor(ROOT.kWhite)
        
        paveText = TPaveText(0.60, 0.45, 0.99, 0.94, "brNDC")
        paveText.SetTextFont(42)
        paveText.SetTextSize(0.025)
        paveText.SetFillColor(ROOT.kWhite)
        for parName in self.fParNames:
            paveText.AddText("{} = {:.4f} #pm {:.4f}".format(parName,self.fRooWorkspace.var(parName).getVal(), self.fRooWorkspace.var(parName).getError()))
            if self.fPdfDict["parForAlicePlot"].count(parName) > 0:
                text = self.fPdfDict["parNameForAlicePlot"][self.fPdfDict["parForAlicePlot"].index(parName)]
                if "sig" in parName:
                    extraText.append("{} = {:.0f} #pm {:.0f}".format(text, self.fRooWorkspace.var(parName).getVal(), self.fRooWorkspace.var(parName).getError()))
                else:
                    extraText.append("{} = {:.3f} #pm {:.4f} GeV".format(text, self.fRooWorkspace.var(parName).getVal(), self.fRooWorkspace.var(parName).getError()))
            for i in range(0, len(self.fPdfDict["pdfName"])):
                if self.fPdfDict["pdfName"][i] in parName:
                    (paveText.GetListOfLines().Last()).SetTextColor(self.fPdfDict["pdfColor"][i])

        # Add the chiSquare value
        paveText.AddText("n Par = %3.2f" % (nPars)) 
        paveText.AddText("n Bins = %3.2f" % (nBins))
        paveText.AddText("#bf{#chi^{2}/dof = %3.2f}" % reduced_chi2)
      
        fRooPlot.addObject(paveText)

        #for calculation of sig/background under 3sigma 
        
        # Optional: Get the errors too
        sig_Jpsi_err = self.fRooWorkspace.var("sig_Jpsi").getError()*signal_frac
        bkg_err = self.fRooWorkspace.var("bkg").getError()*bkg_frac

        # Compute the ratio and its uncertainty (via error propagation)
        ratio = sig_Jpsi_val / bkg_val
        ratio_err = ratio * ((sig_Jpsi_err / sig_Jpsi_val)**2 + (bkg_err / bkg_val)**2)**0.5

        # Print result
        print("sig_Jpsi / bkg = {:.3f} ± {:.3f}".format(ratio, ratio_err))
         # Significance: S / sqrt(S + B)

        significance = sig_Jpsi_val / ((sig_Jpsi_val + bkg_val) ** 0.5)
        dS = ((0.5 * sig_Jpsi_val + bkg_val) / (sig_Jpsi_val + bkg_val) ** 1.5) * sig_Jpsi_err
        # Error propagation
        dB = (-0.5 * sig_Jpsi_val / (sig_Jpsi_val + bkg_val) ** 1.5) * bkg_err

        significance_err = (dS ** 2 + dB ** 2) ** 0.5

        # Display
        print("S / sqrt(S + B) = {:.3f} ± {:.3f}".format(significance, significance_err))


        extraText.append("S/B_{{3#sigma}} = {:.2f} #pm {:.2f}".format(ratio,ratio_err) )
        extraText.append("#frac{{S}}{{#sqrt{{S + B}}}}_{{3#sigma}} = {:.2f}".format(significance))

        extraText.append("#chi^{2}/dof = %3.2f" % reduced_chi2)
     
        # Fit plot
        canvasFit = TCanvas("fit_plot_{}".format(trialName), "fit_plot_{}".format(trialName), 800, 600)
        canvasFit.SetLeftMargin(0.15)
        gPad.SetLeftMargin(0.15)
        fRooPlot.GetYaxis().SetTitleOffset(1.4)
        fRooPlot.Draw()
        
        # Print the fit result
        rooFitRes.Print()
        
        # Official fit plot
        if self.fPdfDict["doAlicePlot"]:
                DoAlicePlot(rooDs, pdf, fRooPlotOff, self.fPdfDict, self.fInputName, trialName, self.fOutPath, extraText)

        # Save results
        self.fFileOut.cd()
        histResults.Write()
        canvasFit.Write()

        rooDs.plotOn(fRooPlotExtra, ROOT.RooFit.DataError(ROOT.RooAbsData.SumW2), ROOT.RooFit.Range(fitRangeMin, fitRangeMax))
        pdf.plotOn(fRooPlotExtra, ROOT.RooFit.Range(fitRangeMin, fitRangeMax))

        # Residual plot
        if self.fDoResidualPlot:
            canvasResidual = DoResidualPlot(fRooPlotExtra, self.fRooMass, trialName)
            canvasResidual.Write()

        # Pull plot
        if self.fDoPullPlot:
            canvasPull = DoPullPlot(fRooPlotExtra, self.fRooMass, trialName)
            canvasPull.Write()

        # Correlation matrix plot
        if self.fDoCorrMatPlot:
            canvasCorrMat = DoCorrMatPlot(rooFitRes, trialName)
            canvasCorrMat.Write()

        rooFitRes.Write("info_fit_results_{}".format(trialName))
    
    def MultiTrial(self):
        '''
        WARNING! To be fixed, multiple fits do not work properly
        Method to perform a multi-trial fit
        '''
        for iRange in range(0, len(self.fFitRangeMin)):
            self.FitInvMassSpectrum(self.fFitMethod, self.fFitRangeMin[iRange], self.fFitRangeMax[iRange])
        self.fFileOut.Close()

        # Update file name
        trialName = self.fTrialName + "_" + str(self.fFitRangeMin[iRange]) + "_" + str(self.fFitRangeMax[iRange]) + ".root"
        oldFileOutName = self.fFileOutName
        newFileOutName = oldFileOutName.replace(str(self.fFitRangeMin[iRange]) + "_" + str(self.fFitRangeMax[iRange]) + ".root", trialName)
        os.rename(oldFileOutName, newFileOutName)

    def SingleFit(self, fitRangeMin, fitRangeMax):
        '''
        Method to perform a single fit (calling multi-trial from external script)
        '''
        self.FitInvMassSpectrum(self.fFitMethod, fitRangeMin, fitRangeMax)
        self.fFileOut.Close()

       
        trialName = self.fTrialName + "_" + str(fitRangeMin) + "_" + str(fitRangeMax)+ "_"+self.fTailsUsed+" tails_"+ self.fMCwidth + " width" + ".root"
       # trialName = self.fTrialName + "_" + str(fitRangeMin) + "_" + str(fitRangeMax) + ".root"
        oldFileOutName = self.fFileOutName
        newFileOutName = oldFileOutName.replace(str(fitRangeMin) + "_" + str(fitRangeMax) + ".root", trialName)
        os.rename(oldFileOutName, newFileOutName)

