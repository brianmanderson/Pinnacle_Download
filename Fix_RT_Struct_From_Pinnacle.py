import time
import os
import dicom
import numpy as np


class Dicom_to_Imagestack:
    def __init__(self,dir_to_dicom):
        self.dir_to_dicom = dir_to_dicom
        self.make_array()

    def make_array(self):
        self.lstFilesDCM = []
        self.Dicom_info = []
        self.lstRSFiles = []
        i = 0
        for dirName, subdirList, fileList in os.walk(self.dir_to_dicom):
            for filename in fileList:
                i += 1
                try:
                    ds = dicom.read_file(os.path.join(dirName,filename))
                    if ds.Modality != 'RTSTRUCT':  # check whether the file's DICOM
                        self.lstFilesDCM.append(os.path.join(dirName, filename))
                        self.Dicom_info.append(ds)
                    elif ".dcm" in filename.lower() and ds.Modality == 'RTSTRUCT':
                        self.lstRSFiles.append(os.path.join(dirName, filename))
                except:
                    continue
        self.num_images = len(self.lstFilesDCM)
        self.get_images_and_mask(image_size=256)
        for self.lstRSFile in self.lstRSFiles:
            self.changetemplate()
            fid = open(self.dir_to_dicom + 'changed.txt', 'w+')
            fid.close()
            dicom.write_file(self.lstRSFile, self.RS_struct)

    def get_images_and_mask(self,image_size):
        self.slice_info = np.zeros([len(self.lstFilesDCM)])
        # Working on the RS structure now
        # Get ref file
        self.RefDs = dicom.read_file(self.lstFilesDCM[0])

        # The array is sized based on 'ConstPixelDims'
        # ArrayDicom = np.zeros(ConstPixelDims, dtype=RefDs.pixel_array.dtype)
        self.ArrayDicom = np.zeros([self.num_images,image_size, image_size, 3], dtype='float32')
        self.SOPClassUID_temp =[None] * self.num_images
        self.SOPClassUID = [None] * self.num_images
        # loop through all the DICOM files
        for filenameDCM in self.lstFilesDCM:
            # read the file
            ds = self.Dicom_info[self.lstFilesDCM.index(filenameDCM)]
            # store the raw image data
            # im[im<200] = 200 #Don't know what the hell these units are, but the min (air) is 0
            self.slice_info[self.lstFilesDCM.index(filenameDCM)] = round(ds.ImagePositionPatient[2],2)
            self.SOPClassUID_temp[self.lstFilesDCM.index(filenameDCM)] = ds.SOPInstanceUID
        indexes = [i[0] for i in sorted(enumerate(self.slice_info),key=lambda x:x[1])]
        self.slice_info = self.slice_info[indexes]
        i = 0
        for index in indexes:
            self.SOPClassUID[i] = self.SOPClassUID_temp[index]
            i += 1
        self.ds = ds

    def changetemplate(self):
        if self.lstRSFile:
            self.RS_struct = dicom.read_file(self.lstRSFile)
            self.template = 0
        else:
            self.template_dir = '\\\\MyMDAFiles\\ou-radonc\\File_share\\RO-Admin\\SHARED\\Radiation physics\\BMAnderson\\template_RS.dcm'
            self.RS_struct = dicom.read_file(self.template_dir)
            self.template = 1
        try:
            x = self.RS_struct.ROIContourSequence
        except:
            self.template = 1
            self.template_dir = '\\\\MyMDAFiles\\ou-radonc\\File_share\\RO-Admin\\SHARED\\Radiation physics\\BMAnderson\\template_RS.dcm'
            self.RS_struct = dicom.read_file(self.template_dir)
        keys = self.RS_struct.keys()
        for key in keys:
            #print(self.RS_struct[key].name)
            if self.RS_struct[key].name == 'Referenced Frame of Reference Sequence':
                break

        for i in range(len(self.RS_struct[key]._value[0].RTReferencedStudySequence[0].RTReferencedSeriesSequence[0].ContourImageSequence)):
            try:
                self.RS_struct[key]._value[0].RTReferencedStudySequence[0].RTReferencedSeriesSequence[
                    0].ContourImageSequence[i].ReferencedSOPInstanceUID = self.SOPClassUID[i]
            except:
                continue


        things_to_change = ['StudyInstanceUID','Specific Character Set','Instance Creation Date','Instance Creation Time','Study Date','Study Time',
                            'Accession Number','Study Description','Patient"s Name','Patient ID','Patients Birth Date','Patients Sex'
                            'Study Instance UID','Study ID','Frame of Reference UID']
        self.RS_struct.PatientsName = self.ds.PatientsName
        self.RS_struct.PatientsSex = self.ds.PatientsSex
        self.RS_struct.PatientsBirthDate = self.ds.PatientsBirthDate
        for key in keys:
            #print(self.RS_struct[key].name)
            if self.RS_struct[key].name in things_to_change:
                try:
                    self.RS_struct[key] = self.ds[key]
                except:
                    continue
        slice_list = self.slice_info.tolist()
        for i in range(len(self.RS_struct.ROIContourSequence)):
            for j in range(len(self.RS_struct.ROIContourSequence[i].ContourSequence)):
                slice = slice_list.index(round(self.RS_struct.ROIContourSequence[i].ContourSequence[j].ContourData[2],2))
                self.RS_struct.ROIContourSequence[i].ContourSequence[j].ContourImageSequence[0].ReferencedSOPInstanceUID = self.SOPClassUID[slice]
        return None
            # Get slice locations

def down_folder(input_path):
    dirs = []
    root = []
    for root, dirs, files in os.walk(input_path):
        break
    if input_path.find('NewDicom') != -1:
        pre_path = input_path.split('NewDicom')[0] + 'finished.txt'
        if not os.path.exists(input_path+'changed.txt') and input_path.find('new_RT') == -1 and os.path.exists(pre_path):
            print(input_path)
            try:
                Dicom_to_Imagestack(input_path)
            except:
                print(input_path + ' had an error...')
    for dir in dirs:
        down_folder(root + dir + '\\')
    return None

go = True
while go:
    print('Checking')
    down_folder('L:\\Morfeus\\BMAnderson\\MRI_Cervix_Patients\\')
    print('Finished it.. Sleeping')
    time.sleep(600)

