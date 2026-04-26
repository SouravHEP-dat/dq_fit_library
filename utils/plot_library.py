import matplotlib.pyplot as plt
import array as arr
import numpy as np
import os
import sys
import argparse
import ROOT
from os import path
from ROOT import TCanvas, TLatex, TF1, TFile, TPaveText, TMath, TH1F, TString, TLegend, TRatioPlot, TGaxis
from ROOT import gROOT, gBenchmark, gPad, gStyle, kTRUE, kFALSE

def SetLatex(latex):
    latex.SetTextSize(0.035)
    latex.SetNDC()
    latex.SetTextFont(42)

def SetLegend(legend):
    legend.SetBorderSize(0)
    legend.SetFillColor(10)
    legend.SetFillStyle(1)
    legend.SetLineStyle(0)
    legend.SetLineColor(0)
    legend.SetTextFont(42)
    legend.SetTextSize(0.04)

def SetGraStat(gra, style, color):
    gra.SetMarkerStyle(style)
    gra.SetMarkerColor(color)
    gra.SetLineWidth(2)
    gra.SetLineColor(color)

def SetGraSyst(gra, style, color):
    gra.SetMarkerStyle(style)
    gra.SetMarkerColor(color)
    gra.SetLineWidth(2)
    gra.SetLineColor(color)
    gra.SetFillStyle(0)

def LoadStyle():
    gStyle.SetPadLeftMargin(0.15)
    gStyle.SetPadBottomMargin(0.15)
    gStyle.SetPadTopMargin(0.05)
    gStyle.SetPadRightMargin(0.05)
    gStyle.SetEndErrorSize(0.0)
    gStyle.SetTitleSize(0.05,"X")
    gStyle.SetTitleSize(0.045,"Y")
    gStyle.SetLabelSize(0.045,"X")
    gStyle.SetLabelSize(0.045,"Y")
    gStyle.SetTitleOffset(1.2,"X")
    gStyle.SetTitleOffset(1.35,"Y")

def DrawRatioPlot(hist1, hist2, dirName, plotName):
    gStyle.SetOptStat(0)
    canvas = TCanvas("canvas", "A ratio example")
    ratioPlot = TRatioPlot(hist1, hist2)
    ratioPlot.Draw()
    ratioPlot.GetLowerRefYaxis().SetRangeUser(0.,2.)
    ratioPlot.GetLowerRefYaxis().SetLabelSize(0.025)

    tmpPad = ratioPlot.GetUpperPad()

    legend = TLegend(0.15, 0.75, 0.35, 0.89, " ", "brNDC")
    legend.SetBorderSize(0)
    legend.SetFillColor(10)
    legend.SetFillStyle(1)
    legend.SetLineStyle(0)
    legend.SetLineColor(0)
    legend.SetTextFont(42)
    legend.SetTextSize(0.03)
    if (plotName.Contains("DCA")):
        legend.AddEntry(hist1, "MC (mean = %3.2f)" % hist1.GetMean(), "PL")
        legend.AddEntry(hist2, "Data (mean = %3.2f)" % hist2.GetMean(), "PL")
    else:
        legend.AddEntry(hist1, "MC", "PL")
        legend.AddEntry(hist2, "Data", "PL")

    legend.Draw()

    tmpPad.Modified() 
    tmpPad.Update() 

    canvas.Update()
    canvas.SaveAs("%s/ratio_%s.pdf" % dirName.Data(), plotName.Data())


def DoResidualPlot(rooPlot, rooVar, trialName):
    rooHistResidual = rooPlot.residHist()
    rooPlotResidual = rooVar.frame(ROOT.RooFit.Title("Residual Distribution"))
    rooPlotResidual.addPlotable(rooHistResidual,"P")
    canvasResidual = TCanvas("residual_plot_{}".format(trialName), "resisual_plot_{}".format(trialName), 600, 600)
    canvasResidual.SetLeftMargin(0.15)
    rooPlotResidual.GetYaxis().SetTitleOffset(1.4)
    rooPlotResidual.Draw()
    return canvasResidual

def DoPullPlot(rooPlot, rooVar, trialName):
    rooHistPull = rooPlot.pullHist()
    rooPlotPull = rooVar.frame(ROOT.RooFit.Title("Pull Distribution"))
    rooPlotPull.addPlotable(rooHistPull,"P")
    canvasPull = TCanvas("pull_plot_{}".format(trialName), "pull_plot_{}".format(trialName), 600, 600)
    canvasPull.SetLeftMargin(0.15)
    rooPlotPull.GetYaxis().SetTitleOffset(1.4)
    rooPlotPull.Draw()
    return canvasPull

def DoCorrMatPlot(rooFitRes, trialName):
    histCorrMat = rooFitRes.correlationHist("hist_corr_mat_{}".format(trialName))
    canvasCorrMat = TCanvas("corr_mat_{}".format(trialName), "corr_mat_{}".format(trialName), 600, 600)
    histCorrMat.Draw("COLZ")
    return canvasCorrMat

