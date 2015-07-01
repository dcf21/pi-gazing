# mod_time.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

import time,datetime

def UTC2datetime(utc):
  return datetime.datetime.fromtimestamp(float(utc))

def datetime2UTC(dt):
  if not dt: return 0
  return time.mktime( dt.timetuple() )

