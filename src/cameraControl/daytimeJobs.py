#!../../virtual-env/bin/python
# daytimeJobs.py
# Meteor Pi, Cambridge Science Centre
# Dominic Ford

# This script is a very generic file processor. It looks for files in
# directories with given extensions, works out the time associated with each
# file from its filename, and performs predefined shell-commands on them if
# they are newer than a given high-water mark. The list of tasks to be
# performed is defined in <mod_daytimejobs>.

import os,time,sys,glob,datetime,operator
from math import *

import mod_log
from mod_log import logTxt,getUTC
from mod_settings import *
from mod_time import *
from mod_daytimejobs import *
import mod_astro
import mod_hwm

import meteorpi_fdb
fdb_handle = meteorpi_fdb.MeteorDatabase( DBPATH , FDBFILESTORE )

import mod_hardwareProps
hw_handle = mod_hardwareProps.hardwareProps( os.path.join( PYTHON_PATH, "..", "sensorProperties") )

import firebirdImport

pid = os.getpid()

# User should supply unix time on commandline at which we are to stop work
if len(sys.argv)!=3:
  print "Need to call daytimeJobs.py with clock offset, and an end time to tell it when it needs to quit by."
  sys.exit(1)

utcOffset = float(sys.argv[1])
quitTime  = float(sys.argv[2])
mod_log.toffset = utcOffset

logTxt("Running daytimeJobs. Need to quit at %s."%(datetime.datetime.fromtimestamp(quitTime).strftime('%Y-%m-%d %H:%M:%S')))

# Cleaning up any output files which are ahead of high water marks
logTxt("Cleaning up any output files which are ahead of high water marks")
import daytimeJobsClean

# Read our high water mark, and only analyse more recently-created data
cwd = os.getcwd()
os.chdir(DATA_PATH)
highWaterMarks = mod_hwm.fetchHWM()

def runJobGrp(jobGrp):
  if (len(jobGrp)< 1): return

  # Run shell commands associated with this group of jobs
  shellcmds = [ " ".join((job['cmd']%job['params']).split()) for job in jobGrp]
  for cmd in shellcmds:
    logTxt("Running command: %s"%cmd)
  if (len(shellcmds)==1):
    cmd = shellcmds[0]
  else:
    cmd = " & ".join(shellcmds) + " & wait"
  os.system(cmd)

  # Cascade metadata from input files to output files
  for job in jobGrp:
    m = job['params'] # Dictionary of metadata
    products = glob.glob("%(filename_out)s*%(outExt)s"%m)
    for product in products:
      stub = product[:-len(m['outExt'])]
      metadata = m['metadata'] # Metadata that was associated with input file
      metadata.update( mod_hwm.fileToDB( "%stxt"%stub ) )
      mod_hwm.DBtoFile( "%stxt"%stub , metadata )

# We raise this exception if we pass the time when we've been told we need to hand execution back
class TimeOut(Exception): pass

jobCounter=0

