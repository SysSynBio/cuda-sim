import os
import re
from libsbml import *
from abcsysbio.relations import *
from Writer import Writer


class ODEPythonWriter(Writer):
    def __init__(self, parsedModel, outputPath=""):
        self.parsedModel = parsedModel
        self.out_file = open(os.path.join(outputPath, self.parsedModel.name + ".py"), "w")
        self.rename()

    def rename(self):
        """
        This function renames parts of self.parsedModel to meet the specific requirements of this writer.
        This behaviour replaces the previous approach of subclassing the parser to produce different results depending
        on the which writer was intended to be used.
        """

        # Remove any zero-padding from single-digit parameter names
        # This reverses any change applied by one of the CUDA writers
        for i in range(self.comp-1, len(self.parsedModel.parameterId)):
            old_name = self.parsedModel.parameterId[i]
            num = old_name[len('parameter'):]
            if len(num) > 1 and num[0] == '0':
                new_name = 'parameter' + str(num[1:])
                self.parsedModel.parameterId[i] = new_name
                self.parsedModel.rename_everywhere(old_name, new_name)

        # Remove any zero-padding from single-digit species names
        # This reverses any change applied by one of the CUDA writers
        for i in range(0, len(self.parsedModel.speciesId)):
            old_name = self.parsedModel.speciesId[i]
            num = old_name[len('species'):]
            if len(num) > 1 and num[0] == '0':
                new_name = 'species' + str(num[1:])
                self.parsedModel.speciesId[i] = new_name
                self.parsedModel.rename_everywhere(old_name, new_name)

    def write(self):
        p = re.compile('\s')
        # Import the necessaries
        self.out_file.write("from math import *\nfrom numpy import *\nfrom abcsysbio.relations import *\n\n")
        # The user-defined functions used in the model must be written in the file

        for i in range(len(self.parsedModel.listOfFunctions)):
            self.out_file.write("def ")
            self.out_file.write(self.parsedModel.listOfFunctions[i].getId())
            self.out_file.write("(")
            for j in range(self.parsedModel.listOfFunctions[i].getNumArguments()):
                self.out_file.write(self.parsedModel.functionArgument[i][j])
                self.out_file.write(",")
            self.out_file.write("):\n\n\toutput=")
            self.out_file.write(self.parsedModel.functionBody[i])
            self.out_file.write("\n\n\treturn output\n\n")

        # Write the modelfunction

        self.out_file.write("def modelfunction((")

        for i in range(len(self.parsedModel.species)):
            self.out_file.write(self.parsedModel.speciesId[i])
            self.out_file.write(",")
        for i in range(len(self.parsedModel.listOfParameter)):
            if not self.parsedModel.listOfParameter[i].getConstant():
                for k in range(len(self.parsedModel.listOfRules)):
                    if self.parsedModel.listOfRules[k].isRate() and self.parsedModel.ruleVariable[k] == \
                            self.parsedModel.parameterId[i]:
                        self.out_file.write(self.parsedModel.parameterId[i])
                        self.out_file.write(",")

        self.out_file.write("),time,parameter=(")
        for i in range(len(self.parsedModel.parameterId)):
            dontPrint = False
            if not self.parsedModel.listOfParameter[i].getConstant():
                for k in range(len(self.parsedModel.listOfRules)):
                    if self.parsedModel.listOfRules[k].isRate() and self.parsedModel.ruleVariable[k] == \
                            self.parsedModel.parameterId[i]:
                        dontPrint = True
            if not dontPrint:
                self.out_file.write(repr(self.parsedModel.parameter[i]))
                self.out_file.write(",")

        self.out_file.write(")):\n\n")

        counter = 0
        for i in range(len(self.parsedModel.parameterId)):
            dontPrint = False
            if not self.parsedModel.listOfParameter[i].getConstant():
                for k in range(len(self.parsedModel.listOfRules)):
                    if self.parsedModel.listOfRules[k].isRate() and self.parsedModel.ruleVariable[k] == self.parsedModel.parameterId[i]:
                        dontPrint = True
            if not dontPrint:
                self.out_file.write("\t" + self.parsedModel.parameterId[i] + "=parameter[" + repr(counter) + "]\n")
                counter += 1

        self.out_file.write("\n")

        # write the derivatives

        for i in range(self.parsedModel.numSpecies):
            self.out_file.write("\td_" + self.parsedModel.speciesId[i] + "=")
            if self.parsedModel.species[i].isSetCompartment():
                self.out_file.write("(")
            for k in range(self.parsedModel.numReactions):
                if not self.parsedModel.stoichiometricMatrix[i][k] == 0.0:
                    self.out_file.write("(")
                    self.out_file.write(repr(self.parsedModel.stoichiometricMatrix[i][k]))
                    self.out_file.write(")*(")
                    string = p.sub('', self.parsedModel.kineticLaw[k])
                    self.out_file.write(string)
                    self.out_file.write(")+")
            self.out_file.write("0")
            if self.parsedModel.species[i].isSetCompartment():
                self.out_file.write(")/")
                mySpeciesCompartment = self.parsedModel.species[i].getCompartment()
                for j in range(len(self.parsedModel.listOfParameter)):
                    if self.parsedModel.listOfParameter[j].getId() == mySpeciesCompartment:
                        self.out_file.write(self.parsedModel.parameterId[j])
                        break
            self.out_file.write("\n")

        for i in range(len(self.parsedModel.listOfRules)):
            if self.parsedModel.listOfRules[i].isRate():
                self.out_file.write("\td_")
                self.out_file.write(self.parsedModel.ruleVariable[i])
                self.out_file.write("=")
                self.out_file.write(self.parsedModel.ruleFormula[i])
                self.out_file.write("\n")

        self.out_file.write("\n\treturn(")

        for i in range(len(self.parsedModel.species)):
            self.out_file.write("d_" + self.parsedModel.speciesId[i])
            self.out_file.write(",")
        for i in range(len(self.parsedModel.listOfParameter)):
            if not self.parsedModel.listOfParameter[i].getConstant():
                for k in range(len(self.parsedModel.listOfRules)):
                    if self.parsedModel.listOfRules[k].isRate() and self.parsedModel.ruleVariable[k] == \
                            self.parsedModel.parameterId[i]:
                        self.out_file.write("d_" + self.parsedModel.parameterId[i])
                        self.out_file.write(",")

        self.out_file.write(")\n")

        # Write the rules
        self.out_file.write("\ndef rules((")

        for i in range(len(self.parsedModel.species)):
            ##if (self.parsedModel.species[i].getConstant() == False):
            self.out_file.write(self.parsedModel.speciesId[i])
            self.out_file.write(",")
        for i in range(len(self.parsedModel.listOfParameter)):
            if not self.parsedModel.listOfParameter[i].getConstant():
                for k in range(len(self.parsedModel.listOfRules)):
                    if self.parsedModel.listOfRules[k].isRate() and self.parsedModel.ruleVariable[k] == \
                            self.parsedModel.parameterId[i]:
                        self.out_file.write(self.parsedModel.parameterId[i])
                        self.out_file.write(",")
        self.out_file.write("),(")
        for i in range(len(self.parsedModel.parameterId)):
            dontPrint = False
            if not self.parsedModel.listOfParameter[i].getConstant():
                for k in range(len(self.parsedModel.listOfRules)):
                    if self.parsedModel.listOfRules[k].isRate() and self.parsedModel.ruleVariable[k] == \
                            self.parsedModel.parameterId[i]:
                        dontPrint = True
            if not dontPrint:
                self.out_file.write(self.parsedModel.parameterId[i])
                self.out_file.write(",")

        self.out_file.write("),time):\n\n")

        # Write the events

        for i in range(len(self.parsedModel.listOfEvents)):
            self.out_file.write("\tif ")
            self.out_file.write(mathMLConditionParser(self.parsedModel.eventCondition[i]))
            self.out_file.write(":\n")
            listOfAssignmentRules = self.parsedModel.listOfEvents[i].getListOfEventAssignments()
            for j in range(len(listOfAssignmentRules)):
                self.out_file.write("\t\t")
                self.out_file.write(self.parsedModel.eventVariable[i][j])
                self.out_file.write("=")
                self.out_file.write(self.parsedModel.eventFormula[i][j])
                self.out_file.write("\n")
            self.out_file.write("\n")

        self.out_file.write("\n")

        # write the rules

        for i in range(len(self.parsedModel.listOfRules)):
            if self.parsedModel.listOfRules[i].isAssignment():
                self.out_file.write("\t")
                self.out_file.write(self.parsedModel.ruleVariable[i])
                self.out_file.write("=")
                self.out_file.write(mathMLConditionParser(self.parsedModel.ruleFormula[i]))
                self.out_file.write("\n")

        self.out_file.write("\n\treturn((")
        for i in range(self.parsedModel.numSpecies):
            self.out_file.write(self.parsedModel.speciesId[i])
            self.out_file.write(",")
        for i in range(len(self.parsedModel.listOfParameter)):
            if not self.parsedModel.listOfParameter[i].getConstant():
                for k in range(len(self.parsedModel.listOfRules)):
                    if self.parsedModel.listOfRules[k].isRate() and self.parsedModel.ruleVariable[k] == \
                            self.parsedModel.parameterId[i]:
                        self.out_file.write(self.parsedModel.parameterId[i])
                        self.out_file.write(",")
        self.out_file.write("),(")

        for i in range(len(self.parsedModel.parameterId)):
            dontPrint = False
            if not self.parsedModel.listOfParameter[i].getConstant():
                for k in range(len(self.parsedModel.listOfRules)):
                    if self.parsedModel.listOfRules[k].isRate() and self.parsedModel.ruleVariable[k] == \
                            self.parsedModel.parameterId[i]:
                        dontPrint = True
            if not dontPrint:
                self.out_file.write(self.parsedModel.parameterId[i])
                self.out_file.write(",")
        self.out_file.write("))\n\n")
        self.out_file.close()
