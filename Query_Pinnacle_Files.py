# -*- coding: utf-8 -*-
"""
Created on Fri Jul  7 11:59:18 2017

@author: BMAnderson
"""

import os,re,sys
import xlrd
import psycopg2
from ftplib import FTP
#import time

def getfile(remote_file,local_file):
    ftp=FTP('pinnacle-research')
    ftp.login('bmanderson','password') # Put your own UN and password in

    global ofile
    ofile=open(local_file,'wb')
    ftp.retrbinary('RETR '+remote_file,handleDownload)
    ofile.close()
    ftp.quit()
    
def getfiles(remote_file,local_file_dir):
    ftp=FTP('pinnacle-research')
    ftp.login('bmanderson','password') # Put your own UN and password in

    filenames = ftp.nlst(remote_file)
    for remote_file in filenames:
        k = remote_file.find('DICOM')
        newname = local_file_dir+'\\'+remote_file[k+6:len(remote_file)]
        global ofile
        ofile=open(newname,'wb')
        ftp.retrbinary('RETR '+remote_file,handleDownload)
        ofile.close()
        
    ftp.quit()

def handleDownload(block):
    ofile.write(block)

def DBQ2(conn_string,query,data):
    try:
        # get a connection, if a connect cannot be made an exception will be raised here
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor()
        cursor.execute(query,data)
        records = cursor.fetchall()
        return records
    except:
        # Get the most recent exception
        exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
        # Exit the script and print an error telling what happened.
        sys.exit("Database connection failed!\n ->%s" % (exceptionValue))

