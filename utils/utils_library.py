from re import TEMPLATE
import matplotlib.pyplot as plt
import array as arr
import numpy as np
from array import array
import os
import sys
import math
import re
import uncertainties
from uncertainties import unumpy
from statistics import mean
import argparse
import ROOT
from os import path
from ROOT import TGraphErrors, TCanvas, TF1, TFile, TPaveText, TMath, TH1F, TH2F, TString, TLegend, TRatioPlot, TGaxis, TLine, TLatex
from ROOT import gROOT, gBenchmark, gPad, gStyle, kTRUE, kFALSE, kBlack, kRed, kGray, kDashed
from plot_library import LoadStyle, SetLatex

def StoreHistogramsFromFile(fIn, histType):
    '''
    Method which returns all the histograms of a certain class from a given file
    '''
    histArray = []
    for key in fIn.GetListOfKeys():
        kname = key.GetName()
        if (fIn.Get(kname).ClassName() == histType):
            histArray.append(fIn.Get(kname))
    return histArray

def ComputeRMS(parValArray):
    '''
    Method to evaluate the RMS of a sample ()
    '''
    mean = 0
    for parVal in parValArray:
        mean += parVal
    mean = mean / len(parValArray)
    stdDev = 0
    for parVal in parValArray:
        stdDev += (parVal - mean) * (parVal - mean)
    stdDev = math.sqrt(stdDev / len(parValArray))
    return stdDev

def PropagateErrorsOnRatio(val1, err1, val2, err2):
    var1 = unumpy.uarray(val1, err1)
    var2 = unumpy.uarray(val2, err2)
    ratio = var2 / var1
    arrVal = unumpy.nominal_values(ratio)
    arrErr = unumpy.std_devs(ratio)
    return arrVal, arrErr

def DoSystematics(path, varBin, parName, fOut):
    '''
    Method to evaluate the systematic errors from signal extraction
    '''
    LoadStyle()
    gStyle.SetOptStat(0)
    gStyle.SetOptFit(0)
    nameTrialArray = []
    trialIndexArray  = array( 'f', [] )
    parValArray  = array( 'f', [] )
    parErrArray = array( 'f', [] )

    fInNameAllList = os.listdir(path)

    # Filter files that contain varBin
    fInNameSelList = [
        os.path.join(path, fInName)
        for fInName in fInNameAllList
        if varBin in fInName and fInName.startswith("hMass") and fInName.endswith(".root")
    ]

    # Sort the list
    fInNameSelList.sort()

    # Print the sorted list
    print("Sorted selected ROOT files:")
    for fname in fInNameSelList:
       print(fname)


    index = 0.5
    for fInName in fInNameSelList:
        fIn = TFile.Open(fInName)
        for key in fIn.GetListOfKeys():
            kname = key.GetName()
            if "fit_results" in fIn.Get(kname).GetName():
                trialIndexArray.append(index)
                nameTrialArray.append(fIn.Get(kname).GetName().replace("fit_results_", ""))
                parValArray.append(fIn.Get(kname).GetBinContent(fIn.Get(kname).GetXaxis().FindBin(parName)))
                parErrArray.append(fIn.Get(kname).GetBinError(fIn.Get(kname).GetXaxis().FindBin(parName)))
                index = index + 1

    N = len(parValArray)
    print("Number of trials=", N)
    ex = np.zeros(N, dtype=np.float64)   # zero x-errors
    graParVal = TGraphErrors(N, trialIndexArray, parValArray, 0, parErrArray)
   # graParVal = TGraphErrors(len(parValArray), trialIndexArray, parValArray, ex, parErrArray)
    graParVal.SetMarkerStyle(24)
    graParVal.SetMarkerSize(1.2)
    graParVal.SetMarkerColor(kBlack)
    graParVal.SetLineColor(kBlack)

    funcParVal = TF1("funcParVal", "[0]", 0, len(trialIndexArray))
    graParVal.Fit(funcParVal, "R0Q")
    funcParVal.SetLineColor(kRed)
    funcParVal.SetLineWidth(2)

    #centralVal = funcParVal.GetParameter(0)
    #statError = funcParVal.GetParError(0)
    centralVal = mean(parValArray)
    #statError = np.std(parValArray, ddof=1) / np.sqrt(np.size(parValArray))
    statError = mean(parErrArray)
    systError = ComputeRMS(parValArray)

    trialIndexWidthArray = array( 'f', [] )
    parValSystArray = array( 'f', [] )
    parErrSystArray = array( 'f', [] )
    for i in range(0, len(parValArray)):
        trialIndexWidthArray.append(0.5)
        parValSystArray.append(centralVal)
        parErrSystArray.append(ComputeRMS(parValArray))

    graParSyst = TGraphErrors(len(parValArray), trialIndexArray, parValSystArray, trialIndexWidthArray, parErrSystArray)
    graParSyst.SetFillColorAlpha(kGray+1, 0.3)

    linePar = TLine(0, centralVal, len(trialIndexArray), centralVal)
    linePar.SetLineColor(kRed)
    linePar.SetLineWidth(2)

    lineParStatUp = TLine(0, centralVal + statError, len(trialIndexArray), centralVal + statError)
    lineParStatUp.SetLineStyle(kDashed)
    lineParStatUp.SetLineColor(kGray+1)

    lineParStatDown = TLine(0, centralVal - statError, len(trialIndexArray), centralVal - statError)
    lineParStatDown.SetLineStyle(kDashed)
    lineParStatDown.SetLineColor(kGray+1)

    latexTitle = TLatex()
    SetLatex(latexTitle)

    canvasParVal = TCanvas("canvasParVal", "canvasParVal", 800, 600)
    canvasParVal.SetBottomMargin(0.5)
    #histGrid = TH2F("histGrid", "", len(parValArray), 0, len(parValArray), 100, 0.7 * max(parValArray), 1.3 * max(parValArray))
    histGrid = TH2F("histGrid", "", len(parValArray), 0, len(parValArray), 100, centralVal-7*systError, centralVal+7*systError)
    indexLabel = 1
    for nameTrial in nameTrialArray:
        histGrid.GetXaxis().SetBinLabel(indexLabel, nameTrial)
        indexLabel += 1
    # Make X-axis labels horizontal and reduce font size
    histGrid.GetXaxis().LabelsOption("v")     # 'h' for horizontal, 'v' for vertical
    histGrid.GetXaxis().SetLabelSize(0.03)     # Reduce from default (~0.04)    
    histGrid.Draw("same")
    linePar.Draw("same")
    lineParStatUp.Draw("same")
    lineParStatDown.Draw("same")
    graParSyst.Draw("E2same")
    graParVal.Draw("EPsame")

    if "sig" in parName:
        if "Jpsi" in parName: latexParName = "N_{J/#psi}"
        if "Psi2s" in parName: latexParName = "N_{#psi(2S)}"
    if "chi2" in parName: latexParName = "#chi^{2}_{FIT}"

    latexTitle.DrawLatex(0.25, 0.85, "%s = #bf{%3.2f} #pm #bf{%3.2f} (%3.2f %%) #pm #bf{%3.2f} (%3.2f %%)" % (latexParName, centralVal, statError, (statError/centralVal)*100, systError, (systError/centralVal)*100))
    print("%s -> %1.0f ± %1.0f (%3.2f%%) ± %1.0f (%3.2f%%)" % (varBin, centralVal, statError, (statError/centralVal)*100, systError, (systError/centralVal)*100))

    #num = re.findall(r'[\d\.\d]+', varBin)
    #fOut.write("%3.2f %3.2f %3.2f %3.2f %3.2f \n" % (float(num[0]), float(num[1]), centralVal, statError, systError))
    fOut.write("%3.2f %3.2f %3.2f %3.2f %3.2f \n" % (0, 20, centralVal, statError, systError))
    canvasParVal.SaveAs("{}/systematics/{}_{}.pdf".format(path, varBin, parName))
    canvasParVal.SaveAs("{}/systematics/{}_{}.png".format(path, varBin, parName))