def DoAlicePlot(rooDs, pdf, rooPlot, pdfDict, histName, trialName, path, extraText):
    # Official fit plot
    rooDs.plotOn(rooPlot, ROOT.RooFit.Name("Data"), ROOT.RooFit.MarkerStyle(20), ROOT.RooFit.MarkerSize(0.5))
    pdf.plotOn(rooPlot, ROOT.RooFit.Name("Fit"), ROOT.RooFit.LineColor(ROOT.kRed+1), ROOT.RooFit.LineWidth(2))
    for i in range(0, len(pdfDict["pdf"])):
        if not pdfDict["pdfName"][i] == "SUM":
            pdf.plotOn(rooPlot, ROOT.RooFit.Components("{}Pdf".format(pdfDict["pdfName"][i])), ROOT.RooFit.Name(pdfDict["pdfNameForLegend"][i]), ROOT.RooFit.LineColor(pdfDict["pdfColor"][i]), ROOT.RooFit.LineStyle(pdfDict["pdfStyle"][i]), ROOT.RooFit.LineWidth(2))
     # Assuming `rooPlot` is your RooPlot object and `canvas` is your TCanvas

    # Get non-zero minimum and maximum Y values
    y_max = rooPlot.GetMaximum()   
    print("print the y_max={}".format(y_max))
    y_min = rooPlot.GetMinimum(0)   # 0 means skip zeros
    print("print the y_min={}".format(y_min))
    # Ensure y_min is strictly positive for log scale
    if y_min <= 0:
         y_min = 1e-2  # or another small positive value based on your data
    # Set Y axis range
   # rooPlot.SetAxisRange(1e1,1e5, "Y")
    rooPlot.GetYaxis().SetRangeUser(-1000.0, y_max+7000.0)
   # rooPlot.SetMinimum(y_min)
   # rooPlot.SetMaximum(y_max)
    


    legend = ROOT.TLegend(0.5, 0.70, 0.65, 0.87, " ", "brNDC")
    legend.SetBorderSize(0)
    legend.SetFillColor(10)
    legend.SetFillStyle(0)
    legend.SetLineStyle(0)
    legend.SetLineColor(0)
    legend.SetTextFont(42)
    legend.SetTextSize(0.04)
    legend.AddEntry(rooPlot.findObject("Data"), "Data", "P")
    legend.AddEntry(rooPlot.findObject("Fit"), "Fit", "L")
    for i in range(0, len(pdfDict["pdf"])):
        if not pdfDict["pdfName"][i] == "SUM":
            legend.AddEntry(rooPlot.findObject(pdfDict["pdfNameForLegend"][i]), pdfDict["pdfNameForLegend"][i], "L")

    rooPlot.SetTitle("")

    canvasALICE = TCanvas("ALICE_{}_{}".format(histName, trialName), "ALICE_{}_{}".format(histName, trialName), 800, 600)
  #  canvasALICE.SetLogy(True)
    canvasALICE.Update()
    canvasALICE.SetLeftMargin(0.15)
    rooPlot.Draw()

    legend.Draw("same")

    letexTitle = TLatex()
    letexTitle.SetTextSize(0.035)
    letexTitle.SetNDC()
    letexTitle.SetTextFont(32)
    for i in range(0, len(pdfDict["text"])):
        letexTitle.DrawLatex(pdfDict["text"][i][0], pdfDict["text"][i][1], pdfDict["text"][i][2])

  #  letexExtraText = TLatex()
  #  letexExtraText.SetTextSize(0.04)
  #  letexExtraText.SetTextColor(ROOT.kGray+3)
   # letexExtraText.SetNDC()
   # letexExtraText.SetTextFont(42)
  #  lineIndex = 0
   # for line in extraText:
    #    letexExtraText.DrawLatex(0.65, 0.52 - lineIndex, line)
    #    lineIndex = lineIndex + 0.06


    # Initialize the legend (position it as you prefer)
    legend1 = ROOT.TLegend(0.65, 0.55, 0.85, 0.95, " ", "brNDC")
    legend1.SetTextFont(42)
    legend1.SetTextSize(0.03)
    legend1.SetFillColor(0)
    legend1.SetFillStyle(0)
    legend1.SetBorderSize(0)

   # Add each line as a non-drawable text entry
    for line in extraText:
       legend1.AddEntry(0, line, "")

    # Draw legend on the canvas
    legend1.Draw()

    if not os.path.isdir(path):
        os.system("mkdir -p %s" % (path))

    canvasALICE.SaveAs("{}ALICE_{}_{}.pdf".format(path, histName, trialName))
    canvasALICE.SaveAs("{}ALICE_{}_{}.png".format(path, histName, trialName))
    canvasALICE.SaveAs("{}ALICE_{}_{}.root".format(path, histName, trialName))