try:
  for taskGroup in dayTimeTasks:
    [HWMout, Nmax , taskList] = taskGroup;
    if HWMout not in highWaterMarks: highWaterMarks[HWMout]=0
    logTxt("Working on task group <%s>"%HWMout)
    HWMmargin = ((VIDEO_MAXRECTIME-5) if HWMout=="rawvideo" else 0.1)
    jobList = []
    for task in taskList:
      [inDir,outDirs,inExt,outExt,cmd] = task

      # Operate on any input files which are newer than HWM
      for dirName, subdirList, fileList in os.walk(inDir):
        for f in fileList:
          if quitTime and (getUTC()>quitTime): raise TimeOut
          inputFile = os.path.join(dirName,f)
          if ( f.endswith(".%s"%inExt) and (os.path.getsize(inputFile)>0) ): # File must have correct extension and non-zero size
            utc = mod_hwm.filenameToUTC(f)
            if (utc < 0): continue
            if (utc > highWaterMarks[HWMout]):

              jobCounter+=1;
              maskFile = "/tmp/triggermask_%d_%d.txt"%(os.getpid(),jobCounter)

              # Make dictionary of information about this job
              params = {'binary_path':BINARY_PATH ,
                        'input':inputFile ,
                        'outdir':outDirs[0] ,
                        'filename':f[:-(len(inExt)+1)] ,
                        'inExt':inExt ,
                        'outExt':outExt ,
                        'date':mod_hwm.fetchDayNameFromFilename(f) ,
                        'tstamp':utc ,
                        'cameraId':CAMERA_ID ,
                        'pid':pid ,
                        'triggermask': maskFile ,
                        'produceFilesWithoutLC': int(floor(utc % 120)==0) , # Produce non-lens-corrected images once every 2 mins
                        'opm': ('_openmax' if I_AM_A_RPI else '') ,
                       }
              params['filename_out'] = "%(outdir)s/%(date)s/%(filename)s"%params
              params['metadata']     = mod_hwm.fileToDB("%s.txt"%os.path.join(dirName,params['filename']))
              params.update( params['metadata'] )
              if 'fps' not in params: params['fps'] = mod_hardwareProps.fetchSensorData(fdb_handle,hw_handle,params['cameraId'],utc).fps

              # Read barrel-correction parameters
              lensData = mod_hardwareProps.fetchLensData(fdb_handle,hw_handle,params['cameraId'],utc)
              params['barrel_a'] = lensData.barrel_a
              params['barrel_b'] = lensData.barrel_b
              params['barrel_c'] = lensData.barrel_c

              # Fetch the status of the camera which made this observation
              cameraStatus = fdb_handle.get_camera_status(camera_id=params['cameraId'],time=UTC2datetime(utc))

              # Create clipping region mask file
              open(maskFile,"w").write( "\n\n".join(["\n".join(["%(x)d %(y)d"%p for p in pointList]) for pointList in cameraStatus.regions]) )

              # Insert metadata about position of Sun
              sunPos   = mod_astro.sunPos(utc)
              sunAltAz = mod_astro.altAz(sunPos[0],sunPos[1],utc,cameraStatus.location.latitude,cameraStatus.location.longitude)
              params['metadata']['sunRA']   = sunPos[0];
              params['metadata']['sunDecl'] = sunPos[1];
              params['metadata']['sunAlt']  = sunAltAz[0];
              params['metadata']['sunAz']   = sunAltAz[1];

              for outDir in outDirs: os.system("mkdir -p %s"%(os.path.join(outDir,params['date'])))
              jobList.append( {'utc':utc, 'cmd':cmd, 'params':params} )

    # Sort jobs in order of timestamp
    jobList.sort(key=operator.itemgetter('utc'))

    # Reset database high water marks
    camerasSeen=[]
    for job in jobList:
      cameraId = job['params']['cameraId']
      if cameraId not in camerasSeen:
        fdb_handle.set_high_water_mark( datetime.datetime.fromtimestamp(job['utc']) , cameraId )
        camerasSeen.append(cameraId);

    # Now do jobs in order, raising local high level water mark as we do each job
    jobGrp = []
    jobListLen = len(jobList)
    if jobListLen:
      for i in range(jobListLen):
        job=jobList[i]
        if quitTime and (getUTC()>quitTime): raise TimeOut
        jobGrp.append(job)
        if len(jobGrp)>=Nmax:
          runJobGrp(jobGrp)
          jobGrp = []
          if (i<jobListLen-1): highWaterMarks[HWMout] = jobList[i+1]['utc']-0.1 # Set HWM so that next job is marked as not yet done (it may have the same timestamp as present job)
          else               : highWaterMarks[HWMout] = job['utc']+HWMmargin # Set HWM so it's just past the job we've just done (0.1 sec)
      runJobGrp(jobGrp)
      highWaterMarks[HWMout] = jobList[jobListLen-1]['utc']+HWMmargin
      logTxt("Completed %d jobs"%len(jobList))
      os.system("rm -f /tmp/triggermask_%d_*"%(os.getpid())) # Delete trigger masks that we've finished with

except TimeOut:
      logTxt("Interrupting processing as we've run out of time")

# Write new list of local high water marks
mod_hwm.writeHWM(highWaterMarks)

# Import events into firebird database (unless we need to start observing again within next five minutes)
os.chdir(cwd)
if (not quitTime) or (quitTime - getUTC() > 300):
  logTxt("Importing events into firebird db")
  # firebirdImport.firebirdImport()

# Figure out orientation of camera -- this may take 5 hours!
if (not quitTime) or (quitTime - getUTC() > 3600*5):
  logTxt("Trying to determine orientation of camera")
  # orientationCalc.orientationCalc( CAMERA_ID , getUTC() , quitTime )

# Clean up temporary files
os.system("rm -Rf /tmp/tmp.* /tmp/dcf21_orientationCalc_*")
# os.system("rm -Rf %s/t*"%(DATA_PATH)) # This deletes all data not imported into firebird. Should be uncommented on production systems where unattended operation needed.

# Twiddle our thumbs
if quitTime:
  logTxt("Finished daytimeJobs. Now twiddling our thumbs for a bit.")
  timeLeft = quitTime - getUTC()
  if (timeLeft>0): time.sleep(timeLeft)
  logTxt("Finished daytimeJobs and also finished twiddling thumbs.")

