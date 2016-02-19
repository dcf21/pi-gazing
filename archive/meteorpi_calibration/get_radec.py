import glob
import json

# Look up star positions
hipp_positions = {}
for line in open("/home/dcf21/svn_repository/StarPlot_ppl8/DataGenerated/HipparcosMerged/output/merged_hipp.dat"):
  words = line.split()
  hipp = int(words[12])
  ra = float(words[1])
  dec = float(words[2])
  mag = float(words[3])
  if (mag>5.5):
    continue
  hipp_positions[hipp] = [ra,dec]

files = glob.glob("*.starlist")

for item in files:
 descriptor = json.loads(open(item).read())
 star_list = []
 for star in descriptor['star_list']:
   words = star.split()
   hipp = int(words[2])
   if hipp not in hipp_positions:
     print  "Could not find star %d"%hd
     continue
   [ra,dec] = hipp_positions[hipp]
   star_list.append({'xpos':int(words[0]), 'ypos':int(words[1]) , 'ra':ra, 'dec':dec})
 descriptor['star_list'] = star_list
 print descriptor