def CheckVariables(fInNames, parNames, xMin, xMax, fOutName, obs):
    '''
    Method to chech the variable evolution vs file in the list
    '''
    LoadStyle()
    gStyle.SetOptStat(0)
    gStyle.SetOptFit(0)

    xBins  = array( 'f', [] )
    xCentr  = array( 'f', [] )
    xError = array( 'f', [] )

    for i in range(0, len(xMin)):
        xCentr.append((xMax[i] + xMin[i]) / 2.)
        xError.append((xMax[i] - xMin[i]) / 2.)
        xBins.append(xMin[i])
    xBins.append(xMax[len(xMin)-1])
    

    fOut = TFile("{}myAnalysis_{}.root".format(fOutName,obs), "RECREATE")

    for parName in parNames:
        parValArray  = array( 'f', [] )
        parErrArray = array( 'f', [] )
        for fInName in fInNames:
            fIn = TFile.Open(fInName)
            for key in fIn.GetListOfKeys():
                kname = key.GetName()
                if "fit_results" in fIn.Get(kname).GetName():
                    parValArray.append(fIn.Get(kname).GetBinContent(fIn.Get(kname).GetXaxis().FindBin(parName)))
                    parErrArray.append(fIn.Get(kname).GetBinError(fIn.Get(kname).GetXaxis().FindBin(parName)))
        
        histParVal = TH1F("hist_{}".format(parName), "", len(xMin), xBins)

        for i in range(0, len(xMin)):
            histParVal.SetBinContent(i+1, parValArray[i])
            histParVal.SetBinError(i+1, parErrArray[i])
            
            
            
  # Instead of fInNames → just fInName (single string)
#  fIn = TFile.Open(fInName)


  # Then loop over histograms inside this file
#  for key in fIn.GetListOfKeys():
 #   kname = key.GetName()
  #  if "fit_results" in kname:
   #     hist = fIn.Get(kname)
    #    parValArray.append(hist.GetBinContent(hist.GetXaxis().FindBin(parName)))
     #   parErrArray.append(hist.GetBinError(hist.GetXaxis().FindBin(parName)))


        graParVal = TGraphErrors(len(parValArray), xCentr, parValArray, xError, parErrArray)
        graParVal.SetMarkerStyle(24)
        graParVal.SetMarkerSize(1.2)
        graParVal.SetMarkerColor(kBlack)
        graParVal.SetLineColor(kBlack)

        fOut.cd()
        histParVal.Write("hist_{}".format(parName))
        graParVal.Write("gra_{}".format(parName))

    

    #canvasParVal = TCanvas("canvasParVal", "canvasParVal", 800, 600)
    #histGrid = TH2F("histGrid", "", 100, xMin[0], xMax[len(xMax)-1], 100, 0.7 * min(parValArray), 1.3 * max(parValArray))
    #histGrid.Draw("same")
    #graParVal.Draw("EPsame")

def ToCArray(values, ctype="float", name="table", formatter=str, colcount=8):
    # apply formatting to each element
    values = [formatter(v) for v in values]

    # split into rows with up to `colcount` elements per row
    rows = [values[i:i+colcount] for i in range(0, len(values), colcount)]

    # separate elements with commas, separate rows with newlines
    body = ',\n    '.join([', '.join(r) for r in rows])

    # assemble components into the complete string
    return '{} {}[] = {{\n    {}}};'.format(ctype, name, body)


    
