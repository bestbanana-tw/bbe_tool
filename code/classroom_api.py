# from bbe_tool.code.classroom_api import CAPI
# from importlib import reload
# reload(CAPI)
# mApi = CAPI("/content/drive/MyDrive/course/1101/token.json","/content/drive/MyDrive/course/1101/credentials.json")
# courses = mApi.get_course()
# course_work = mApi.set_courseWork('369311598141')
# reviews = mApi.get_review(2)
# display(courses)
# print(course_work)
# print(reviews)

from __future__ import print_function
import os.path
import re
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import pandas as pd

class CAPI:
  SCOPES = ['https://www.googleapis.com/auth/classroom.courses.readonly',
          'https://www.googleapis.com/auth/classroom.rosters.readonly',
          'https://www.googleapis.com/auth/classroom.rosters',
          'https://www.googleapis.com/auth/classroom.student-submissions.students.readonly',
         ]

  def __init__(self,path_token,path_credential):
    creds = None
    if os.path.exists(path_token):
        creds = Credentials.from_authorized_user_file(path_token, self.SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                path_credential, self.SCOPES)
            creds = flow.run_local_server(port=0)
        with open(path_token, 'w') as token:
            token.write(creds.to_json())
    self.service = build('classroom', 'v1', credentials=creds)
  
  def get_course(self):
    r = self.service.courses().list(pageSize=30).execute()
    df_c = pd.DataFrame(r['courses'])
    df_c = df_c.loc[:,['id','name','section']]
    return df_c
  
  def set_courseWork(self,idCourse):
    self.id_course = idCourse
    l = self.service.courses().courseWork().list(pageSize=30,courseId=self.id_course).execute()['courseWork']
    df = pd.DataFrame(l)
    df = df.loc[:,['id','title','dueDate']]
    df.dueDate = df.dueDate.apply(lambda x: x['year']*10000 + x['month']*100 + x['day'])
    self.courseWork = df.sort_values('dueDate',ignore_index=True);
    return self.courseWork
  
  def set_students(self,token=""):
    r = self.service.courses().students().list(courseId=self.id_course,pageToken=token).execute()
    ls = r['students']
    if token == "":
      if 'nextPageToken' in r:
        self.students = [{'userId':v['userId'],'name':v['profile']['name']['fullName']} for v in ls] + self.set_students(r['nextPageToken'])
      else:
        self.students = [{'userId':v['userId'],'name':v['profile']['name']['fullName']} for v in ls]
      self.students = pd.DataFrame(self.students)
      self.students['name'] = self.students['name'].apply(lambda x: "".join(re.findall(r'[\u4e00-\u9fff]+',x)))
    else:
      if 'nextPageToken' in r: return [{'userId':v['userId'],'name':v['profile']['name']['fullName']} for v in ls] + self.set_students(r['nextPageToken'])
      else: return [{'userId':v['userId'],'name':v['profile']['name']['fullName']} for v in ls]
    
  def get_submissions(self,token="",i_work=0):
    r = self.service.courses().courseWork().studentSubmissions().list(courseId=self.id_course,courseWorkId=self.courseWork.loc[i_work,'id'],pageToken=token).execute()
    ls = r['studentSubmissions']
    if token == "":
      if 'nextPageToken' in r: ls = [{'userId':v['userId'],'state':v['state'],'late':v.get('late',False)} for v in ls] + self.get_submissions(token=r['nextPageToken'],i_work=i_work)
      else: ls = [{'userId':v['userId'],'state':v['state'],'late':v.get('late',False)} for v in ls]
      df = pd.DataFrame(ls)
      df[self.courseWork.loc[i_work,'title']] = df.apply(self.get_status,axis=1)
      return df.drop(['state','late'],axis=1)
    else:
      if 'nextPageToken' in r: return [{'userId':v['userId'],'state':v['state'],'late':v.get('late',False)} for v in ls] + self.get_submissions(token=r['nextPageToken'],i_work=i_work)
      else: return [{'userId':v['userId'],'state':v['state'],'late':v.get('late',False)} for v in ls]

  def get_status(self,x):
    if x['late']:
      if x['state'] == 'TURNED_IN': return 'late'
      else: return 'missing'
    else:
      if x['state'] == 'TURNED_IN': return 'ok'
      else: return 'yet'
  
  def set_submission(self):
    for i in range(len(self.courseWork)):
      self.students = self.students.merge(self.get_submissions(i_work=i),how="left",on="userId");

  def get_review(self,i_work=0,token=''):
    r = self.service.courses().courseWork().studentSubmissions().list(courseId=self.id_course,courseWorkId=self.courseWork.loc[i_work,'id'],pageToken=token).execute()
    ls = r['studentSubmissions']
    if token == "":
      if 'nextPageToken' in r: ls = [v.get("shortAnswerSubmission",{"answer":""}).get("answer","") for v in ls] + self.get_review(i_work=i_work,token=r['nextPageToken'])
      else: ls = [v.get("shortAnswerSubmission",{"answer":""}).get("answer","") for v in ls]
      return ls
    else:
      if 'nextPageToken' in r: return [v.get("shortAnswerSubmission",{"answer":""}).get("answer","") for v in ls] + self.get_review(i_work=i_work,token=r['nextPageToken'])
      else: return [v.get("shortAnswerSubmission",{"answer":""}).get("answer","") for v in ls]