def main():
    #Initial
    ddir=r'C:\Data\CervicalPatients' # Where do you want your files to go?
    inst_id='xxx' # Put in your institute ID
    ex_file=r'S:\SHARED\Radiation physics\CECardenas\MRNs for Carlos.xlsx' # Load in the excel sheet with MRNs
    
    #Process Excel File
    #MRNs in 3rd Column
    wb=xlrd.open_workbook(ex_file)   
    sh=wb.sheet_by_index(0)
    col1=sh.col_values(2)
    for x in range(0,len(col1)):
        col1[x]=str(int(col1[x]))
        if '.' in col1[x]:
            result=re.search(r'^(.*?)\.',col1[x])
            col1[x]=result.group(1)
    
    #Process Queries
    cs = "host='pinnacle-research' dbname='court' user='user' password='password'" # Not actual credentials, change
    Fails=[]
    for i in col1:
        qy="SELECT patientid,patientpath FROM patient WHERE (medicalrecordnumber) = (%s) AND (institutionid) = (%s);"
        dats=(i,inst_id)
        data=DBQ2(cs,qy,dats)
    
        if len(data) > 1:
            print ('Multiple patients for %s'%str(i))
            print (data)
            Fails.append(i)
            continue
        elif len(data)==0:
            print ('No patient found for %s'%str(i))
            Fails.append(i)
            continue
        
        patientid=data[0][0]
        patientpath=data[0][1]
        
        qy="SELECT planid,primaryctimagesetid FROM plan WHERE (patientid) = (%s);"
        dats=(patientid,)
        data=DBQ2(cs,qy,dats)
        
        if len(data) > 1:
            print ('Multiple plans for %s'%str(i))
            print (data)
            #Fails.append(i)    #Took this out, I know we have multiple plans
            #continue
        elif len(data)==0:
            print ('No plans found for %{}'%str(i))
            Fails.append(i)
            continue
            
        
        #Create CAT-like entry   
        cat_dir=os.path.join(ddir,i) # i+time.strftime('_%Y%m%dT%H%M%S'), I took out the time to ensure no overlaps
        log_dir=os.path.join(cat_dir,'Log')
        data_dir=os.path.join(cat_dir,'MatlabData')
        plan_dir=os.path.join(cat_dir,'Plan')
        os.mkdir(cat_dir)
        os.mkdir(log_dir)
        os.mkdir(data_dir)
        os.mkdir(plan_dir)
        
        # Determine where my plan is (Plan BMA)
        err = 1
        for xxx in range(0,len(data)):
            planid = data[xxx][0]
            primaryctimagesetid=data[xxx][1] # Used to be 0
            remote_PlanInfo='/pinnacle_patient_expansion/court/'+patientpath+'/Plan_'+str(planid)+'/plan.PlanInfo'
            local_PlanInfo = os.path.join(cat_dir,'Test')
            getfile(remote_PlanInfo,local_PlanInfo)
            ofile=open(local_PlanInfo,'r')
            try:
                for ii in ofile:
                    if ii.find('BMA'):
                        err = 0
                        break
                
                if err == 0:
                    ofile.close()
                    break
            except ValueError:
                print('Something wrong with reading?')
                err = 1
                break
                
            ofile.close()
        if err == 1:
            Fails.append(i)
            print('Wrong plan for %s'%str(i))
            
        local_ImageSet_dir=os.path.join(cat_dir,'ImageSet_'+str(primaryctimagesetid)+'.DICOM')
        os.mkdir(local_ImageSet_dir)
        remote_ImageSet = '/pinnacle_patient_expansion/court/'+patientpath+'/'+'ImageSet_'+str(primaryctimagesetid)+'.DICOM'
        getfiles(remote_ImageSet,local_ImageSet_dir)
        
        subplan_dir=os.path.join(plan_dir,'Plan_'+str(planid))
        os.mkdir(subplan_dir)
        
        ImageHeader_base='ImageSet_'+str(primaryctimagesetid)+'.header'
        ImageInfo_base='ImageSet_'+str(primaryctimagesetid)+'.ImageInfo'
        ImageSet_base='ImageSet_'+str(primaryctimagesetid)+'.ImageSet'
        ImageRaw_base='ImageSet_'+str(primaryctimagesetid)+'.img'
        PatientFile_base='Patient'
        
        
        local_ImageHeader=os.path.join(plan_dir,ImageHeader_base)
        local_ImageInfo=os.path.join(plan_dir,ImageInfo_base)
        local_ImageSet=os.path.join(plan_dir,ImageSet_base)
        local_ImageRaw=os.path.join(plan_dir,ImageRaw_base)
        local_PatientFile=os.path.join(plan_dir,PatientFile_base)   
        
        remote_ImageHeader='/pinnacle_patient_expansion/court/'+patientpath+'/'+ImageHeader_base
        remote_ImageInfo='/pinnacle_patient_expansion/court/'+patientpath+'/'+ImageInfo_base
        remote_ImageSet='/pinnacle_patient_expansion/court/'+patientpath+'/'+ImageSet_base
        remote_ImageRaw='/pinnacle_patient_expansion/court/'+patientpath+'/'+ImageRaw_base
        remote_PatientFile='/pinnacle_patient_expansion/court/'+patientpath+'/'+PatientFile_base
        
        getfile(remote_ImageHeader,local_ImageHeader)
        getfile(remote_ImageInfo,local_ImageInfo)
        getfile(remote_ImageSet,local_ImageSet)
        getfile(remote_ImageRaw,local_ImageRaw)
        getfile(remote_PatientFile,local_PatientFile)
        
        local_Pinnacle=os.path.join(subplan_dir,'plan.Pinnacle')
        local_PlanRev=os.path.join(subplan_dir,'plan.PlanRev')
        local_Points=os.path.join(subplan_dir,'plan.Points')
        local_ROI=os.path.join(subplan_dir,'plan.roi')
        
        remote_Pinnacle='/pinnacle_patient_expansion/court/'+patientpath+'/Plan_'+str(planid)+'/plan.Pinnacle'
        remote_PlanRev='/pinnacle_patient_expansion/court/'+patientpath+'/Plan_'+str(planid)+'/plan.PlanRev'
        remote_Points='/pinnacle_patient_expansion/court/'+patientpath+'/Plan_'+str(planid)+'/plan.Points'
        remote_ROI='/pinnacle_patient_expansion/court/'+patientpath+'/Plan_'+str(planid)+'/plan.roi'
        
        getfile(remote_Pinnacle,local_Pinnacle)
        getfile(remote_PlanRev,local_PlanRev)
        getfile(remote_Points,local_Points)
        getfile(remote_ROI,local_ROI)    

if __name__ == '__main__':
    sys.exit(main())